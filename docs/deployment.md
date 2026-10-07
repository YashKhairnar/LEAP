# LEAP deployment

Repository configuration reviewed 2026-09-14. This guide describes the checked-in setup;
it does not verify the current health or settings of an external deployment.

The topology is a Vercel frontend, Render application API and private world-model service,
and Neon PostgreSQL. A configured Qwen generator and an isolated code runtime must also
be reachable from the backend.

## Backend and private model service

The root [render.yaml](../render.yaml) builds from the repository root, not a renamed
service folder. Entry points remain:

- `uvicorn backend.app.main:app` for the API;
- `uvicorn model_service.app:app` for the model service, with one worker.

Configure the API environment:

- `DATABASE_URL`: Neon PostgreSQL connection string with required TLS settings.
- `ENVIRONMENT=production`.
- `LEAP_COLLECTION_MODE`: explicitly choose development, pilot or study per the
  [collection guide](collection.md). This is a data label, not research approval.
- `FRONTEND_ORIGINS`: exact frontend origins.
- `TUTOR_LLM_PROVIDER=ollama` with `OLLAMA_CHAT_URL` and `OLLAMA_MODEL`, or
  `TUTOR_LLM_PROVIDER=openrouter` with `OPENROUTER_MODEL` and `OPENROUTER_API_KEY`.
  The generator must be reachable from Render, not localhost unless co-hosted.
- `WORLD_MODEL_SERVICE_URL`: private inference-service address.
- `WORLD_MODEL_SERVICE_TOKEN`: the same strong secret on both services.
- `CODE_EXECUTION_ENGINE=codapi`, `CODAPI_URL`, and token when needed for the checked-in
  hosted setup. Use a properly isolated self-hosted runtime where required.

The Blueprint links the model service address, but it does not provision a Qwen host
or all code-runtime dependencies. Configure those before calling the deployment complete.
Do not put secrets in committed YAML or examples.

The model service needs the complete checksummed bundle in `backend/model_artifacts/`.
Use [bundle promotion instructions](../backend/model_artifacts/README.md) only with
compatible reviewed artifacts and truthful training-dataset labels.

API `/health` is not a complete dependency test. The model service has its own `/health`;
`/model-info` and `/predict-action` require the configured service token.

## Frontend

Use `frontend` as the Vercel Root Directory. Set `BACKEND_URL` to the application API
origin and omit `NEXT_PUBLIC_API_URL` for same-origin `/api/*` proxying and first-party
session cookies. Redeploy when changing configuration.

URLs and root service locations are unchanged by the feature-folder reorganization.
Internal Python imports have changed; see the [migration map](project-structure.md).

## Verification before inviting participants

1. Use an explicitly excluded development account; verify registration, login and logout.
2. Load a task introduction/dataset, generate a lesson and run an executable cell.
3. Check that no question presentation is recorded until Practice/Split view exposes it.
4. Test hints, incorrect answers, retries, reload and offline/reconnect synchronization.
5. Confirm immutable question records, ordered events and assistance labels in the database.
6. Complete a task and submit the final assessment; ensure early previews are blocked in
   pilot/study mode and that the first submission is preserved.
7. Restart services and verify persistence. Confirm no pending/rejected browser records.
8. Audit an approved pilot allowlist; exclude development accounts rather than assuming
   all stored data belongs in training.

The signup notice is still a draft. Obtain the appropriate approval and finalize consent,
withdrawal, retention and outcome measures before formal human-subjects collection.
See [current limits](status.md); a successful deployment is not proof of learning benefit.
