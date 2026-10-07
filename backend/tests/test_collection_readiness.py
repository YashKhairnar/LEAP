import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from app.assessments.service import get_assessment
from app.collection.export import build_collection_export, learner_split
from app.database import (
    connect, initialize_database, list_progress, resume_tutor_content,
    save_behavior_event, save_generated_tutor_content, save_interaction,
)
from app.main import tutor_plan
from app.models import (
    BehaviorEventCreate, InteractionCreate, PlannerRequest, TutorGenerationRequest,
    TutorGenerationResponse, UserRecord,
)
from app.planning.client import WorldModelUnavailable


class CollectionReadinessTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        environment = patch.dict(os.environ, {
            "DATABASE_URL": "", "LEAP_DATABASE_PATH": str(Path(directory.name) / "collection.db"),
            "LEAP_COLLECTION_MODE": "pilot", "ENVIRONMENT": "development",
        })
        environment.start()
        self.addCleanup(environment.stop)
        initialize_database()
        self.location = {"task": "cnn", "stage": "load_images", "step": "connect"}
        self.decision = {
            "assignment_policy": "uniform_random_v1", "selected_index": 0,
            "selection_probability": 1.0, "action_probabilities": [1.0],
            "candidates": [{"action_type": "connect.concept_matching", "prompt": "Match concepts"}],
        }
        self.context = TutorGenerationRequest(
            **self.location, action_type="connect.concept_matching",
            reference_prompt="Identify training inputs.", planner_decision=self.decision,
        )
        self.generated = TutorGenerationResponse(
            content_instance_id="question-1", model="fixture", prompt_version="fixture-v1",
            code_version="fixture-code", dataset={},
            lesson={"title": "Training data", "introduction": "Inputs and labels.", "sections": [
                {"type": "concept_bridge", "title": "Meaning", "body": "Train with inputs."},
                {"type": "real_life_analogy", "title": "Analogy", "body": "Practice before an exam."},
                {"type": "code", "title": "Code", "body": "Inspect inputs.", "code": "print(data)", "language": "python"},
            ], "takeaways": ["Hold out test data."]},
            content={"question": "Which data trains a model?", "options": ["Training", "Test"],
                "expected_answer": "Training", "hint": "Keep test data separate.",
                "explanation": "Training uses training data.", "concepts_tested": ["training_data"]},
        )
        save_generated_tutor_content(self.context, self.generated, "learner-a")

    def event(self, event_id="presentation-1", event_type="content_presented", **data):
        return BehaviorEventCreate(
            event_id=event_id, session_id="session-1", event_type=event_type, location=self.location,
            event_timestamp="2026-09-14T12:00:00Z", data={
                "content_id": self.generated.collection_content.content_id,
                "presentation_id": "presentation-1", "content_instance_id": "question-1", **data,
            },
        )

    def interaction(self, transition_id="attempt-1", **observation):
        return InteractionCreate(
            session_id="session-1", transition_id=transition_id,
            content=self.generated.collection_content.model_copy(deep=True),
            location_before=self.location, location_after=self.location,
            instructional_action={"action_type": self.context.action_type, "content_id": self.generated.collection_content.content_id},
            learner_action={"response": "Training"},
            observation={"correct": True, "score": 1, "attempt": 1, "response_time_ms": 1200,
                "hint_used": False, "answer_revealed_before_attempt": False, "evidence_kind": "independent",
                "timing_version": "visible_foreground_v1", "exposure_id": "presentation-1", **observation},
            progression={"decision": "remain_on_step"}, event_timestamp="2026-09-14T12:00:02Z",
            presentation_id="presentation-1", selection_policy="uniform_random_v1",
        )

    def test_generated_content_is_saved_before_any_answer_and_restored_exactly(self):
        with connect() as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) AS n FROM content_items").fetchone()["n"], 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) AS n FROM transitions").fetchone()["n"], 0)
        resumed = resume_tutor_content("learner-a", **self.location, prompt_version="fixture-v1")
        self.assertEqual(resumed.active_question.collection_content, self.generated.collection_content)

    def test_resume_metadata_changes_preserve_original_provenance(self):
        original = save_interaction(self.interaction(), "learner-a")
        retry = self.interaction("attempt-2", attempt=2, answer_revealed_before_attempt=True, evidence_kind="post_feedback_retry")
        retry.content.planner_decision = {"assignment_policy": "reconstructed"}
        retry.content.generation_metadata = {"content_instance_id": "question-1"}
        saved = save_interaction(retry, "learner-a")
        self.assertEqual(saved.selection_policy, original.selection_policy)
        self.assertEqual(saved.collection_mode, "pilot")
        resumed = resume_tutor_content("learner-a", **self.location, prompt_version="fixture-v1")
        self.assertEqual(resumed.question_state.attempt, 2)
        self.assertEqual(resumed.active_question.collection_content.planner_decision, self.decision)
        self.assertEqual(saved.observation.evidence_kind, "post_feedback_retry")

    def test_actual_question_mutation_still_rejected(self):
        changed = self.interaction()
        changed.content.prompt = "A different question"
        with self.assertRaisesRegex(ValueError, "different content"):
            save_interaction(changed, "learner-a")

    def test_hint_exposure_restores_assistance_without_changing_progress(self):
        before = list_progress("learner-a")
        save_behavior_event(self.event("hint-1", "content_exposure", kind="hint_opened"), "learner-a")
        self.assertEqual(list_progress("learner-a"), before)
        resumed = resume_tutor_content("learner-a", **self.location, prompt_version="fixture-v1")
        self.assertTrue(resumed.question_state.hint_used)

    def test_assessment_preview_is_development_only(self):
        for mode, environment, expected in (("pilot", "development", False), ("study", "development", False), ("development", "production", False), ("development", "development", True)):
            with self.subTest(mode=mode, environment=environment), patch.dict(os.environ, {"LEAP_COLLECTION_MODE": mode, "ENVIRONMENT": environment}):
                result = get_assessment("new-learner", "cnn")
                self.assertEqual(result["preview_allowed"], expected)
                self.assertEqual(len(result["questions"]), 10 if expected else 0)

    def test_shadow_outage_preserves_uniform_policy_without_fabricated_states(self):
        request = PlannerRequest(session_id="session-1", **self.location, candidates=self.decision["candidates"])
        user = UserRecord(user_id="learner-a", participant_code="LP-000000000000", java_experience="comfortable")
        with patch("app.main.plan_next_action", side_effect=WorldModelUnavailable("offline")):
            result = tutor_plan(request, user)
        self.assertEqual(result.assignment_policy, "uniform_random_v1")
        self.assertEqual(result.action_probabilities, [1.0])
        self.assertEqual(result.shadow_status, "unavailable")
        self.assertEqual(result.predicted_state, [])
        with self.assertRaises(ValidationError):
            PlannerRequest(session_id="session-1", **self.location, candidates=self.decision["candidates"] * 2)

    def test_export_joins_presentation_and_keeps_assisted_attempts_labeled(self):
        save_behavior_event(self.event(), "learner-a")
        save_interaction(self.interaction(), "learner-a")
        save_interaction(self.interaction("attempt-2", attempt=2, answer_revealed_before_attempt=True, evidence_kind="post_feedback_retry"), "learner-a")
        bundle = build_collection_export({"learner-a"})
        self.assertEqual(bundle["manifest"]["issues"], {})
        self.assertEqual(bundle["manifest"]["records"], 2)
        self.assertEqual(bundle["manifest"]["independent_outcomes"], 1)
        self.assertEqual(bundle["records"][0]["split"], bundle["records"][1]["split"])
        self.assertEqual(bundle["records"][0]["split"], learner_split("learner-a"))
        self.assertEqual(build_collection_export({"someone-else"})["manifest"]["records"], 0)
        self.assertEqual(build_collection_export({"learner-a"}, mode="study")["manifest"]["records"], 0)
        self.assertNotIn("password", json.dumps(bundle))
        with self.assertRaises(ValueError):
            build_collection_export(set())

    def test_export_flags_unverified_and_inconsistent_evidence(self):
        save_interaction(self.interaction(timing_version=None, evidence_kind="unknown"), "learner-a")
        save_interaction(self.interaction("attempt-2", hint_used=True), "learner-a")
        issues = build_collection_export({"learner-a"})["manifest"]["issues"]
        self.assertEqual(issues["missing_presentation"], 2)
        self.assertEqual(issues["unknown_assistance"], 1)
        self.assertEqual(issues["inconsistent_independence"], 1)
        self.assertEqual(issues["unverified_timing"], 1)


if __name__ == "__main__":
    unittest.main()
