import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { stripTypeScriptTypes } from "node:module";

// Execute the real queue implementation with only its auth/network/browser boundaries
// substituted. No app server or participant storage is used.
const source = stripTypeScriptTypes(await readFile(new URL("../src/features/collection/lib/collection.ts", import.meta.url), "utf8"))
  .replace('import { API_URL, getAuth } from "@/lib/auth";', 'const API_URL = "https://collection.invalid"; const getAuth = () => ({ user: { user_id: "test-learner" } });');
const queueKey = "leap.collection.queue.v2.test-learner";
const failureKey = "leap.collection.failed.v1.test-learner";

async function fixture(t, fetchStub) {
  const storage = new Map();
  const originalWindow = globalThis.window;
  const originalFetch = globalThis.fetch;
  const browser = new EventTarget();
  browser.localStorage = { getItem: (key) => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) };
  globalThis.window = browser;
  globalThis.fetch = fetchStub;
  t.after(() => { globalThis.window = originalWindow; globalThis.fetch = originalFetch; });
  const queue = await import(`data:text/javascript;base64,${Buffer.from(source).toString("base64")}#${crypto.randomUUID()}`);
  return { storage, ...queue };
}

test("permanent rejection retains a copy and allows the next record to sync", async (t) => {
  const calls = [];
  const queue = await fixture(t, async (_url, request) => {
    calls.push(JSON.parse(request.body));
    return calls.length === 1 ? new Response(JSON.stringify({ detail: "content_id already exists with different content" }), { status: 409 }) : new Response("{}", { status: 201 });
  });
  queue.storage.set(queueKey, JSON.stringify([
    { endpoint: "/api/interactions", payload: { transition_id: "bad" } },
    { endpoint: "/api/events", payload: { event_id: "good" } },
  ]));
  await queue.flushCollectionQueue();
  assert.equal(calls.length, 2);
  assert.deepEqual(queue.collectionStatus(), { pending: 0, failed: 1 });
  assert.equal(JSON.parse(queue.storage.get(failureKey))[0].item.payload.transition_id, "bad");
});

test("offline attempt stays queued and saves after reconnection", async (t) => {
  let offline = true;
  const queue = await fixture(t, async () => {
    if (offline) throw new TypeError("Network unavailable");
    return new Response("{}", { status: 201 });
  });
  await assert.rejects(queue.enqueueCollection({ endpoint: "/api/events", payload: { event_id: "offline" } }));
  assert.deepEqual(queue.collectionStatus(), { pending: 1, failed: 0 });
  offline = false;
  await queue.flushCollectionQueue();
  assert.deepEqual(queue.collectionStatus(), { pending: 0, failed: 0 });
});

test("idempotent duplicates succeed without quarantine", async (t) => {
  const queue = await fixture(t, async () => new Response(JSON.stringify({ detail: "event already exists" }), { status: 409 }));
  await queue.enqueueCollection({ endpoint: "/api/events", payload: { event_id: "existing" } });
  assert.deepEqual(queue.collectionStatus(), { pending: 0, failed: 0 });
});

test("a corrupt saved queue is reported and never overwritten", async (t) => {
  const queue = await fixture(t, async () => assert.fail("No request should be sent"));
  queue.storage.set(queueKey, "broken JSON");
  await assert.rejects(queue.enqueueCollection({ endpoint: "/api/events", payload: { event_id: "new" } }));
  assert.equal(queue.storage.get(queueKey), "broken JSON");
});
