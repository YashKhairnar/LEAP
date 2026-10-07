# Reproduction guide

This guide reproduces research experiments inside `LEAP/`. For the app, use
[local development](../../../docs/local-development.md). All commands below run from
`LEAP/`, not the enclosing repository root. Saved metrics are historical until explicitly
rerun; the application reorganization does not change checkpoints or training data.

## Requirements

- Python 3.11 or later
- PyTorch 2.2 or later
- Transformers 4.40 or later for CodeT5+
- pandas 2.0 or later
- pytest 8 or later for tests

Create and activate an isolated environment, then install the project:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,models]'
```

## Rebuild the pipeline

Run commands from the research project root (`LEAP/`).

### 1. Preprocess DCU

```bash
python scripts/learner_state/preprocess_dcu.py
```

This creates:

- `data/dcu/processed/trajectories.jsonl`
- `data/dcu/processed/trajectory_statistics.json`

### 2. Generate frozen code embeddings

```bash
python scripts/code_embeddings/generate_embeddings.py
```

This downloads/loads the configured CodeT5+ checkpoint and creates
`data/dcu/features/code_embeddings.pt`.

### 3. Create student splits

```bash
python scripts/learner_state/prepare_training_data.py
```

The existing split manifest is reused unless `--force` is provided. Avoid forcing a new
split when reproducing the reported results.

### 4. Run tests

```bash
pytest
```

### 5. Run a bounded smoke test

```bash
python scripts/learner_state/train_jepa.py --device mps --run-name smoke \
  --epochs 1 --max-train-batches 20 --max-validation-batches 5 \
  --max-test-batches 5
```

Replace `mps` with `cpu` or `cuda` as appropriate.

### 6. Train the full baseline

```bash
python scripts/learner_state/train_jepa.py --device mps --run-name jepa_baseline
```

### 7. Evaluate against identity

```bash
python scripts/learner_state/evaluate_identity_baseline.py --device mps
```

### 8. Prepare instructional actions

```bash
python scripts/action/prepare_action_dataset.py
python scripts/action/generate_prompt_embeddings.py
```

### 9. Prepare learner observations

```bash
python scripts/observation/prepare_observation_dataset.py
python scripts/observation/generate_response_embeddings.py
```

### 10. Train the action-conditioned model

```bash
python scripts/action/prepare_experiment_splits.py
python scripts/action/train_experiment_one.py --epochs 100 --run-name experiment_one_100
```

### 11. Run the no-action comparison

```bash
python scripts/action/train_no_action_baseline.py
```

### 12. Prepare and probe generic ML concepts

```bash
python scripts/concepts/prepare_concept_labels.py
python scripts/concepts/train_probe.py
python scripts/concepts/train_probe.py --config configs/concepts/probe_v2.json
```

### 13. Run one-step planning

```bash
python scripts/planning/demo_one_step.py \
  --output outputs/planning/one_step_demo.json
```

### 14. Build LLM tutoring context

```bash
python scripts/llm/build_demo_context.py
```

This writes `outputs/llm/demo_context.json`. It prepares messages but does not call an LLM.

## Configuration map

| File | Purpose |
|---|---|
| `configs/learner_state/dcu.json` | Raw-data paths and minimum trajectory length |
| `configs/code_embeddings/code_encoder.json` | CodeT5+ checkpoint and embedding settings |
| `configs/learner_state/temporal_encoder.json` | Temporal encoder architecture |
| `configs/learner_state/jepa_baseline.json` | Splits, optimization, losses, and outputs |
| `configs/action/prompt_encoder.json` | Frozen instructional-prompt embeddings |
| `configs/observation/response_encoder.json` | Frozen learner-response embeddings |
| `configs/action/experiment_one.json` | Action-conditioned JEPA experiment |
| `configs/action/no_action_baseline.json` | Tutoring-domain no-action comparison |
| `configs/concepts/concept_vocabulary_v2.json` | Generic 64-concept ML ontology |
| `configs/concepts/probe_v1.json` | Frozen-state linear concept probe |
| `configs/concepts/probe_v2.json` | Predicted-next-state concept probe |
| `configs/llm/action_specifications_v1.json` | Question rules for all 12 actions |

Command-line overrides are available in each script. Preserve the saved configurations,
split manifest, and metrics alongside any research result so the run remains auditable.

## New application data and inference deployment

The app's [collection exporter](../../../docs/collection.md) requires an explicit participant
allowlist and audits timing, exposure, assistance and assignment provenance. Do not overwrite
the historical `data/action/raw/transitions.json` to try an export. Prepare a separate,
versioned input and configuration; explicitly carry its learner split and quality labels
through action/observation preprocessing. Existing scripts do not automatically honor those
new labels, and stored model predictions must not become observed response targets.

After training and evaluation, `scripts/deployment/export_backend_bundle.py` promotes a
compatible checksummed bundle for [the inference service](../../../model_service/README.md).
Use truthful model/dataset versions and a new output directory for review. Exporting records
does not train weights; promoting weights does not validate learning effectiveness.
