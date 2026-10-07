"""Goal-state definitions used by planning experiments."""

import torch


def handcrafted_binary_goal(
    state_dim: int = 128,
    understanding_dimensions: int = 64,
    *,
    device: torch.device | str | None = None,
) -> torch.Tensor:
    """Return a goal with leading understanding ones and remaining zeros."""
    if not 0 <= understanding_dimensions <= state_dim:
        raise ValueError("understanding_dimensions must be between zero and state_dim")
    return torch.cat(
        (
            torch.ones(understanding_dimensions, device=device),
            torch.zeros(state_dim - understanding_dimensions, device=device),
        )
    )
