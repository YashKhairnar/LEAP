# LEAP application API

FastAPI for authentication, persisted lessons, question attempts, final assessments,
code execution and research collection. SQLite is the local default; `DATABASE_URL`
selects PostgreSQL. The API does not load the research training stack.

## Run

From `backend/`:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Configuration is listed in [.env.example](.env.example). A local `.env` is not loaded
automatically; pass `--env-file .env` if using one, and replace sample values. Unset
`DATABASE_URL` for local SQLite. See [complete local setup](../docs/local-development.md).

## Packages

| Package/file under `app/` | Responsibility |
|---|---|
| `main.py` | HTTP routes, authentication dependencies and application lifecycle |
| `models.py` | Shared validated contracts |
| `database.py`, `auth.py`, `paths.py` | Persistence, credential primitives and stable asset paths |
| `tutoring/` | Ollama or Gemini generation, fixed lesson code and authored experiments |
| `assessments/` | Ten-question banks, unlock rules and server scoring |
| `collection/` | Mode settings and quality-checked export |
| `execution/` | Dataset access, executable cells and isolated code evaluator |
| `planning/` | Private world-model client and artifact utilities |

The startup paths remain `app.main:app` from this directory and
`backend.app.main:app` from the repository root.

## Endpoints

Interactive contracts are at `http://localhost:8000/docs`.

| Routes | Purpose |
|---|---|
| `GET /health` | API health |
| `POST /api/auth/register`, `login`, `logout`; `GET /api/auth/me` | Participant-code accounts and cookie sessions |
| `GET /api/progress` | Authenticated learner progress |
| `GET /api/datasets/{task}` | Dataset metadata and preview |
| `POST /api/code/evaluate`, `/api/code/run` | Restricted checks and real cell execution |
| `POST /api/tutor/generate` | Schema-validated lesson/question generation |
| `GET /api/tutor/resume/{task}/{stage}/{step}` | Persisted lesson/question; optional completed-stage review |
| `POST /api/tutor/plan` | Uniform delivered action plus optional shadow recommendation |
| `POST /api/interactions`, `/api/events` | Ordered responses and behavior events |
| `GET /api/assessments/{task}`, `POST /api/assessments/{task}` | Final questions and immutable first submission |

## External dependencies and data

Ollama defaults to `http://127.0.0.1:11434/api/chat` with `qwen3:8b`.
For hosted lesson generation, configure `TUTOR_LLM_PROVIDER=gemini` and provide
`GEMINI_MODEL` and `GEMINI_API_KEY`.
Actual cell execution requires [Docker/Codapi configuration](execution_runtime/README.md).
Exercise datasets and licenses stay in [datasets/ATTRIBUTION.md](datasets/ATTRIBUTION.md).

The [private model service](../model_service/README.md) reads promoted weights from
`backend/model_artifacts/`. Its outage leaves the uniform collection policy available,
with missing predictions explicitly marked; it does not bypass an unavailable generator.

Local participant data stays in `data/leap.db`. Registration uses random participant
codes rather than names/emails; internal learner IDs remain sensitive research identifiers.
There is no public research-data export endpoint.

## Collection and verification

Registration accepts `analogy_preference: "java" | "everyday"`. The signup form no longer
asks for Java experience; new accounts store `java_experience="unspecified"` for compatibility
with existing account and research schemas. Startup adds the preference column to existing
SQLite/PostgreSQL databases with a `java` default, preserving existing behavior.
Generation uses the authenticated account setting, not a caller's override, for both
new lessons and subsequent questions. Only the learner's server-saved lesson is reused;
browser-supplied lessons are not trusted as generation context. The prompt version was
updated; completed-stage review still preserves historical content.

Read [collection readiness](../docs/collection.md) before a pilot. It documents exact content
provenance, exposure timing, assistance labels, development-only assessment preview,
queue quarantine, explicit participant allowlists and export quality checks.

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/export_collection.py --help
```

Tests use temporary databases. The optional real-experiment test requires ML execution
packages. Exporting more responses does not retrain or promote a model.
