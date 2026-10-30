"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { getTaskProgress, logout, validateAuth, type AuthUser, type TaskProgress } from "@/lib/auth";
import { flushCollectionQueue } from "@/features/collection/lib/collection";

const tasks = [
  { id: "sentiment_classification", title: "Review sentiment", description: "Teach a model to recognize positive and negative reviews.", level: "Beginner", time: "2–3 hours", href: "/learn/sentiment" },
  { id: "regression", title: "House prices", description: "Use house details to estimate a sale price.", level: "Beginner", time: "2–3 hours", href: "/learn/regression" },
  { id: "cnn", title: "Handwritten digits", description: "Teach a neural network to recognize digits in images.", level: "Intermediate", time: "3–4 hours", href: "/learn/cnn" },
];

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [progress, setProgress] = useState<TaskProgress[]>([]);
  const [loggingOut, setLoggingOut] = useState(false);

  useEffect(() => {
    let active = true;
    void validateAuth().then((authenticatedUser) => {
      if (!active) return;
      if (!authenticatedUser) { router.replace("/login"); return; }
      setUser(authenticatedUser);
      void flushCollectionQueue().catch(() => 0).then(getTaskProgress)
        .then((records) => { if (active) setProgress(records); })
        .catch(() => undefined);
    });
    return () => { active = false; };
  }, [router]);

  const signOut = async () => {
    setLoggingOut(true);
    await logout();
    router.replace("/login");
    router.refresh();
  };

  const latest = progress.filter((record) => tasks.some((task) => task.id === record.task)).sort((a, b) => b.updated_at.localeCompare(a.updated_at))[0];
  const latestTask = latest && tasks.find((task) => task.id === latest.task);
  const resume = latest && latestTask ? { record: latest, task: latestTask, percent: latest.task_complete ? 100 : Math.round((latest.completed_stages / Math.max(1, latest.total_stages)) * 100) } : null;

  if (!user) return <main className="auth-loading" aria-live="polite">Loading your learning paths…</main>;

  return <main className="dashboard-shell simple-dashboard">
    <header className="topbar dashboard-nav">
      <Link className="brand" href="/">LEAP</Link>
      <div className="account-controls">
        <span className="account-name">Participant {user.participant_code}</span>
        <button className="logout-button" disabled={loggingOut} onClick={signOut}>{loggingOut ? "Signing out…" : "Log out"}</button>
      </div>
    </header>
    <section className="simple-dashboard-content" aria-labelledby="paths-title">
      {resume ? <>
        <header className="simple-page-heading">
          <h1 id="paths-title">Welcome back</h1>
          <p>Pick up where you left off.</p>
        </header>
        <section className="resume-card" aria-label="Continue learning">
          <div>
            <span className="resume-meta">{resume.task.title} · {resume.task.level}</span>
            <h2>{resume.record.task_complete ? "All stages done — final assessment next" : `Stage ${Math.min(resume.record.completed_stages + 1, resume.record.total_stages)} of ${resume.record.total_stages}`}</h2>
            <div className="resume-progress" role="progressbar" aria-label={`${resume.task.title} progress`} aria-valuemin={0} aria-valuemax={100} aria-valuenow={resume.percent}><span style={{ width: `${resume.percent}%` }} /></div>
          </div>
          <Link className="primary-button" href={`${resume.task.href}/lesson`}>{resume.record.task_complete ? "Open" : "Continue"} <span aria-hidden="true">→</span></Link>
        </section>
      </> : <header className="simple-page-heading">
        <h1 id="paths-title">Choose a learning path</h1>
        <p>Follow your study instructions if a path was assigned. New to machine learning? Start with review sentiment.</p>
      </header>}
      <section className="path-section" aria-labelledby="all-paths-title">
        <div className="path-section-heading">
          <h2 id="all-paths-title">{resume ? "All learning paths" : "Learning paths"}</h2>
        </div>
        <div className="simple-path-list">
          {tasks.map((task) => {
            const record = progress.find((item) => item.task === task.id);
            const status = record?.task_complete ? "Completed" : record ? "In progress" : "Not started";
            return <article className="simple-path" key={task.id}>
              <span className={`path-status ${record ? "started" : ""}`}>{status}</span>
              <h3>{task.title}</h3>
              <p>{task.description}</p>
              <p className="simple-path-meta">{task.level} · {task.time}</p>
              <Link className="path-link" href={record ? `${task.href}/lesson` : task.href}>{record?.task_complete ? "Review" : record ? "Continue" : "Start"} <span aria-hidden="true">→</span></Link>
            </article>;
          })}
        </div>
      </section>
      <details className="how-paths-work">
        <summary>How a learning path works</summary>
        <ol>
          <li><strong>Starting assessment.</strong> Answer 10 questions to record what you know before the lesson.</li>
          <li><strong>Explore the dataset.</strong> See a few examples and learn what information the data contains.</li>
          <li><strong>Learn and practise.</strong> Six stages, each with a short idea, code to run, and three practice questions.</li>
          <li><strong>Final assessment.</strong> Answer 10 questions on your own to check your understanding.</li>
        </ol>
        <p>Practice questions help you learn and don’t count toward your assessment scores.</p>
      </details>
    </section>
  </main>;
}
