"""Experiment 1 construction, training, evaluation, and checkpointing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader

from leap.action.data import ActionConditionedDataset
from leap.action.models import (
    ActionConditionedJEPA,
    ActionConditionedPredictor,
    ActionEncoder,
    NoActionJEPA,
    NoActionPredictor,
)
from leap.learner_state.models import TemporalLearnerEncoder
from leap.learner_state.training.losses import jepa_loss
from leap.observation.models import ObservationEncoder


def build_experiment_one_loaders(config: dict[str, Any]) -> dict[str, DataLoader]:
    """Build deterministic learner-separated DataLoaders."""
    common = {
        "action_data_path": config["action_data_path"],
        "observation_data_path": config["observation_data_path"],
        "action_vocabulary_path": config["action_vocabulary_path"],
        "prompt_embedding_path": config["prompt_embedding_path"],
        "response_embedding_path": config["response_embedding_path"],
        "split_path": config["split_path"],
        "max_history": int(config["max_history"]),
    }
    generator = torch.Generator().manual_seed(int(config["seed"]))
    return {
        split: DataLoader(
            ActionConditionedDataset(**common, split=split),
            batch_size=int(config["batch_size"]),
            shuffle=split == "train",
            num_workers=int(config.get("num_workers", 0)),
            generator=generator if split == "train" else None,
        )
        for split in ("train", "validation", "test")
    }


def build_experiment_one(
    config: dict[str, Any], temporal_config: dict[str, Any]
) -> ActionConditionedJEPA:
    """Construct Experiment 1 and initialize it from the pretrained learner JEPA."""
    with Path(config["action_vocabulary_path"]).open(encoding="utf-8") as file:
        vocabularies = json.load(file)
    prompt_store = torch.load(config["prompt_embedding_path"], weights_only=False)
    response_store = torch.load(config["response_embedding_path"], weights_only=False)
    prompt_dim = int(prompt_store["embeddings"].shape[-1])
    response_dim = int(response_store["embeddings"].shape[-1])

    observation_encoder = ObservationEncoder(
        response_dim=response_dim,
        numeric_dim=4,
        hidden_dim=int(config["observation_hidden_dim"]),
        output_dim=int(config["observation_dim"]),
        dropout=float(config["observation_dropout"]),
    )
    temporal_encoder = TemporalLearnerEncoder(**temporal_config)
    action_encoder = ActionEncoder(
        task_count=len(vocabularies["task"]),
        stage_count=len(vocabularies["stage"]),
        step_count=len(vocabularies["step"]),
        action_type_count=len(vocabularies["action_type"]),
        content_count=len(vocabularies["content_id"]),
        categorical_dim=int(config["categorical_dim"]),
        prompt_dim=prompt_dim,
        action_dim=int(config["action_dim"]),
    )
    predictor = ActionConditionedPredictor(
        state_dim=int(config["state_dim"]),
        action_dim=int(config["action_dim"]),
        hidden_dim=int(config["predictor_hidden_dim"]),
        dropout=float(config["predictor_dropout"]),
    )
    model = ActionConditionedJEPA(
        observation_encoder,
        temporal_encoder,
        action_encoder,
        predictor,
        train_temporal_encoder=bool(config["train_temporal_encoder"]),
    )
    model.load_pretrained_temporal_checkpoint(config["pretrained_checkpoint"])
    return model


def build_no_action_baseline(
    config: dict[str, Any], temporal_config: dict[str, Any]
) -> NoActionJEPA:
    """Construct the tutoring-domain baseline without action information."""
    response_store = torch.load(config["response_embedding_path"], weights_only=False)
    observation_encoder = ObservationEncoder(
        response_dim=int(response_store["embeddings"].shape[-1]),
        numeric_dim=4,
        hidden_dim=int(config["observation_hidden_dim"]),
        output_dim=int(config["observation_dim"]),
        dropout=float(config["observation_dropout"]),
    )
    model = NoActionJEPA(
        observation_encoder,
        TemporalLearnerEncoder(**temporal_config),
        NoActionPredictor(
            state_dim=int(config["state_dim"]),
            hidden_dim=int(config["predictor_hidden_dim"]),
            dropout=float(config["predictor_dropout"]),
        ),
        train_temporal_encoder=bool(config["train_temporal_encoder"]),
    )
    model.load_pretrained_temporal_checkpoint(config["pretrained_checkpoint"])
    return model


def _move_batch(batch: dict[str, Any], device: torch.device) -> dict[str, Any]:
    return {
        key: value.to(device) if isinstance(value, torch.Tensor) else value
        for key, value in batch.items()
    }


def _run_epoch(
    model: ActionConditionedJEPA,
    loader: DataLoader,
    device: torch.device,
    config: dict[str, Any],
    optimizer: torch.optim.Optimizer | None = None,
    max_batches: int | None = None,
) -> dict[str, float]:
    training = optimizer is not None
    model.train(training)
    totals: dict[str, float] = {}
    examples = 0

    for batch_index, batch in enumerate(loader):
        if max_batches is not None and batch_index >= max_batches:
            break
        batch = _move_batch(batch, device)
        with torch.set_grad_enabled(training):
            predicted, target, current, _ = model(batch)
            loss, metrics = jepa_loss(
                predicted,
                target,
                current,
                variance_weight=float(config["variance_weight"]),
                minimum_std=float(config["minimum_state_std"]),
            )
        if training:
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(
                list(model.trainable_parameters()), float(config["max_gradient_norm"])
            )
            optimizer.step()
            model.update_target_encoders(float(config["target_momentum"]))

        batch_size = predicted.shape[0]
        examples += batch_size
        for name, value in metrics.items():
            totals[name] = totals.get(name, 0.0) + float(value) * batch_size

    if examples == 0:
        raise ValueError("DataLoader produced no examples")
    return {name: value / examples for name, value in totals.items()}


@torch.no_grad()
def evaluate(
    model: ActionConditionedJEPA,
    loader: DataLoader,
    device: torch.device,
    config: dict[str, Any],
    max_batches: int | None = None,
) -> dict[str, float]:
    return _run_epoch(model, loader, device, config, max_batches=max_batches)


def _save_checkpoint(
    path: Path,
    model: ActionConditionedJEPA,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    best_validation_loss: float,
    config: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(
        {
            "format_version": 1,
            "experiment": config.get(
                "experiment_name", "action_conditioned_jepa_experiment_one"
            ),
            "epoch": epoch,
            "best_validation_loss": best_validation_loss,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "config": config,
        },
        temporary,
    )
    temporary.replace(path)


def load_experiment_checkpoint(
    path: str | Path,
    model: ActionConditionedJEPA,
    optimizer: torch.optim.Optimizer | None = None,
    map_location: str | torch.device = "cpu",
    expected_experiment: str | None = None,
) -> dict[str, Any]:
    checkpoint = torch.load(path, map_location=map_location, weights_only=False)
    expected = expected_experiment or "action_conditioned_jepa_experiment_one"
    if checkpoint.get("experiment") != expected:
        raise ValueError(f"Expected {expected!r} checkpoint")
    model.load_state_dict(checkpoint["model_state_dict"])
    if optimizer is not None:
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
    return checkpoint


def fit(
    model: ActionConditionedJEPA,
    loaders: dict[str, DataLoader],
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    config: dict[str, Any],
    *,
    start_epoch: int = 0,
    best_validation_loss: float = float("inf"),
    max_train_batches: int | None = None,
    max_validation_batches: int | None = None,
) -> dict[str, Any]:
    checkpoint_directory = Path(config["checkpoint_directory"])
    metrics_path = Path(config["metrics_path"])
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    for epoch in range(start_epoch + 1, int(config["epochs"]) + 1):
        train_metrics = _run_epoch(
            model, loaders["train"], device, config, optimizer, max_train_batches
        )
        validation_metrics = evaluate(
            model, loaders["validation"], device, config, max_validation_batches
        )
        improved = validation_metrics["loss"] < best_validation_loss
        if improved:
            best_validation_loss = validation_metrics["loss"]

        record = {
            "epoch": epoch,
            "train": train_metrics,
            "validation": validation_metrics,
            "best_validation_loss": best_validation_loss,
        }
        with metrics_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record) + "\n")
        _save_checkpoint(
            checkpoint_directory / "latest.pt",
            model,
            optimizer,
            epoch,
            best_validation_loss,
            config,
        )
        if improved:
            _save_checkpoint(
                checkpoint_directory / "best_validation.pt",
                model,
                optimizer,
                epoch,
                best_validation_loss,
                config,
            )
        print(
            f"Epoch {epoch:03d} | train={train_metrics['loss']:.4f} "
            f"validation={validation_metrics['loss']:.4f}"
        )

    return {"best_validation_loss": best_validation_loss}
