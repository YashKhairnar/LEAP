# Shared component

Location: `src/leap/shared/`

Paths here are relative to the research project `LEAP/`. For application packages and
runtime assets, see the [workspace file map](../../../docs/project-structure.md).

This component contains infrastructure used by multiple research components:

- `config.py`: loads JSON configuration files and validates that their root is an object;
- `device.py`: selects CUDA, Apple MPS, or CPU execution.

Example:

```python
from leap.shared import load_json_config, select_device

config = load_json_config("configs/learner_state/jepa_baseline.json")
device = select_device()
```

Shared code should remain domain-independent. Learner-state, action, or observation logic
belongs in its corresponding component.

The web backend intentionally keeps its own lightweight API contracts and asset root in
`backend/app/models.py` and `backend/app/paths.py`. It does not depend on the research
training stack just to collect a learner response. Shared deployment/collection instructions
belong in the workspace `docs/`, not this research-utility package.
