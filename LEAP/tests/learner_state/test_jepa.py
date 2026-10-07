import torch

from leap.learner_state.models import FutureStatePredictor, LearnerJEPA, TemporalLearnerEncoder
from leap.learner_state.training import cosine_prediction_loss, train_jepa_step


def build_small_jepa() -> LearnerJEPA:
    context_encoder = TemporalLearnerEncoder(
        code_dim=8,
        metadata_dim=3,
        metadata_hidden_dim=4,
        d_model=16,
        state_dim=6,
        num_layers=1,
        num_heads=4,
        feedforward_dim=32,
        max_attempts=4,
        dropout=0.0,
    )
    predictor = FutureStatePredictor(state_dim=6, hidden_dim=12, dropout=0.0)
    return LearnerJEPA(context_encoder, predictor)


def make_batch(batch_size: int = 4) -> dict[str, torch.Tensor]:
    return {
        "context_embeddings": torch.randn(batch_size, 3, 8),
        "context_metadata": torch.randn(batch_size, 3, 3),
        "context_padding_mask": torch.zeros(batch_size, 3, dtype=torch.bool),
        "target_embeddings": torch.randn(batch_size, 4, 8),
        "target_metadata": torch.randn(batch_size, 4, 3),
        "target_padding_mask": torch.zeros(batch_size, 4, dtype=torch.bool),
    }


def test_target_encoder_is_frozen_and_ema_updated() -> None:
    model = build_small_jepa()
    assert not model.target_encoder.training
    assert all(not parameter.requires_grad for parameter in model.target_encoder.parameters())

    target_parameter = next(model.target_encoder.encoder.parameters())
    context_parameter = next(model.context_encoder.parameters())
    original_target = target_parameter.detach().clone()
    with torch.no_grad():
        context_parameter.add_(2.0)

    model.update_target_encoder(momentum=0.75)
    expected = original_target * 0.75 + context_parameter.detach() * 0.25
    assert torch.allclose(target_parameter, expected)


def test_training_step_updates_context_but_not_target_by_gradient() -> None:
    model = build_small_jepa()
    optimizer = torch.optim.AdamW(model.trainable_parameters(), lr=1e-3)
    context_before = next(model.context_encoder.parameters()).detach().clone()

    metrics = train_jepa_step(model, make_batch(), optimizer, target_momentum=0.9)

    context_after = next(model.context_encoder.parameters()).detach()
    assert not torch.equal(context_before, context_after)
    assert all(parameter.grad is None for parameter in model.target_encoder.parameters())
    assert set(metrics) == {
        "loss",
        "prediction_loss",
        "variance_loss",
        "context_state_std",
        "gradient_norm",
    }
    assert all(torch.isfinite(torch.tensor(value)) for value in metrics.values())


def test_cosine_prediction_loss_is_zero_for_identical_states() -> None:
    states = torch.randn(4, 6)
    assert torch.allclose(cosine_prediction_loss(states, states), torch.tensor(0.0), atol=1e-6)
