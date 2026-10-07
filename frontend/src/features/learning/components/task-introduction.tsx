"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import LearningShell from "@/features/learning/components/learning-shell";
import { getTaskProgress, type TaskProgress } from "@/lib/auth";
import { flushCollectionQueue } from "@/features/collection/lib/collection";
import type { TaskIntroduction } from "@/features/learning/lib/lesson-introductions";
import DatasetIntroduction from "@/features/learning/components/dataset-introduction";
import TaskAssessment, { AssessmentNavigation } from "@/features/assessment/components/task-assessment";

export default function TaskIntroductionPage({ task, initialView = "introduction" }: { task: TaskIntroduction; initialView?: "introduction" | "dataset" | "assessment" }) {
  const router = useRouter();
  const [progress, setProgress] = useState<TaskProgress | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    let active = true;
    void flushCollectionQueue().catch(() => undefined).then(getTaskProgress).then((records) => {
      if (active) setProgress(records.find((record) => record.task === task.taskId) ?? null);
    }).catch(() => undefined)
      .finally(() => { if (active) setLoaded(true); });
    return () => { active = false; };
  }, [task.taskId]);

  const savedStageIndex = task.stages.findIndex((stage) => stage.id === progress?.current_stage);
  const currentIndex = savedStageIndex >= 0 ? savedStageIndex : Math.min(progress?.completed_stages ?? 0, task.stages.length - 1);
  const action = !loaded ? "Checking progress…" : progress?.task_complete ? "View completed task" : progress ? "Continue learning" : "Start learning";
  const launch = !loaded ? <button className="intro-primary" type="button" disabled>Checking progress…</button> : <Link className="intro-primary" href={`/learn/${task.slug}/lesson`}>{action}<span aria-hidden="true">→</span></Link>;
  const navigator = <aside className="progress-section" aria-labelledby="path-title" id="learning-path-panel">
    <div className="progress-heading">
      <div><p className="eyebrow">Your learning path</p><h1 id="path-title">{task.title}</h1></div>
      <p className="path-count"><strong>{initialView === "assessment" ? "Quiz" : initialView === "dataset" ? "Data" : "Intro"}</strong></p>
    </div>
    <ol className="stage-track">
      <li className={`stage introduction-stage ${initialView === "introduction" ? "active selected-stage" : ""}`}>
        {initialView === "introduction" ? <div className="stage-navigation-button" aria-current="step">
          <span className="stage-node" aria-hidden="true">i</span>
          <span className="stage-copy"><span>Start here</span><strong>Task introduction</strong></span>
        </div> : <Link className="stage-navigation-button" data-stage-navigation href={`/learn/${task.slug}`} aria-label="Open task introduction"><span className="stage-node" aria-hidden="true">i</span><span className="stage-copy"><span>Start here</span><strong>Task introduction</strong></span></Link>}
      </li>
      <li className={`stage dataset-stage ${initialView === "dataset" ? "active selected-stage" : ""}`}>
        {initialView === "dataset" ? <div className="stage-navigation-button" aria-current="step">
          <span className="stage-node" aria-hidden="true">D</span>
          <span className="stage-copy"><span>Explore</span><strong>Dataset preview</strong></span>
        </div> : <Link className="stage-navigation-button" data-stage-navigation href={`/learn/${task.slug}?view=dataset`} aria-label="Open dataset preview"><span className="stage-node" aria-hidden="true">D</span><span className="stage-copy"><span>Explore</span><strong>Dataset preview</strong></span></Link>}
      </li>
      {task.stages.map((stage, index) => {
        const complete = index < (progress?.completed_stages ?? 0);
        const current = loaded && !progress?.task_complete && index === currentIndex;
        const href = complete
          ? `/learn/${task.slug}/lesson?review=${encodeURIComponent(stage.id)}`
          : current
            ? `/learn/${task.slug}/lesson`
            : null;
        const content = <><span className="stage-node">{complete ? "✓" : index + 1}</span><span className="stage-copy"><span>Stage {index + 1}</span><strong>{stage.label}</strong></span></>;
        return <li className={`stage ${complete ? "complete-stage" : current ? "next-stage" : "locked"}`} key={stage.id}>
          {href ? <Link className="stage-navigation-button" data-stage-navigation href={href} aria-label={`${complete ? "Review completed" : "Open"} stage ${index + 1}: ${stage.label}`}>{content}</Link> : <button className="stage-navigation-button" type="button" disabled>{content}</button>}
        </li>;
      })}
      <AssessmentNavigation unlocked={loaded && Boolean(progress?.task_complete)} selected={initialView === "assessment"} href={`/learn/${task.slug}?view=assessment`} />
    </ol>
  </aside>;

  return <LearningShell taskTitle={task.title} navigator={navigator}>
    <article className={`lesson-content task-introduction-content intro-theme-${task.slug}`}>
    {initialView === "assessment" ? <>
      <Link className="text-button" href={`/learn/${task.slug}/lesson`}>← Back to learning</Link>
      <TaskAssessment key={task.taskId} task={task.taskId} onReview={(stageId) => router.push(`/learn/${task.slug}/lesson?review=${encodeURIComponent(stageId)}`)} />
    </> : initialView === "dataset" ? <DatasetIntroduction task={task} /> : <div className="intro-container">
      <div className="intro-overview" aria-labelledby="intro-title">
        <header>
          <p className="intro-kicker">Task {task.number} · {task.level}</p>
          <h1 id="intro-title">{task.title}</h1>
          <p className="intro-headline">{task.headline}</p>
          <p className="intro-description">{task.description}</p>
        </header>

        <section className="intro-question" aria-labelledby="guiding-question-title">
          <p>The question you’ll answer</p>
          <h2 id="guiding-question-title">{task.question}</h2>
          <p>{task.purpose}</p>
        </section>

        <section className="intro-build" aria-labelledby="build-title">
          <div className="intro-section-heading">
            <h2 id="build-title">What you’ll build</h2>
            <p>Follow one dataset through a complete machine-learning workflow.</p>
          </div>
          <ol className="intro-workflow" aria-label="Task workflow">
            {task.pipeline.map((item, index) => <li key={item}>
              <span className="intro-workflow-number" aria-hidden="true">{index + 1}</span>
              <span>{item}</span>
              {index < task.pipeline.length - 1 && <span className="intro-workflow-arrow" aria-hidden="true">→</span>}
            </li>)}
          </ol>
        </section>

        <div className="intro-detail-grid">
          <section className="intro-outcomes" aria-labelledby="objectives-title">
            <h2 id="objectives-title">By the end, you’ll be able to</h2>
            <ul>{task.objectives.map((objective) => <li key={objective}>{objective}</li>)}</ul>
          </section>
          <section className="intro-prerequisites" aria-labelledby="prerequisites-title">
            <h2 id="prerequisites-title">Before you begin</h2>
            <ul>{task.prerequisites.map((prerequisite) => <li key={prerequisite}>{prerequisite}</li>)}</ul>
            <h3>Tools you’ll meet</h3>
            <ul className="intro-tools" aria-label="Tools used in this task">{task.tools.map((tool) => <li key={tool}>{tool}</li>)}</ul>
          </section>
        </div>

        <section className="intro-dataset-bridge" aria-labelledby="dataset-bridge-title">
          <div>
            <p>Real data, used throughout</p>
            <h2 id="dataset-bridge-title">Meet the dataset before writing code</h2>
            <span>{task.datasetSummary}</span>
          </div>
          <Link href={`/learn/${task.slug}?view=dataset`}>Preview the dataset <span aria-hidden="true">→</span></Link>
        </section>

        <section className="intro-success" aria-labelledby="success-title">
          <h2 id="success-title">What success looks like</h2>
          <p>{task.success}</p>
        </section>

        <TaskAssessment phase="pre" task={task.taskId} />

        <footer className="intro-actions">
          <span>{task.stages.length} stages + 10-question assessment · {task.duration}</span>
          {launch}
        </footer>
      </div>
    </div>}
    </article>
  </LearningShell>;
}
