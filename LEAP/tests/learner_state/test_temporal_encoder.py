import torch

from leap.learner_state.models import TemporalLearnerEncoder


def test_temporal_encoder_output_shape() -> None:
    model = TemporalLearnerEncoder(
        code_dim=8, d_model=16, state_dim=6, num_heads=4, feedforward_dim=32, max_attempts=5
    )
    result = model(torch.randn(2, 3, 8), torch.randn(2, 3, 3))
    assert result.shape == (2, 6)

