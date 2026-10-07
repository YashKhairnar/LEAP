# Current implementation

Reviewed against source on 2026-09-14. This is not a claim that a production deployment has
been updated or that published experimental results have been rerun.

## Implemented

- Signup preference for Java references or everyday analogies, independent of Java experience.
  The account setting controls full lessons and follow-up questions; Python examples remain fixed.

- Three tasks (sentiment, CNN, regression), six stages each; current lesson navigation uses
  Bridge, Apply and Check (`connect`, `practice`, `review`).
- Task introduction followed by dataset preview; completed-stage review and persisted resume.
- Six-part generated lessons: meaning, analogy, example, Python code, result, why it matters;
  code explanations, deterministic exploration edits and short takeaways.
- Fixed server-owned code and prerequisites, versioned exercise datasets, isolated execution.
- Ten authored MCQs per task, server-side scoring, immutable first submission, no early
  question preview in pilot/study modes.
- Original content/provenance saved before answering, visibility-based timing, hint/reveal
  evidence labels, ordered events, queue retry/quarantine and visible sync warnings.
- Explicit participant-allowlisted exports with quality audits and learner-level split labels.
- A private inference service and a uniform-random delivered-action policy. World-model
  recommendations remain shadow-only, with a marked outage fallback.
- Research code for passive JEPA pretraining, action-conditioned training, no-action/identity
  baselines, concept probes, offline planning and model-bundle promotion.

## Not yet established

- Approved consent/withdrawal/retention protocol: the current consent version is still a draft.
- Reviewed baseline, unseen-transfer and delayed assessments demonstrating learning gain.
- Reliable concept mastery decoding or benefit from adaptive action selection. The handcrafted
  latent goal and probe outputs are experimental, not validated knowledge measurements.
- End-to-end automated training that honors new export quality/split labels. Existing research
  preprocessors accept the record envelope but need an explicit reviewed integration step.
- Validated multi-tab/offline field collection. A clean server export alone cannot prove that
  every browser has finished syncing. Check participant devices during a technical pilot.

## Next sequence

1. Run the field checklist in [collection](collection.md), including reload/offline/retry cases.
2. Review instructional content and define baseline/transfer outcomes and participant governance.
3. Collect an approved cohort using fixed mode, explicit eligibility and logged probabilities.
4. Audit/export; preserve learner-level splits and distinguish assisted from independent evidence.
5. Compare against no-action baselines and evaluate action sensitivity before policy promotion.

Research metrics already recorded in `LEAP/docs/` are historical results for their recorded
datasets/checkpoints; more app responses do not update those metrics automatically.
