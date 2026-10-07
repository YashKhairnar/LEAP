import json

import pytest

from leap.llm import (
    OllamaGenerationError,
    OllamaTutorContentGenerator,
    validate_tutor_response,
)

VALID_CONTENT = {
    "question": "Why is this Java list relevant to labeled ML examples?",
    "options": None,
    "expected_answer": "Each object can hold an input and its label.",
    "hint": "Think about fields stored in one object.",
    "explanation": "A record groups features with the label used during training.",
    "concepts_tested": ["labeled_example_representation"],
}


def _ollama_response(content):
    return json.dumps({"message": {"content": json.dumps(content)}}).encode()


def test_generator_sends_schema_and_returns_valid_content():
    captured = {}

    def transport(request, timeout):
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _ollama_response(VALID_CONTENT)

    result = OllamaTutorContentGenerator(transport=transport).generate(
        [{"role": "user", "content": "Generate it."}]
    )

    assert result == VALID_CONTENT
    assert captured["payload"]["format"]["required"]
    assert captured["payload"]["think"] is False
    assert captured["payload"]["stream"] is False


def test_generator_retries_invalid_content():
    responses = [
        _ollama_response({"question": "Incomplete"}),
        _ollama_response(VALID_CONTENT),
    ]

    def transport(_request, _timeout):
        return responses.pop(0)

    result = OllamaTutorContentGenerator(max_retries=1, transport=transport).generate(
        [{"role": "user", "content": "Generate it."}]
    )
    assert result == VALID_CONTENT


def test_generator_raises_after_retry_limit():
    def transport(_request, _timeout):
        return b"not-json"

    with pytest.raises(OllamaGenerationError, match="attempt 2"):
        OllamaTutorContentGenerator(max_retries=1, transport=transport).generate(
            [{"role": "user", "content": "Generate it."}]
        )


def test_validator_rejects_unknown_fields():
    with pytest.raises(ValueError, match="unexpected"):
        validate_tutor_response({**VALID_CONTENT, "extra": "field"})


def test_validator_rejects_catalog_instruction_echo():
    echoed = {
        **VALID_CONTENT,
        "question": "Show a minimal Java construct. Why is it relevant?",
    }
    with pytest.raises(ValueError, match="repeats a catalog instruction"):
        validate_tutor_response(echoed)
