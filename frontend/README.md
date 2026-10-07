# LEAP frontend

Next.js App Router + React learner interface. Routes stay under `src/app`; learning,
assessment and collection implementations are grouped under `src/features`.

Signup includes a choice between Java-reference lessons and everyday examples, separate
from Java experience. The server saves the choice and applies it to generated lessons and
follow-up questions; executable Python code and final assessments are unchanged.

## Run

From `frontend/`:

```sh
npm ci
BACKEND_URL=http://localhost:8000 npm run dev
```

Open http://localhost:3000. Omit `NEXT_PUBLIC_API_URL` for same-origin API proxying.
Check existing `.env.local` settings: the default proxy target is the hosted backend,
so explicitly configure localhost for local work.

## Find code

- `src/features/learning/components/`: introductions, lesson cards, task clients and review.
- `src/features/learning/lib/`: stage/task metadata and action/question banks.
- `src/features/assessment/components/`: final ten-question assessment.
- `src/features/collection/`: event queue, exposure timing and sync status.
- `src/components/ui/`: shared visual primitives.
- `src/lib/auth.ts`: shared API/session access.
- `src/app/globals.css`: current shared styles.
- `tests/`: timing and queue regression tests.

Use [the file map](../docs/project-structure.md) for specific edit locations.
The former UI prompt is now a [historical design brief](../docs/design/lesson-ui-brief.md).

## Checks

```sh
npm test
npm run lint
npm run typecheck
npm run build -- --webpack
```

Tests use Node 24's native TypeScript support. The webpack option avoids local Turbopack
sandbox restrictions; the default build script is unchanged. Run type checking after,
not concurrently with, a build that rewrites `.next` types.

See [local development](../docs/local-development.md), [current status](../docs/status.md),
and [collection safeguards](../docs/collection.md). This folder reorganization does not
change learner-facing URLs or automatically deploy the application.
