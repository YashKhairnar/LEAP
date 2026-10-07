# Where code belongs

Updated 2026-09-14. Top-level service names, API routes and storage locations are unchanged.

## Frontend

```text
frontend/src/
├── app/                        Next.js routes, layouts and global styles
│   └── learn/                  Task introductions and lesson route entry points
├── features/
│   ├── learning/
│   │   ├── components/         Lesson UI, navigation, introductions, review, lesson clients
│   │   └── lib/                Task banks, stage metadata and instructional action types
│   ├── assessment/components/  Final questionnaire and assessment navigation
│   └── collection/
│       ├── components/         Sync status and retry UI
│       └── lib/                Queue, content IDs, event types and exposure clock
├── components/                 Cross-feature controls such as logout
│   └── ui/                     Reusable presentation primitives
├── lib/auth.ts                 Shared session and API access
└── proxy.ts                    Route authentication gate
```

Use `@/features/...` for feature imports. A route file should select the page and pass route
inputs; reusable lesson behavior belongs in the learning feature. Sentiment retains its
specialized lesson client, while CNN/regression share `task-lesson-client.tsx`. This move
does not merge their behavior. `adaptive-question.tsx` is retained legacy UI; current lesson
clients use `generated-tutor-card.tsx`.

| Change | File relative to `frontend/src/` |
|---|---|
| Lesson layout, analogy, explanation, experiments | `features/learning/components/generated-tutor-card.tsx` |
| Task or dataset introduction | `features/learning/components/task-introduction.tsx`, `dataset-introduction.tsx` |
| Sidebar and shell | `features/learning/components/learning-shell.tsx` |
| Task/stage text | `features/learning/lib/lesson-introductions.ts`, task banks |
| Final-assessment UI | `features/assessment/components/task-assessment.tsx` |
| Timing or failed sync | `features/collection/lib/`, `features/collection/components/` |

## Backend

```text
backend/
├── app/
│   ├── main.py          FastAPI entry point, auth dependencies and HTTP handlers
│   ├── models.py        Shared validated API/data contracts
│   ├── database.py      Transactions, persistence and resume state
│   ├── auth.py          Password and session-token primitives
│   ├── paths.py         Stable backend asset root
│   ├── tutoring/        generator.py, lesson_code.py
│   ├── assessments/     bank.py, service.py
│   ├── collection/      config.py, export.py
│   ├── execution/       cells.py, sandbox.py, runner.py, datasets.py
│   └── planning/        client.py, artifacts.py
├── scripts/             Dataset preparation and allowlisted collection export
├── tests/               API/domain regression tests (temporary databases)
├── datasets/            Versioned learner-exercise datasets and attribution
├── execution_runtime/   Isolated Python container definition
├── model_artifacts/     Promoted inference bundle, not research training outputs
└── data/                Local participant database; not source code
```

`tutoring/generator.py` owns LLM prompting/validation; `tutoring/lesson_code.py` owns the
fixed code, prerequisites and authored explore-the-code edits. Final MCQs and answer keys
live in `assessments/bank.py`; scoring lives in `assessments/service.py`. Python packages use
relative imports so both local `app.main:app` and root-level `backend.app.main:app` work.
Keep `runner.py` alongside `sandbox.py`: it is executed as an isolated script.

The shared persistence and contract modules remain centralized. Splitting them into more
files should be driven by ownership needs, not just file count.

## Research and inference

`LEAP/src/leap/` already has component packages: `shared`, `code_embeddings`, `learner_state`,
`action`, `observation`, `concepts`, `planning`, and `llm`. Matching scripts/configs/docs
remain in `LEAP`; its datasets, checkpoints and experiment paths are preserved.

`model_service/app.py` hosts `leap.planning.runtime.WorldModelRuntime`. It loads a promoted
bundle once. The application backend calls it through `app/planning/client.py`; it does
not import the research training stack to serve lessons.

## Import migration

Internal imports have changed; there are no duplicate compatibility implementations.
Update personal scripts/notebooks using old module names:

| Previous | Current |
|---|---|
| `app.tutor_generator` | `app.tutoring.generator` |
| `app.lesson_code` | `app.tutoring.lesson_code` |
| `app.assessment_bank` / `app.assessments` | `app.assessments.bank` / `app.assessments.service` |
| `app.collection_config` / `app.collection_export` | `app.collection.config` / `app.collection.export` |
| `app.cell_execution` / `app.code_sandbox` | `app.execution.cells` / `app.execution.sandbox` |
| `app.datasets` | `app.execution.datasets` |
| `app.world_model` / `app.model_artifacts` | `app.planning.client` / `app.planning.artifacts` |
| `src/components/generated-tutor-card.tsx` | `src/features/learning/components/generated-tutor-card.tsx` |
| `src/lib/collection.ts` | `src/features/collection/lib/collection.ts` |

Operational docs now live in `docs/`. The old deployment and collection-guide paths contain
short links to their canonical replacements. The design prompt is archived under `docs/design/`.
