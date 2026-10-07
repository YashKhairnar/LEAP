"""Run one-step planning with three real actions and the handcrafted binary goal."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import torch

from leap.action.data import ActionConditionedDataset
from leap.action.data.prompt_embeddings import PromptEmbeddingLookup
from leap.action.training import build_experiment_one, load_experiment_checkpoint
from leap.concepts import ConceptProbe
from leap.concepts.probe_training import load_probe_checkpoint
from leap.planning import OneStepPlanner, handcrafted_binary_goal
from leap.shared.config import load_json_config


def _load_actions(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("outputs/action/checkpoints/experiment_one_100/best_validation.pt"),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--probe-checkpoint",
        type=Path,
        default=Path("outputs/concepts/checkpoints/probe_v2/best_validation.pt"),
    )
    args = parser.parse_args()

    config = load_json_config("configs/action/experiment_one.json")
    temporal_config = load_json_config("configs/learner_state/temporal_encoder.json")
    model = build_experiment_one(config, temporal_config)
    load_experiment_checkpoint(args.checkpoint, model)
    model.eval()

    grouped: defaultdict[tuple[str, str, str], dict[tuple[str, str], dict]] = defaultdict(dict)
    for action in _load_actions(config["action_data_path"]):
        location = (action["task"], action["stage"], action["step"])
        grouped[location][(action["action_type"], action["content_id"])] = action
    location, action_map = next(
        (location, actions) for location, actions in grouped.items() if len(actions) == 3
    )
    candidates = list(action_map.values())

    dataset = ActionConditionedDataset(
        config["action_data_path"],
        config["observation_data_path"],
        config["action_vocabulary_path"],
        config["prompt_embedding_path"],
        config["response_embedding_path"],
        max_history=int(config["max_history"]),
        split_path=config["split_path"],
        split="validation",
    )
    example_index = next(
        index
        for index, (_, action, _) in enumerate(dataset.examples)
        if (action["task"], action["stage"], action["step"]) == location
    )
    example = dataset[example_index]
    history = {
        key: value.unsqueeze(0)
        for key, value in example.items()
        if isinstance(value, torch.Tensor) and key.startswith("context_")
    }

    with Path(config["action_vocabulary_path"]).open(encoding="utf-8") as file:
        vocabularies = json.load(file)
    prompt_lookup = PromptEmbeddingLookup(config["prompt_embedding_path"])
    candidate_batch = {
        f"{field}_id" if field != "content_id" else field: torch.tensor(
            [[vocabularies[field].get(action[field], 0) for action in candidates]]
        )
        for field in ("task", "stage", "step", "action_type", "content_id")
    }
    candidate_batch["prompt_embedding"] = torch.stack(
        [prompt_lookup.get_prompt(action["prompt"]) for action in candidates]
    ).unsqueeze(0)

    probe = ConceptProbe()
    load_probe_checkpoint(
        args.probe_checkpoint,
        probe,
        expected_experiment="concept_probe_predicted_state_v2",
    )
    planner = OneStepPlanner(model, concept_probe=probe)
    goal = handcrafted_binary_goal()
    result = planner.plan_from_history(history, candidate_batch, goal)
    selected = int(result["selected_indices"].item())
    report = {
        "checkpoint": str(args.checkpoint),
        "learner_id": example["learner_id"],
        "location": {"task": location[0], "stage": location[1], "step": location[2]},
        "goal": goal.tolist(),
        "current_state": result["current_state"][0].tolist(),
        "selected_index": selected,
        "selected_action": {
            key: candidates[selected][key]
            for key in ("action_type", "content_id", "prompt")
        },
        "selected_concept_mastery": result["selected_concept_mastery"][0].tolist(),
        "candidates": [
            {
                "index": index,
                "action_type": action["action_type"],
                "content_id": action["content_id"],
                "prompt": action["prompt"],
                "cosine_distance": float(result["candidate_distances"][0, index]),
                "predicted_state": result["candidate_predicted_states"][0, index].tolist(),
            }
            for index, action in enumerate(candidates)
        ],
    }
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
