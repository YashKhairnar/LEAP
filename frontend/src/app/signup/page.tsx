"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { authenticate, type AnalogyPreference } from "@/lib/auth";

export default function SignupPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [participantCode, setParticipantCode] = useState("");
  const [analogyPreference, setAnalogyPreference] = useState<AnalogyPreference>("pure_ml");

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const session = await authenticate("register", {
        password: data.get("password"),
        analogy_preference: analogyPreference,
        consent: data.get("consent") === "on",
        consent_version: "draft-research-consent-v1",
      });
      setParticipantCode(session.user.participant_code);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create account");
    } finally {
      setBusy(false);
    }
  };

  return <main className="auth-shell">
    <section className="auth-aside">
      <Link className="brand auth-brand" href="/"><span>LEAP</span></Link>
      <div>
        <p className="eyebrow">Start with what you know</p>
        <h1>Learn machine learning through familiar ideas.</h1>
        <p>Choose a direct ML path, everyday-life analogies, or Java references to understand Python and machine learning.</p>
      </div>
      <p className="auth-footnote">Learn by connecting, implementing, and practicing.</p>
    </section>
    <section className="auth-form-wrap">
      {participantCode ? <section className="auth-form" aria-live="polite">
        <p className="eyebrow blue">Anonymous account created</p>
        <h2>Save your participant code</h2>
        <p className="auth-subtitle">You will need this code and your password to sign in again. LEAP does not collect an email address, so the code cannot be recovered by email.</p>
        <output className="participant-code">{participantCode}</output>
        <button className="auth-submit" type="button" onClick={() => router.push("/")}>I saved my code →</button>
      </section> : <form className="auth-form" onSubmit={submit}>
        <p className="eyebrow blue">Create your account</p>
        <h2>Begin anonymously</h2>
        <p className="auth-subtitle">No name or email address is requested. LEAP will issue a random participant code.</p>
        <label>Password<input name="password" required minLength={8} maxLength={128} type="password" autoComplete="new-password" placeholder="At least 8 characters" disabled={busy} /></label>
        <fieldset className="analogy-preference" disabled={busy} aria-describedby="analogy-preference-help">
          <legend>How should your lessons explain machine learning?</legend>
          <p id="analogy-preference-help">All three options teach the same Python and machine-learning concepts. Only the explanation style changes.</p>
          <label className="analogy-choice">
            <input type="radio" name="analogy_preference" value="pure_ml" checked={analogyPreference === "pure_ml"} onChange={() => setAnalogyPreference("pure_ml")} required />
            <span><strong>Pure ML</strong><small>Explain the machine-learning concepts and Python implementation directly, without analogy framing.</small></span>
          </label>
          <label className="analogy-choice">
            <input type="radio" name="analogy_preference" value="java" checked={analogyPreference === "java"} onChange={() => setAnalogyPreference("java")} required />
            <span><strong>Java connections</strong><small>Relate ML ideas to familiar Java concepts like objects, collections, and methods.</small></span>
          </label>
          <label className="analogy-choice">
            <input type="radio" name="analogy_preference" value="everyday" checked={analogyPreference === "everyday"} onChange={() => setAnalogyPreference("everyday")} required />
            <span><strong>Everyday-life analogies</strong><small>Explain Python and machine-learning ideas through real-life situations without Java references.</small></span>
          </label>
        </fieldset>
        <label className="consent-check"><input name="consent" required type="checkbox" disabled={busy} /><span>I consent to collection of my learning interactions for research and model development. I have read the <Link href="/privacy" target="_blank">draft research notice</Link>.</span></label>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="auth-submit" disabled={busy} type="submit">{busy ? "Creating account…" : "Create anonymous account"}</button>
        <p className="auth-switch">Already have an account? <Link href="/login">Sign in</Link></p>
      </form>}
    </section>
  </main>;
}
