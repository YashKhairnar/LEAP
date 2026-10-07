"""Transformer encoder for a chronological sequence of learner attempts."""

import torch
from torch import nn


class TemporalLearnerEncoder(nn.Module):
    """Summarize code embeddings and attempt metadata into a learner state.

    Architecture diagram:
    
    CodeT5 embeddings        Metadata
    [B, T, 256]             [B, T, 3]
          │                       │
          │                 Metadata MLP
          │                  [B, T, 16]
          └──────────┬────────────┘
                     ↓
              Concatenate
              [B, T, 272]
                     ↓
                Fusion MLP
              [B, T, 256]
                     ↓
           Add [STATE] token
              [B, T+1, 256]
                     ↓
         Add positional embeddings
               [B, T+1, 256]
                     ↓
           Transformer Encoder
               [B, T+1, 256]
                     ↓
           Take [STATE] output
                 [B, 256]
                     ↓
             Projection layer
                     ↓
           Learner state [B, 128]
    """

    def __init__(
        self,
        code_dim: int = 256,
        metadata_dim: int = 3,
        metadata_hidden_dim: int = 16,
        d_model: int = 256,
        state_dim: int = 128,
        num_layers: int = 2,
        num_heads: int = 4,
        feedforward_dim: int = 512,
        max_attempts: int = 20,
        dropout: float = 0.1,
    ) -> None:
        super().__init__()
        
        self.max_attempts = max_attempts

        # [B, T, metadata_dim] -> [B, T, metadata_hidden_dim] (e.g. [B, T, 3] -> [B, T, 16])
        self.metadata_mlp = nn.Sequential(
            nn.Linear(metadata_dim, metadata_hidden_dim),
            nn.GELU(),
            nn.Linear(metadata_hidden_dim, metadata_hidden_dim),
        )

        # [B, T, code_dim + metadata_hidden_dim] -> [B, T, d_model] (e.g. [B, T, 272] -> [B, T, 256])
        self.attempt_fusion = nn.Sequential(
            nn.Linear(code_dim + metadata_hidden_dim, d_model),
            nn.GELU(),
            nn.LayerNorm(d_model),
        )

        # [1, 1, d_model] (e.g. [1, 1, 256])
        self.state_token = nn.Parameter(torch.randn(1, 1, d_model) * 0.02)

        # Learnable positional embeddings: [max_attempts + 1, d_model] (e.g. [21, 256])
        self.position_embedding = nn.Embedding(max_attempts + 1, d_model)

        # Multi-head self-attention + feedforward blocks
        # [B, T + 1, d_model] -> [B, T + 1, d_model] (e.g. [B, T + 1, 256] -> [B, T + 1, 256])
        layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=num_heads,
            dim_feedforward=feedforward_dim,
            dropout=dropout,
            activation="gelu",
            batch_first=True,
            norm_first=True,
        )
        self.transformer = nn.TransformerEncoder(
            encoder_layer=layer, num_layers=num_layers, norm=nn.LayerNorm(d_model)
        )
        # [B, d_model] -> [B, state_dim] (e.g. [B, 256] -> [B, 128])
        self.state_projection = nn.Sequential(nn.Linear(d_model, state_dim), nn.LayerNorm(state_dim))

    def forward(
        self,
        code_embeddings: torch.Tensor,
        metadata: torch.Tensor,
        padding_mask: torch.Tensor | None = None,
    ) -> torch.Tensor:
        """Return a tensor of shape ``[batch, state_dim]``."""
        
        if code_embeddings.ndim != 3 or metadata.ndim != 3:
            raise ValueError("code_embeddings and metadata must have shape [batch, attempts, features]")
        if code_embeddings.shape[:2] != metadata.shape[:2]:
            raise ValueError("code_embeddings and metadata must share batch and attempt dimensions")

        batch_size, num_attempts, _ = code_embeddings.shape
        if num_attempts > self.max_attempts:
            raise ValueError(f"Received {num_attempts} attempts; maximum is {self.max_attempts}")
        if padding_mask is not None and padding_mask.shape != (batch_size, num_attempts):
            raise ValueError("padding_mask must have shape [batch, attempts]")

        # code_embeddings shape: [B, T, code_dim]
        # metadata shape: [B, T, metadata_dim]

        # [B, T, metadata_dim] -> [B, T, metadata_hidden_dim] (e.g. [B, T, 3] -> [B, T, 16])
        metadata_embedding = self.metadata_mlp(metadata)
        
        # [B, T, code_dim + metadata_hidden_dim] -> [B, T, d_model] (e.g. [B, T, 272] -> [B, T, 256])
        attempts = self.attempt_fusion(torch.cat([code_embeddings, metadata_embedding], dim=-1))
        
        # [1, 1, d_model] -> [B, 1, d_model]
        state_token = self.state_token.expand(batch_size, -1, -1)
        
        # [B, 1, d_model] concat [B, T, d_model] -> [B, T + 1, d_model]
        sequence = torch.cat([state_token, attempts], dim=1)
        
        # positions: [T + 1] -> positional_embeddings: [1, T + 1, d_model]
        positions = torch.arange(num_attempts + 1, device=sequence.device)
        sequence = sequence + self.position_embedding(positions).unsqueeze(0)

        transformer_mask = None
        if padding_mask is not None:
            # state_mask: [B, 1]
            # padding_mask: [B, T] -> transformer_mask: [B, T + 1]
            state_mask = torch.zeros(batch_size, 1, dtype=torch.bool, device=padding_mask.device)
            transformer_mask = torch.cat([state_mask, padding_mask.bool()], dim=1)

        # [B, T + 1, d_model] -> [B, T + 1, d_model]
        encoded = self.transformer(sequence, src_key_padding_mask=transformer_mask)
        
        # encoded[:, 0, :] is state_token output: [B, d_model] -> projection: [B, state_dim]
        return self.state_projection(encoded[:, 0, :])

