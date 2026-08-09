"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { authenticate } from "@/lib/auth";

export default function SignupPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError("");
    const data = new FormData(event.currentTarget);
    try {
      await authenticate("register", { name: data.get("name"), email: data.get("email"), password: data.get("password"), java_experience: data.get("java_experience"), consent: data.get("consent") === "on", consent_version: "draft-research-consent-v1" });
      router.push("/");
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Unable to create account"); setBusy(false); }
  };
  return <main className="auth-shell"><section className="auth-aside"><Link className="brand auth-brand" href="/"><span>LEAP</span></Link><div><p className="eyebrow">Start with experience</p><h1>Your Java knowledge is the starting point.</h1><p>Translate familiar programming ideas into Python, pandas, and the reasoning behind machine learning.</p></div><p className="auth-footnote">Learn by connecting, implementing, and practicing.</p></section><section className="auth-form-wrap"><form className="auth-form" onSubmit={submit}><p className="eyebrow blue">Create your account</p><h2>Begin the learning path</h2><p className="auth-subtitle">Your account gives every learner trajectory a stable anonymous user ID.</p><label>Full name<input name="name" required type="text" autoComplete="name" placeholder="Your name" /></label><label>Email address<input name="email" required type="email" autoComplete="email" placeholder="you@university.edu" /></label><label>Password<input name="password" required minLength={8} maxLength={128} type="password" autoComplete="new-password" placeholder="At least 8 characters" /></label><label>Java experience<select name="java_experience" defaultValue="comfortable"><option value="beginner">I know the basics</option><option value="comfortable">I’m comfortable with Java</option><option value="advanced">I use Java regularly</option></select></label><label className="consent-check"><input name="consent" required type="checkbox" /> <span>I consent to collection of my learning interactions for research and model development. I have read the <Link href="/privacy" target="_blank">draft research notice</Link>.</span></label>{error && <p className="auth-error" role="alert">{error}</p>}<button className="auth-submit" disabled={busy} type="submit">{busy ? "Creating account…" : "Create account"}</button><p className="auth-switch">Already have an account? <Link href="/login">Sign in</Link></p></form></section></main>;
}
