"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import LearningShell from "@/features/learning/components/learning-shell";
import { API_URL, getTaskProgress, type TaskProgress } from "@/lib/auth";
import { flushCollectionQueue } from "@/features/collection/lib/collection";
import type { TaskIntroduction } from "@/features/learning/lib/lesson-introductions";
import DatasetIntroduction from "@/features/learning/components/dataset-introduction";
import TaskAssessment, { AssessmentNavigation } from "@/features/assessment/components/task-assessment";
import { nextPathAction } from "@/features/learning/lib/learning-flow";
import DigitMatrixExample from "@/features/learning/components/digit-matrix-example";

export default function TaskIntroductionPage({ task, initialView = "introduction" }: { task: TaskIntroduction; initialView?: "introduction" | "dataset" | "assessment" | "starting-assessment" }) {
  const router = useRouter();
  const [progress, setProgress] = useState<TaskProgress | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [baselineComplete, setBaselineComplete] = useState(false);
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let active = true;
    void flushCollectionQueue().catch(() => undefined).then(() => Promise.all([
      getTaskProgress(),
      fetch(`${API_URL}/api/assessments/${encodeURIComponent(task.taskId)}?phase=pre`, { credentials: "include", cache: "no-store" }).then(async (response) => {
        if (!response.ok) throw new Error("Could not check your starting assessment");
        return response.json() as Promise<{ result: unknown }>;
      }),
    ])).then(([records, baseline]) => {
      if (active) {
        setProgress(records.find((record) => record.task === task.taskId) ?? null);
        setBaselineComplete(Boolean(baseline.result));
      }
    }).catch(() => { if (active) setLoadError(true); })
      .finally(() => { if (active) setLoaded(true); });
    return () => { active = false; };
  }, [task.taskId]);

  const savedStageIndex = task.stages.findIndex((stage) => stage.id === progress?.current_stage);
  const currentIndex = savedStageIndex >= 0 ? savedStageIndex : Math.min(progress?.completed_stages ?? 0, task.stages.length - 1);
  const next = nextPathAction(task.slug, baselineComplete, progress);
  const launch = !loaded ? <button className="intro-primary" type="button" disabled>Checking progress…</button> : loadError ? <p role="alert">Could not check your progress. Please reload to try again.</p> : <Link className="intro-primary" href={next.href}>{next.label}<span aria-hidden="true">→</span></Link>;
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
      <li className={`stage ${initialView === "starting-assessment" ? "active selected-stage" : baselineComplete ? "complete-stage" : "next-stage"}`}>
        <Link className="stage-navigation-button" data-stage-navigation href={`/learn/${task.slug}?view=starting-assessment`} aria-current={initialView === "starting-assessment" ? "step" : undefined}>
          <span className="stage-node" aria-hidden="true">{baselineComplete ? "✓" : "Q"}</span>
          <span className="stage-copy"><span>Before the lesson</span><strong>Starting assessment</strong></span>
        </Link>
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
    {initialView === "starting-assessment" ? <>
      <Link className="text-button" href={`/learn/${task.slug}`}>← Back to overview</Link>
      <TaskAssessment key={`${task.taskId}.pre`} phase="pre" task={task.taskId} />
    </> : initialView === "assessment" ? <>
      <Link className="text-button" href={`/learn/${task.slug}/lesson`}>← Back to learning</Link>
      <TaskAssessment key={task.taskId} task={task.taskId} onReview={(stageId) => router.push(`/learn/${task.slug}/lesson?review=${encodeURIComponent(stageId)}`)} />
    </> : initialView === "dataset" ? <DatasetIntroduction task={task} /> : <div className="intro-container">
      <div className="intro-overview" aria-labelledby="intro-title">
        <header>
          <p className="intro-kicker">Task {task.number} · {task.level}</p>
          <h1 id="intro-title">{task.title}</h1>
          <p className="intro-description">{task.description}</p>
        </header>

        <section className="intro-problem" aria-labelledby="intro-problem-title">
          <h2 id="intro-problem-title">{task.question}</h2>
          <p>{task.purpose}</p>
        </section>

        <section className="intro-task-example" aria-labelledby="intro-example-title">
          <div className="intro-example-heading">
            <h2 id="intro-example-title">A simple example</h2>
          </div>
          <dl className="intro-example-pair">
            <div className="intro-example-step intro-example-input">
              <dt><span aria-hidden="true">1</span>What the model receives</dt>
              <dd>{task.example.input}{task.slug === "cnn" && <DigitMatrixExample />}</dd>
            </div>
            <div className="intro-example-step intro-example-output">
              <dt><span aria-hidden="true">2</span>What it predicts</dt>
              <dd>{task.example.output}</dd>
            </div>
          </dl>
          <div className="intro-example-explanation">
            <strong>What’s happening?</strong>
            <p>{task.example.explanation}</p>
          </div>
        </section>

        <section className="intro-build" aria-labelledby="build-title">
          <div className="intro-section-heading">
            <h2 id="build-title">What you’ll build</h2>
            <p>{task.success}</p>
          </div>
          <ol className="intro-workflow" aria-label="Task workflow">
            {task.pipeline.map((item, index) => <li key={item}>
              <span className="intro-workflow-number" aria-hidden="true">{index + 1}</span>
              <span>{item}</span>
              {index < task.pipeline.length - 1 && <span className="intro-workflow-arrow" aria-hidden="true">→</span>}
            </li>)}
          </ol>
        </section>

        <section className="intro-learning-goals" aria-labelledby="objectives-title">
          <h2 id="objectives-title">By the end, you’ll be able to</h2>
          <ul>{task.objectives.map((objective) => <li key={objective}>{objective}</li>)}</ul>
        </section>

        <section className="assessment-intro-callout" aria-labelledby="starting-assessment-title">
          <p className="intro-kicker">Your next step</p>
          <h2 id="starting-assessment-title">{baselineComplete ? progress?.task_complete ? "Finish with the final assessment" : progress ? "Pick up where you left off" : "Explore your data" : "Check your starting knowledge"}</h2>
          <p>{baselineComplete ? "Your starting assessment is saved. Continue with the next step below." : "Some ideas will be new. Answer as best you can; there is no pass or fail."}</p>
           {launch}
        </section>
      </div>
    </div>}
    </article>
  </LearningShell>;
}
