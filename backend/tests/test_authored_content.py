import re
import unittest
from collections import Counter

from app.assessments.bank import QUESTION_BANK
from app.assessments.final_bank import FINAL_QUESTION_BANK

from app.models import InstructionalActionType, TutorGenerationRequest
from app.tutoring.authored_content import AUTHORED_CONTENT_VERSION, STAGES_BY_TASK, _stable_shuffle, authored_tutor_content
from app.tutoring.authored_questions import QUESTIONS
from app.tutoring.lesson_code import FIXED_LESSON_CODE

ALL_QUESTIONS = [(task, stage, pool, question) for task, stages in QUESTIONS.items() for stage, pools in stages.items() for pool, questions in pools.items() for question in questions]


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

    def test_every_question_teaches_and_has_four_plausible_options(self):
        for task, stage, pool, (prompt, correct, options, explanation, hint) in ALL_QUESTIONS:
            with self.subTest(task=task, stage=stage, pool=pool, prompt=prompt):
                self.assertEqual(len(options), 4)
                self.assertEqual(len(set(options)), 4)
                self.assertEqual(options.count(correct), 1)
                self.assertTrue(all(len(option.split()) <= 10 for option in options))
                self.assertNotEqual(explanation.strip(), correct)
                self.assertGreater(len(explanation.split()), 12)
                self.assertNotIn(correct.lower(), hint.lower())
                self.assertIn(prompt.count("```"), (0, 2))

    def test_every_stage_has_every_pool_with_a_second_question(self):
        for task, stages in STAGES_BY_TASK.items():
            for stage in stages:
                with self.subTest(task=task, stage=stage):
                    pools = QUESTIONS[task][stage]
                    self.assertEqual(set(pools), {"operation", "variable", "boundary", "ordering", "transfer", "code"})
                    self.assertTrue(all(len(questions) >= 2 for questions in pools.values()))

    def test_the_correct_answer_cannot_be_spotted_by_length_or_position(self):
        uniquely_longest = 0
        positions = Counter()
        for task, stage, _, (prompt, correct, options, _, _) in ALL_QUESTIONS:
            lengths = sorted(len(option) for option in options)
            uniquely_longest += len(correct) == lengths[-1] > lengths[-2]
            positions[_stable_shuffle(list(options), f"{task}.{stage}.{prompt}").index(correct)] += 1
        # With four options, the longest one is right about a quarter of the time by chance.
        self.assertLessEqual(uniquely_longest / len(ALL_QUESTIONS), 0.25)
        self.assertTrue(all(0.15 <= positions[slot] / len(ALL_QUESTIONS) <= 0.35 for slot in range(4)))

    def test_retries_and_later_steps_show_a_different_question(self):
        for task, stages in STAGES_BY_TASK.items():
            for stage in stages:
                for action in InstructionalActionType:
                    step = action.value.split(".", 1)[0]
                    if step not in {"connect", "practice", "review"}:
                        continue
                    def ask(variant):
                        request = TutorGenerationRequest(task=task, stage=stage, step=step, action_type=action, reference_prompt="test")
                        return authored_tutor_content(request, variant=variant).content.question
                    with self.subTest(task=task, stage=stage, action=action.value):
                        self.assertNotEqual(ask(0), ask(1))
        def boundary(step, action):
            request = TutorGenerationRequest(task="sentiment_classification", stage="data_loading_and_preparation", step=step, action_type=action, reference_prompt="test")
            return authored_tutor_content(request).content.question
        self.assertEqual(len({boundary("connect", InstructionalActionType.CONNECT_CONCEPT_MATCHING),
                              boundary("practice", InstructionalActionType.PRACTICE_MISCONCEPTION_DIAGNOSIS),
                              boundary("review", InstructionalActionType.REVIEW_CONCEPT_SUMMARY)}), 3)

    def test_every_stage_first_practice_question_is_applied(self):
        practice = [action for action in InstructionalActionType if action.value.startswith("practice.")]
        for task, stages in STAGES_BY_TASK.items():
            for stage in stages:
                for action in practice:
                    request = TutorGenerationRequest(task=task, stage=stage, step="practice", action_type=action, reference_prompt="test")
                    with self.subTest(task=task, stage=stage, action=action.value):
                        self.assertIn("```", authored_tutor_content(request).content.question)

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
        for _, name, _, (prompt, *_) in ALL_QUESTIONS:
            for item in assessment:
                if item.stage != name:
                    continue
                overlap = len(words(prompt) & words(item.prompt)) / len(words(prompt) | words(item.prompt))
                with self.subTest(stage=name, prompt=prompt, assessment=item.id):
                    self.assertLess(overlap, 0.5)


if __name__ == "__main__":
    unittest.main()
