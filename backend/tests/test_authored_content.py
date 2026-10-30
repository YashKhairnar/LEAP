import re
import unittest

from app.assessments.bank import QUESTION_BANK
from app.assessments.final_bank import FINAL_QUESTION_BANK

from app.models import InstructionalActionType, TutorGenerationRequest
from app.tutoring.authored_content import AUTHORED_CONTENT_VERSION, STAGES_BY_TASK, authored_tutor_content
from app.tutoring.lesson_code import FIXED_LESSON_CODE


class AuthoredContentTests(unittest.TestCase):
    def test_shortened_answers_still_have_one_unambiguous_correct_option(self):
        for task, stages in STAGES_BY_TASK.items():
            for stage in stages:
                for action in InstructionalActionType:
                    request = TutorGenerationRequest(task=task, stage=stage, step=action.value.split(".")[0], action_type=action, reference_prompt="test")
                    content = authored_tutor_content(request).content
                    with self.subTest(task=task, stage=stage, action=action):
                        self.assertEqual(len(content.options), len(set(content.options)))
                        self.assertEqual(content.options.count(content.expected_answer), 1)
                        self.assertTrue(all(len(option.split()) <= 10 for option in content.options))

    def test_everyday_analogies_do_not_require_java_knowledge(self):
        for task, stages in STAGES_BY_TASK.items():
            for stage in stages:
                request = TutorGenerationRequest(task=task, stage=stage, step="connect", action_type=InstructionalActionType.CONNECT_CONCEPT_MATCHING, reference_prompt="test", analogy_preference="everyday")
                analogy = authored_tutor_content(request).lesson.sections[1]
                self.assertEqual(analogy.type, "analogy")
                self.assertNotIn("Java", analogy.body)

    def test_all_sentiment_stages_and_steps_have_valid_content(self):
        for stage in FIXED_LESSON_CODE["sentiment_classification"]:
            for action in InstructionalActionType:
                if action.value.split(".", 1)[0] not in {"connect", "practice", "review"}:
                    continue
                with self.subTest(stage=stage, action=action.value):
                    request = TutorGenerationRequest(
                        task="sentiment_classification", stage=stage,
                        step=action.value.split(".", 1)[0], action_type=action,
                        reference_prompt="authored test",
                    )
                    result = authored_tutor_content(request)
                    self.assertEqual(result.model, "authored")
                    self.assertEqual(result.prompt_version, AUTHORED_CONTENT_VERSION)
                    self.assertEqual(len(result.lesson.sections), 6)
                    self.assertIn(result.content.expected_answer, result.content.options)

    def test_content_does_not_depend_on_environment_or_remote_service(self):
        request = TutorGenerationRequest(
            task="sentiment_classification", stage="evaluation", step="review",
            action_type=InstructionalActionType.REVIEW_CONCEPT_SUMMARY,
            reference_prompt="authored test",
        )
        first = authored_tutor_content(request).model_dump(mode="json")
        second = authored_tutor_content(request).model_dump(mode="json")
        first.pop("content_instance_id")
        second.pop("content_instance_id")
        self.assertEqual(first, second)

    def test_cnn_and_regression_stages_have_authored_content(self):
        stages_by_task = {
            "cnn": ["load_images", "normalize_split", "build_cnn", "train_network", "classify_images", "evaluate_cnn"],
            "regression": ["prepare_housing_data", "split_housing_data", "scale_features", "train_regression", "predict_prices", "evaluate_regression"],
        }
        for task, stages in stages_by_task.items():
            for stage in stages:
                with self.subTest(task=task, stage=stage):
                    request = TutorGenerationRequest(
                        task=task, stage=stage, step="review",
                        action_type=InstructionalActionType.REVIEW_CONCEPT_SUMMARY,
                        reference_prompt="authored test",
                    )
                    result = authored_tutor_content(request)
                    self.assertEqual(result.model, "authored")
                    self.assertEqual(len(result.lesson.sections), 6)
                    self.assertIn(result.content.expected_answer, result.content.options)
                    self.assertTrue(result.lesson.sections[4].code)

    def test_pooled_questions_teach_and_rotate(self):
        pooled = [(task, name, stage) for task, stages in STAGES_BY_TASK.items() for name, stage in stages.items() if "questions" in stage]
        self.assertGreaterEqual(len(pooled), 7)
        for task, name, stage in pooled:
          for pool, variants in stage["questions"].items():
            for prompt, correct, options, explanation, hint in variants:
                with self.subTest(task=task, stage=name, pool=pool, prompt=prompt):
                    self.assertEqual(options.count(correct), 1)
                    self.assertTrue(all(len(option.split()) <= 10 for option in options))
                    self.assertNotEqual(explanation.strip(), correct)
                    self.assertGreater(len(explanation.split()), 12)
                    self.assertNotIn(correct.lower(), hint.lower())
        def ask(step, action, variant=0):
            request = TutorGenerationRequest(task="sentiment_classification", stage="data_loading_and_preparation", step=step,
                                             action_type=action, reference_prompt="test")
            return authored_tutor_content(request, variant=variant).content.question
        boundary = [ask("connect", InstructionalActionType.CONNECT_CONCEPT_MATCHING),
                    ask("practice", InstructionalActionType.PRACTICE_MISCONCEPTION_DIAGNOSIS),
                    ask("review", InstructionalActionType.REVIEW_CONCEPT_SUMMARY)]
        self.assertEqual(len(set(boundary)), 3)
        retry = InstructionalActionType.PRACTICE_PIPELINE_ORDERING
        self.assertNotEqual(ask("practice", retry, 0), ask("practice", retry, 1))

    def test_pilot_lesson_covers_every_analogy_preference(self):
        bodies = set()
        for preference in ("java", "everyday", "pure_ml"):
            request = TutorGenerationRequest(task="sentiment_classification", stage="data_loading_and_preparation", step="connect",
                                             action_type=InstructionalActionType.CONNECT_CONCEPT_MATCHING, reference_prompt="test",
                                             analogy_preference=preference)
            lesson = authored_tutor_content(request).lesson
            bodies.add(lesson.sections[1].body)
            self.assertTrue(lesson.code_explanation)
            self.assertTrue(lesson.sections[2].items)
        self.assertEqual(len(bodies), 3)

    def test_practice_questions_do_not_copy_assessment_items(self):
        assessment = [question for bank in (QUESTION_BANK, FINAL_QUESTION_BANK) for questions in bank.values() for question in questions]
        def words(text):
            return set(re.findall(r"[a-z0-9.]+", text.lower()))
        for task, stages in STAGES_BY_TASK.items():
            for name, stage in stages.items():
                for variants in stage.get("questions", {}).values():
                    for prompt, *_ in variants:
                        for item in assessment:
                            if item.stage != name:
                                continue
                            overlap = len(words(prompt) & words(item.prompt)) / len(words(prompt) | words(item.prompt))
                            with self.subTest(stage=name, prompt=prompt, assessment=item.id):
                                self.assertLess(overlap, 0.5)


if __name__ == "__main__":
    unittest.main()
