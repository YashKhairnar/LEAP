# Collection readiness

The collection plumbing supports a technical pilot. These changes do **not** establish
research approval, validate a learning-gain measure, or retrain the world model.

## Configure a cohort

Set `LEAP_COLLECTION_MODE` on the backend and restart it:

- `development` (default): development data; incomplete assessment previews are available
  only when `ENVIRONMENT` is not `production`.
- `pilot`: tagged pilot records; final questions are withheld until all stages are complete.
- `study`: the same technical restrictions, separately tagged. This is not an approval flag.

Use fresh participant accounts for a new cohort. Do not mix development/preview accounts
into the participant allowlist or switch modes halfway through a learner's task. Existing
records are not relabeled; old records without a mode remain `legacy_unknown`.

## What is recorded

- Signup stores `analogy_preference` (`java` or `everyday`). New accounts use
  `java_experience="unspecified"`; the legacy field remains so existing records stay readable.
  Generated-content metadata includes both values, so analyses can distinguish the
  learner-selected explanation styles. This preference is not a randomized intervention.

- The server saves the exact generated lesson/question and original planner/generator
  provenance before any response. Resume reuses that immutable content. Metadata-only
  differences from older clients cannot overwrite provenance or block subsequent attempts;
  actual question/lesson changes under the same ID are still rejected.
- `content_presented` fires on the first viewport intersection while the document is
  visible, not on generation. A fresh presentation ID identifies each resume/retry.
- `response_time_ms` with `timing_version=visible_foreground_v1` counts foreground,
  viewport-visible question time. Lesson-only time, background-tab time and time after
  checking an answer are excluded. This measures visibility, **not attention**. Scrolling
  any portion of the question into view qualifies; it does not prove the question was read.
- `content_exposure` events describe visibility, hints and answer reveals without changing
  the learner's navigation position.
- `evidence_kind` separates `independent`, `hint_assisted`, `post_feedback_retry` and
  `unknown`. A resumed unanswered question is conservatively unknown because another tab
  may have unsynced hints. A correct post-feedback retry is not independent mastery evidence.
- The delivered instructional action remains uniform random with logged probabilities.
  The world model is a shadow policy only. On its outage, vectors are empty and
  `shadow_status=unavailable`; no observed learner state is fabricated.
- Transitions, behavioral events, code executions and final assessments carry collection
  mode tags. First final-assessment submissions remain server-scored and immutable.

## Sync failures

The lesson shell displays pending/rejected record counts and retries periodically and
when the browser reconnects. Network/server errors retain the queue. Permanent validation
errors (400/422) and non-idempotent conflicts (409) are retained under
`leap.collection.failed.v1.<user_id>` in local storage so later records can sync.
Duplicate already-saved IDs are treated as successful retries. Corrupt queues are not erased.

Do not clear browser storage while records are pending or rejected. The Retry sync button
retries the pending queue; rejected copies need researcher review and are **not** automatically
resubmitted. Quarantine is local, so a clean server export cannot prove that no browser has
unsynced/rejected data. Check each pilot browser before declaring a session complete.
Use one active lesson tab per participant during the pilot; concurrent tabs are not a
validated collection workflow. Durable offline storage/withdrawal procedures still need
operational review.

## Audit and export

Create a JSON array containing only approved internal learner IDs (not participant login
codes). Use your deployment's database environment. Run from `backend/`:

```sh
.venv/bin/python scripts/export_collection.py --learner-ids /path/to/approved-learners.json --mode pilot --output /path/to/new-export --audit-only
.venv/bin/python scripts/export_collection.py --learner-ids /path/to/approved-learners.json --mode pilot --output /path/to/new-export
```

Audit-only does not write export files. Export refuses existing output directories, broken
presentation/content links, unverified timing/assistance/assignment, missing allowlisted
learners, or empty train/validation/test splits. Very small cohorts can legitimately have
empty splits: inspect them with audit-only and collect more data, rather than rerolling a
seed to optimize evaluation results. Invalid/legacy evidence is flagged, not silently fixed.

`transitions.json` uses the existing LEAP `learning_record` envelope and includes `quality`
and a stable, learner-level `split`. `manifest.json` records the seed and membership;
`events.json`, `assessments.json`, and `code_executions.json` retain related observations.
Treat internal IDs, answers and code as sensitive research data; no passwords, login codes
or authentication sessions are exported. The allowlist is an operator control, not an
automated consent/withdrawal verifier.

Assisted attempts remain in histories, labeled as such. Only clean first unassisted attempts
get `quality.independent_outcome=true`. Training code must explicitly honor the exported
split and quality fields; existing LEAP preprocessors do not automatically enforce them.
Do not randomly split individual responses across learners' histories or use
`learner_state.state_after` (a model prediction) as an observed target. No training run or
checkpoint promotion is performed by this exporter.

## Before formal collection or claims of improved understanding

1. Approve consent, withdrawal, retention and participant eligibility procedures. Signup
   currently records `draft-research-consent-v1`; changing collection mode does not change it.
2. Review generated questions/answer keys and the fixed final MCQs for correctness and
   coverage. Add a reviewed baseline and unseen transfer/delayed assessment protocol.
   Final MCQ accuracy alone does not establish learning gain or question-selection benefit.
3. Define the outcome and comparison policy before model optimization. The existing
   handcrafted latent goal is not a validated mastery target and remains shadow-only.
4. Run a field pilot: open Lesson without Practice (no presentation), reveal Practice,
   switch tabs, open a hint, answer incorrectly, retry, reload, disconnect/reconnect,
   complete a task and submit its assessment. Inspect the exported trace and sync status.

## Automated checks

From `backend/`:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

From `frontend/` (Node 24+ for the native TypeScript test import):

```sh
node --experimental-strip-types --test tests/*.test.mjs
npm run lint
npx tsc --noEmit
npx next build --webpack
```

The pure timing tests do not replace a browser field pilot. Tests use temporary databases,
not participant records; the optional lesson-runtime test requires ML execution packages.
