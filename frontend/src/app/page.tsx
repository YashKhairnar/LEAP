"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { logout, validateAuth, type AuthUser } from "@/lib/auth";

const tasks = [
  { number: "01", title: "Review Sentiment Classification", description: "Turn written reviews into positive or negative predictions while learning the complete text-classification pipeline.", level: "Foundation", time: "6 stages · 2–3 hours", href: "/learn/sentiment", status: "Continue", progress: 17, stages: ["Prepare data", "Split data", "TF-IDF", "Train model", "Predict", "Evaluate"] },
  { number: "02", title: "Image Classification with CNNs", description: "Build a convolutional neural network that learns to recognize categories from labeled images.", level: "Intermediate", time: "6 stages · 3–4 hours", href: "/learn/cnn", status: "View path", progress: 0, stages: ["Load images", "Split & augment", "Build CNN", "Train network", "Classify", "Evaluate"] },
  { number: "03", title: "House Price Regression", description: "Use property features to predict a continuous price and understand how regression differs from classification.", level: "Foundation", time: "6 stages · 2–3 hours", href: "/learn/regression", status: "View path", progress: 0, stages: ["Prepare data", "Split data", "Select features", "Train model", "Predict price", "Measure error"] },
];

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    let active = true;
    void validateAuth().then((authenticatedUser) => {
      if (!active) return;
      if (!authenticatedUser) { router.replace("/login"); return; }
      setUser(authenticatedUser);
    });
    return () => { active = false; };
  }, [router]);

  const signOut = async () => {
    setLoggingOut(true);
    await logout();
    router.replace("/login");
    router.refresh();
  };

  if (!user) return <main className="auth-loading" aria-live="polite">Checking your LEAP session…</main>;
  const initials = user.name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase();

  return <main className="dashboard-shell">
    <header className="topbar dashboard-nav" style={{display: "flex", justifyContent: "space-between"}}>
      <Link className="brand" href="/"><span>LEAP</span></Link>
      <div className="account-controls"><span className="account-name">{user.name}</span><span className="avatar" aria-hidden="true">{initials}</span><button className="logout-button" disabled={loggingOut} onClick={signOut}>{loggingOut ? "Signing out…" : "Log out"}</button></div>
    </header>
    <section className="dashboard-hero"><h1>Choose a problem.<br />Learn the pipeline.</h1><p>Each problem is a guided path from familiar Java concepts to a complete machine-learning workflow.</p></section>
    <section className="task-list" aria-labelledby="paths-title"><div className="task-list-heading"><h2 id="paths-title">Learning paths</h2><span>3 available</span></div>{tasks.map((task) => <article className="task-row" key={task.number}><div className="task-index">{task.number}</div><div className="task-main"><div className="task-meta"><span>{task.level}</span><span>{task.time}</span></div><h3>{task.title}</h3><p>{task.description}</p><ol className="mini-stages" aria-label={`${task.title} stages`}>{task.stages.map((stage, index) => <li key={stage} className={task.progress > 0 && index === 0 ? "in-progress" : ""}><span>{index + 1}</span>{stage}</li>)}</ol></div><div className="task-action">{task.progress > 0 && <div className="task-progress"><span><i style={{ width: `${task.progress}%` }} /></span><small>{task.progress}% complete</small></div>}<Link href={task.href}>{task.status}<span>→</span></Link></div></article>)}</section>
  </main>;
}
