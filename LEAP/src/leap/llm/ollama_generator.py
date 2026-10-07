"""Generate validated tutoring content with a local Ollama model."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TUTOR_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "options": {
            "anyOf": [
                {"type": "array", "items": {"type": "string"}},
                {"type": "null"},
            ]
        },
        "expected_answer": {"type": "string"},
        "hint": {"type": "string"},
        "explanation": {"type": "string"},
        "concepts_tested": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "question",
        "options",
        "expected_answer",
        "hint",
        "explanation",
        "concepts_tested",
    ],
    "additionalProperties": False,
}


class OllamaGenerationError(RuntimeError):
    """Raised when Ollama cannot produce a valid tutor response."""


def validate_tutor_response(value: Any) -> dict[str, Any]:
    """Validate the small response contract without adding a schema dependency."""
    if not isinstance(value, dict):
        raise TypeError("tutor response must be a JSON object")

    required = set(TUTOR_RESPONSE_SCHEMA["required"])
    missing = required - set(value)
    extra = set(value) - required
    if missing:
        raise ValueError(f"tutor response is missing fields: {sorted(missing)}")
    if extra:
        raise ValueError(f"tutor response has unexpected fields: {sorted(extra)}")

    for field in ("question", "expected_answer", "hint", "explanation"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise ValueError(f"{field} must be a non-empty string")

    normalized_question = value["question"].strip().lower()
    instruction_echoes = (
        "show a minimal",
        "create a short",
        "create a minimal",
        "present several possible",
        "provide a shuffled list",
        "provide programming concepts",
        "give a focused implementation goal",
    )
    if normalized_question.startswith(instruction_echoes):
        raise ValueError(
            "question repeats a catalog instruction instead of including the requested "
            "learner-facing example, code, choices, or list"
        )

    options = value["options"]
    if options is not None and (
        not isinstance(options, list)
        or not all(isinstance(option, str) and option.strip() for option in options)
    ):
        raise ValueError("options must be null or an array of non-empty strings")

    concepts = value["concepts_tested"]
    if not isinstance(concepts, list) or not all(
        isinstance(concept, str) and concept.strip() for concept in concepts
    ):
        raise ValueError("concepts_tested must be an array of non-empty strings")

    return value


Transport = Callable[[Request, float], bytes]


def _default_transport(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:
        return response.read()


class OllamaTutorContentGenerator:
    """Call Ollama's local chat API and return schema-validated tutoring content."""

    def __init__(
        self,
        model: str = "qwen3:8b",
        *,
        endpoint: str = "http://127.0.0.1:11434/api/chat",
        timeout_seconds: float = 180.0,
        max_retries: int = 2,
        temperature: float = 0.2,
        transport: Transport | None = None,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self.model = model
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.temperature = temperature
        self._transport = transport or _default_transport

    def _request(self, messages: Sequence[dict[str, str]]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": list(messages),
            "stream": False,
            "think": False,
            "format": TUTOR_RESPONSE_SCHEMA,
            "options": {"temperature": self.temperature},
        }
        request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        raw = self._transport(request, self.timeout_seconds)
        response = json.loads(raw.decode("utf-8"))
        content = response.get("message", {}).get("content")
        if not isinstance(content, str):
            raise TypeError("Ollama response does not contain message.content")
        return json.loads(content)

    def generate(self, messages: Sequence[dict[str, str]]) -> dict[str, Any]:
        if not messages:
            raise ValueError("messages cannot be empty")

        errors: list[str] = []
        retry_messages = list(messages)
        for attempt in range(self.max_retries + 1):
            try:
                return validate_tutor_response(self._request(retry_messages))
            except (
                HTTPError,
                URLError,
                TimeoutError,
                json.JSONDecodeError,
                TypeError,
                ValueError,
            ) as error:
                errors.append(f"attempt {attempt + 1}: {error}")
                if attempt < self.max_retries:
                    retry_messages = [
                        *messages,
                        {
                            "role": "user",
                            "content": (
                                f"The previous output was invalid because: {error}. Correct "
                                "that problem. Return only one JSON object that exactly matches "
                                "the required schema."
                            ),
                        },
                    ]

        raise OllamaGenerationError(
            f"Ollama failed to generate valid tutor content with {self.model}: "
            + "; ".join(errors)
        )
