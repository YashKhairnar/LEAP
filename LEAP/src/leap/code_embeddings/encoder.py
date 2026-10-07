"""Frozen CodeT5+ encoder for individual source-code submissions."""

from __future__ import annotations

from collections.abc import Sequence

import torch


class CodeEncoder:
    """Convert source-code strings into fixed-size CodeT5+ embeddings."""

    def __init__(self, tokenizer, model, device: torch.device, max_length: int = 512) -> None:
        self.tokenizer = tokenizer
        self.model = model.eval()
        self.device = device
        self.max_length = max_length
        self.model.requires_grad_(False)

    @classmethod
    def from_pretrained(
        cls,
        checkpoint: str = "Salesforce/codet5p-110m-embedding",
        *,
        device: str | torch.device = "cpu",
        max_length: int = 512,
    ) -> "CodeEncoder":
    
        """Load the tokenizer and native embedding model from a checkpoint."""
        from transformers import AutoConfig, AutoModel, AutoTokenizer

        device = torch.device(device)
        tokenizer = AutoTokenizer.from_pretrained(checkpoint, trust_remote_code=True)
        config = AutoConfig.from_pretrained(checkpoint, trust_remote_code=True)

        # The embedding checkpoint is encoder-only in practice. These settings avoid
        # decoder/cache assumptions in newer Transformers versions.
        config.is_decoder = False
        config.is_encoder_decoder = False
        config.use_cache = False
        model = AutoModel.from_pretrained(
            checkpoint,
            config=config,
            trust_remote_code=True,
        ).to(device)
        return cls(tokenizer, model, device, max_length=max_length)

    @property
    def embedding_dim(self) -> int:
        """Dimension of vectors produced by the checkpoint's projection head."""
        dimension = getattr(self.model.config, "embed_dim", None)
        if dimension is None:
            raise ValueError("The model configuration does not define embed_dim")
        return int(dimension)

    @torch.inference_mode()
    def encode(self, code: Sequence[str]) -> torch.Tensor:
        """Return CPU embeddings with shape ``[len(code), embedding_dim]``."""
        if not code:
            return torch.empty((0, self.embedding_dim), dtype=torch.float32)

        tokens = self.tokenizer(
            list(code),
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        tokens = {name: value.to(self.device) for name, value in tokens.items()}
        output = self.model(**tokens)
        embeddings = output if isinstance(output, torch.Tensor) else output.last_hidden_state[:, 0]
        if embeddings.ndim != 2:
            raise ValueError(f"Expected a 2-D embedding tensor, received {embeddings.shape}")
        return embeddings.detach().to(device="cpu", dtype=torch.float32)

