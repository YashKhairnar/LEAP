"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { VersionChoiceNeeded, enterWorkshop, type WorkshopVersionInfo } from "@/features/workshop/lib/workshop-api";
import { WORKSHOP_HREF } from "@/features/workshop/lib/visibility";

/**
 * Sign-in for the workshop: a research ID only, no account or password.
 * A new ID then chooses its version of the workshop once; a returning ID goes straight in.
 */
export default function ResearchIdEntry() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [researchId, setResearchId] = useState("");
  const [versions, setVersions] = useState<WorkshopVersionInfo[] | null>(null);
  const [choice, setChoice] = useState("");

  const enter = async (version?: string) => {
    setBusy(true); setError("");
    try {
      await enterWorkshop(researchId.trim(), version);
      router.replace(WORKSHOP_HREF);
    } catch (reason) {
      if (reason instanceof VersionChoiceNeeded) { setVersions(reason.versions); setBusy(false); return; }
      setError(reason instanceof Error ? reason.message : "We couldn’t sign you in.");
      setBusy(false);
    }
  };

  const submitId = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!researchId.trim()) { setError("Enter your research ID."); return; }
    void enter();
  };

  const submitChoice = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!choice) { setError("Choose one option to continue."); return; }
    void enter(choice);
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
      {versions ? <form className="auth-form" onSubmit={submitChoice}>
        <p className="eyebrow blue">Research ID {researchId.trim()}</p>
        <h2>How should the workshop explain things?</h2>
        <p className="auth-subtitle">Every option teaches the same Python and machine learning, with the same code. Only the explanations change. You choose once: this research ID keeps your choice.</p>
        <fieldset className="analogy-preference" disabled={busy}>
          <legend className="visually-hidden">Workshop version</legend>
          {versions.map((version) => <label className="analogy-choice" key={version.version_id}>
            <input type="radio" name="workshop_version" value={version.version_id} checked={choice === version.version_id} onChange={() => { setChoice(version.version_id); setError(""); }} required />
            <span><strong>{version.label}</strong><small>{version.description}</small></span>
          </label>)}
        </fieldset>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="auth-submit" disabled={busy} type="submit">{busy ? "Entering…" : "Start the workshop"}</button>
        <p className="auth-switch"><button type="button" className="text-button" disabled={busy} onClick={() => { setVersions(null); setChoice(""); setError(""); }}>← Use a different research ID</button></p>
      </form> : <form className="auth-form" onSubmit={submitId}>
        <p className="eyebrow blue">Welcome</p>
        <h2>Enter the workshop</h2>
        <p className="auth-subtitle">Type the research ID you were given. Use the same ID to come back later and continue where you left off.</p>
        <label>Research ID<input name="research_id" required maxLength={64} type="text" autoComplete="off" autoCapitalize="characters" spellCheck={false} placeholder="Your research ID" disabled={busy} value={researchId} onChange={(event) => setResearchId(event.target.value)} /></label>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="auth-submit" disabled={busy} type="submit">{busy ? "Entering…" : "Enter workshop"}</button>
      </form>}
    </section>
  </main>;
}
