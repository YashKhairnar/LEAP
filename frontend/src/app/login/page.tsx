"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { authenticate } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError("");
    const data = new FormData(event.currentTarget);
    try {
      await authenticate("login", { participant_code: data.get("participant_code"), password: data.get("password") });
      router.push("/");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to sign in"); setBusy(false); }
  };
  return <main className="auth-shell"><section className="auth-aside"><Link className="brand auth-brand" href="/"><span>LEAP</span></Link><div><p className="eyebrow">Java → Python → ML</p><h1>Build on what you already know.</h1><p>Learn a complete machine-learning pipeline through familiar Java concepts and one continuous sentiment-classification problem.</p></div><p className="auth-footnote">Six stages. One connected learning path.</p></section><section className="auth-form-wrap"><form className="auth-form" onSubmit={submit}><p className="eyebrow blue">Welcome back</p><h2>Continue learning</h2><p className="auth-subtitle">Use the anonymous participant code issued when you registered.</p><label>Participant code<input name="participant_code" required type="text" autoCapitalize="characters" autoComplete="username" pattern="LP-[A-Fa-f0-9]{12}" placeholder="LP-1234ABCD5678" /></label><label>Password<input name="password" required type="password" autoComplete="current-password" placeholder="Enter your password" /></label>{error && <p className="auth-error" role="alert">{error}</p>}<button className="auth-submit" disabled={busy} type="submit">{busy ? "Signing in…" : "Sign in"}</button><p className="auth-switch">New to LEAP? <Link href="/signup">Create an account</Link></p></form></section></main>;
}
