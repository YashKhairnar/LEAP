from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import asdict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..execution.datasets import dataset_for_task
from .lesson_code import EXPERIMENT_VERSION, fixed_code_experiments, fixed_lesson_code
from ..models import (
    GeneratedLessonContent,
    TutorContent,
    TutorGenerationRequest,
    TutorGenerationResponse,
)

TUTOR_PROMPT_VERSION = f"analogy_preference_v14.{EXPERIMENT_VERSION}"

TUTOR_SCHEMA = {
    "type": "object",
    "properties": {
        "lesson": {"type": "object", "properties": {
            "title": {"type": "string"}, "introduction": {"type": "string"},
            "sections": {"type": "array", "minItems": 5, "maxItems": 6, "items": {
                "type": "object", "properties": {
                    "type": {"type": "string", "enum": ["meaning", "concept", "analogy", "example", "code", "result", "why_it_matters"]},
                    "title": {"type": "string"}, "body": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
                    "code": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                    "language": {"anyOf": [{"type": "string"}, {"type": "null"}]}
                }, "required": ["type", "title", "body", "items", "code", "language"], "additionalProperties": False
            }},
            "code_explanation": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 6},
            "key_takeaway": {"type": "string", "minLength": 1, "maxLength": 160}
        }, "required": ["title", "introduction", "sections", "code_explanation", "key_takeaway"], "additionalProperties": False},
        "question": {"type": "object", "properties": {
            "question": {"type": "string", "minLength": 1},
            "options": {"type": "array", "items": {"type": "string"}, "minItems": 3, "maxItems": 4},
            "expected_answer": {"type": "string", "minLength": 1},
            "hint": {"type": "string", "minLength": 1},
            "explanation": {"type": "string", "minLength": 1},
            "concepts_tested": {"type": "array", "items": {"type": "string"}}
        }, "required": ["question", "options", "expected_answer", "hint", "explanation", "concepts_tested"], "additionalProperties": False},
    },
    "required": ["lesson", "question"],
    "additionalProperties": False,
}

QUESTION_SCHEMA = TUTOR_SCHEMA["properties"]["question"]


class TutorGenerationUnavailable(RuntimeError):
    pass


logger = logging.getLogger(__name__)


def _lesson_with_fixed_code(lesson: dict, task: str, stage: str) -> GeneratedLessonContent:
    """Server-owned code and experiments win over generated or cached content."""
    canonical = fixed_lesson_code(task, stage)
    return GeneratedLessonContent.model_validate({
        **lesson,
        "sections": [
            {**section, "code": canonical.code, "language": canonical.language}
            if section.get("type") == "code" else section
            for section in lesson["sections"]
        ],
        "try_this": [asdict(experiment) for experiment in fixed_code_experiments(task, stage)],
    })


def generate_tutor_content(
    context: TutorGenerationRequest,
    content_instance_id: str,
) -> TutorGenerationResponse:
    provider = os.getenv("TUTOR_LLM_PROVIDER", "ollama").lower()
    if provider == "openrouter":
        model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
        endpoint = os.getenv("OPENROUTER_CHAT_URL", "https://openrouter.ai/api/v1/chat/completions")
        timeout = float(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "180"))
        api_key = os.getenv("OPENROUTER_API_KEY")
        if os.getenv("ENVIRONMENT", "development").lower() == "production" and not api_key:
            raise TutorGenerationUnavailable("OPENROUTER_API_KEY is required in production")
    elif provider == "ollama":
        model = os.getenv("OLLAMA_MODEL", "qwen3:8b")
        endpoint = os.getenv("OLLAMA_CHAT_URL", "http://127.0.0.1:11434/api/chat")
        timeout = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180"))
    else:
        raise TutorGenerationUnavailable(f"Unsupported tutor LLM provider: {provider}")
    dataset = dataset_for_task(context.task).public()
    canonical_code = fixed_lesson_code(context.task, context.stage)
    existing_lesson = (
        _lesson_with_fixed_code(context.existing_lesson.model_dump(), context.task, context.stage)
        if context.existing_lesson is not None else None
    )
    audience = (
        "You are LEAP, a tutor helping learners understand Python code used for machine learning. "
        "Assume little or no machine-learning knowledge. All implementation, APIs and code snippets must be Python. "
    )
    if context.analogy_preference == "java":
        audience += (
            "The learner has opted into Java references. Use familiar Java concepts such as objects, collections, "
            "methods, loops and types as conceptual bridges, only in prose. Do not assume a particular Java proficiency; "
            "briefly define the Java concept before using it. Never output Java source code or syntax, "
            "mention Java ML libraries, or implement machine learning in Java. "
        )
        analogy_instruction = (
            "(2) analogy: connect the concept directly to one simple Java language or standard-library idea. "
            "Explain the correspondence and an important difference in prose, without Java code. "
        )
    elif context.analogy_preference == "everyday":
        audience += (
            "The learner selected everyday-life analogies and opted out of Java references. Keep the instructional focus on Python and machine-learning concepts. "
            "Use everyday, real-life analogies, such as sorting groceries, "
            "learning from practice examples, or checking a recipe. Do not mention Java, Java APIs, Java syntax or Java "
            "comparisons anywhere in the lesson, question, options, hint, explanation or takeaway. Do not assume prior "
            "Java knowledge, regardless of reported experience. If action identifiers or curriculum metadata refer to "
            "Java, preserve the underlying learning objective but explain it using everyday experience and Python only. "
        )
        analogy_instruction = (
            "(2) analogy: use one simple everyday situation, explain how it maps to the ML concept, and point out "
            "where the comparison stops being accurate. Do not use a programming-language analogy. "
        )
    else:
        audience += (
            "The learner selected the pure machine-learning path and opted out of Java references. Explain the machine-learning concepts and Python implementation directly, "
            "without analogy framing, Java references, or everyday-life comparisons. Do not mention Java, Java APIs, Java syntax or Java comparisons. "
        )
        analogy_instruction = (
            "(2) concept section: do not present an analogy. State the direct machine-learning relationship, constraint, or mechanism "
            "that the learner must understand for this stage. Use precise ML terminology and define it briefly when needed. "
        )
    lesson_sequence_instruction = (
        "The lesson must contain exactly these six sections, exactly once, in this order: meaning, concept, example, code, result, why_it_matters. "
        if context.analogy_preference == "pure_ml" else
        "The lesson must contain exactly these six sections, exactly once, in this order: meaning, analogy, example, code, result, why_it_matters. "
    )
    if existing_lesson is None:
        system = audience + (
            "First create clear learner-facing instructional content for the requested stage that remains useful throughout "
            "the three-step flow: Bridge, Apply, and Check. " + lesson_sequence_instruction + "Follow these requirements for each section: "
            "(1) meaning: answer 'What is this concept?' with a short, plain-language definition. Define unfamiliar ML terms. "
            + analogy_instruction +
            "(3) example: give one very small, concrete, easy-to-follow example grounded in the supplied dataset. It must lead "
            "directly into the canonical code: use the same scenario, operation, variable meanings, and input/output relationship "
            "that the code demonstrates. Use only the minimum values or records needed to make the concept visible. "
            "(4) code: show only the Python needed for this stage's concept. Put Python exclusively in the code field. The body "
            "must be one short prose instruction describing what to do or notice; never copy, flatten, paraphrase, or enumerate "
            "the code in the body or items fields. "
            "(5) result: state exactly what the supplied code produces. If it prints output, show a concise representative "
            "output using supplied dataset facts; if it creates or changes an object without printing, explicitly say that and "
            "describe the resulting object or state. Briefly explain why that result occurred. Never claim that earlier or later "
            "pipeline work was performed by this code. "
            "(6) why_it_matters: connect this stage to the overall ML pipeline, including what it receives, what it passes to the "
            "next stage, and when or why the concept is used. Keep every section focused on its assigned purpose and avoid "
            "repeating information across sections. Use the items field only when a few concise values or steps improve clarity. "
            "Do not include Markdown heading markers such as # or #### inside titles or section bodies because the interface "
            "supplies its own numbered visual hierarchy. "
            "The context supplies canonical_lesson_code. Include exactly one code section and copy that code verbatim; do not "
            "rewrite, shorten, extend, or replace it. Generate the explanation around that fixed code. Also return two to six "
            "code_explanation entries. Each entry must name one actual function, method call, argument, operator, or assignment "
            "from canonical_lesson_code and explain its job in plain language. Use the format 'code element — explanation'. Cover "
            "the central operation without explaining trivial syntax. The application supplies fixed code experiments separately. "
            "Do not generate try_this, alternative code, or exploration instructions in any lesson field. "
            "Finally, return key_takeaway as one concrete sentence of at most 18 words summarizing the stage. "
            "Keep the introduction focused, but give section bodies enough context for a novice to understand the purpose and "
            "reasoning without guessing. Avoid repetition and filler. For non-code sections set code and language "
            "to null; for code sections provide both. "
            "All code must run against the supplied dataset. Use its runtime_filename exactly and do not invent files, "
            "columns, or rows. The available execution packages are pandas, NumPy, scikit-learn, matplotlib, and CPU-only "
            "PyTorch. For the image-classification task, describe and use the supplied PyTorch CNN code; never substitute "
            "TensorFlow, Keras, or a non-convolutional classifier. "
            "Then create one question grounded specifically in that lesson and matching the selected action. Ask only about "
            "ideas that the lesson explicitly explained, and test reasoning rather than unexplained terminology or memorization. "
            "The lesson must contain enough information to work out the answer without guessing. "
            "Always make the question multiple-choice with three or four options and make expected_answer "
            "exactly equal to one option. The explanation must state why the correct option is correct, why each distractor is "
            "incorrect, and how the answer connects to the ML pipeline. Return only JSON matching the supplied schema."
        )
        response_schema = TUTOR_SCHEMA
    else:
        system = audience + (
            "Create only one multiple-choice question "
            "grounded in the supplied fixed stage lesson and matching the selected instructional action. "
            "Do not rewrite or replace the lesson. Ask only about concepts explicitly explained in that lesson, and ensure the "
            "learner can reason out the answer rather than guess from unexplained terminology. Use three or four distinct, "
            "plausible options and make expected_answer exactly equal to one option. The explanation must define the relevant "
            "concept in plain language, explain why the correct option is correct, explain why every distractor is incorrect, "
            "and connect the answer to the overall ML pipeline. Return only JSON matching the supplied schema."
        )
        response_schema = QUESTION_SCHEMA
    user = {
        "location": {"task": context.task, "stage": context.stage, "step": context.step},
        "selected_action": context.action_type.value,
        "reference_prompt": (
            context.reference_prompt if context.analogy_preference == "java" else
            f"Explain {context.stage.replace('_', ' ')} using the supplied dataset, Python code and "
            + ("everyday-life analogies." if context.analogy_preference == "everyday" else "direct machine-learning explanations without analogies.")
        ),
        "learner_preferences": {"analogy_preference": context.analogy_preference,
                                "java_experience": context.java_experience},
        "learning_objectives": context.learning_objectives,
        "dataset": dataset,
        "canonical_lesson_code": {
            "version": canonical_code.version,
            "language": canonical_code.language,
            "code": canonical_code.code,
        },
        "fixed_code_experiments": [asdict(experiment) for experiment in fixed_code_experiments(context.task, context.stage)],
        "fixed_stage_lesson": existing_lesson.model_dump() if existing_lesson else None,
    }
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": "Generate the next tutoring question from this context:\n" + json.dumps(user)},
    ]
    headers = {"Content-Type": "application/json"}
    if provider == "openrouter":
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": 0.7,
            "max_tokens": int(os.getenv("OPENROUTER_MAX_TOKENS", "4096")),
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "leap_tutor", "schema": response_schema, "strict": True,
            }},
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
    else:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "think": False,
            "format": response_schema,
            "options": {"temperature": 0.2},
        }
    request = Request(endpoint, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            outer = json.loads(response.read().decode())
        if provider == "openrouter":
            choice = outer["choices"][0]
            if choice.get("finish_reason") == "length":
                raise ValueError("OpenRouter response exceeded OPENROUTER_MAX_TOKENS")
            generated = json.loads(choice["message"]["content"])
        else:
            generated = json.loads(outer["message"]["content"])
        if existing_lesson is None:
            lesson = _lesson_with_fixed_code(generated["lesson"], context.task, context.stage)
            question_payload = generated["question"]
        else:
            lesson = existing_lesson
            question_payload = generated
        if not str(question_payload.get("hint", "")).strip():
            question_payload["hint"] = "Use the lesson example to reason through the answer."
        content = TutorContent.model_validate(question_payload)
        if context.analogy_preference in {"everyday", "pure_ml"} and re.search(
            r"\b(?:java|ArrayList|HashMap|System\.out)\b",
            json.dumps({"lesson": lesson.model_dump(), "question": content.model_dump()}), re.IGNORECASE,
        ):
            raise ValueError("Generated content included Java references despite the everyday-example preference. Please try again.")
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:1000]
        logger.error("Tutor generation HTTP failure: provider=%s model=%s status=%s detail=%s", provider, model, error.code, detail)
        raise TutorGenerationUnavailable(f"LLM provider returned HTTP {error.code}: {detail}") from error
    except (URLError, TimeoutError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        logger.exception("Tutor generation failed: provider=%s model=%s endpoint=%s", provider, model, endpoint)
        raise TutorGenerationUnavailable(str(error)) from error
    return TutorGenerationResponse(
        content_instance_id=content_instance_id,
        model=model,
        prompt_version=TUTOR_PROMPT_VERSION,
        code_version=canonical_code.version,
        dataset=dataset,
        lesson=lesson,
        content=content,
    )
