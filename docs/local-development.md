# Local development

All `cd` commands below start at the repository root unless stated otherwise. Use separate
terminals for services. No data migration is required for the folder restructure.

## Prerequisites

- Node 24+ for native TypeScript tests.
- Python 3.12 is the deployment target; use separate API and research environments.
- Ollama or OpenRouter with the configured model for lesson generation.
- Docker with the lesson runtime image, or a configured Codapi endpoint, for cells.
- The world-model service is optional for collection: uniform selection survives its
  outage, but model scoring is unavailable. Generation still requires a configured LLM.

## Backend (port 8000)

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Set environment variables before starting. Defaults use SQLite at `backend/data/leap.db`;
unset `DATABASE_URL` for SQLite. `.env.example` documents options but is not automatically
loaded. If creating a `.env`, replace the sample PostgreSQL URL and launch with
`uvicorn app.main:app --reload --env-file .env`. Never commit credentials or participant data.

Keep `ENVIRONMENT=development` and `LEAP_COLLECTION_MODE=development` for UI testing.
Read the [collection guide](collection.md) before selecting `pilot`. API docs are at
http://localhost:8000/docs; `/health` checks the API, not every external dependency.

## Frontend (port 3000)

```sh
cd frontend
npm ci
BACKEND_URL=http://localhost:8000 npm run dev
```

Open http://localhost:3000. Omit `NEXT_PUBLIC_API_URL` for same-origin `/api` proxying.
An existing `.env.local` containing that public variable overrides the browser target.
Explicitly set the local backend URL: `next.config.ts` otherwise defaults to the hosted
API. Direct public-URL mode remains supported.

## Generation and Python execution

```sh
ollama pull qwen3:8b
ollama serve
```

If Ollama already runs as a service, do not start a second instance. Configure
`OLLAMA_CHAT_URL`, `OLLAMA_MODEL` and timeout on the backend if changing defaults.

Build the runtime from the repository root:

```sh
docker build -t leap-python-runtime:latest backend/execution_runtime
```

Start the backend with `CODE_EXECUTION_ENGINE=docker`. Alternatively configure
`CODE_EXECUTION_ENGINE=codapi` and `CODAPI_URL`; see the
[runtime guide](../backend/execution_runtime/README.md). Exercise datasets under
`backend/datasets/` are separate from research data under `LEAP/data/`.

## Optional model service (port 8001)

See [model_service/README.md](../model_service/README.md) for installation/startup.
It requires a complete verified bundle in `backend/model_artifacts/`, not an arbitrary
checkpoint. Do not rebuild/promote weights simply to reorganize files.

## Checks

From `backend/`:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/export_collection.py --help
```

From `frontend/`:

```sh
npm test
npm run lint
npm run typecheck
npm run build -- --webpack
```

The webpack option is useful where Turbopack is restricted by the local sandbox, not a
change to production build defaults. Tests use temporary databases; the optional real ML
execution test requires runtime packages. Research tests and training are documented in
[LEAP reproduction](../LEAP/docs/system/reproduction.md).
