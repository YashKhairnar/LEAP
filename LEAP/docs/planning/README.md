# One-step planner

Location: `src/leap/planning/`

The planner implements receding-horizon, one-step planning. Given current learner state
`z_t`, a set of valid actions, and a 128-D goal state, it computes:

```text
each candidate action -> ActionEncoder -> a_i
(z_t, a_i) -> ActionConditionedPredictor -> predicted next state
predicted next state vs. goal state -> distance
smallest distance -> selected action
```

In the intended adaptive loop, after delivering an action the system observes the learner
response, re-encodes a latent estimate from history, and runs the planner again. Candidate sets may contain any number
of actions; the current tutor supplies three. Invalid candidates can be excluded with a
boolean mask.

The current web application does not deliver the greedy recommendation: it samples the
eligible action types uniformly and logs this planner as a shadow policy. Online inference
lives in `runtime.py`, hosted by `model_service/app.py` at the workspace root. API requests
allow one to three distinct phase-valid candidates. If that optional service fails, the API
retains uniform assignment and explicitly records unavailable predictions.

Cosine distance is the default because the JEPA predictor was trained with cosine loss.
Euclidean distance is also supported. `plan_from_history` performs state encoding and
planning together, while `forward` accepts a precomputed 128-D current state.

The planner returns the selected index and action, its predicted state and distance, plus
all candidate action vectors, predicted states, and distances for logging and analysis.
When Probe V2 is supplied, it also converts every predicted next state into 64 concept
mastery scores and returns `selected_concept_mastery` for the LLM-content stage.

This is currently a pipeline implementation, not evidence of educational effectiveness.
Action sensitivity should be validated when more tutoring data is available.

## Current experimental goal

The current demonstration uses a handcrafted 128-D goal containing 64 leading ones and 64
trailing zeros. It is implemented by `handcrafted_binary_goal`. This is a user-defined
planning target; the learned latent dimensions are not yet validated as literal
understanding and misunderstanding coordinates.

A generic 64-concept ontology, weak mastery labels, and two linear probes now exist. Probe
V2 is trained specifically on predicted next states and is integrated with the planner.
Its held-out result does not beat the baseline, so the output must not yet be treated as a
reliable mastery estimate or proof that the latent dimensions represent those concepts.

Run the real three-action demonstration with:

```bash
python scripts/planning/demo_one_step.py
```
