# Current research roadmap

Updated 2026-09-14. For application status, see
[the cross-project status](../../../docs/status.md).

## Already implemented

The repository includes passive DCU JEPA pretraining, action/observation adapters,
action-conditioned training with EMA targets, no-action and identity baselines,
one-step planning, generic concept probes, LLM context demos, and a private inference
runtime with checksummed bundle promotion.

The app now records immutable generated content, visible-question timing, hint/reveal
labels and uniform assignment probabilities. Pilot/study assessment previews are locked,
and explicit-allowlist exports audit provenance and provide learner-level split labels.
These are collection capabilities, not new training results.

## Next: collect interpretable evidence

1. Finalize participant governance and review generated content and fixed final MCQs.
2. Define a baseline, unseen transfer/delayed outcomes, and a comparison policy. Final
   questionnaire correctness alone does not establish learning gain.
3. Run a technical pilot using the [collection checklist](../../../docs/collection.md).
4. Gather an approved cohort with a fixed collection mode and explicit account eligibility.
5. Audit joined content, presentations and responses before preparing training inputs.
   Preserve complete histories, assistance labels, assignment probabilities and learner splits.

The current application selects uniformly among eligible action types in the active
phase; the model's recommendation is logged as a shadow policy. Do not switch to a
greedy model policy merely because inference works.

## Training and evaluation work

- Integrate the export's quality and split labels explicitly: existing research
  preprocessors do not automatically enforce them.
- Build targets from actual responses/history, never from stored model predictions.
- Reassess action-conditioned prediction against the no-action baseline on held-out learners.
- Evaluate sensitivity to action changes, calibration and unseen concept/transfer outcomes.
- Keep semantic mastery claims separate from latent-distance metrics; the handcrafted goal
  is not a validated mastery target, and the recorded probe results remain inconclusive.
- Consider unfreezing or learner-specific adapters only after the global action signal is
  reliable. Promote a compatible bundle only after reviewed evaluation.

## Why more data matters

Passive code attempts do not identify the effects of teaching interventions. New records
must distinguish the exact delivered question, assignment mechanism, prior exposures,
assistance and later independent outcomes. Repeated correct answers after revealing a
solution should not become independent-success labels.

Historical Experiment 1 and probe metrics in the component docs remain tied to their
recorded datasets/checkpoints. Collecting new app responses does not update those results
or the deployed checkpoint automatically.
