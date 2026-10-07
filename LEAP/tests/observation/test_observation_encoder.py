import torch

from leap.observation.models import ObservationEncoder


def test_observation_encoder_output_shape_and_gradients():
    model = ObservationEncoder(dropout=0.0)
    batch = {
        "response_embedding": torch.randn(8, 384),
        "numeric_features": torch.randn(8, 4),
    }
    output = model(batch)
    output.square().mean().backward()
    assert output.shape == (8, 256)
    assert all(parameter.grad is not None for parameter in model.parameters())
