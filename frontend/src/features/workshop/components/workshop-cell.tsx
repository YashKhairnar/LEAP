"use client";
/* eslint-disable @next/next/no-img-element -- the sandbox returns plots as data URLs. */

import { useRef, useState } from "react";
import RichText from "@/features/workshop/components/rich-text";
import { runWorkshopCell, type CellRun, type WorkshopCell as Cell, type WorkshopContent } from "@/features/workshop/lib/workshop-api";

type Props = {
  cell: Cell;
  learnerId: string;
  run: CellRun | null;
  done: boolean;
  locked: string | null;
  dataset: WorkshopContent["dataset"];
  onRan: (run: CellRun & { done: boolean }) => void;
};

function draftKey(learnerId: string, cellId: string) { return `leap.workshop.draft.v1.${learnerId}.${cellId}`; }
function readDraft(key: string): string | null { try { return window.localStorage.getItem(key); } catch { return null; } }
function writeDraft(key: string, value: string) { try { window.localStorage.setItem(key, value); } catch { /* drafts are a convenience */ } }

export default function WorkshopCell({ cell, learnerId, run, done, locked, dataset, onRan }: Props) {
  const key = draftKey(learnerId, cell.cell_id);
  const [code, setCode] = useState(() => (typeof window !== "undefined" ? readDraft(key) : null) ?? run?.code ?? `${cell.paste_placeholder}\n`);
  const [result, setResult] = useState<CellRun | null>(run);
  const [running, setRunning] = useState(false);
  const [waitingForFile, setWaitingForFile] = useState(false);
  const [message, setMessage] = useState("");
  const [copied, setCopied] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);
  const sourceHeader = `# YOUR TURN — ${cell.label}: copy this code, paste it into the empty code cell below, then click ▶ Run`;
  const hasCode = code.split("\n").some((line) => line.trim() && !line.trim().startsWith("#"));

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(cell.code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch { setMessage("Copying isn’t allowed here. Select the code and press Ctrl + C (Cmd + C on a Mac)."); }
  };

  const execute = async (uploadedFile?: { name: string; size: number }) => {
    setRunning(true); setMessage("");
    try {
      const ran = await runWorkshopCell(cell.cell_id, code, uploadedFile);
      setResult(ran);
      onRan(ran);
      if (cell.kind === "own_reviews" && ran.success && !ran.done) setMessage("Now replace each “Write … here” with your own review, then click ▶ Run again.");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "The cell didn’t run. Try again.");
    } finally { setRunning(false); }
  };

  const run_ = () => {
    writeDraft(key, code);
    if (cell.kind === "upload") { setResult(null); setMessage(""); setWaitingForFile(true); return; }
    void execute();
  };

  const chooseFile = async (file: File | undefined) => {
    if (!file) return;
    const firstLine = (await file.slice(0, 200).text()).split(/\r?\n/, 1)[0].replace(/^﻿/, "").trim();
    if (firstLine !== dataset.header || file.size !== dataset.bytes) {
      setMessage(`“${file.name}” isn’t the workshop’s ${dataset.filename}. Choose the file you downloaded in 2.1.`);
      if (fileInput.current) fileInput.current.value = "";
      return;
    }
    setWaitingForFile(false);
    await execute({ name: file.name, size: file.size });
  };

  return <section className={`ws-cell ${done ? "is-done" : ""}`} aria-label={`${cell.label}: ${cell.title}`}>
    <div className="ws-your-turn">
      <h4>YOUR TURN – {cell.label}: {cell.title}</h4>
      {cell.instructions.map((line) => <p key={line}><RichText text={line} /></p>)}
    </div>

    <div className="ws-source">
      <button type="button" className="ws-copy" onClick={() => void copy()}>{copied ? "Copied" : "Copy"}</button>
      <pre><code><span className="ws-comment">{sourceHeader}</span>{"\n"}{cell.code}</code></pre>
    </div>

    <div className="executable-cell ws-paste-cell">
      <div className="code-heading">
        <div className="code-heading-left">
          <span className="ws-count" aria-label={result ? `Run number ${result.execution_count}` : "Not run yet"}>[{result ? result.execution_count : " "}]</span>
          <span className="code-language-label">Python</span>
          {cell.kind === "upload" && <span className="code-file-label">{dataset.filename}</span>}
        </div>
        {done && <span className="ws-done-badge">✓ Done</span>}
      </div>
      <textarea
        aria-label={`Code cell for ${cell.label}: paste the code here`}
        disabled={running || Boolean(locked)}
        spellCheck={false}
        value={code}
        rows={Math.min(14, Math.max(4, code.split("\n").length + 1))}
        onChange={(event) => { setCode(event.target.value); writeDraft(key, event.target.value); }}
      />
      <div className="cell-toolbar">
        {locked ? <p className="cell-edit-status">{locked}</p> : !hasCode && <p className="cell-edit-status">Paste the code from the grey box above, then click ▶ Run.</p>}
        <button type="button" className="run-code-button" disabled={running || waitingForFile || Boolean(locked) || !hasCode} onClick={run_}>
          {running ? "Running…" : "▶ Run"}
        </button>
      </div>

      {waitingForFile && <div className="cell-output ws-upload">
        <label className="ws-file-button">
          Choose Files
          <input ref={fileInput} type="file" accept=".csv,text/csv" onChange={(event) => void chooseFile(event.target.files?.[0])} />
        </label>
        <span>no files selected</span>
        <button type="button" className="text-button" onClick={() => { setWaitingForFile(false); setMessage(""); }}>Cancel upload</button>
      </div>}

      {result && !running && <CellOutput run={result} />}
    </div>
    {message && <p className="ws-cell-message" role="status">{message}</p>}
  </section>;
}

function CellOutput({ run }: { run: CellRun }) {
  const empty = !run.stdout && !run.stderr && !run.table_preview && (run.result === null || run.result === undefined);
  return <div className={run.success ? "cell-output success" : "cell-output error"}>
    {run.stdout && <pre className="output-stdout">{run.stdout}</pre>}
    {run.stderr && <pre className="output-stderr">{run.stderr}</pre>}
    {run.table_preview
      ? <div className="cell-table-wrap"><table>
          <thead><tr><th scope="col" aria-label="Row index" />{run.table_preview.columns.map((column) => <th scope="col" key={column}>{column}</th>)}</tr></thead>
          <tbody>{run.table_preview.rows.map((row, index) => <tr key={index}><th scope="row">{index}</th>{run.table_preview!.columns.map((column) => <td key={column}>{String(row[column] ?? "")}</td>)}</tr>)}</tbody>
        </table></div>
      : run.result !== null && run.result !== undefined && <pre className="output-raw">{typeof run.result === "string" ? run.result : JSON.stringify(run.result, null, 2)}</pre>}
    {run.plots?.length > 0 && <div className="cell-plots">{run.plots.map((plot, index) => <img src={plot} alt={`Plot ${index + 1}`} key={index} />)}</div>}
    {empty && run.success && <p className="ws-no-output">Ran with no output.</p>}
  </div>;
}
