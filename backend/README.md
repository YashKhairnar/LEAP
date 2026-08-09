# LEAP backend

FastAPI service for authenticating learners and storing ordered learning events. Local
development uses SQLite; production uses PostgreSQL when `DATABASE_URL` is set.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Interactive documentation is available at `/docs`.

## Endpoints

- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/logout`
- `GET /api/progress` (returns authenticated learner progress for dashboard display)
- `POST /api/code/evaluate` (runs a stage-specific code-construction check in a restricted subprocess)
- `POST /api/interactions` (atomically stores content and an authenticated question attempt)
- `POST /api/events` (stores optional content, confidence, and navigation behavior)

Instructional content and raw learner transitions are stored in `data/leap.db` locally.
Production requires a PostgreSQL `DATABASE_URL`. Research data has no public read endpoint;
inspect or export it using authenticated database administration tools.

Raw transitions intentionally do not contain a fabricated learner-state vector. A learned state encoder will derive versioned latent states from ordered learner/session trajectories during model training.

Code construction is checked with a short-lived Python process using isolated mode, AST restrictions, a temporary working directory, a two-second timeout, and operating-system resource limits. It uses instrumented pandas/scikit-learn substitutes to verify the required learning operation without exposing the host dataset, network, or filesystem.
