import { API_URL, setAuth, type AuthUser } from "@/lib/auth";

const RESEARCH_ID_KEY = "leap.workshop.research-id.v1";

export function storedResearchId(): string | null {
  try { return window.localStorage.getItem(RESEARCH_ID_KEY); } catch { return null; }
}

export function rememberResearchId(researchId: string | null): void {
  try {
    if (researchId) window.localStorage.setItem(RESEARCH_ID_KEY, researchId);
    else window.localStorage.removeItem(RESEARCH_ID_KEY);
  } catch { /* display convenience only */ }
}

export type WorkshopVersionInfo = { version_id: string; label: string; description: string };

/** A new research ID has to pick a version before entering. */
export class VersionChoiceNeeded extends Error {
  constructor(readonly versions: WorkshopVersionInfo[]) { super("Choose a version of the workshop."); }
}

/** Enter the workshop with a research ID only; the server sets the session cookie. */
export async function enterWorkshop(researchId: string, version?: string): Promise<{ user: AuthUser; research_id: string; workshop_version: WorkshopVersionInfo }> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/workshop/enter`, {
      method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ research_id: researchId, version: version ?? null }),
    });
  } catch {
    throw new Error("We couldn’t reach the workshop. Check your connection and try again.");
  }
  const body = await response.json().catch(() => ({})) as { user?: AuthUser; research_id?: string; workshop_version?: WorkshopVersionInfo; detail?: unknown };
  const detail = body.detail as { needs_version?: boolean; versions?: WorkshopVersionInfo[] } | string | undefined;
  if (response.status === 409 && detail && typeof detail === "object" && detail.needs_version) throw new VersionChoiceNeeded(detail.versions ?? []);
  if (!response.ok || !body.user || !body.research_id || !body.workshop_version) {
    throw new Error(typeof body.detail === "string" ? body.detail : "We couldn’t sign you in. Check your research ID and try again.");
  }
  setAuth({ user: body.user });
  rememberResearchId(body.research_id);
  return { user: body.user, research_id: body.research_id, workshop_version: body.workshop_version };
}

export type BoxVariant = "see" | "did" | "check" | "warning" | "plain" | "analogy";
export type WorkshopBlock =
  | { type: "paragraph"; text: string }
  | { type: "heading"; text: string; level: 2 | 3 }
  | { type: "quote"; text: string; cite: string | null }
  | { type: "aside"; text: string }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "box"; variant: BoxVariant; title: string | null; items: string[] }
  | { type: "table"; columns: string[]; rows: string[][] }
  | { type: "cell"; cell_id: string }
  | { type: "questions" }
  | { type: "banner"; title: string; items: string[]; note: string }
  | { type: "dataset_download" }
  | { type: "own_reviews_guide"; items: { label: string; from: string; to: string }[]; notes: string[] }
  | { type: "post_survey" }
  | { type: "checklist"; title: string; intro: string; items: { text: string; auto: "cells" | "answers" | null }[]; note: string };

export type WorkshopCell = { cell_id: string; stage_id: string; label: string; title: string; code: string; kind: "standard" | "upload" | "own_reviews"; instructions: string[]; paste_placeholder: string };
export type WorkshopQuestion = { question_id: string; stage_id: string; prompt: string };
export type WorkshopStage = { stage_id: string; nav_label: string; short_label: string; title: string; blocks: WorkshopBlock[]; cells: WorkshopCell[]; questions: WorkshopQuestion[] };
export type WorkshopContent = { workshop_id: string; version: string; workshop_version: WorkshopVersionInfo; title: string; dataset: { filename: string; bytes: number; header: string }; post_survey_url: string | null; stages: WorkshopStage[] };

export type TablePreview = { columns: string[]; rows: Record<string, unknown>[] };
export type CellRun = { run_id: string; cell_id: string; execution_count: number; code: string; success: boolean; stdout: string; stderr: string; result: unknown; table_preview: TablePreview | null; plots: string[]; duration_ms: number; created_at: string };
export type WorkshopState = {
  research_id: string | null;
  workshop_version: WorkshopVersionInfo;
  current_stage: string;
  completed_stages: string[];
  uploaded_filename: string | null;
  workshop_complete: boolean;
  cells: Record<string, { done: boolean; latest: CellRun | null }>;
  answers: Record<string, { answer: string; saved_at: string }>;
  cells_done: number; cells_total: number; answers_done: number; answers_total: number;
};

export class WorkshopError extends Error {
  constructor(message: string, readonly status: number, readonly missing: string[] = []) { super(message); }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}/api/workshop${path}`, {
    credentials: "include", cache: "no-store", ...init,
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
  });
  const body = await response.json().catch(() => ({})) as { detail?: string | { message: string; missing: string[] } };
  if (!response.ok) {
    const detail = body.detail;
    if (detail && typeof detail === "object") throw new WorkshopError(detail.message, response.status, detail.missing);
    throw new WorkshopError(typeof detail === "string" ? detail : `The workshop service returned ${response.status}.`, response.status);
  }
  return body as T;
}

export const workshopDatasetUrl = `${API_URL}/api/workshop/dataset.csv`;
export const getWorkshopContent = () => request<WorkshopContent>("/content");
export const getWorkshopState = () => request<WorkshopState>("/state");
export const completeWorkshopStage = (stageId: string) => request<WorkshopState>(`/stages/${encodeURIComponent(stageId)}/complete`, { method: "POST" });
export const saveWorkshopAnswer = (questionId: string, answer: string) =>
  request<{ question_id: string; answer: string; saved_at: string }>(`/answers/${encodeURIComponent(questionId)}`, { method: "PUT", body: JSON.stringify({ answer }) });
export const runWorkshopCell = (cellId: string, code: string, uploadedFile?: { name: string; size: number }) =>
  request<CellRun & { done: boolean }>(`/cells/${encodeURIComponent(cellId)}/run`, { method: "POST", body: JSON.stringify({ code, uploaded_file: uploadedFile ?? null }) });

/** Stages a learner can open: every completed stage plus the current one. */
export function stageUnlocked(state: WorkshopState, stageId: string): boolean {
  return state.completed_stages.includes(stageId) || state.current_stage === stageId;
}
