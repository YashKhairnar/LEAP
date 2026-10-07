"""Build LLM-ready context from the saved one-step planning demonstration."""

import argparse
import json
from pathlib import Path

from leap.concepts import ConceptVocabulary
from leap.llm import ActionSpecificationCatalog, LLMContextBuilder, TutorPromptBuilder


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--plan",
        type=Path,
        default=Path("outputs/planning/one_step_demo.json"),
    )
    parser.add_argument(
        "--actions",
        type=Path,
        default=Path("data/action/processed/action_data.jsonl"),
    )
    parser.add_argument(
        "--observations",
        type=Path,
        default=Path("data/observation/processed/observations.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/llm/demo_context.json"),
    )
    args = parser.parse_args()

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    selected = plan["selected_action"]
    action = next(
        record
        for record in _read_jsonl(args.actions)
        if record["content_id"] == selected["content_id"]
    )
    learner_observations = [
        record
        for record in _read_jsonl(args.observations)
        if record["learner_id"] == plan["learner_id"]
    ]
    learner_observations.sort(key=lambda item: (item["session_id"], item["sequence_index"]))
    recent = learner_observations[-3:]
    learner_context = {
        "learner_id": plan["learner_id"],
        "recent_correctness": [item["correct"] for item in recent],
        "recent_attempts": [item["attempt"] for item in recent],
        "recent_responses": [item["response"] for item in recent],
    }

    builder = LLMContextBuilder(
        ActionSpecificationCatalog("configs/llm/action_specifications_v1.json"),
        ConceptVocabulary("configs/concepts/concept_vocabulary_v2.json"),
    )
    context = builder.build(
        action,
        plan["selected_concept_mastery"],
        learner_context,
    )
    artifact = {
        "context": context,
        "messages": TutorPromptBuilder().build_messages(context),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2))


if __name__ == "__main__":
    main()
