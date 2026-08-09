"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getTaskProgress, logout, validateAuth, type AuthUser, type TaskProgress } from "@/lib/auth";
import { flushCollectionQueue } from "@/lib/collection";

const tasks = [
  { id: "sentiment_classification", number: "01", title: "Review Sentiment Classification", description: "Turn written reviews into positive or negative predictions while learning the complete text-classification pipeline.", level: "Foundation", time: "6 stages · 2–3 hours", href: "/learn/sentiment", stages: ["Prepare data", "Split data", "TF-IDF", "Train model", "Predict", "Evaluate"] },
  { id: "cnn", number: "02", title: "Image Classification with CNNs", description: "Build a convolutional neural network that learns to recognize categories from labeled images.", level: "Intermediate", time: "6 stages · 3–4 hours", href: "/learn/cnn", stages: ["Load images", "Split & augment", "Build CNN", "Train network", "Classify", "Evaluate"] },
  { id: "regression", number: "03", title: "House Price Regression", description: "Use property features to predict a continuous price and understand how regression differs from classification.", level: "Foundation", time: "6 stages · 2–3 hours", href: "/learn/regression", stages: ["Prepare data", "Split data", "Select features", "Train model", "Predict price", "Measure error"] },
];

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [progressRecords, setProgressRecords] = useState<TaskProgress[]>([]);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    let active = true;
    void validateAuth().then((authenticatedUser) => {
      if (!active) return;
      if (!authenticatedUser) { router.replace("/login"); return; }
      setUser(authenticatedUser);
      void flushCollectionQueue().catch(() => 0).then(() => getTaskProgress()).then((records) => { if (active) setProgressRecords(records); });
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
    <section className="task-list" aria-labelledby="paths-title"><div className="task-list-heading"><h2 id="paths-title">Learning paths</h2><span>3 available</span></div>{tasks.map((task) => { const record = progressRecords.find((item) => item.task === task.id); const percentage = record ? Math.round(record.completed_stages / record.total_stages * 100) : 0; const status = record?.task_complete ? "Completed" : percentage > 0 ? "Continue" : "View path"; return <article className="task-row" key={task.number}><div className="task-index">{task.number}</div><div className="task-main"><div className="task-meta"><span>{task.level}</span><span>{task.time}</span></div><h3>{task.title}</h3><p>{task.description}</p><ol className="mini-stages" aria-label={`${task.title} stages`}>{task.stages.map((stage, index) => <li key={stage} className={record && index < record.completed_stages ? "completed-mini-stage" : percentage > 0 && index === record?.completed_stages ? "in-progress" : ""}><span>{record && index < record.completed_stages ? "✓" : index + 1}</span>{stage}</li>)}</ol></div><div className="task-action">{record && <div className="task-progress"><span><i style={{ width: `${percentage}%` }} /></span><small>{percentage}% complete</small></div>}<Link href={task.href}>{status}<span>{record?.task_complete ? "✓" : "→"}</span></Link></div></article>; })}</section>
  </main>;
}
