"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { enterWorkshop } from "@/features/workshop/lib/workshop-api";
import { WORKSHOP_HREF } from "@/features/workshop/lib/visibility";

/** Sign-in for the workshop: a research ID only, no account or password. */
export default function ResearchIdEntry() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const researchId = String(new FormData(event.currentTarget).get("research_id") ?? "").trim();
    if (!researchId) { setError("Enter your research ID."); return; }
    setBusy(true); setError("");
    try {
      await enterWorkshop(researchId);
      router.replace(WORKSHOP_HREF);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "We couldn’t sign you in.");
      setBusy(false);
    }
  };

  return <main className="auth-shell">
    <section className="auth-aside">
      <span className="brand auth-brand"><span>LEAP</span></span>
      <div>
        <p className="eyebrow">SJSU CSED Research Lab</p>
        <h1>Machine Learning Workshop</h1>
        <p>Build a model that reads a restaurant review and decides whether it is positive or negative, one small piece of code at a time.</p>
      </div>
      <p className="auth-footnote">Six steps. One model you build yourself.</p>
    </section>
    <section className="auth-form-wrap">
      <form className="auth-form" onSubmit={submit}>
        <p className="eyebrow blue">Welcome</p>
        <h2>Enter the workshop</h2>
        <p className="auth-subtitle">Type the research ID you were given. Use the same ID to come back later and continue where you left off.</p>
        <label>Research ID<input name="research_id" required maxLength={64} type="text" autoComplete="off" autoCapitalize="characters" spellCheck={false} placeholder="Your research ID" disabled={busy} /></label>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="auth-submit" disabled={busy} type="submit">{busy ? "Entering…" : "Enter workshop"}</button>
      </form>
    </section>
  </main>;
}
