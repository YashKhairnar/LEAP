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


class GeminiTutorTests(unittest.TestCase):
    def context(self, existing_lesson=None):
        return TutorGenerationRequest(
            task="sentiment", stage="model_training", step="connect",
            action_type="connect.concept_matching", reference_prompt="Explain training.",
            existing_lesson=existing_lesson,
        )

    def test_gemini_generation_preserves_schema_and_api_key(self):
        for reuse in (False, True):
            with self.subTest(reuse=reuse):
                lesson = lesson_with(SECTION_ORDER)
                generated = QUESTION if reuse else {"lesson": lesson, "question": QUESTION}
                response = io.BytesIO(json.dumps({"candidates": [{
                    "finishReason": "STOP",
                    "content": {"parts": [{"text": json.dumps(generated)}]},
                }]}).encode())
                config = {
                    "TUTOR_LLM_PROVIDER": "gemini", "GEMINI_MODEL": "gemini-2.5-flash",
                    "GEMINI_API_URL": "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    "GEMINI_API_KEY": "test-secret", "ENVIRONMENT": "production",
                }
                with patch.dict(os.environ, config), patch("app.tutoring.generator.urlopen", return_value=response) as call:
                    result = generate_tutor_content(self.context(lesson if reuse else None), "fixture")
                request = call.call_args.args[0]
                payload = json.loads(request.data)
                self.assertEqual(request.full_url, config["GEMINI_API_URL"].format(model=config["GEMINI_MODEL"]))
                self.assertEqual(request.get_header("X-goog-api-key"), "test-secret")
                self.assertEqual(payload["generationConfig"]["responseMimeType"], "application/json")
                schema = payload["generationConfig"]["responseJsonSchema"]
                self.assertEqual(
                    set(schema["properties"]),
                    set(QUESTION) if reuse else {"lesson", "question"},
                )
                self.assertEqual(result.content.question, QUESTION["question"])
                self.assertEqual(result.model, config["GEMINI_MODEL"])

    def test_production_gemini_requires_key(self):
        with patch.dict(os.environ, {
            "TUTOR_LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "", "ENVIRONMENT": "production",
        }), self.assertRaisesRegex(TutorGenerationUnavailable, "GEMINI_API_KEY"):
            generate_tutor_content(self.context(), "fixture")


if __name__ == "__main__":
    unittest.main()
