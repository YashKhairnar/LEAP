import test from "node:test";
import assert from "node:assert/strict";
import { QuestionExposureClock, evidenceKind } from "../src/features/collection/lib/question-exposure.ts";

test("timing excludes generation, lesson view, hidden-tab time and feedback", () => {
  const clock = new QuestionExposureClock();
  assert.equal(clock.elapsed(10000), 0);
  clock.setVisible(true, 10000);
  assert.equal(clock.elapsed(11000), 1000);
  clock.setVisible(false, 12000);
  assert.equal(clock.elapsed(90000), 2000);
  clock.setVisible(true, 90000);
  clock.setVisible(false, 90500);
  assert.equal(clock.elapsed(100000), 2500);
  clock.reset();
  assert.equal(clock.elapsed(110000), 0);
});

test("duplicate visibility events do not restart the clock", () => {
  const clock = new QuestionExposureClock();
  clock.setVisible(true, 100);
  clock.setVisible(true, 200);
  clock.setVisible(false, 300);
  clock.setVisible(false, 400);
  assert.equal(clock.elapsed(500), 200);
});

test("only known, unassisted first responses are independent evidence", () => {
  assert.equal(evidenceKind(false, false, true), "independent");
  assert.equal(evidenceKind(true, false, true), "hint_assisted");
  assert.equal(evidenceKind(false, true, true), "post_feedback_retry");
  assert.equal(evidenceKind(true, true, true), "post_feedback_retry");
  assert.equal(evidenceKind(false, false, false), "unknown");
});
