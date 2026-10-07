import io
import json
import os
import unittest
from unittest.mock import patch

from app.models import TutorGenerationRequest
from app.tutoring.generator import TutorGenerationUnavailable, generate_tutor_content
from test_lesson_structure import SECTION_ORDER, lesson_with


QUESTION = {
    "question": "What does fitting use?",
    "options": ["Training examples", "Test examples", "No examples"],
    "expected_answer": "Training examples",
    "hint": "Keep testing separate.",
    "explanation": "Fitting uses training examples.",
    "concepts_tested": ["training"],
}


class OpenRouterTutorTests(unittest.TestCase):
    def context(self, existing_lesson=None):
        return TutorGenerationRequest(
            task="sentiment", stage="model_training", step="connect",
            action_type="connect.concept_matching", reference_prompt="Explain training.",
            existing_lesson=existing_lesson,
        )

    def test_openrouter_chat_completion_preserves_schema_and_bearer_token(self):
        for reuse in (False, True):
            with self.subTest(reuse=reuse):
                lesson = lesson_with(SECTION_ORDER)
                generated = QUESTION if reuse else {"lesson": lesson, "question": QUESTION}
                response = io.BytesIO(json.dumps({"choices": [{
                    "finish_reason": "stop", "message": {"content": json.dumps(generated)},
                }]}).encode())
                config = {
                    "TUTOR_LLM_PROVIDER": "openrouter", "OPENROUTER_MODEL": "openrouter/free",
                    "OPENROUTER_CHAT_URL": "https://openrouter.ai/api/v1/chat/completions",
                    "OPENROUTER_API_KEY": "test-secret", "ENVIRONMENT": "production",
                }
                with patch.dict(os.environ, config), patch("app.tutoring.generator.urlopen", return_value=response) as call:
                    result = generate_tutor_content(self.context(lesson if reuse else None), "fixture")
                request = call.call_args.args[0]
                payload = json.loads(request.data)
                self.assertEqual(request.full_url, config["OPENROUTER_CHAT_URL"])
                self.assertEqual(request.get_header("Authorization"), "Bearer test-secret")
                self.assertEqual(payload["model"], config["OPENROUTER_MODEL"])
                self.assertEqual(payload["response_format"]["type"], "json_schema")
                schema = payload["response_format"]["json_schema"]["schema"]
                self.assertEqual(
                    set(schema["properties"]),
                    set(QUESTION) if reuse else {"lesson", "question"},
                )
                self.assertEqual(result.content.question, QUESTION["question"])
                self.assertEqual(result.model, config["OPENROUTER_MODEL"])

    def test_production_openrouter_requires_key(self):
        with patch.dict(os.environ, {
            "TUTOR_LLM_PROVIDER": "openrouter", "OPENROUTER_API_KEY": "", "ENVIRONMENT": "production",
        }), self.assertRaisesRegex(TutorGenerationUnavailable, "OPENROUTER_API_KEY"):
            generate_tutor_content(self.context(), "fixture")


if __name__ == "__main__":
    unittest.main()
