"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AdaptiveQuestion from "./adaptive-question";
import { questionBank, type QuestionItem, type StepId } from "@/lib/question-bank";
import { enqueueCollection, flushCollectionQueue, learningSessionId } from "@/lib/collection";
import { getAuth, validateAuth } from "@/lib/auth";

const stages = [["01", "Prepare data"], ["02", "Split data"], ["03", "TF-IDF"], ["04", "Train model"], ["05", "Predict"], ["06", "Evaluate"]];
const lessonSteps: { id: StepId; label: string }[] = [{ id: "activate", label: "Activate" }, { id: "connect", label: "Connect" }, { id: "implement", label: "Implement" }, { id: "learn", label: "Learn" }, { id: "practice", label: "Practice" }, { id: "review", label: "Review" }];
const titles = ["Start with what you know", "Map familiar ideas to the dataset", "Load the reviews in Python", "Notice the important shift", "Apply the distinction", "Connect the whole idea"];
const intros = ["Recall how Java keeps each review and its sentiment together.", "The representation changes, but the review information stays the same.", "pandas reads the entire file into one table instead of constructing reviews one at a time.", "Separate what transfers from Java from what is new in pandas and machine learning.", "Use the concept independently before moving to the final review.", "Confirm that the idea transfers beyond this exact review example."];
const javaCode = `public class Review {
  private String text;
  private String sentiment;

  public Review(String text, String sentiment) {
    this.text = text;
    this.sentiment = sentiment;
  }
}`;
const pythonCode = `import pandas as pd

df = pd.read_csv("reviews.csv")

print(df.head())
print("Rows:", len(df))`;
const learningObjectivesByStep: Record<StepId, string[]> = {
  activate: ["java_prior_knowledge", "labeled_example_representation"],
  connect: ["object_to_row_transfer", "collection_to_table_transfer"],
  implement: ["pandas_data_loading", "dataframe_representation"],
  learn: ["record_to_table_shift", "loading_vs_training"],
  practice: ["data_preparation_reasoning", "pipeline_order"],
  review: ["cross_task_transfer", "data_loading_mastery"],
};

export default function SentimentLesson() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [furthestStep, setFurthestStep] = useState(0);
  const [mastered, setMastered] = useState<Record<StepId, boolean>>({ activate: false, connect: false, implement: false, learn: false, practice: false, review: false });
  const [showAnalogy, setShowAnalogy] = useState(false);
  const [confidence, setConfidence] = useState<string | null>(null);
  const [stageComplete, setStageComplete] = useState(false);
  const [sessionId] = useState(() => typeof window === "undefined" ? "" : learningSessionId());
  const [eventCount, setEventCount] = useState(0);
  const current = lessonSteps[step];

  useEffect(() => {
    if (!getAuth()) { router.replace("/login"); return; }
    void validateAuth().then((user) => {
      if (!user) { router.replace("/login"); return; }
      void flushCollectionQueue().catch((error) => console.warn("Pending learner events will retry later.", error));
    });
  }, [router]);

  const recordBehavior = (eventType: "content_exposure" | "confidence_checkpoint" | "navigation", data: Record<string, unknown>, locationStep = current.id) => {
    setEventCount((count) => count + 1);
    void enqueueCollection({ endpoint: "/api/events", payload: {
      event_id: crypto.randomUUID(), session_id: sessionId, event_type: eventType,
      location: { task: "sentiment_classification", stage: "data_loading_and_preparation", step: locationStep },
      event_timestamp: new Date().toISOString(), data,
    }}).catch((error) => console.warn("Learner event queued for retry.", error));
  };

  const recordAttempt = (item: QuestionItem, answer: string, correct: boolean, attempt: number, responseTimeMs: number) => {
    const itemStepIndex = lessonSteps.findIndex((lessonStep) => lessonStep.id === item.step);
    const isReview = item.step === "review";
    const decision = correct ? (isReview ? "advance_stage" : "advance_step") : "remain_on_step";
    const locationAfter = correct
      ? isReview
        ? { task: "sentiment_classification", stage: "train_test_split", step: "activate" }
        : { task: "sentiment_classification", stage: "data_loading_and_preparation", step: lessonSteps[itemStepIndex + 1].id }
      : { task: "sentiment_classification", stage: "data_loading_and_preparation", step: item.step };
    const contentId = `sentiment.data_loading.${item.id}`;
    const transition = {
      transition_id: crypto.randomUUID(),
      session_id: sessionId,
      location_before: { task: "sentiment_classification", stage: "data_loading_and_preparation", step: item.step },
      instructional_action: { action_type: item.actionType, content_id: contentId },
      learner_action: { response: answer },
      observation: { correct, score: correct ? 1 : 0, attempt, response_time_ms: responseTimeMs, misconception: correct ? null : item.misconception },
      progression: { decision },
      location_after: locationAfter,
      event_timestamp: new Date().toISOString(),
      selection_policy: "predefined_sequence_v1",
    };
    setEventCount((count) => count + 1);
    void enqueueCollection({ endpoint: "/api/interactions", payload: { ...transition, content: {
      content_id: contentId,
      task: "sentiment_classification",
      stage: "data_loading_and_preparation",
      step: item.step,
      action_type: item.actionType,
      prompt: item.prompt,
      options: item.options,
      correct_answer: item.correctAnswer,
      explanation: item.explanation,
      misconception: item.misconception,
      learning_objectives: item.learningObjectives ?? learningObjectivesByStep[item.step],
    }}}).catch((error) => console.warn("Interaction queued for retry.", error));
    if (correct) setMastered((state) => ({ ...state, [item.step]: true }));
  };

  const moveTo = (index: number) => {
    if (index > furthestStep) return;
    if (index !== step) recordBehavior("navigation", { direction: index < step ? "previous" : "direct", from_step: current.id, to_step: lessonSteps[index].id });
    setStep(index);
    document.getElementById("lesson")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const continueLesson = () => {
    const next = step + 1;
    recordBehavior("navigation", { direction: "continue", from_step: current.id, to_step: lessonSteps[next].id });
    setFurthestStep(Math.max(furthestStep, next));
    setStep(next);
  };

  return <main className="site-shell">
    <header className="topbar"><Link className="brand" href="/" aria-label="LEAP home"><span>LEAP</span></Link><div className="header-context"><Link className="back-link" href="/">← All learning paths</Link><span>Sentiment classification</span></div><nav className="account-nav" aria-label="Account navigation"><span className="streak"><span className="streak-dot" /> {eventCount} learner signals</span><Link className="avatar" href="/login">YS</Link></nav></header>

    <section className="progress-section" aria-labelledby="path-title"><div className="progress-heading"><div><p className="eyebrow">Your learning path</p><h1 id="path-title">Build a sentiment classifier</h1></div><p className="path-count"><strong>1</strong> of 6 stages</p></div><ol className="stage-track">{stages.map(([number, label], index) => <li className={index === 0 ? "stage active" : "stage locked"} key={number}><span className="stage-node">{index + 1}</span><span className="stage-copy"><span>Stage {index + 1}</span><strong>{label}</strong></span></li>)}</ol></section>

    <section className="lesson-header" id="lesson"><div className="lesson-title-row"><div><p className="eyebrow blue">Stage 1 · Data loading &amp; preparation</p><h2>From Java objects to a dataset</h2><p className="lesson-intro">Master each step before LEAP unlocks the next part of the pipeline.</p></div><div className="time-estimate"><ClockIcon /> 12 min</div></div><ol className="lesson-steps">{lessonSteps.map((item, index) => <li key={item.id}><button disabled={index > furthestStep} className={index === step ? "lesson-step current" : mastered[item.id] ? "lesson-step complete" : index > furthestStep ? "lesson-step locked-step" : "lesson-step"} onClick={() => moveTo(index)}><span>{mastered[item.id] ? <CheckIcon /> : index + 1}</span>{item.label}</button></li>)}</ol></section>

    <article className="lesson-content">
      <div className="section-number">0{step + 1}</div><p className="eyebrow">{current.label}</p><h3>{titles[step]}</h3><p className="lead">{intros[step]}</p>

      {(current.id === "activate" || current.id === "connect") && <div className="comparison-grid"><section className="code-block"><div className="code-heading"><span className="language-dot java" /> Java · familiar</div><pre><code>{javaCode}</code></pre></section><section className="mapping-panel"><p className="panel-kicker">Contextual link</p><h4>Same reviews, new shape</h4><dl className="mapping-list"><div><dt>One Review object</dt><dd>One row</dd></div><div><dt>text field</dt><dd>text column</dd></div><div><dt>sentiment field</dt><dd>sentiment column</dd></div><div><dt>ArrayList&lt;Review&gt;</dt><dd>Complete dataset</dd></div></dl></section></div>}

      {(["implement", "learn", "practice"] as StepId[]).includes(current.id) && <><div className="implementation-grid"><section className="code-block dark"><div className="code-heading"><span className="language-dot python" /> Python · new</div><pre><code>{pythonCode}</code></pre></section><section className="dataset-panel"><div className="dataset-heading"><span>reviews.csv</span><span>3 rows × 2 columns</span></div><div className="table-wrap"><table><thead><tr><th>#</th><th>text</th><th>sentiment</th></tr></thead><tbody><tr><td>0</td><td>The instructor explained the concepts clearly.</td><td><span className="positive">positive</span></td></tr><tr><td>1</td><td>The assignment instructions were confusing.</td><td><span className="negative">negative</span></td></tr><tr><td>2</td><td>The laboratory activities were helpful.</td><td><span className="positive">positive</span></td></tr></tbody></table></div></section></div><div className="transfer-strip"><div><span className="transfer-index">01</span><p><strong>You already know</strong>Objects, fields, lists, and counting.</p></div><div><span className="transfer-index">02</span><p><strong>What transfers</strong>Each review stays paired with its label.</p></div><div><span className="transfer-index">03</span><p><strong>What is new</strong>One call organizes the complete table.</p></div></div></>}

      {(current.id === "connect" || current.id === "implement") && <section className={showAnalogy ? "analogy open" : "analogy"}><button onClick={() => { const opening = !showAnalogy; setShowAnalogy(opening); if (opening) recordBehavior("content_exposure", { content_id: "sentiment.data_loading.doctor_analogy", exposure: "opened" }); }}><span className="analogy-icon"><BulbIcon /></span><span><small>Optional instructional content</small>See the doctor and patient-file analogy</span><ChevronIcon open={showAnalogy} /></button>{showAnalogy && <p>Each patient file keeps symptoms connected to a diagnosis. In the shared table, one patient becomes one row and those details become columns. The information stays connected; only its shape changes.</p>}</section>}

      {current.id === "review" && <blockquote className="transfer-statement">“Java explains what is inside the dataset. pandas changes how the complete collection is built and handled.”</blockquote>}

      <AdaptiveQuestion key={current.id} items={questionBank[current.id]} onAttempt={recordAttempt} />

      {current.id === "review" && mastered.review && <fieldset className="confidence-check"><legend>How confident are you in this idea?</legend><div>{["Not yet", "Somewhat", "Confident"].map((level) => <button type="button" className={confidence === level ? "confidence selected" : "confidence"} onClick={() => { setConfidence(level); recordBehavior("confidence_checkpoint", { confidence: level }); }} key={level}>{level}</button>)}</div></fieldset>}
      {stageComplete && <p className="stage-complete-message"><CheckIcon /> Stage 1 mastered. The response path is ready as world-model evidence.</p>}

      <footer className="lesson-footer"><button className="text-button" disabled={step === 0} onClick={() => moveTo(step - 1)}>← Previous</button><span>Step {step + 1} of {lessonSteps.length}</span>{step < lessonSteps.length - 1 ? <button className="primary-button" disabled={!mastered[current.id]} onClick={continueLesson}>Continue <span>→</span></button> : <button className="primary-button" disabled={!mastered.review || !confidence || stageComplete} onClick={() => { setStageComplete(true); recordBehavior("navigation", { direction: "complete_stage", to_stage: "train_test_split" }); }}>{stageComplete ? "Completed" : "Complete stage"} <span>{stageComplete ? "✓" : "→"}</span></button>}</footer>
    </article>
  </main>;
}

function ClockIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>; }
function CheckIcon() { return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m5 10 3 3 7-7"/></svg>; }
function BulbIcon() { return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 18h6M10 22h4M8.5 14.5A6 6 0 1 1 15.5 14.5c-.8.7-1.3 1.4-1.5 2.5h-4c-.2-1.1-.7-1.8-1.5-2.5Z"/></svg>; }
function ChevronIcon({ open }: { open: boolean }) { return <svg className={open ? "chevron rotated" : "chevron"} viewBox="0 0 20 20" aria-hidden="true"><path d="m6 8 4 4 4-4"/></svg>; }
