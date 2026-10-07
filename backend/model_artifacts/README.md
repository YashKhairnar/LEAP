# Model artifacts

This directory contains inference-only artifacts promoted from `LEAP/`. Do not manually mix
weights and configuration files. Create a complete, checksummed bundle from the repository's
`LEAP/` directory:

```bash
python scripts/deployment/export_backend_bundle.py \
  --model-version world-model-v1 \
  --training-dataset REPLACE_WITH_ACTUAL_TRAINING_DATASET_VERSION
```

The private model service requires `manifest.json` and verifies every listed file before
loading the planner. Its runtime lives in `LEAP/src/leap/planning/runtime.py`; the API
uses the client in `backend/app/planning/client.py`. This asset directory is unchanged by
the package restructure.
Training datasets, notebooks, optimizer experiments, and metrics do not belong here.

Replace the placeholder label with the dataset on which those weights were actually
trained. More collected transitions do not update existing weights automatically.
Use `--output` with a new review directory to avoid overwriting a deployed bundle.
