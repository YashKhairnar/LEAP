"""Train the tutoring-domain no-action baseline."""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path

os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

import torch

from leap.action.training import (
    build_experiment_one_loaders,
    build_no_action_baseline,
    evaluate,
    fit,
    load_experiment_checkpoint,
)
from leap.shared.config import load_json_config
from leap.shared.device import select_device


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/action/no_action_baseline.json")
    )
    parser.add_argument(
        "--temporal-config",
        type=Path,
        default=Path("configs/learner_state/temporal_encoder.json"),
    )
    parser.add_argument("--device", choices=["cpu", "cuda", "mps"])
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--max-train-batches", type=int)
    parser.add_argument("--max-validation-batches", type=int)
    parser.add_argument("--max-test-batches", type=int)
    args = parser.parse_args()

    config = load_json_config(args.config)
    temporal_config = load_json_config(args.temporal_config)
    if args.epochs is not None:
        config["epochs"] = args.epochs
    random.seed(int(config["seed"]))
    torch.manual_seed(int(config["seed"]))
    device = torch.device(args.device) if args.device else select_device()
    print(f"Device: {device}")

    loaders = build_experiment_one_loaders(config)
    print(", ".join(f"{name}={len(loader.dataset)}" for name, loader in loaders.items()))
    model = build_no_action_baseline(config, temporal_config).to(device)
    optimizer = torch.optim.AdamW(
        model.trainable_parameters(),
        lr=float(config["learning_rate"]),
        weight_decay=float(config["weight_decay"]),
    )
    result = fit(
        model,
        loaders,
        optimizer,
        device,
        config,
        max_train_batches=args.max_train_batches,
        max_validation_batches=args.max_validation_batches,
    )

    best_path = Path(config["checkpoint_directory"]) / "best_validation.pt"
    load_experiment_checkpoint(
        best_path,
        model,
        map_location=device,
        expected_experiment=str(config["experiment_name"]),
    )
    test_metrics = evaluate(model, loaders["test"], device, config, args.max_test_batches)
    test_path = Path("outputs/action/metrics/no_action_baseline_test.json")
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text(json.dumps(test_metrics, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({**result, "best_checkpoint": str(best_path), "test": test_metrics}, indent=2))


if __name__ == "__main__":
    main()
