import pytest
import torch

from leap.concepts import ConceptProbe, masked_probe_loss


def test_probe_shape_and_masked_gradients():
    model = ConceptProbe(state_dim=8, concept_count=4)
    logits = model(torch.randn(3, 8))
    targets = torch.rand(3, 4)
    mask = torch.tensor(
        [[True, False, False, False], [False, True, False, False], [False, False, True, True]]
    )

    loss = masked_probe_loss(logits, targets, mask)
    loss.backward()

    assert logits.shape == (3, 4)
    assert model.linear.weight.grad is not None


def test_probe_loss_rejects_empty_mask():
    with pytest.raises(ValueError, match="no supervised"):
        masked_probe_loss(torch.zeros(2, 4), torch.zeros(2, 4), torch.zeros(2, 4).bool())
