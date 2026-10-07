import pytest
import torch

from leap.action.models import ActionConditionedPredictor


def test_action_conditioned_predictor_output_shape_and_gradients():
    model = ActionConditionedPredictor(state_dim=128, action_dim=32, dropout=0.0)
    learner_state = torch.randn(8, 128, requires_grad=True)
    action_vector = torch.randn(8, 32, requires_grad=True)

    output = model(learner_state, action_vector)
    output.square().mean().backward()

    assert output.shape == (8, 128)
    assert learner_state.grad is not None
    assert action_vector.grad is not None


def test_action_conditioned_predictor_rejects_mismatched_batch_sizes():
    model = ActionConditionedPredictor()

    with pytest.raises(ValueError, match="batch dimension"):
        model(torch.randn(8, 128), torch.randn(7, 32))
