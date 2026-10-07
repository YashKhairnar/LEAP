"""Create weak concept-mastery labels from tutoring transitions."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .vocabulary import ConceptVocabulary


def _read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]


def _active_concepts(action: dict[str, Any], vocabulary: ConceptVocabulary) -> list[str]:
    concepts: set[str] = set()
    for objective in action.get("learning_objectives", []):
        concepts.update(vocabulary.concepts_for_objective(action["task"], objective))
    if not concepts:
        concepts.update(vocabulary.concepts_for_stage(action["task"], action["stage"]))
    if not concepts:
        raise ValueError(f"No concept mapping for transition {action['transition_id']}")
    return sorted(concepts, key=vocabulary.indices.__getitem__)


def build_concept_labels(
    action_data_path: str | Path,
    observation_data_path: str | Path,
    vocabulary_path: str | Path,
) -> list[dict[str, Any]]:
    """Return chronological before/after mastery estimates for every transition.

    Mastery is the running mean of observed scores for a concept within one learner
    session. Masks distinguish unseen concepts from genuine zero-valued estimates.
    """
    vocabulary = ConceptVocabulary(vocabulary_path)
    actions = {record["transition_id"]: record for record in _read_jsonl(action_data_path)}
    observations = {
        record["transition_id"]: record for record in _read_jsonl(observation_data_path)
    }
    if actions.keys() != observations.keys():
        raise ValueError("Action and observation transition IDs differ")

    sessions: defaultdict[tuple[str, str], list[tuple[dict, dict]]] = defaultdict(list)
    for transition_id, action in actions.items():
        observation = observations[transition_id]
        if (
            str(action["learner_id"]) != str(observation["learner_id"])
            or str(action["session_id"]) != str(observation["session_id"])
            or int(action["sequence_index"]) != int(observation["sequence_index"])
        ):
            raise ValueError(f"Joined transition metadata differs for {transition_id}")
        sessions[(str(action["learner_id"]), str(action["session_id"]))].append(
            (action, observation)
        )

    labels: list[dict[str, Any]] = []
    for transitions in sessions.values():
        transitions.sort(key=lambda pair: int(pair[0]["sequence_index"]))
        score_sums = [0.0] * vocabulary.capacity
        evidence_counts = [0] * vocabulary.capacity
        for action, observation in transitions:
            score = float(observation["score"])
            if not 0.0 <= score <= 1.0:
                raise ValueError("Observation scores must be between zero and one")
            concept_ids = _active_concepts(action, vocabulary)
            concept_indices = [vocabulary.indices[value] for value in concept_ids]
            mastery_before = [
                score_sums[index] / evidence_counts[index]
                if evidence_counts[index]
                else 0.0
                for index in range(vocabulary.capacity)
            ]
            mastery_mask_before = [count > 0 for count in evidence_counts]

            for index in concept_indices:
                score_sums[index] += score
                evidence_counts[index] += 1

            mastery_after = [
                score_sums[index] / evidence_counts[index]
                if evidence_counts[index]
                else 0.0
                for index in range(vocabulary.capacity)
            ]
            mastery_mask_after = [count > 0 for count in evidence_counts]
            active_mask = [index in concept_indices for index in range(vocabulary.capacity)]
            evidence = [score if active else 0.0 for active in active_mask]
            labels.append(
                {
                    "transition_id": action["transition_id"],
                    "learner_id": str(action["learner_id"]),
                    "session_id": str(action["session_id"]),
                    "sequence_index": int(action["sequence_index"]),
                    "task": action["task"],
                    "stage": action["stage"],
                    "step": action["step"],
                    "active_concept_ids": concept_ids,
                    "active_concept_indices": concept_indices,
                    "active_concept_mask": active_mask,
                    "concept_evidence": evidence,
                    "mastery_before": mastery_before,
                    "mastery_mask_before": mastery_mask_before,
                    "mastery_after": mastery_after,
                    "mastery_mask_after": mastery_mask_after,
                    "evidence_counts_after": list(evidence_counts),
                }
            )
    labels.sort(
        key=lambda item: (item["learner_id"], item["session_id"], item["sequence_index"])
    )
    return labels


def write_concept_labels(
    action_data_path: str | Path,
    observation_data_path: str | Path,
    vocabulary_path: str | Path,
    output_path: str | Path,
) -> dict[str, Any]:
    labels = build_concept_labels(action_data_path, observation_data_path, vocabulary_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for label in labels:
            file.write(json.dumps(label) + "\n")
    observed_concepts = {
        concept_id for label in labels for concept_id in label["active_concept_ids"]
    }
    return {
        "records": len(labels),
        "observed_concepts": len(observed_concepts),
        "output_path": str(output_path),
    }
