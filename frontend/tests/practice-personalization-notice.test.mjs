import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const component = await readFile(
  new URL("../src/features/learning/components/generated-tutor-card.tsx", import.meta.url),
  "utf8",
);

test("the personalization notice gates only the learner's first practice question per task", () => {
  assert.match(component, /step === "practice"/);
  assert.match(component, /personalization-notice\.v1\.\$\{learner\?\.user_id/);
  assert.match(component, /generated && item && !showPersonalizationNotice/);
  assert.match(component, /I understand — start practice/);
});

test("the notice accurately names the learning signals used for personalization", () => {
  assert.match(component, /answer and whether it was correct/i);
  assert.match(component, /attempt count and whether you opened a hint/i);
  assert.match(component, /active response time while the question is visible/i);
  assert.match(component, /separate from the final assessment score/i);
  assert.match(component, /href="\/privacy"/);
});
