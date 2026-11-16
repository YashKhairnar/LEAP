import type { ReactNode } from "react";
import RichText from "@/features/workshop/components/rich-text";
import { workshopDatasetUrl, type WorkshopBlock, type WorkshopContent, type WorkshopState } from "@/features/workshop/lib/workshop-api";

type Context = {
  content: WorkshopContent;
  state: WorkshopState;
  participantCode: string;
  renderCell: (cellId: string) => ReactNode;
  renderQuestions: () => ReactNode;
};

const BOX_TITLES: Record<string, string> = { see: "What you should see", did: "What the code did" };

export default function WorkshopBlocks({ blocks, context }: { blocks: WorkshopBlock[]; context: Context }) {
  return <>{blocks.map((block, index) => <Block block={block} context={context} key={`${block.type}.${index}`} />)}</>;
}

function Block({ block, context }: { block: WorkshopBlock; context: Context }) {
  switch (block.type) {
    case "paragraph":
      return <p className="ws-paragraph"><RichText text={block.text} /></p>;
    case "heading":
      return block.level === 2 ? <h2 className="ws-heading-2">{block.text}</h2> : <h3 className="ws-heading-3">{block.text}</h3>;
    case "quote":
      return <blockquote className="ws-quote"><p>“<RichText text={block.text} />”{block.cite && <cite> ({block.cite})</cite>}</p></blockquote>;
    case "aside":
      return <p className="ws-aside"><RichText text={block.text} /></p>;
    case "list": {
      const items = block.items.map((item) => <li key={item}><RichText text={item} /></li>);
      return block.ordered ? <ol className="ws-list">{items}</ol> : <ul className="ws-list">{items}</ul>;
    }
    case "box": {
      const title = block.title ?? BOX_TITLES[block.variant];
      return <section className={`ws-box ws-box-${block.variant}`}>
        {title && <h4>{title}</h4>}
        {block.items.map((item) => item.startsWith("pre:")
          ? <pre className="ws-box-output" key={item}>{item.slice(4)}</pre>
          : <p key={item}><RichText text={item} /></p>)}
      </section>;
    }
    case "table":
      return <div className="ws-table-wrap"><table className="ws-table">
        <thead><tr>{block.columns.map((column) => <th scope="col" key={column}>{column}</th>)}</tr></thead>
        <tbody>{block.rows.map(([word, ...rest]) => <tr key={word}><th scope="row">{word}</th>{rest.map((value) => <td key={value}>{value}</td>)}</tr>)}</tbody>
      </table></div>;
    case "cell":
      return <>{context.renderCell(block.cell_id)}</>;
    case "questions":
      return <>{context.renderQuestions()}</>;
    case "banner":
      return <header className="ws-banner">
        <h2>{block.title}</h2>
        {block.items.map((item) => <p key={item}><RichText text={item} /></p>)}
        <small>{block.note}</small>
      </header>;
    case "dataset_download":
      return <p className="ws-download">
        Can’t reach the lab website? <a href={workshopDatasetUrl} download={context.content.dataset.filename}>Download {context.content.dataset.filename} here</a>.
      </p>;
    case "own_reviews_guide":
      return <section className="ws-own-guide">
        {block.items.map((item) => <div key={item.label}>
          <p className="ws-own-label">{item.label}</p>
          <p><code className="ws-inline-code">{item.from}</code> → <code className="ws-inline-code">{item.to}</code></p>
        </div>)}
        {block.notes.map((note) => <p key={note}><RichText text={note} /></p>)}
      </section>;
    case "post_survey":
      return <section className="ws-box ws-box-plain">
        <h4>YOUR TURN – Finish: Complete the post-survey</h4>
        <p>Open the post-survey: {context.content.post_survey_url
          ? <a href={context.content.post_survey_url} target="_blank" rel="noreferrer">Post-Workshop Survey</a>
          : <strong>Post-Workshop Survey</strong>}{!context.content.post_survey_url && " (your facilitator will share the link)"}</p>
        <p>Enter your <strong>student ID</strong> (the same one you used in the pre-survey).</p>
        <p>Answer all the questions. Where it asks for your notebook link, enter your participant code: <strong className="ws-participant-code">{context.participantCode}</strong></p>
      </section>;
    case "checklist": {
      const { state } = context;
      const autoDone = { cells: state.cells_done >= state.cells_total, answers: state.answers_done >= state.answers_total };
      return <section className="ws-box ws-box-check">
        <h4>{block.title}</h4>
        <p><RichText text={block.intro} /></p>
        <ul className="ws-checklist">
          {block.items.map((item) => {
            const checked = item.auto ? autoDone[item.auto] : false;
            const detail = item.auto === "cells" ? ` (${state.cells_done} of ${state.cells_total})` : item.auto === "answers" ? ` (${state.answers_done} of ${state.answers_total})` : "";
            return <li className={checked ? "is-checked" : ""} key={item.text}>
              <span aria-hidden="true">{checked ? "☑" : "☐"}</span>
              <span><RichText text={item.text} />{detail}{item.auto && <span className="visually-hidden">{checked ? " — done" : " — not done yet"}</span>}</span>
            </li>;
          })}
        </ul>
        <p>{block.note}</p>
      </section>;
    }
  }
}
