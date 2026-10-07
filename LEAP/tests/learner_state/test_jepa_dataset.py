import json

import torch

from leap.learner_state.data import JEPAPrefixDataset, create_student_splits
from leap.code_embeddings.store import code_sha256


def write_fixture(tmp_path):
    trajectory_path = tmp_path / "trajectories.jsonl"
    records = []
    all_code = []
    for student_index in range(6):
        attempts = [
            {
                "attempt_number": number,
                "code": f"student_{student_index}_attempt_{number}",
                "correct": number % 2 == 0,
            }
            for number in range(1, 6)
        ]
        records.append(
            {
                "trajectory_id": f"student_{student_index}__task",
                "student_id": f"student_{student_index}",
                "attempts": attempts,
            }
        )
        all_code.extend(attempt["code"] for attempt in attempts)
    trajectory_path.write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8"
    )

    embedding_path = tmp_path / "embeddings.pt"
    torch.save(
        {
            "format_version": 1,
            "checkpoint": "fake",
            "embedding_dim": 2,
            "code_hashes": [code_sha256(code) for code in all_code],
            "embeddings": torch.arange(len(all_code) * 2, dtype=torch.float32).reshape(-1, 2),
        },
        embedding_path,
    )
    return trajectory_path, embedding_path


def test_student_splits_are_deterministic_and_disjoint(tmp_path) -> None:
    trajectory_path, _ = write_fixture(tmp_path)
    first = create_student_splits(
        trajectory_path, tmp_path / "first.json", train_ratio=0.5, validation_ratio=0.25,
        test_ratio=0.25, seed=7
    )
    second = create_student_splits(
        trajectory_path, tmp_path / "second.json", train_ratio=0.5, validation_ratio=0.25,
        test_ratio=0.25, seed=7
    )
    assert first["splits"] == second["splits"]
    split_sets = [set(first["splits"][name]) for name in ("train", "validation", "test")]
    assert not (split_sets[0] & split_sets[1] or split_sets[0] & split_sets[2] or split_sets[1] & split_sets[2])


def test_jepa_prefix_dataset_shapes_and_rolling_window(tmp_path) -> None:
    trajectory_path, embedding_path = write_fixture(tmp_path)
    dataset = JEPAPrefixDataset(trajectory_path, embedding_path, max_attempts=3)

    # Four transitions for each of six five-attempt trajectories.
    assert len(dataset) == 24
    late_example = dataset[3]
    assert late_example["target_attempt_number"] == 5
    assert late_example["context_embeddings"].shape == (3, 2)
    assert late_example["target_embeddings"].shape == (3, 2)
    assert late_example["context_padding_mask"].tolist() == [False, False, True]
    assert late_example["target_padding_mask"].tolist() == [False, False, False]
    # The rolling target window for attempt five contains attempts three, four, and five.
    assert late_example["target_metadata"][:, 1].tolist() == [1.0, 0.0, 1.0]


def test_jepa_dataset_respects_student_split(tmp_path) -> None:
    trajectory_path, embedding_path = write_fixture(tmp_path)
    split_path = tmp_path / "splits.json"
    manifest = create_student_splits(
        trajectory_path, split_path, train_ratio=0.5, validation_ratio=0.25,
        test_ratio=0.25, seed=42
    )
    dataset = JEPAPrefixDataset(
        trajectory_path, embedding_path, max_attempts=3, split_path=split_path, split="train"
    )
    assert {dataset[index]["student_id"] for index in range(len(dataset))} == set(
        manifest["splits"]["train"]
    )
