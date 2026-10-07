"""Build frozen learner-state tensors for concept-probe training."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader, TensorDataset

from leap.action.training import (
    build_experiment_one,
    build_experiment_one_loaders,
    load_experiment_checkpoint,
)


def _load_labels(path: str | Path) -> dict[str, dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as file:
        return {
            record["transition_id"]: record
            for line in file
            if line.strip()
            for record in [json.loads(line)]
        }


@torch.no_grad()
def build_probe_datasets(
    action_config: dict[str, Any],
    temporal_config: dict[str, Any],
    probe_config: dict[str, Any],
    device: torch.device,
) -> dict[str, TensorDataset]:
    """Encode learner states once and join the configured mastery targets."""
    loaders = build_experiment_one_loaders(action_config)
    model = build_experiment_one(action_config, temporal_config).to(device)
    load_experiment_checkpoint(probe_config["state_model_checkpoint"], model, map_location=device)
    model.eval()
    labels = _load_labels(probe_config["concept_labels_path"])
    state_source = str(probe_config.get("state_source", "current"))
    if state_source not in {"current", "predicted_next"}:
        raise ValueError("state_source must be 'current' or 'predicted_next'")
    target_field = str(probe_config.get("target_field", "mastery_before"))
    mask_field = str(probe_config.get("mask_field", "mastery_mask_before"))
    datasets: dict[str, TensorDataset] = {}

    for split, loader in loaders.items():
        state_parts: list[torch.Tensor] = []
        target_parts: list[torch.Tensor] = []
        mask_parts: list[torch.Tensor] = []
        for batch in loader:
            device_batch = {
                key: value.to(device) if isinstance(value, torch.Tensor) else value
                for key, value in batch.items()
            }
            if state_source == "predicted_next":
                states = model(device_batch)[0].cpu()
            else:
                observations = model.context_observation_encoder(
                    {
                        "response_embedding": device_batch[
                            "context_response_embeddings"
                        ],
                        "numeric_features": device_batch["context_numeric_features"],
                    }
                )
                states = model.context_temporal_encoder(
                    observations,
                    device_batch["context_metadata"],
                    device_batch["context_padding_mask"],
                ).cpu()
            targets = torch.tensor(
                [labels[value][target_field] for value in batch["transition_id"]],
                dtype=torch.float32,
            )
            masks = torch.tensor(
                [labels[value][mask_field] for value in batch["transition_id"]],
                dtype=torch.bool,
            )
            supervised_rows = masks.any(dim=1)
            state_parts.append(states[supervised_rows])
            target_parts.append(targets[supervised_rows])
            mask_parts.append(masks[supervised_rows])

        datasets[split] = TensorDataset(
            torch.cat(state_parts),
            torch.cat(target_parts),
            torch.cat(mask_parts),
        )
    return datasets


def build_probe_loaders(
    datasets: dict[str, TensorDataset], batch_size: int, seed: int
) -> dict[str, DataLoader]:
    generator = torch.Generator().manual_seed(seed)
    return {
        split: DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=split == "train",
            generator=generator if split == "train" else None,
        )
        for split, dataset in datasets.items()
    }
