"use client";

type Outcome = "learned" | "kept" | "slipped" | "still_learning" | "no_baseline";
export type AssessmentReport = {
  before_score: number | null;
  before_unsure: number | null;
  after_score: number;
  total: number;
  outcomes: Record<Exclude<Outcome, "no_baseline">, number>;
  stages: { stage: string; title: string; total: number; after: number; before: number | null }[];
  concepts: { stage: string; concept: string; after: boolean; before: boolean | "unsure" | null; outcome: Outcome }[];
};

const OUTCOMES: { key: Exclude<Outcome, "no_baseline">; label: string; detail: string }[] = [
  { key: "learned", label: "Learned", detail: "Missed or unsure before, right now" },
  { key: "kept", label: "Already knew", detail: "Right before and after" },
  { key: "slipped", label: "Slipped", detail: "Right before, missed now" },
  { key: "still_learning", label: "Still learning", detail: "Not right yet" },
];

function Dots({ correct, total, tone }: { correct: number; total: number; tone: "before" | "after" }) {
  return <span className={`report-dots is-${tone}`} aria-hidden="true">
    {Array.from({ length: total }, (_, index) => <i key={index} className={index < correct ? "is-on" : ""} />)}
  </span>;
}

// Shown once the final assessment is submitted: how each concept changed since the
// starting assessment, and which stages are worth another look.
export default function AssessmentReportView({ report, onReview }: { report: AssessmentReport; onReview?: (stage: string) => void }) {
  const hasBaseline = report.before_score !== null;
  const change = hasBaseline ? report.after_score - (report.before_score ?? 0) : 0;
  const percent = (score: number) => Math.round((score / report.total) * 100);

  return <section className="assessment-report" aria-labelledby="assessment-report-title">
    <header className="report-header">
      <p className="eyebrow blue">Analysis report</p>
      <h3 id="assessment-report-title">{hasBaseline ? "How your understanding changed" : "Your results by stage"}</h3>
    </header>

    <div className="report-scores">
      {hasBaseline && <div className="report-score is-before">
        <span>Before the lesson</span>
        <strong>{report.before_score}<small> / {report.total}</small></strong>
        <em>{percent(report.before_score ?? 0)}% correct</em>
      </div>}
      {hasBaseline && <span className="report-arrow" aria-hidden="true">→</span>}
      <div className="report-score is-after">
        <span>After the lesson</span>
        <strong>{report.after_score}<small> / {report.total}</small></strong>
        <em>{percent(report.after_score)}% correct</em>
      </div>
      {hasBaseline && <div className={`report-change ${change > 0 ? "is-up" : change < 0 ? "is-down" : ""}`}>
        <strong>{change > 0 ? "+" : ""}{change}</strong>
        <span>{Math.abs(change) === 1 ? "point" : "points"}</span>
      </div>}
    </div>
    {hasBaseline && report.before_unsure ? <p className="report-note">At the start you chose “I’m not sure yet” on {report.before_unsure} of {report.total} questions.</p> : null}
    {!hasBaseline && <p className="report-note">No starting assessment was saved for this task, so there is nothing to compare against.</p>}

    {hasBaseline && <ul className="report-outcomes">
      {OUTCOMES.map((outcome) => {
        const concepts = report.concepts.filter((item) => item.outcome === outcome.key);
        return <li key={outcome.key} className={`is-${outcome.key}`}>
          <div><strong>{report.outcomes[outcome.key]}</strong><span>{outcome.label}</span></div>
          <p>{outcome.detail}</p>
          {concepts.length > 0 && <ul>{concepts.map((item) => <li key={`${item.stage}-${item.concept}`}>{item.concept}</li>)}</ul>}
        </li>;
      })}
    </ul>}

    <div className="report-stages">
      <h4>By lesson stage</h4>
      <table>
        <thead><tr>
          <th scope="col">Stage</th>
          {hasBaseline && <th scope="col">Before</th>}
          <th scope="col">After</th>
          <th scope="col"><span className="visually-hidden">Next step</span></th>
        </tr></thead>
        <tbody>{report.stages.map((stage, index) => {
          const solid = stage.after === stage.total;
          return <tr key={stage.stage}>
            <th scope="row"><span className="report-stage-number">{index + 1}</span>{stage.title}</th>
            {hasBaseline && <td><Dots correct={stage.before ?? 0} total={stage.total} tone="before" /><span className="report-count">{stage.before}/{stage.total}</span></td>}
            <td><Dots correct={stage.after} total={stage.total} tone="after" /><span className="report-count">{stage.after}/{stage.total}</span></td>
            <td>{solid
              ? <span className="report-status is-solid">Solid</span>
              : <button className="text-button report-review" type="button" onClick={() => onReview?.(stage.stage)}>Review stage →</button>}</td>
          </tr>;
        })}</tbody>
      </table>
    </div>
  </section>;
}
