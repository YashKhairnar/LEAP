"""Train a frozen-state linear probe for the 64 generic ML concepts."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import torch

from leap.concepts import ConceptProbe
from leap.concepts.probe_data import build_probe_datasets, build_probe_loaders
from leap.concepts.probe_training import (
    evaluate_mean_baseline,
    evaluate_probe,
    fit_mean_baseline,
    fit_probe,
    load_probe_checkpoint,
)
from leap.shared.config import load_json_config
from leap.shared.device import select_device


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/concepts/probe_v1.json")
    )
    parser.add_argument(
        "--action-config",
        type=Path,
        default=Path("configs/action/experiment_one.json"),
    )
    parser.add_argument(
        "--temporal-config",
        type=Path,
        default=Path("configs/learner_state/temporal_encoder.json"),
    )
    parser.add_argument("--device", choices=["cpu", "cuda", "mps"])
    parser.add_argument("--epochs", type=int)
    args = parser.parse_args()

    config = load_json_config(args.config)
    action_config = load_json_config(args.action_config)
    temporal_config = load_json_config(args.temporal_config)
    if args.epochs is not None:
        config["epochs"] = args.epochs
    seed = int(config["seed"])
    random.seed(seed)
    torch.manual_seed(seed)
    device = torch.device(args.device) if args.device else select_device()
    print(f"Device: {device}")
    print("Encoding frozen learner states...")
    datasets = build_probe_datasets(action_config, temporal_config, config, device)
    print(", ".join(f"{name}={len(dataset)}" for name, dataset in datasets.items()))
    loaders = build_probe_loaders(datasets, int(config["batch_size"]), seed)

    model = ConceptProbe(state_dim=128, concept_count=64).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config["learning_rate"]),
        weight_decay=float(config["weight_decay"]),
    )
    result = fit_probe(model, loaders, optimizer, device, config)
    load_probe_checkpoint(
        config["checkpoint_path"],
        model,
        device,
        expected_experiment=str(config.get("experiment_name", "concept_probe_v1")),
    )
    test_metrics = {
        "probe": evaluate_probe(model, loaders["test"], device),
        "mean_baseline": evaluate_mean_baseline(
            fit_mean_baseline(loaders["train"]), loaders["test"]
        ),
    }
    test_path = Path(config["test_metrics_path"])
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(json.dumps(test_metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**result, "test": test_metrics}, indent=2))


if __name__ == "__main__":
    main()
