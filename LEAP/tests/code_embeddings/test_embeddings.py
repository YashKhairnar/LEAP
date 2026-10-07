import json

import torch

from leap.code_embeddings.store import code_sha256, generate_embedding_store, load_embedding_store


class FakeEncoder:
    embedding_dim = 3

    def encode(self, code: list[str]) -> torch.Tensor:
        return torch.tensor([[len(value), value.count("\n"), 1.0] for value in code])


def test_generate_embedding_store_deduplicates_code(tmp_path) -> None:
    trajectories = tmp_path / "trajectories.jsonl"
    records = [
        {"trajectory_id": "a", "attempts": [{"code": "x = 1"}, {"code": "x = 2"}]},
        {"trajectory_id": "b", "attempts": [{"code": "x = 1"}]},
    ]
    trajectories.write_text("".join(json.dumps(row) + "\n" for row in records), encoding="utf-8")

    output = tmp_path / "embeddings.pt"
    summary = generate_embedding_store(
        trajectories, output, FakeEncoder(), checkpoint="fake", batch_size=1
    )
    store = load_embedding_store(output)

    assert summary["unique_submissions"] == 2
    assert store["code_hashes"] == [code_sha256("x = 1"), code_sha256("x = 2")]
    assert store["embeddings"].shape == (2, 3)

