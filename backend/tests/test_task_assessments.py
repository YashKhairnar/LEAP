import ast
import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.assessments.bank import QUESTION_BANK, VERSION
from app.assessments.service import AssessmentSubmission, get_assessment, submit_assessment
from app.database import connect, initialize_database, list_progress
from app.tutoring.lesson_code import FIXED_LESSON_CODE
from app.main import app, current_user
from app.models import UserRecord


class TaskAssessmentTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {"DATABASE_URL": "", "LEAP_DATABASE_PATH": str(Path(directory.name) / "assessment.db")})
        environment.start()
        self.addCleanup(environment.stop)
        initialize_database()
        for task in QUESTION_BANK:
            self.unlock("student-a", task)

    def unlock(self, learner, task):
        with connect() as connection:
            connection.execute(
                "INSERT INTO user_progress (learner_id, task, completed_stages, task_complete) VALUES (?, ?, 6, 1)",
                (learner, task),
            )

    def submission(self, task, correct_count=10):
        return AssessmentSubmission(version=VERSION, answers={
            question.id: question.answer if index < correct_count else (question.answer + 1) % 4
            for index, question in enumerate(QUESTION_BANK[task])
        })

    def test_each_task_has_ten_mcqs_covering_every_stage(self):
        self.assertEqual(set(QUESTION_BANK), set(FIXED_LESSON_CODE))
        all_ids = []
        for task, questions in QUESTION_BANK.items():
            with self.subTest(task=task):
                self.assertEqual(len(questions), 10)
                self.assertEqual({item.stage for item in questions}, set(FIXED_LESSON_CODE[task]))
                self.assertEqual({item.answer for item in questions}, {0, 1, 2, 3})
                for question in questions:
                    all_ids.append(question.id)
                    self.assertEqual(len(set(question.options)), 4)
                    self.assertTrue(question.prompt and question.explanation and question.concept)
                    self.assertIn(question.answer, range(4))
                    if question.code:
                        ast.parse(question.code)
        self.assertEqual(len(all_ids), len(set(all_ids)))

    def test_answer_keys_are_hidden_until_submission(self):
        for task in QUESTION_BANK:
            public = get_assessment("student-a", task)
            self.assertTrue(public["unlocked"])
            self.assertIsNone(public["result"])
            self.assertEqual(len(public["questions"]), 10)
            for question in public["questions"]:
                self.assertNotIn("answer", question)
                self.assertNotIn("explanation", question)

    def test_scores_all_tasks_and_restores_results(self):
        for task in QUESTION_BANK:
            for score in (0, 6, 10):
                with self.subTest(task=task, score=score):
                    learner = f"learner-{task}-{score}"
                    self.unlock(learner, task)
                    result = submit_assessment(learner, task, self.submission(task, score))
                    self.assertEqual(result["score"], score)
                    self.assertEqual(result["total"], 10)
                    self.assertEqual(len(result["questions"]), 10)
                    self.assertEqual(sum(item["correct"] for item in result["questions"]), score)
                    self.assertEqual(get_assessment(learner, task)["result"], result)

    def test_pre_assessment_uses_same_questions_and_is_available_before_learning(self):
        learner = "pretest-student"
        public = get_assessment(learner, "cnn", "pre")
        self.assertEqual(public["phase"], "pre")
        self.assertTrue(public["unlocked"])
        self.assertEqual([question["id"] for question in public["questions"]], [question.id for question in QUESTION_BANK["cnn"]])
        result = submit_assessment(learner, "cnn", self.submission("cnn", 6), "pre")
        self.assertEqual(result["phase"], "pre")
        self.assertEqual(result["score"], 6)
        self.assertEqual(get_assessment(learner, "cnn", "pre")["result"], result)
        with connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) AS count FROM task_pre_assessments").fetchone()["count"], 1)

    def test_pre_and_post_assessments_are_stored_separately(self):
        learner = "paired-assessment-student"
        self.unlock(learner, "cnn")
        pre = submit_assessment(learner, "cnn", self.submission("cnn", 3), "pre")
        post = submit_assessment(learner, "cnn", self.submission("cnn", 9), "post")
        self.assertEqual((pre["phase"], pre["score"]), ("pre", 3))
        self.assertEqual((post["phase"], post["score"]), ("post", 9))

    def test_first_submission_is_preserved_on_retry_or_changed_answers(self):
        first = submit_assessment("student-a", "cnn", self.submission("cnn", 4))
        second = submit_assessment("student-a", "cnn", self.submission("cnn", 10))
        self.assertEqual(second, first)
        with connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) AS count FROM task_assessments").fetchone()["count"], 1)

    def test_student_and_task_records_are_isolated(self):
        submit_assessment("student-a", "cnn", self.submission("cnn"))
        self.unlock("student-b", "cnn")
        self.assertIsNone(get_assessment("student-b", "cnn")["result"])
        self.assertIsNone(get_assessment("student-a", "regression")["result"])

    def test_incomplete_stages_allow_preview_but_lock_submission(self):
        with connect() as connection:
            connection.execute("UPDATE user_progress SET completed_stages = 5, task_complete = 0 WHERE learner_id = ?", ("student-a",))
        for learner in ("student-a", "new-student"):
            public = get_assessment(learner, "cnn")
            self.assertFalse(public["unlocked"])
            self.assertEqual(len(public["questions"]), 10)
            self.assertIsNone(public["result"])
            self.assertTrue(all("answer" not in question and "explanation" not in question for question in public["questions"]))
            with self.assertRaises(PermissionError):
                submit_assessment(learner, "cnn", self.submission("cnn"))

    def test_preview_all_tasks_without_creating_progress_or_results(self):
        for task in QUESTION_BANK:
            status, public = self.api_request("GET", task, learner="preview-student")
            self.assertEqual(status, 200)
            self.assertFalse(public["unlocked"])
            self.assertEqual(len(public["questions"]), 10)
            self.assertIsNone(public["result"])
        with connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) AS count FROM user_progress WHERE learner_id = ?", ("preview-student",)).fetchone()["count"], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) AS count FROM task_assessments WHERE learner_id = ?", ("preview-student",)).fetchone()["count"], 0)

    def test_malformed_answers_are_rejected(self):
        answers = self.submission("cnn").answers
        for invalid in ({}, {**answers, "extra": 0}, {**answers, "cnn-01": -1}, {**answers, "cnn-01": 4}, {**answers, "cnn-01": True}, {**answers, "cnn-01": "1"}):
            with self.subTest(answers=invalid), self.assertRaises(ValidationError):
                AssessmentSubmission(version=VERSION, answers=invalid)
        with self.assertRaises(ValidationError):
            AssessmentSubmission(version=VERSION, answers=answers, score=10)

    def test_wrong_task_questions_and_stale_versions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "10 questions"):
            submit_assessment("student-a", "cnn", self.submission("regression"))
        stale = self.submission("cnn").model_copy(update={"version": "old-version"})
        with self.assertRaisesRegex(ValueError, "assessment has changed"):
            submit_assessment("student-a", "cnn", stale)

    def test_sentiment_alias_uses_the_same_assessment_and_result(self):
        result = submit_assessment("student-a", "sentiment", self.submission("sentiment_classification"))
        self.assertEqual(get_assessment("student-a", "sentiment_classification")["result"], result)

    def test_assessment_does_not_overwrite_lesson_progress(self):
        before = [record.model_dump() for record in list_progress("student-a")]
        submit_assessment("student-a", "cnn", self.submission("cnn", 0))
        self.assertEqual([record.model_dump() for record in list_progress("student-a")], before)

    def test_unknown_task_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unknown assessment task"):
            get_assessment("student-a", "unknown")

    def api_request(self, method, task, body=None, learner=None):
        """Exercise the ASGI app without network access or an HTTP test dependency."""
        async def request():
            messages = []
            delivered = False

            async def receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": json.dumps(body).encode() if body is not None else b"", "more_body": False}
                await asyncio.Event().wait()

            async def send(message):
                messages.append(message)

            path = f"/api/assessments/{task}"
            await app({
                "type": "http", "asgi": {"version": "3.0", "spec_version": "2.4"},
                "http_version": "1.1", "method": method, "scheme": "http",
                "path": path, "raw_path": path.encode(), "query_string": b"",
                "headers": [(b"content-type", b"application/json")],
                "client": ("127.0.0.1", 12345), "server": ("test", 80), "root_path": "",
            }, receive, send)
            status = next(message["status"] for message in messages if message["type"] == "http.response.start")
            payload = b"".join(message.get("body", b"") for message in messages if message["type"] == "http.response.body")
            return status, json.loads(payload)

        overrides = {current_user: lambda: UserRecord(user_id=learner, participant_code="test-participant", java_experience="comfortable")} if learner else {}
        with patch.dict(app.dependency_overrides, overrides, clear=True):
            return asyncio.run(request())

    def test_api_requires_authentication_for_questions_and_submission(self):
        self.assertEqual(self.api_request("GET", "cnn")[0], 401)
        self.assertEqual(self.api_request("POST", "cnn", self.submission("cnn").model_dump())[0], 401)

    def test_api_get_submit_restore_and_validation(self):
        status, public = self.api_request("GET", "cnn", learner="student-a")
        self.assertEqual(status, 200)
        self.assertNotIn("answer", public["questions"][0])
        status, result = self.api_request("POST", "cnn", self.submission("cnn", 7).model_dump(), learner="student-a")
        self.assertEqual((status, result["score"]), (200, 7))
        self.assertEqual(self.api_request("GET", "cnn", learner="student-a")[1]["result"], result)
        self.assertEqual(self.api_request("POST", "cnn", {"version": VERSION, "answers": {}}, learner="student-a")[0], 422)
        self.assertEqual(self.api_request("POST", "cnn", self.submission("cnn").model_dump(), learner="student-b")[0], 403)
        self.assertEqual(self.api_request("GET", "missing", learner="student-a")[0], 404)


if __name__ == "__main__":
    unittest.main()
