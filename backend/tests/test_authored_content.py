import unittest

from app.models import InstructionalActionType, TutorGenerationRequest
from app.tutoring.authored_content import AUTHORED_CONTENT_VERSION, authored_tutor_content
from app.tutoring.lesson_code import FIXED_LESSON_CODE


class AuthoredContentTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
