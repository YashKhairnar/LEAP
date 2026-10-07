import { API_URL, getAuth } from "@/lib/auth";

const QUEUE_PREFIX = "leap.collection.queue.v2";
const SESSION_KEY = "leap.learning.session.v1";

export type QueueItem = { endpoint: "/api/interactions" | "/api/events"; payload: unknown };
let activeFlush: Promise<number> | null = null;
const FAILED_PREFIX = "leap.collection.failed.v1";
export const COLLECTION_STATUS_EVENT = "leap-collection-status";

export function collectionStatus(): { pending: number; failed: number } {
  const user = getAuth()?.user.user_id;
  if (!user) return { pending: 0, failed: 0 };
  const failures = JSON.parse(window.localStorage.getItem(`${FAILED_PREFIX}.${user}`) ?? "[]") as unknown[];
  return { pending: readQueue(user).length, failed: failures.length };
}

function notifyStatus() { window.dispatchEvent(new Event(COLLECTION_STATUS_EVENT)); }

function queueKey(userId: string): string { return `${QUEUE_PREFIX}.${userId}`; }

function readQueue(userId: string): QueueItem[] {
  const raw = window.localStorage.getItem(queueKey(userId));
  if (!raw) return [];
  const parsed: unknown = JSON.parse(raw);
  if (!Array.isArray(parsed)) throw new Error("The saved collection queue is unreadable. Its raw data has been retained.");
  return parsed as QueueItem[];
}

function writeQueue(userId: string, queue: QueueItem[]): void {
  window.localStorage.setItem(queueKey(userId), JSON.stringify(queue));
  notifyStatus();
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
    if (getAuth()?.user.user_id !== userId) throw new Error("Account changed while syncing. Sign in to the original account to retry.");
    const queue = readQueue(userId);
    if (!queue.length) break;
    const item = queue[0];
    const response = await fetch(`${API_URL}${item.endpoint}`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(item.payload),
      signal: AbortSignal.timeout(20000),
    });
    if (!response.ok) {
      let detail = "";
      try { detail = String((await response.json() as { detail?: unknown }).detail ?? ""); } catch { /* Non-JSON API error. */ }
      const idempotentConflict = response.status === 409 &&
        (detail === "interaction already exists" || detail === "event already exists");
      if (!idempotentConflict) {
        if ([400, 409, 422].includes(response.status)) {
          // Preserve rejected records separately so one poison item cannot hold
          // every later response hostage. Never discard the raw failed payload.
          const key = `${FAILED_PREFIX}.${userId}`;
          const failures = JSON.parse(window.localStorage.getItem(key) ?? "[]") as unknown[];
          failures.push({ item, status: response.status, detail, failed_at: new Date().toISOString() });
          window.localStorage.setItem(key, JSON.stringify(failures));
        } else {
          throw new Error(`Collection API returned ${response.status}${detail ? `: ${detail}` : ""}`);
        }
      }
    }
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
  if (!activeFlush) activeFlush = drainQueue().finally(() => { activeFlush = null; notifyStatus(); });
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
