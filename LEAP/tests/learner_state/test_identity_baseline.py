import torch
from torch import nn

from leap.learner_state.training import evaluate_identity_baseline


class FakeIdentityModel(nn.Module):
    def forward(
        self,
        context_embeddings,
        context_metadata,
        context_padding_mask,
        target_embeddings,
        target_metadata,
        target_padding_mask,
    ):
        current = context_embeddings[:, 0, :]
        target = target_embeddings[:, 0, :]
        predicted = target.clone()
        return predicted, target, current


def test_identity_baseline_detects_predictor_improvement() -> None:
    batch = {
        "context_embeddings": torch.tensor([[[1.0, 0.0]], [[0.0, 1.0]]]),
        "target_embeddings": torch.tensor([[[0.0, 1.0]], [[1.0, 0.0]]]),
        "context_metadata": torch.zeros(2, 1, 3),
        "target_metadata": torch.zeros(2, 1, 3),
        "context_padding_mask": torch.zeros(2, 1, dtype=torch.bool),
        "target_padding_mask": torch.zeros(2, 1, dtype=torch.bool),
    }
    metrics = evaluate_identity_baseline(FakeIdentityModel(), [batch], "cpu")
    assert metrics["predicted_target_cosine"] == 1.0
    assert metrics["identity_target_cosine"] == 0.0
    assert metrics["mean_improvement"] == 1.0
    assert metrics["predictor_win_rate"] == 1.0
