# LEAP research project

Research code for constructing and modelling learner trajectories from programming
submissions and tutoring interactions. This folder owns training and experiments; the
web application and private inference host are sibling projects, described in the
[workspace guide](../README.md).

Detailed documentation of the completed DCU pipeline, JEPA architecture, experimental
results, and current action-conditioned pipeline is available in [`docs/`](docs/README.md).
The [current roadmap](docs/system/roadmap.md) distinguishes completed implementation from
unvalidated learning-effectiveness claims and new collection work.

## Component layout

```text
src/leap/
├── shared/             # Configuration and device selection
├── code_embeddings/    # Frozen CodeT5+ encoder and embedding store
├── learner_state/      # DCU data, JEPA models, training, and evaluation
├── action/             # Action data, prompt embeddings, and action encoder
├── observation/        # Learner responses, response embeddings, and adapter
├── concepts/           # Generic ML ontology, mastery labels, and state probe
├── planning/           # One-step instructional-action planner
└── llm/                # Action specifications and structured LLM context

data/
├── dcu/{raw,processed,features}/
├── action/{raw,processed,features}/
├── observation/{processed,features}/
└── concepts/processed/

configs/ and scripts/
├── code_embeddings/
├── learner_state/
├── action/
├── observation/
├── concepts/
├── planning/
└── llm/

tests/
├── shared/
├── code_embeddings/
├── learner_state/
├── action/
├── observation/
├── concepts/
└── planning/

outputs/
├── learner_state/{checkpoints,metrics}/
├── action/{checkpoints,metrics}/
└── concepts/{checkpoints,metrics}/
```

## Setup

Run these commands from `LEAP/`, not the enclosing web-app repository root. The
`scripts/deployment/` directory also contains the reviewed-bundle promotion entry point;
promotion is separate from model training and collection.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,models]'
```

## Workflow

```bash
# Convert raw DCU submissions into trajectories
python scripts/learner_state/preprocess_dcu.py

# Generate one frozen CodeT5+ embedding per unique code submission
python scripts/code_embeddings/generate_embeddings.py

# Create deterministic student-level train/validation/test splits
python scripts/learner_state/prepare_training_data.py

# Run the test suite
pytest
```

Reusable implementation lives in `src/leap/`; `scripts/` contains thin command-line
entry points; `notebooks/` is for exploration; generated files go under `data/dcu/processed/`
or `outputs/`.

The original data currently remains in `data/dcu/raw/`. The preprocessing script uses that
location by default so existing work continues to run.

Data defaults are defined in `configs/learner_state/dcu.json`. Any value can be overridden for a
single run, for example:

```bash
python scripts/learner_state/preprocess_dcu.py --minimum-attempts 3 --output-dir data/dcu/processed/dcu-v2
```

## Embedding pipeline

`generate_embeddings.py` reads the processed trajectory JSONL, hashes each normalized code
submission, encodes each unique submission once with CodeT5+, and saves a lookup table at
`data/dcu/features/code_embeddings.pt`. `TrajectoryDataset` joins this table back to each
trajectory and returns:

- `code_embeddings`: `[max_attempts, 256]`
- `metadata`: `[max_attempts, 3]` containing normalized attempt number, previous correctness,
  and an is-first-attempt flag
- `padding_mask`: `[max_attempts]`, where `True` marks padding
- `correctness`: `[max_attempts]`

PyTorch's default `DataLoader` collates these into the batch shapes expected by
`TemporalLearnerEncoder`.

## JEPA components

The future-state model consists of a trainable context encoder, a trainable predictor, and
a frozen target encoder updated by exponential moving average (EMA):

```python
import torch

from leap.learner_state.models import FutureStatePredictor, LearnerJEPA, TemporalLearnerEncoder
from leap.learner_state.training import train_jepa_step

context_encoder = TemporalLearnerEncoder()
predictor = FutureStatePredictor()
model = LearnerJEPA(context_encoder, predictor)

optimizer = torch.optim.AdamW(
    model.trainable_parameters(),
    lr=1e-4,
    weight_decay=1e-2,
)

metrics = train_jepa_step(
    model,
    batch,
    optimizer,
    target_momentum=0.996,
    variance_weight=0.1,
)
```

Each `batch` must contain context tensors for attempts `1..t` and target tensors for
attempts `1..t+1`: `context_embeddings`, `context_metadata`, `context_padding_mask`,
`target_embeddings`, `target_metadata`, and `target_padding_mask`.

`JEPAPrefixDataset` creates these pairs lazily and filters them using
`data/dcu/processed/student_splits.json`:

```python
from leap.learner_state.data import JEPAPrefixDataset

train_dataset = JEPAPrefixDataset(
    "data/dcu/processed/trajectories.jsonl",
    "data/dcu/features/code_embeddings.pt",
    max_attempts=20,
    split_path="data/dcu/processed/student_splits.json",
    split="train",
)
```

Run a bounded MPS smoke test before full training:

```bash
python scripts/learner_state/train_jepa.py --device mps --run-name smoke \
  --epochs 1 --max-train-batches 20 --max-validation-batches 5 \
  --max-test-batches 5
```

Then start the complete experiment:

```bash
python scripts/learner_state/train_jepa.py --device mps --run-name jepa_baseline
```
