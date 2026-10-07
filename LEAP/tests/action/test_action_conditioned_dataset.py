import json

import torch

from leap.action.data import ActionConditionedDataset
from leap.action.data.prompt_embeddings import prompt_sha256
from leap.observation.data.response_embeddings import response_sha256


def test_conditioned_dataset_separates_context_from_current_outcome(tmp_path):
    actions = [
        {
            "transition_id": "t1", "learner_id": "l1", "session_id": "s1",
            "sequence_index": 1, "task": "task", "stage": "stage", "step": "step",
            "action_type": "question", "content_id": "c1", "prompt": "Prompt one",
        },
        {
            "transition_id": "t2", "learner_id": "l1", "session_id": "s1",
            "sequence_index": 2, "task": "task", "stage": "stage", "step": "step",
            "action_type": "question", "content_id": "c2", "prompt": "Prompt two",
        },
    ]
    observations = [
        {
            "transition_id": "t1", "learner_id": "l1", "session_id": "s1",
            "sequence_index": 1, "response": "First", "correct": True,
            "score": 1.0, "attempt": 1, "response_time_ms": 1000,
        },
        {
            "transition_id": "t2", "learner_id": "l1", "session_id": "s1",
            "sequence_index": 2, "response": "Second", "correct": False,
            "score": 0.0, "attempt": 1, "response_time_ms": 2000,
        },
    ]
    action_path = tmp_path / "actions.jsonl"
    observation_path = tmp_path / "observations.jsonl"
    action_path.write_text("".join(json.dumps(x) + "\n" for x in actions))
    observation_path.write_text("".join(json.dumps(x) + "\n" for x in observations))
    vocabularies = {
        field: {"<UNK>": 0, **{str(value): i + 1 for i, value in enumerate(sorted({x[field] for x in actions}))}}
        for field in ("task", "stage", "step", "action_type", "content_id")
    }
    vocabulary_path = tmp_path / "vocab.json"
    vocabulary_path.write_text(json.dumps(vocabularies))
    prompt_path = tmp_path / "prompts.pt"
    torch.save({
        "format_version": 1, "checkpoint": "test", "embedding_dim": 3,
        "prompt_hashes": [prompt_sha256(x["prompt"]) for x in actions],
        "embeddings": torch.randn(2, 3),
    }, prompt_path)
    response_path = tmp_path / "responses.pt"
    torch.save({
        "format_version": 1, "checkpoint": "test", "embedding_dim": 4,
        "response_hashes": [response_sha256(x["response"]) for x in observations],
        "embeddings": torch.randn(2, 4),
    }, response_path)

    dataset = ActionConditionedDataset(
        action_path, observation_path, vocabulary_path, prompt_path, response_path,
        max_history=3,
    )

    first = dataset[0]
    second = dataset[1]
    assert first["context_padding_mask"].tolist() == [True, True, True]
    assert first["target_padding_mask"].tolist() == [False, True, True]
    assert second["context_padding_mask"].tolist() == [False, True, True]
    assert second["target_padding_mask"].tolist() == [False, False, True]
    assert second["context_numeric_features"][0, 0].item() == 1.0
    assert second["target_numeric_features"][1, 0].item() == 0.0
