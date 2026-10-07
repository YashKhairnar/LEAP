"""Frozen sentence encoder for learner responses."""

from __future__ import annotations

from collections.abc import Sequence

import torch
import torch.nn.functional as F


class ResponseTextEncoder:
    def __init__(self, tokenizer, model, device: torch.device, max_length: int = 256) -> None:
        self.tokenizer = tokenizer
        self.model = model.eval()
        self.device = device
        self.max_length = max_length
        self.model.requires_grad_(False)

    @classmethod
    def from_pretrained(
        cls,
        checkpoint: str = "sentence-transformers/all-MiniLM-L6-v2",
        *,
        device: str | torch.device = "cpu",
        max_length: int = 256,
    ) -> ResponseTextEncoder:
        from transformers import AutoModel, AutoTokenizer

        device = torch.device(device)
        return cls(
            AutoTokenizer.from_pretrained(checkpoint),
            AutoModel.from_pretrained(checkpoint).to(device),
            device,
            max_length,
        )

    @property
    def embedding_dim(self) -> int:
        return int(self.model.config.hidden_size)

    @torch.inference_mode()
    def encode(self, responses: Sequence[str]) -> torch.Tensor:
        if not responses:
            return torch.empty((0, self.embedding_dim), dtype=torch.float32)
        tokens = self.tokenizer(
            list(responses), padding=True, truncation=True,
            max_length=self.max_length, return_tensors="pt",
        )
        tokens = {name: value.to(self.device) for name, value in tokens.items()}
        hidden = self.model(**tokens).last_hidden_state
        mask = tokens["attention_mask"].unsqueeze(-1).to(hidden.dtype)
        pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1.0)
        return F.normalize(pooled, dim=-1).detach().to(device="cpu", dtype=torch.float32)
