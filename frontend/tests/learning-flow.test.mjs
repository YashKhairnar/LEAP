import test from "node:test";
import assert from "node:assert/strict";
import { initialStageScreen, nextPathAction } from "../src/features/learning/lib/learning-flow.ts";

test("each new stage starts with its lesson and all later questions stay in practice", () => {
  assert.equal(initialStageScreen("connect", false), "learn");
  assert.equal(initialStageScreen("connect", true), "practice");
  for (const step of ["practice", "review"]) {
    assert.equal(initialStageScreen(step, false), "practice");
    assert.equal(initialStageScreen(step, true), "practice");
  }
  // Starting the next stage has its own false flag, regardless of the last question.
  assert.equal(initialStageScreen("connect", false), "learn");
});

test("all paths follow baseline, data, resumed learning, then final assessment", () => {
  for (const slug of ["sentiment", "cnn", "regression"]) {
    const root = `/learn/${slug}`;
    assert.equal(nextPathAction(slug, false, null).href, `${root}?view=starting-assessment`);
    assert.equal(nextPathAction(slug, true, null).href, `${root}?view=dataset`);
    assert.equal(nextPathAction(slug, true, { task_complete: false }).href, `${root}/lesson`);
    assert.equal(nextPathAction(slug, true, { task_complete: true }).href, `${root}?view=assessment`);
    // Legacy learning progress must not silently imply a completed baseline.
    assert.equal(nextPathAction(slug, false, { task_complete: false }).href, `${root}?view=starting-assessment`);
  }
});
