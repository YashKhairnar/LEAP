import { API_URL, getAuth } from "./auth";

const QUEUE_PREFIX = "leap.collection.queue.v2";
const SESSION_KEY = "leap.learning.session.v1";

export type QueueItem = { endpoint: "/api/interactions" | "/api/events"; payload: unknown };
let activeFlush: Promise<number> | null = null;

function queueKey(userId: string): string { return `${QUEUE_PREFIX}.${userId}`; }

function readQueue(userId: string): QueueItem[] {
  const raw = window.localStorage.getItem(queueKey(userId));
  if (!raw) return [];
  try { return JSON.parse(raw) as QueueItem[]; } catch { return []; }
}

function writeQueue(userId: string, queue: QueueItem[]): void {
  window.localStorage.setItem(queueKey(userId), JSON.stringify(queue));
}

export function learningSessionId(): string {
  const existing = window.sessionStorage.getItem(SESSION_KEY);
  if (existing) return existing;
  const created = crypto.randomUUID();
  window.sessionStorage.setItem(SESSION_KEY, created);
  return created;
}

async function drainQueue(): Promise<number> {
  const auth = getAuth();
  if (!auth) throw new Error("Sign in before collecting learner events");
  const userId = auth.user.user_id;
  let saved = 0;
  while (true) {
    const queue = readQueue(userId);
    if (!queue.length) break;
    const item = queue[0];
    const response = await fetch(`${API_URL}${item.endpoint}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item.payload),
    });
    if (!response.ok && response.status !== 409) throw new Error(`Collection API returned ${response.status}`);
    const latestQueue = readQueue(userId);
    const itemSignature = JSON.stringify(item);
    const savedIndex = latestQueue.findIndex((candidate) => JSON.stringify(candidate) === itemSignature);
    if (savedIndex >= 0) latestQueue.splice(savedIndex, 1);
    writeQueue(userId, latestQueue);
    saved += 1;
  }
  return saved;
}

export function flushCollectionQueue(): Promise<number> {
  if (!activeFlush) activeFlush = drainQueue().finally(() => { activeFlush = null; });
  return activeFlush;
}

export async function enqueueCollection(item: QueueItem): Promise<void> {
  const auth = getAuth();
  if (!auth) throw new Error("Sign in before collecting learner events");
  const queue = readQueue(auth.user.user_id);
  queue.push(item);
  writeQueue(auth.user.user_id, queue);
  await flushCollectionQueue();
}
