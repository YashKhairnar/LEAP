export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");
const AUTH_KEY = "leap.auth.v1";

export type AuthUser = { user_id: string; email: string; name: string; java_experience: string };
export type AuthSession = { user: AuthUser };

export function getAuth(): AuthSession | null {
  if (typeof window === "undefined") return null;
  const value = window.localStorage.getItem(AUTH_KEY);
  if (!value) return null;
  try { return JSON.parse(value) as AuthSession; } catch { return null; }
}

export function setAuth(auth: AuthSession): void {
  window.localStorage.setItem(AUTH_KEY, JSON.stringify(auth));
}

export function clearAuth(): void {
  window.localStorage.removeItem(AUTH_KEY);
}

export async function validateAuth(): Promise<AuthUser | null> {
  const response = await fetch(`${API_URL}/api/auth/me`, { credentials: "include" });
  if (!response.ok) { clearAuth(); return null; }
  const user = await response.json() as AuthUser;
  setAuth({ user });
  return user;
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
  }
}
