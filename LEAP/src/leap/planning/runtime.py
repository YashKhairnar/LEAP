"""Persistent runtime for online action-conditioned world-model inference."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import torch

from leap.action.models.prompt_encoder import PromptEncoder
from leap.action.training import build_experiment_one, load_experiment_checkpoint
from leap.observation.data import observation_numeric_features
from leap.planning.goals import handcrafted_binary_goal
from leap.planning.one_step import OneStepPlanner
from leap.shared.config import load_json_config

PLANNER_VERSION = "world_model_one_step_experimental_v1"
REQUIRED_ARTIFACTS = {
    "action_checkpoint",
    "temporal_checkpoint",
    "action_vocabularies",
    "action_config",
    "temporal_config",
    "prompt_encoder_config",
}


def verify_bundle(directory: Path) -> dict[str, Any]:
    """Verify a promoted model bundle before loading executable artifacts."""
    directory = directory.expanduser().resolve()
    manifest_path = directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts")
    if manifest.get("format_version") != 1 or not isinstance(artifacts, dict):
        raise ValueError("unsupported model artifact manifest")
    if not REQUIRED_ARTIFACTS.issubset(artifacts):
        raise ValueError("model artifact manifest is incomplete")
    for name, metadata in artifacts.items():
        path = (directory / metadata["file"]).resolve()
        if path.parent != directory or not path.is_file():
            raise ValueError(f"invalid model artifact: {name}")
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != metadata["sha256"]:
            raise ValueError(f"model artifact checksum mismatch: {name}")
    return manifest


class WorldModelRuntime:
    """Load the model once and serve repeated planning requests."""

    def __init__(self, artifact_directory: Path, *, device: str = "cpu") -> None:
        self.device = torch.device(device)
        if self.device.type == "cuda" and not torch.cuda.is_available():
            raise RuntimeError("WORLD_MODEL_DEVICE requests CUDA, but CUDA is unavailable")
        self.artifact_directory = artifact_directory.expanduser().resolve()
        self.manifest = verify_bundle(self.artifact_directory)
        artifacts = self.manifest["artifacts"]

        def artifact(name: str) -> Path:
            return self.artifact_directory / artifacts[name]["file"]

        self.checkpoint_path = artifact("action_checkpoint")
        self.config = load_json_config(artifact("action_config"))
        self.config.update({
            "action_vocabulary_path": str(artifact("action_vocabularies")),
            "prompt_embedding_path": str(artifact("prompt_embedding_store")),
            "response_embedding_path": str(artifact("response_embedding_store")),
            "pretrained_checkpoint": str(artifact("temporal_checkpoint")),
        })
        temporal_config = load_json_config(artifact("temporal_config"))
        self.model = build_experiment_one(self.config, temporal_config)
        load_experiment_checkpoint(self.checkpoint_path, self.model)
        self.model.to(self.device).eval()
        self.planner = OneStepPlanner(self.model)

        prompt_config = load_json_config(artifact("prompt_encoder_config"))
        self.encoder = PromptEncoder.from_pretrained(prompt_config["checkpoint"], device=self.device)
        self.max_history = int(self.config["max_history"])
        with artifact("action_vocabularies").open(encoding="utf-8") as file:
            self.vocabularies = json.load(file)

    @property
    def model_info(self) -> dict[str, Any]:
        return {
            "status": "ready",
            "model_version": self.manifest["model_version"],
            "training_dataset": self.manifest["training_dataset"],
            "planner_version": PLANNER_VERSION,
            "state_dimension": int(self.config["state_dim"]),
            "device": str(self.device),
        }

    @torch.inference_mode()
    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        observations = request.get("observations", [])[-self.max_history:]
        candidates = request["candidates"]
        categorical_values = {
            "task_id": [self.vocabularies["task"].get(request["task"], 0) for _ in candidates],
            "stage_id": [self.vocabularies["stage"].get(request["stage"], 0) for _ in candidates],
            "step_id": [self.vocabularies["step"].get(request["step"], 0) for _ in candidates],
            "action_type_id": [self.vocabularies["action_type"].get(item["action_type"], 0) for item in candidates],
            "content_id": [0 for _ in candidates],
        }
        candidate_batch = {
            key: torch.tensor([values], device=self.device) for key, values in categorical_values.items()
        }
        candidate_batch["prompt_embedding"] = self.encoder.encode(
            [item["prompt"] for item in candidates]
        ).unsqueeze(0).to(self.device)

        if observations:
            responses = self.encoder.encode([str(item["response"]) for item in observations])
            response_embeddings = torch.zeros(1, self.max_history, responses.shape[-1], device=self.device)
            numeric_features = torch.zeros(1, self.max_history, 4, device=self.device)
            metadata = torch.zeros(1, self.max_history, 3, device=self.device)
            padding_mask = torch.ones(1, self.max_history, dtype=torch.bool, device=self.device)
            history_offset = max(0, int(request.get("observation_count", len(observations))) - len(observations))
            for position, (observation, embedding) in enumerate(zip(observations, responses)):
                absolute_index = history_offset + position
                response_embeddings[0, position] = embedding.to(self.device)
                numeric_features[0, position] = observation_numeric_features(observation).to(self.device)
                previous_correct = bool(observations[position - 1]["correct"]) if position else False
                metadata[0, position] = torch.tensor([
                    min((absolute_index + 1) / self.max_history, 1.0),
                    float(previous_correct),
                    float(absolute_index == 0),
                ], device=self.device)
                padding_mask[0, position] = False
            result = self.planner.plan_from_history({
                "context_response_embeddings": response_embeddings,
                "context_numeric_features": numeric_features,
                "context_metadata": metadata,
                "context_padding_mask": padding_mask,
            }, candidate_batch, handcrafted_binary_goal(device=self.device))
            initialization = "encoded_session_history"
        else:
            generator = torch.Generator().manual_seed(int(request["initial_state_seed"]))
            current_state = torch.randn(
                1, int(self.config["state_dim"]), generator=generator
            )
            current_state = torch.nn.functional.layer_norm(
                current_state, (int(self.config["state_dim"]),)
            ).to(self.device)
            result = self.planner(current_state, candidate_batch, handcrafted_binary_goal(device=self.device))
            result["current_state"] = current_state
            initialization = "deterministic_random_initial_state"

        selected = int(result["selected_indices"].item())
        return {
            "planner_version": PLANNER_VERSION,
            "checkpoint": f"{self.manifest['model_version']}:{self.checkpoint_path.name}",
            "selected_action_type": candidates[selected]["action_type"],
            "selected_index": selected,
            "current_state": result["current_state"][0].tolist(),
            "predicted_state": result["selected_predicted_states"][0].tolist(),
            "candidate_predicted_states": result["candidate_predicted_states"][0].tolist(),
            "candidate_distances": result["candidate_distances"][0].tolist(),
            "initialization": initialization,
            "initial_state_seed": int(request["initial_state_seed"]),
            "goal_state": handcrafted_binary_goal().tolist(),
            "candidates": candidates,
        }
