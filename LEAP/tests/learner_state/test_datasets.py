import json

import torch

from leap.learner_state.data.datasets import TrajectoryDataset
from leap.code_embeddings.store import code_sha256


def test_trajectory_dataset_builds_metadata_and_padding(tmp_path) -> None:
    attempts = [
        {"attempt_number": 1, "code": "x = 1", "correct": False},
        {"attempt_number": 2, "code": "x = 2", "correct": True},
        {"attempt_number": 3, "code": "x = 3", "correct": False},
    ]
    trajectory_path = tmp_path / "trajectories.jsonl"
    trajectory_path.write_text(
        json.dumps({"trajectory_id": "student__task", "attempts": attempts}) + "\n",
        encoding="utf-8",
    )
    embedding_path = tmp_path / "embeddings.pt"
    torch.save(
        {
            "format_version": 1,
            "checkpoint": "fake",
            "embedding_dim": 2,
            "code_hashes": [code_sha256(item["code"]) for item in attempts],
            "embeddings": torch.tensor([[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]),
        },
        embedding_path,
    )

    item = TrajectoryDataset(
        trajectory_path, embedding_path, max_attempts=4, truncation="latest"
    )[0]

    assert item["code_embeddings"].shape == (4, 2)
    assert item["metadata"].tolist() == [
        [0.25, 0.0, 1.0],
        [0.5, 0.0, 0.0],
        [0.75, 1.0, 0.0],
        [0.0, 0.0, 0.0],
    ]
    assert item["padding_mask"].tolist() == [False, False, False, True]
    assert item["attempt_count"] == 3

