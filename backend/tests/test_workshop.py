import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.database import connect, initialize_database
from app.execution.cells import UnsafeCode, validate_code
from app.main import app
from app.models import UserRecord
from app.workshop import router as workshop_router
from app.workshop.content import CELLS, LEARNING_STAGES, QUESTIONS, STAGES, own_reviews_written
from app.workshop.runner import DATASET_PATH, WORKSHOP_DUNDERS, WORKSHOP_IMPORTS, prelude, workshop_program
from app.workshop.store import initialize_workshop_tables

USER = UserRecord(user_id="learner-1", participant_code="P1234", java_experience="none", analogy_preference="pure_ml")
OTHER = UserRecord(user_id="learner-2", participant_code="P5678", java_experience="none", analogy_preference="pure_ml")
UPLOAD = {"name": "dataset.csv", "size": DATASET_PATH.stat().st_size}


def fake_run(cell_id, code, uploaded_filename):
    return {"success": True, "stdout": f"ran {cell_id}", "stderr": "", "result": None, "table_preview": None,
            "plots": [], "duration_ms": 1, "engine": "test"}


class WorkshopContentTests(unittest.TestCase):
    def test_matches_the_colab_structure(self):
        self.assertEqual([stage.stage_id for stage in STAGES],
                         ["start", "import_libraries", "load_data", "split_data", "text_to_numbers", "train_model", "evaluate_model", "finish"])
        # 16 numbered cells (the Colab labels two cells "Cell 2") plus the practice cell.
        self.assertEqual(len(CELLS), 17)
        self.assertEqual([question.question_id for question in QUESTIONS],
                         ["q1_1", "q2_1", "q2_2", "q3_1", "q3_2", "q4_1", "q4_2", "q5_1", "q5_2", "q6_1", "q6_2"])
        for stage in STAGES:
            placed = [block["cell_id"] for block in stage.blocks if block["type"] == "cell"]
            with self.subTest(stage=stage.stage_id):
                self.assertEqual(placed, [cell.cell_id for cell in stage.cells])
                self.assertEqual(any(block["type"] == "questions" for block in stage.blocks), bool(stage.questions))

    def test_every_cell_passes_the_workshop_safety_check(self):
        for cell in CELLS:
            with self.subTest(cell=cell.cell_id):
                program = workshop_program(cell.cell_id, cell.code, "dataset.csv")
                self.assertLess(len(program), 20_000)  # the Modal sandbox's program limit

    def test_safety_check_still_blocks_unsafe_code(self):
        for code in ('open("x")', "import os", "np.__class__", 'pd.read_csv("../secret.csv")'):
            with self.subTest(code=code), self.assertRaises(UnsafeCode):
                validate_code(code, WORKSHOP_IMPORTS, WORKSHOP_DUNDERS)
        # The lesson paths keep their stricter defaults.
        for code in ("import io", "print(np.__version__)"):
            with self.subTest(code=code), self.assertRaises(UnsafeCode):
                validate_code(code)

    def test_upload_name_is_escaped_in_the_prelude(self):
        self.assertIn('"dataset (1).csv"', prelude("dataset (1).csv"))
        self.assertIn('"dataset.csv"', prelude('evil"); import os; ("'))

    def test_own_reviews_must_replace_placeholders(self):
        own = next(cell for cell in CELLS if cell.kind == "own_reviews")
        self.assertFalse(own_reviews_written(own.code))
        self.assertTrue(own_reviews_written(own.code.replace("Write a", "I liked a")))

    def test_dataset_matches_the_colab_file(self):
        self.assertEqual(DATASET_PATH.stat().st_size, 1366043)
        with DATASET_PATH.open(encoding="utf-8") as file:
            self.assertEqual(file.readline().strip(), "text,sentiment")


class WorkshopApiTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {"DATABASE_URL": "", "LEAP_DATABASE_PATH": str(Path(directory.name) / "workshop.db")})
        environment.start()
        self.addCleanup(environment.stop)
        initialize_database()
        initialize_workshop_tables()
        runner = patch.object(workshop_router, "run_workshop_cell", side_effect=fake_run)
        runner.start()
        self.addCleanup(runner.stop)
        router = workshop_router.build_workshop_router(lambda: USER)
        self.routes = {route.name: route.endpoint for route in router.routes}

    def run_cell(self, cell_id, code=None, user=USER, upload=None):
        cell = next(item for item in CELLS if item.cell_id == cell_id)
        request = workshop_router.CellRunRequest(code=code or cell.code, uploaded_file=upload)
        return self.routes["run_cell"](cell_id, request, user)

    def answer(self, question_id, text, user=USER):
        return self.routes["answer"](question_id, workshop_router.AnswerRequest(answer=text), user)

    def finish_stage(self, stage, user=USER):
        for cell in stage.cells:
            code = cell.code.replace("Write a", "My own") if cell.kind == "own_reviews" else cell.code
            self.run_cell(cell.cell_id, code, user, UPLOAD if cell.kind == "upload" else None)
        for question in stage.questions:
            self.answer(question.question_id, f"My answer to {question.question_id}", user)
        return self.routes["complete"](stage.stage_id, user)

    def test_routes_are_registered(self):
        self.assertEqual(set(self.routes), {"content", "state", "dataset", "run_cell", "answer", "complete"})
        self.assertIn("/api/workshop/cells/{cell_id}/run", app.openapi()["paths"])

    def test_new_learner_starts_at_the_beginning(self):
        state = self.routes["state"](USER)
        self.assertEqual(state["current_stage"], "start")
        self.assertEqual(state["completed_stages"], [])
        self.assertEqual((state["cells_total"], state["answers_total"]), (16, 11))

    def test_later_steps_are_locked(self):
        with self.assertRaises(HTTPException) as raised:
            self.run_cell("imports")
        self.assertEqual(raised.exception.status_code, 403)
        with self.assertRaises(HTTPException) as raised:
            self.answer("q1_1", "early")
        self.assertEqual(raised.exception.status_code, 403)

    def test_cells_run_in_order_within_a_step(self):
        self.finish_stage(STAGES[0])
        with self.assertRaises(HTTPException) as raised:
            self.run_cell("versions")
        self.assertEqual(raised.exception.status_code, 409)
        self.assertEqual(self.run_cell("imports")["execution_count"], 2)
        self.assertEqual(self.run_cell("versions")["execution_count"], 3)

    def test_a_step_needs_every_cell_and_answer(self):
        self.finish_stage(STAGES[0])
        self.run_cell("imports")
        self.run_cell("versions")
        with self.assertRaises(HTTPException) as raised:
            self.routes["complete"]("import_libraries", USER)
        self.assertEqual(raised.exception.detail["missing"], ["Answer q1_1"])
        self.answer("q1_1", "   ")
        with self.assertRaises(HTTPException):
            self.routes["complete"]("import_libraries", USER)
        self.answer("q1_1", "pandas loads the table")
        state = self.routes["complete"]("import_libraries", USER)
        self.assertEqual(state["current_stage"], "load_data")
        self.assertEqual(state["answers"]["q1_1"]["answer"], "pandas loads the table")

    def test_upload_requires_the_workshop_file(self):
        for stage in STAGES[:2]:
            self.finish_stage(stage)
        with self.assertRaises(HTTPException):
            self.run_cell("upload")
        with self.assertRaises(HTTPException):
            self.run_cell("upload", upload={"name": "other.csv", "size": 10})
        self.run_cell("upload", upload={"name": "dataset (1).csv", "size": UPLOAD["size"]})
        self.assertEqual(self.routes["state"](USER)["uploaded_filename"], "dataset (1).csv")

    def test_own_reviews_need_new_text(self):
        for stage in LEARNING_STAGES[:-1]:
            self.finish_stage(stage)
        self.run_cell("accuracy")
        self.run_cell("mistakes")
        self.assertFalse(self.run_cell("own_reviews")["done"])
        self.assertTrue(self.run_cell("own_reviews", 'my_reviews = ["Great food"]\nprint(my_reviews)')["done"])

    def test_full_workshop_and_learners_are_separate(self):
        for stage in LEARNING_STAGES:
            state = self.finish_stage(stage)
        self.assertTrue(state["workshop_complete"])
        self.assertEqual(state["current_stage"], "finish")
        self.assertEqual((state["cells_done"], state["answers_done"]), (16, 11))
        other = self.routes["state"](OTHER)
        self.assertEqual((other["current_stage"], other["cells"], other["answers"]), ("start", {}, {}))
        with connect() as connection:
            runs = connection.execute("SELECT COUNT(*) AS n FROM workshop_cell_runs").fetchone()["n"]
            answers = connection.execute("SELECT COUNT(*) AS n FROM workshop_answers").fetchone()["n"]
            completed = connection.execute("SELECT completed_at FROM workshop_progress WHERE learner_id = ?", (USER.user_id,)).fetchone()["completed_at"]
        self.assertEqual((runs, answers), (17, 11))
        self.assertIsNotNone(completed)

    def test_revisiting_an_earlier_step_keeps_progress(self):
        for stage in LEARNING_STAGES[:3]:
            self.finish_stage(stage)
        self.answer("q1_1", "edited later")
        state = self.routes["complete"]("import_libraries", USER)
        self.assertEqual(state["current_stage"], "split_data")
        self.assertEqual(state["answers"]["q1_1"]["answer"], "edited later")


if __name__ == "__main__":
    unittest.main()
