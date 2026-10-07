import torch
from torch import nn

from leap.action.models import NoActionJEPA, NoActionPredictor
from leap.learner_state.models import TemporalLearnerEncoder
from leap.observation.models import ObservationEncoder


def test_no_action_model_ignores_action_fields_and_backpropagates():
    model = NoActionJEPA(
        ObservationEncoder(
            response_dim=12, hidden_dim=16, output_dim=16, dropout=0.0
        ),
        TemporalLearnerEncoder(
            code_dim=16,
            d_model=16,
            state_dim=8,
            num_layers=1,
            num_heads=2,
            feedforward_dim=24,
            max_attempts=3,
            dropout=0.0,
        ),
        NoActionPredictor(state_dim=8, hidden_dim=16, dropout=0.0),
    )
    batch_size, attempts = 2, 3
    batch = {
        "context_response_embeddings": torch.randn(batch_size, attempts, 12),
        "context_numeric_features": torch.randn(batch_size, attempts, 4),
        "context_metadata": torch.randn(batch_size, attempts, 3),
        "context_padding_mask": torch.zeros(batch_size, attempts, dtype=torch.bool),
        "target_response_embeddings": torch.randn(batch_size, attempts, 12),
        "target_numeric_features": torch.randn(batch_size, attempts, 4),
        "target_metadata": torch.randn(batch_size, attempts, 3),
        "target_padding_mask": torch.zeros(batch_size, attempts, dtype=torch.bool),
    }

    predicted, target, current, no_action = model(batch)
    nn.functional.mse_loss(predicted, target).backward()

    assert predicted.shape == target.shape == current.shape == (2, 8)
    assert no_action.shape == (2, 0)
    assert any(parameter.grad is not None for parameter in model.predictor.parameters())
    assert all(
        parameter.grad is None
        for parameter in model.context_temporal_encoder.parameters()
    )
