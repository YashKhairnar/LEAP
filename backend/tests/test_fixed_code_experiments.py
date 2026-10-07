import contextlib
from dataclasses import asdict
import importlib.util
import io
import json
import unittest
from unittest.mock import patch

from app.execution.cells import validate_code
from app.execution.datasets import dataset_for_task
from app.tutoring.lesson_code import (
    FIXED_CODE_EXPERIMENTS,
    FIXED_LESSON_CODE,
    fixed_code_experiments,
    fixed_lesson_code,
    fixed_lesson_prerequisites,
)
from app.models import TutorGenerationRequest
from app.tutoring.generator import _lesson_with_fixed_code, generate_tutor_content
from test_lesson_structure import SECTION_ORDER, lesson_with


class FixedCodeExperimentTests(unittest.TestCase):
    def test_every_stage_has_valid_fixed_experiments(self):
        self.assertEqual(set(FIXED_CODE_EXPERIMENTS), set(FIXED_LESSON_CODE))
        for task, stages in FIXED_LESSON_CODE.items():
            self.assertEqual(set(FIXED_CODE_EXPERIMENTS[task]), set(stages))
            for stage, canonical in stages.items():
                with self.subTest(task=task, stage=stage):
                    experiments = fixed_code_experiments(task, stage)
                    self.assertGreaterEqual(len(experiments), 1)
                    lesson = _lesson_with_fixed_code(lesson_with(SECTION_ORDER), task, stage)
                    self.assertEqual(lesson.model_dump()["try_this"], [asdict(item) for item in experiments])
                    for experiment in experiments:
                        self.assertEqual(canonical.code.count(experiment.find), 1)
                        validate_code(canonical.code.replace(experiment.find, experiment.replace, 1))

    def test_sentiment_alias_uses_the_same_experiments(self):
        for stage in FIXED_LESSON_CODE["sentiment_classification"]:
            self.assertEqual(fixed_code_experiments("sentiment", stage), fixed_code_experiments("sentiment_classification", stage))

    def test_unknown_stage_does_not_silently_get_unrelated_experiments(self):
        with self.assertRaisesRegex(ValueError, "no fixed code experiments"):
            fixed_code_experiments("cnn", "missing")

    def test_fixed_content_does_not_mutate_the_source_lesson(self):
        source = lesson_with(SECTION_ORDER)
        before = json.dumps(source)
        _lesson_with_fixed_code(source, "sentiment", "model_training")
        self.assertEqual(json.dumps(source), before)

    def test_generated_and_reused_lessons_use_server_owned_experiments(self):
        question = {
            "question": "What does fitting use?", "options": ["Training examples", "Test examples", "No examples"],
            "expected_answer": "Training examples", "hint": "Keep testing separate.",
            "explanation": "Fitting uses the training examples.", "concepts_tested": ["training"],
        }
        for reuse in (False, True):
            with self.subTest(reuse=reuse):
                source = lesson_with(SECTION_ORDER)
                context = TutorGenerationRequest(
                    task="sentiment", stage="model_training", step="connect",
                    action_type="connect.concept_matching", reference_prompt="Explain training.",
                    existing_lesson=source if reuse else None,
                )
                generated = question if reuse else {"lesson": source, "question": question}
                response = io.BytesIO(json.dumps({"message": {"content": json.dumps(generated)}}).encode())
                with patch("app.tutoring.generator.urlopen", return_value=response) as request:
                    result = generate_tutor_content(context, "test-fixed-experiments")
                expected = [asdict(item) for item in fixed_code_experiments("sentiment", "model_training")]
                self.assertEqual(result.lesson.model_dump()["try_this"], expected)
                self.assertEqual(result.lesson.sections[3].code, fixed_lesson_code("sentiment", "model_training").code)
                payload = json.loads(request.call_args.args[0].data)
                if not reuse:
                    self.assertNotIn("try_this", payload["format"]["properties"]["lesson"]["properties"])
                supplied_context = json.loads(payload["messages"][1]["content"].split("\n", 1)[1])
                self.assertEqual(supplied_context["fixed_code_experiments"], expected)
                if reuse:
                    self.assertEqual(supplied_context["fixed_stage_lesson"]["try_this"], expected)

    @unittest.skipUnless(
        all(importlib.util.find_spec(name) for name in ("pandas", "numpy", "sklearn", "torch")),
        "Requires the lesson execution packages",
    )
    def test_every_experiment_runs_with_canonical_prerequisites(self):
        try:
            import pandas as pd
            import sklearn  # noqa: F401 — verify the execution packages can load
            import torch
        except (ImportError, OSError) as error:
            self.skipTest(f"Lesson execution packages cannot load: {error}")

        read_csv = pd.read_csv
        original_threads = torch.get_num_threads()
        torch.set_num_threads(1)
        self.addCleanup(torch.set_num_threads, original_threads)
        for task, stages in FIXED_LESSON_CODE.items():
            dataset = dataset_for_task(task)
            for stage, canonical in stages.items():
                for experiment in fixed_code_experiments(task, stage):
                    with self.subTest(task=task, stage=stage, experiment=experiment.title):
                        namespace = {}
                        output = io.StringIO()
                        # Redirect only the known runtime filename to its checked-in CSV.
                        def load_dataset(filename):
                            self.assertEqual(filename, dataset.runtime_filename)
                            return read_csv(dataset.path)

                        with patch.object(pd, "read_csv", side_effect=load_dataset):
                            with contextlib.redirect_stdout(io.StringIO()):
                                for prerequisite in fixed_lesson_prerequisites(task, stage):
                                    exec(prerequisite, namespace)
                            with contextlib.redirect_stdout(output):
                                exec(canonical.code.replace(experiment.find, experiment.replace, 1), namespace)
                        self.assertTrue(output.getvalue().strip(), "An experiment must make its effect visible")
                        if stage == "tfidf_vectorization":
                            self.assertEqual(namespace["X_train_tfidf"].shape[1], 100)
                            self.assertEqual(namespace["X_test_tfidf"].shape[1], 100)
                        if stage == "train_test_split":
                            self.assertEqual((len(namespace["X_train"]), len(namespace["X_test"])), (2100, 900))
                        if stage == "normalize_split":
                            self.assertEqual(namespace["train_loader"].batch_size, 32)
                            self.assertEqual(len(namespace["train_loader"]), 141)


if __name__ == "__main__":
    unittest.main()
