import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import postcss from "postcss";

// Structural CSS regression checks, not a substitute for browser layout testing.
const stylesheet = postcss.parse(await readFile(new URL("../src/app/globals.css", import.meta.url), "utf8"));
const rules = [];
stylesheet.walkRules((rule) => rules.push(rule));
const declaration = (rule, property) => rule.nodes.find((node) => node.type === "decl" && node.prop === property)?.value;

test("full-width auth fields exclude radio buttons and checkboxes", () => {
  const fields = rules.filter((rule) => rule.selector.includes(".auth-form input") && declaration(rule, "width") === "100%");
  assert.ok(fields.length > 0);
  for (const rule of fields) {
    for (const selector of rule.selectors.filter((selector) => selector.includes("input"))) {
      assert.match(selector, /:not\(\[type=radio\]\)/);
      assert.match(selector, /:not\(\[type=checkbox\]\)/);
    }
  }
});

test("analogy cards keep controls compact and let text shrink on narrow screens", () => {
  const card = rules.find((rule) => rule.selector === ".auth-form .analogy-choice");
  const radio = rules.find((rule) => rule.selector === ".auth-form .analogy-choice input[type=radio]");
  const copy = rules.find((rule) => rule.selector === ".analogy-choice > span");
  assert.equal(declaration(card, "display"), "grid");
  assert.equal(declaration(card, "grid-template-columns"), "18px minmax(0, 1fr)");
  assert.equal(declaration(radio, "width"), "18px");
  assert.equal(declaration(radio, "height"), "18px");
  assert.equal(declaration(copy, "min-width"), "0");
});
