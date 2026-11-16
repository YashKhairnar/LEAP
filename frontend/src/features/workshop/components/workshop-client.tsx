"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import LearningShell from "@/features/learning/components/learning-shell";
import WorkshopBlocks from "@/features/workshop/components/workshop-blocks";
import WorkshopCell from "@/features/workshop/components/workshop-cell";
import WorkshopQuestions, { type QuestionsHandle } from "@/features/workshop/components/workshop-questions";
import {
  WorkshopError, completeWorkshopStage, getWorkshopContent, getWorkshopState, stageUnlocked,
  type CellRun, type WorkshopContent, type WorkshopStage, type WorkshopState,
} from "@/features/workshop/lib/workshop-api";
import { getAuth } from "@/lib/auth";

function withCounts(content: WorkshopContent, state: WorkshopState): WorkshopState {
  const cells = content.stages.flatMap((stage) => stage.cells).filter((cell) => cell.stage_id !== "start");
  const questions = content.stages.flatMap((stage) => stage.questions);
  return {
    ...state,
    cells_done: cells.filter((cell) => state.cells[cell.cell_id]?.done).length,
    answers_done: questions.filter((question) => state.answers[question.question_id]?.answer.trim()).length,
  };
}

export default function WorkshopClient() {
  const learner = getAuth()?.user;
  const [content, setContent] = useState<WorkshopContent | null>(null);
  const [state, setState] = useState<WorkshopState | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [loadError, setLoadError] = useState("");
  const [completing, setCompleting] = useState(false);
  const [completionError, setCompletionError] = useState<{ message: string; missing: string[] } | null>(null);
  const questionsRef = useRef<QuestionsHandle>(null);

  const load = useCallback(() => {
    void Promise.all([getWorkshopContent(), getWorkshopState()])
      .then(([loadedContent, loadedState]) => {
        setContent(loadedContent);
        setState(withCounts(loadedContent, loadedState));
        setSelected((current) => current ?? loadedState.current_stage);
      })
      .catch((reason) => setLoadError(reason instanceof Error ? reason.message : "The workshop didn’t load."));
  }, []);
  useEffect(() => { load(); }, [load]);

  const openStage = (stageId: string) => {
    setSelected(stageId);
    setCompletionError(null);
    requestAnimationFrame(() => document.getElementById("lesson")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  };

  if (!content || !state || !selected) {
    return <LearningShell taskTitle="ML Workshop" navigator={<aside className="progress-section" id="learning-path-panel" />}>
      <article className="lesson-content" id="lesson">
        {loadError
          ? <div className="card-error-state"><p className="generated-tutor-error">The workshop didn’t load. {loadError}</p><button type="button" className="alternate-button" onClick={() => { setLoadError(""); load(); }}>Try again</button></div>
          : <p className="question-loading">Loading the workshop…</p>}
      </article>
    </LearningShell>;
  }

  const stages = content.stages;
  const learningStages = stages.slice(0, -1);
  const stageIndex = Math.max(0, stages.findIndex((stage) => stage.stage_id === selected));
  const stage = stages[stageIndex];
  const nextStage: WorkshopStage | undefined = stages[stageIndex + 1];
  const isFinish = stageIndex === stages.length - 1;
  const completedCount = learningStages.filter((item) => state.completed_stages.includes(item.stage_id)).length;
  const progress = (completedCount / learningStages.length) * 100;

  const recordRun = (run: CellRun & { done: boolean }) => { setCompletionError(null); setState((current) => current && withCounts(content, {
    ...current,
    // Mirrors the server: a cell stays done after a failed rerun; a successful run decides it.
    cells: { ...current.cells, [run.cell_id]: { done: run.success ? run.done : Boolean(current.cells[run.cell_id]?.done), latest: run } },
  })); };
  const recordAnswer = (questionId: string, answer: string, savedAt: string) => { setCompletionError(null); setState((current) => current && withCounts(content, {
    ...current, answers: { ...current.answers, [questionId]: { answer, saved_at: savedAt } },
  })); };

  const complete = async () => {
    setCompleting(true); setCompletionError(null);
    try {
      await questionsRef.current?.saveAll();
      const updated = await completeWorkshopStage(stage.stage_id);
      setState(withCounts(content, updated));
      if (nextStage) openStage(nextStage.stage_id);
    } catch (reason) {
      if (reason instanceof WorkshopError) setCompletionError({ message: reason.message, missing: reason.missing });
      else setCompletionError({ message: "We couldn’t save your progress. Check your connection and try again.", missing: [] });
    } finally { setCompleting(false); }
  };

  const renderCell = (cellId: string) => {
    const cell = stage.cells.find((item) => item.cell_id === cellId);
    if (!cell) return null;
    const position = stage.cells.indexOf(cell);
    const blocker = stage.cells.slice(0, position).find((item) => !state.cells[item.cell_id]?.done);
    return <WorkshopCell
      key={`${stage.stage_id}.${cellId}`}
      cell={cell}
      learnerId={learner?.user_id ?? "anonymous"}
      run={state.cells[cellId]?.latest ?? null}
      done={Boolean(state.cells[cellId]?.done)}
      locked={blocker ? `Run ${blocker.label} (${blocker.title}) above first.` : null}
      dataset={content.dataset}
      onRan={recordRun}
    />;
  };
  const renderQuestions = () => <WorkshopQuestions
    key={stage.stage_id}
    ref={questionsRef}
    stepLabel={stage.nav_label}
    questions={stage.questions}
    saved={state.answers}
    onSaved={recordAnswer}
  />;

  const navigator = <aside className="progress-section" aria-labelledby="path-title" id="learning-path-panel">
    <div className="progress-heading">
      <div><p className="eyebrow">Your workshop</p><h1 id="path-title">Classify restaurant reviews</h1></div>
      <p className="path-count">{completedCount} of {learningStages.length} parts done</p>
    </div>
    <ol className="stage-track">
      {stages.map((item, index) => {
        const complete = state.completed_stages.includes(item.stage_id);
        const unlocked = stageUnlocked(state, item.stage_id);
        const isSelected = item.stage_id === stage.stage_id;
        const node = complete ? "✓" : !unlocked ? "🔒" : index === 0 ? "i" : index === stages.length - 1 ? "★" : index;
        return <li className={`stage ${complete ? "complete-stage" : unlocked ? "active" : "locked"} ${isSelected ? "selected-stage" : ""}`} key={item.stage_id}>
          <button type="button" className="stage-navigation-button" data-stage-navigation disabled={!unlocked} aria-current={isSelected ? "step" : undefined}
            aria-label={`${complete ? "Review completed" : unlocked ? "Open" : "Locked"} ${item.nav_label}: ${item.short_label}`} onClick={() => openStage(item.stage_id)}>
            <span className="stage-node" aria-hidden="true">{node}</span>
            <span className="stage-copy"><span>{!unlocked ? "Locked · " : ""}{item.nav_label}</span><strong>{item.short_label}</strong></span>
          </button>
        </li>;
      })}
    </ol>
  </aside>;

  const continueLabel = stage.stage_id === "start" ? "Start Step 1" : nextStage && isFinishStage(nextStage, stages) ? "Finish the workshop" : `Next: ${nextStage?.nav_label ?? ""}`;

  return <LearningShell taskTitle="ML Workshop" location={`${stage.nav_label} · ${stage.short_label}`} progress={progress} navigator={navigator}>
    <article className="lesson-content ws-lesson" id="lesson" tabIndex={-1}>
      <h1 className="lesson-part-title ws-stage-title">{stage.title}</h1>
      <WorkshopBlocks blocks={stage.blocks} context={{ content, state, researchId: state.research_id ?? learner?.participant_code ?? "", renderCell, renderQuestions }} />

      {!isFinish && <footer className="ws-stage-footer">
        {completionError && <div className="ws-completion-error" role="alert">
          <strong>{completionError.message}</strong>
          {completionError.missing.length > 0 && <ul>{completionError.missing.map((item) => <li key={item}>{item}</li>)}</ul>}
        </div>}
        <div className="lesson-part-nav">
          {stageIndex > 0 ? <button type="button" className="text-button" onClick={() => openStage(stages[stageIndex - 1].stage_id)}>← {stages[stageIndex - 1].nav_label}</button> : <span />}
          <button type="button" className="primary-button" disabled={completing} onClick={() => void complete()}>
            {completing ? "Saving…" : continueLabel} <span aria-hidden="true">→</span>
          </button>
        </div>
      </footer>}
      {isFinish && <div className="lesson-part-nav"><span /><Link className="primary-button" href="/">Back to home</Link></div>}
    </article>
  </LearningShell>;
}

function isFinishStage(stage: WorkshopStage, stages: WorkshopStage[]) {
  return stage.stage_id === stages[stages.length - 1].stage_id;
}
