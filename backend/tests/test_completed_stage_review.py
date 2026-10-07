import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.database import (
    connect,
    initialize_database,
    list_progress,
    resume_tutor_content,
    save_generated_tutor_content,
)
from app.models import TutorGenerationRequest, TutorGenerationResponse


class CompletedStageReviewTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {
            "DATABASE_URL": "",
            "LEAP_DATABASE_PATH": str(Path(directory.name) / "review.db"),
        })
        environment.start()
        self.addCleanup(environment.stop)
        initialize_database()
        lesson = {
            "title": "Saved lesson",
            "introduction": "A lesson the learner already completed.",
            "sections": [
                {"type": "concept_bridge", "title": "Bridge", "body": "Connect inputs to outputs."},
                {"type": "real_life_analogy", "title": "Analogy", "body": "Practice before a final exam."},
                {"type": "code", "title": "Code", "body": "Inspect the data.", "code": "print(data)", "language": "python"},
            ],
            "takeaways": ["Keep inputs aligned.", "Hold out test data."],
        }
        for task in ("sentiment_classification", "cnn", "regression"):
            context = TutorGenerationRequest(
                task=task, stage="completed_stage", step="connect",
                action_type="connect.concept_matching", reference_prompt="Review a concept.",
            )
            generated = TutorGenerationResponse(
                content_instance_id=f"saved-{task}", model="saved-model",
                prompt_version="previous-version", code_version="saved-code", dataset={},
                lesson=lesson,
                content={
                    "question": "Which data trains the model?", "options": ["Training data", "Test data"],
                    "expected_answer": "Training data", "hint": "Keep the test set separate.",
                    "explanation": "Training uses training data.", "concepts_tested": ["train_test_separation"],
                },
            )
            save_generated_tutor_content(context, generated, "learner-a")
            with connect() as connection:
                connection.execute(
                    "UPDATE tutor_question_instances SET latest_answer = ?, latest_correct = 1, latest_attempt = 2 WHERE content_instance_id = ?",
                    ("Training data", f"saved-{task}"),
                )
                connection.execute(
                    """INSERT INTO user_progress
                    (learner_id, task, completed_stages, task_complete, current_stage, current_step)
                    VALUES (?, ?, 2, 0, 'current_stage', 'practice')""",
                    ("learner-a", task),
                )

    def test_review_restores_saved_content_and_answers_across_prompt_versions(self):
        for task in ("sentiment_classification", "cnn", "regression"):
            with self.subTest(task=task):
                result = resume_tutor_content("learner-a", task, "completed_stage", "connect", "new-version", review=True)
                self.assertEqual(result.lesson.title, "Saved lesson")
                self.assertEqual(result.active_question.prompt_version, "previous-version")
                self.assertEqual(result.question_state.answer, "Training data")
                self.assertTrue(result.question_state.correct)
                self.assertEqual(result.question_state.attempt, 2)

    def test_normal_learning_still_requires_the_current_prompt_version(self):
        result = resume_tutor_content("learner-a", "cnn", "completed_stage", "connect", "new-version")
        self.assertIsNone(result.lesson)
        self.assertIsNone(result.active_question)

    def test_review_preserves_resume_position_and_completion(self):
        for completed in (False, True):
            with self.subTest(completed=completed):
                if completed:
                    with connect() as connection:
                        connection.execute("UPDATE user_progress SET completed_stages = 6, task_complete = 1")
                before = [record.model_dump() for record in list_progress("learner-a")]
                for step in ("connect", "practice", "review"):
                    resume_tutor_content("learner-a", "cnn", "completed_stage", step, "new-version", review=True)
                self.assertEqual(before, [record.model_dump() for record in list_progress("learner-a")])

    def test_review_cannot_read_another_learners_content(self):
        result = resume_tutor_content("learner-b", "cnn", "completed_stage", "connect", "new-version", review=True)
        self.assertIsNone(result.lesson)
        self.assertIsNone(result.active_question)

    def test_missing_question_keeps_the_saved_lesson_available(self):
        result = resume_tutor_content("learner-a", "cnn", "completed_stage", "practice", "new-version", review=True)
        self.assertIsNotNone(result.lesson)
        self.assertIsNone(result.active_question)


if __name__ == "__main__":
    unittest.main()
