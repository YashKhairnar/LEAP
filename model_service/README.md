# LEAP world-model service

This internal FastAPI service verifies and loads the promoted world-model bundle once during
startup. It keeps the model and prompt encoder resident for all planning requests.

Install the research inference dependencies in a separate environment, from the repository
root (reuse an existing compatible environment if available):

```bash
python3 -m venv LEAP/.venv
LEAP/.venv/bin/python -m pip install -e './LEAP[models]' -r model_service/requirements.txt
```

Start with a complete, reviewed bundle in `backend/model_artifacts/`:

```bash
LEAP_MODEL_ARTIFACT_DIR=backend/model_artifacts \
LEAP/.venv/bin/uvicorn model_service.app:app --host 127.0.0.1 --port 8001 --workers 1
```

The application backend defaults to `http://127.0.0.1:8001`. In production, configure the
same strong `WORLD_MODEL_SERVICE_TOKEN` on both services and set
`WORLD_MODEL_SERVICE_URL` on the application backend to the private service URL.
Set `WORLD_MODEL_DEVICE=cuda:0` to place the planner and text encoder on a CUDA GPU.
The default is `cpu`; deploy this service separately from the public lesson-generation provider.

Endpoints:

- `GET /health`: reports whether startup loading has completed.
- `GET /model-info`: returns the active model and training-dataset versions.
- `POST /predict-action`: scores candidate instructional actions.

`/model-info` and `/predict-action` require bearer authorization when the service token is
configured (required in production). The implementation imports `leap.planning.runtime`;
it does not generate lesson content or run learner Python cells.

The application currently samples actions uniformly and records these predictions as a
shadow policy. It can continue collection without this service, labeling its predictions
unavailable. That fallback is in `backend/app/main.py`, not in this inference host.

See [deployment](../docs/deployment.md), [project structure](../docs/project-structure.md),
and [research status](../LEAP/docs/system/roadmap.md).
