# LLM tutoring context

Location: `src/leap/llm/`

This component prepares structured context and uses a local Ollama model to generate
tutoring content. It does not fine-tune an LLM or send learner data to a cloud API.

This describes the research/demo generator. The running website uses the separate
`backend/app/tutoring/generator.py` implementation: six-part lessons and practice questions
conditioned on the randomly delivered action, with server-owned code/experiments from
`tutoring/lesson_code.py`. It does not consume this demo's probe output as validated mastery.
The 12 observed catalog actions below describe the historical research data, not the full
18-action application enum (the current UI uses the connect/practice/review phases).

## Flow

```text
planner-selected action
+ predicted 64-D concept mastery
+ learner history summary
+ task, stage, and learning objectives
        ↓
ActionSpecificationCatalog
        ↓
LLMContextBuilder
        ↓
TutorPromptBuilder
        ↓
system message + structured user message
        ↓
OllamaTutorContentGenerator (Qwen3 8B)
        ↓
validated tutoring-question JSON
```

## Action specification catalog

`configs/llm/action_specifications_v1.json` defines all 12 observed action types. Each
entry tells the LLM:

- the pedagogical purpose;
- the question family and expected answer format;
- how to construct the question;
- elements that must be present;
- mistakes the generator must avoid.

The catalog separates action selection from content generation. The planner chooses the
action; the catalog explains how the LLM must realize it.

## Context builder

`LLMContextBuilder` adds the learner, location, selected action, learning objectives,
relevant concept-mastery scores, generation constraints, and output schema. Only concepts
targeted by the selected action are included; the raw 128-D state and unrelated 64-D
scores are excluded.

The mastery field is explicitly labeled experimental because predicted-state Probe V2 is
currently below its baseline.

`TutorPromptBuilder` turns the structured context into system and user messages and asks
for JSON containing the question, options when applicable, expected answer, hint,
explanation, and concepts tested. The system prompt requires finished learner-facing
content so the model does not echo catalog instructions in place of a question.

Build the demonstration context after running the planning demo:

```bash
python scripts/llm/build_demo_context.py
```

Output: `outputs/llm/demo_context.json`

## Local Qwen generation

The Ollama adapter calls `http://127.0.0.1:11434/api/chat` with streaming and model
thinking disabled. It supplies a JSON Schema for the six required output fields, validates
the decoded response, and retries malformed responses up to two times by default.

After installing Ollama and downloading `qwen3:8b`, generate a question with:

```bash
python scripts/llm/generate_tutor_content.py
```

Output: `outputs/llm/demo_tutor_content.json`

The model, paths, timeout, and retry count can be overridden:

```bash
python scripts/llm/generate_tutor_content.py \
  --model qwen3:8b \
  --context outputs/llm/demo_context.json \
  --output outputs/llm/demo_tutor_content.json \
  --timeout 180 \
  --max-retries 2
```
