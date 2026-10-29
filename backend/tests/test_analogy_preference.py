import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import Response
from pydantic import ValidationError

from app.database import authenticate_user, connect, create_user, initialize_database, user_for_token
from app.main import register, tutor_generate
from app.models import RegisterRequest, TutorGenerationRequest, TutorGenerationResponse, UserRecord
from app.tutoring.generator import TUTOR_PROMPT_VERSION, TutorGenerationUnavailable, generate_tutor_content
from app.tutoring.lesson_code import FIXED_LESSON_CODE, fixed_lesson_code
from test_lesson_structure import SECTION_ORDER, lesson_with


QUESTION = {
    "question": "What does fitting use?", "options": ["Training examples", "Test examples", "No examples"],
    "expected_answer": "Training examples", "hint": "Keep testing separate.",
    "explanation": "Fitting uses training examples.", "concepts_tested": ["training"],
}


class AnalogyPreferenceTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        env = patch.dict(os.environ, {"DATABASE_URL": "", "LEAP_DATABASE_PATH": str(Path(directory.name) / "preferences.db")})
        env.start()
        self.addCleanup(env.stop)
        initialize_database()

    def test_signup_login_and_me_preserve_both_choices(self):
        for preference in ("pure_ml", "everyday", "java"):
            request = RegisterRequest(password="test-password-only", java_experience="none",
                analogy_preference=preference, consent=True, consent_version="draft-research-consent-v1")
            session = register(request, Response())
            self.assertEqual(session.user.analogy_preference, preference)
            self.assertEqual(session.user.java_experience, "none")
            login = authenticate_user(session.user.participant_code, "test-password-only")
            self.assertEqual(login.user.analogy_preference, preference)
            self.assertEqual(user_for_token(login.access_token).analogy_preference, preference)

    def test_legacy_database_migration_is_idempotent_and_keeps_accounts(self):
        account = create_user("legacy", "test-password-only", "comfortable", "draft-research-consent-v1")
        with connect() as connection:
            connection.execute("ALTER TABLE users DROP COLUMN analogy_preference")
        initialize_database()
        initialize_database()
        login = authenticate_user(account.user.participant_code, "test-password-only")
        self.assertEqual(login.user.user_id, "legacy")
        self.assertEqual(login.user.analogy_preference, "java")

    def test_preferences_are_validated_and_old_clients_keep_java_default(self):
        fields = dict(password="test-password-only", consent=True, consent_version="draft-research-consent-v1")
        request = RegisterRequest(**fields)
        self.assertEqual(request.analogy_preference, "java")
        self.assertEqual(request.java_experience, "unspecified")
        for invalid in ("python", "", True):
            with self.subTest(value=invalid), self.assertRaises(ValidationError):
                RegisterRequest(**fields, analogy_preference=invalid)

    def test_signup_payload_does_not_require_java_experience(self):
        request = RegisterRequest.model_validate({
            "password": "test-password-only",
            "analogy_preference": "everyday",
            "consent": True,
            "consent_version": "draft-research-consent-v1",
        })
        session = register(request, Response())
        self.assertEqual(session.user.java_experience, "unspecified")
        self.assertEqual(session.user.analogy_preference, "everyday")

    def test_server_binds_preference_and_reuses_only_its_own_saved_lesson(self):
        user = UserRecord(user_id="everyday-student", participant_code="LP-000000000000",
                          java_experience="none", analogy_preference="everyday")
        request = TutorGenerationRequest(task="sentiment", stage="model_training", step="connect",
            action_type="connect.analogy_mapping", reference_prompt="Explain training.",
            analogy_preference="java", java_experience="advanced", existing_lesson=lesson_with(SECTION_ORDER))
        def fake_generation(context, instance_id):
            return TutorGenerationResponse(content_instance_id=instance_id, model="fixture", prompt_version=TUTOR_PROMPT_VERSION,
                code_version="fixture", dataset={}, lesson=lesson_with(SECTION_ORDER), content=QUESTION)
        with patch("app.main.generate_tutor_content", side_effect=fake_generation) as generator:
            generated = tutor_generate(request, user)
            first = generator.call_args.args[0]
            self.assertEqual(first.analogy_preference, "everyday")
            self.assertEqual(first.java_experience, "none")
            self.assertIsNone(first.existing_lesson)
            self.assertEqual(generated.collection_content.generation_metadata["analogy_preference"], "everyday")
            tutor_generate(request, user)
            self.assertIsNotNone(generator.call_args.args[0].existing_lesson)
            other = user.model_copy(update={"user_id": "other-student"})
            tutor_generate(request, other)
            self.assertIsNone(generator.call_args.args[0].existing_lesson)
