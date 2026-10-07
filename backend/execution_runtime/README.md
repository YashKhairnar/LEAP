# LEAP lesson execution runtime

Build once from the repository root:

```bash
docker build -t leap-python-runtime:latest backend/execution_runtime
```

Set `CODE_EXECUTION_ENGINE=docker` in the backend environment (pass `--env-file .env` to
Uvicorn if using `backend/.env`). Each submitted program runs as an unprivileged user with
no network, a read-only root filesystem, bounded CPU/memory/process resources, and only
its temporary dataset workspace mounted read-only.

The API implementation now lives in `backend/app/execution/cells.py`; the container files
and dataset paths are unchanged. This real ML runtime is distinct from the small instrumented
code-construction evaluator in `backend/app/execution/sandbox.py` and `runner.py`.
