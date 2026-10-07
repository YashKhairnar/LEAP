export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");
const AUTH_KEY = "leap.auth.v2";
const LEGACY_AUTH_KEY = "leap.auth.v1";

export type AnalogyPreference = "pure_ml" | "everyday" | "java";
export type AuthUser = { user_id: string; participant_code: string; java_experience: string; analogy_preference: AnalogyPreference };
export type AuthSession = { user: AuthUser };
export type TaskProgress = { task: string; completed_stages: number; total_stages: number; task_complete: boolean; current_stage: string | null; current_step: string | null; updated_at: string };

export function getAuth(): AuthSession | null {
  if (typeof window === "undefined") return null;
  window.localStorage.removeItem(LEGACY_AUTH_KEY);
  const value = window.localStorage.getItem(AUTH_KEY);
  if (!value) return null;
  try { return JSON.parse(value) as AuthSession; } catch { return null; }
}

export function setAuth(auth: AuthSession): void {
  window.localStorage.removeItem(LEGACY_AUTH_KEY);
  window.localStorage.setItem(AUTH_KEY, JSON.stringify(auth));
}

export function clearAuth(): void {
  window.localStorage.removeItem(AUTH_KEY);
  window.localStorage.removeItem(LEGACY_AUTH_KEY);
}

export async function validateAuth(): Promise<AuthUser | null> {
  const response = await fetch(`${API_URL}/api/auth/me`, { credentials: "include" });
  if (!response.ok) { clearAuth(); return null; }
  const user = await response.json() as AuthUser;
  setAuth({ user });
  return user;
}

export async function getTaskProgress(): Promise<TaskProgress[]> {
  const response = await fetch(`${API_URL}/api/progress`, { credentials: "include", cache: "no-store" });
  if (!response.ok) return [];
  return response.json() as Promise<TaskProgress[]>;
}

export async function authenticate(path: "register" | "login", body: object): Promise<AuthSession> {
  const response = await fetch(`${API_URL}/api/auth/${path}`, {
    method: "POST", credentials: "include", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail ?? "Authentication failed");
  setAuth(result as AuthSession);
  return result as AuthSession;
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_URL}/api/auth/logout`, { method: "POST", credentials: "include" });
  } finally {
    clearAuth();
    window.sessionStorage.removeItem("leap.learning.session.v1");
  }
}
