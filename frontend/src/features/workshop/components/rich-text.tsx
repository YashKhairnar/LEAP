import type { ReactNode } from "react";

// Inline markup used by the workshop content: `code`, **bold**, *italic* and [label](https://url).
const TOKEN = /`([^`]+)`|\*\*(.+?)\*\*|\*(.+?)\*|\[([^\]]+)\]\((https:\/\/[^)\s]+)\)/g;

export default function RichText({ text }: { text: string }) {
  return <>{renderInline(text)}</>;
}

function renderInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(TOKEN)) {
    const index = match.index ?? 0;
    if (index > last) nodes.push(text.slice(last, index));
    const [, code, bold, italic, label, href] = match;
    const key = `${index}.${match[0]}`;
    if (code !== undefined) nodes.push(<code className="ws-inline-code" key={key}>{code}</code>);
    else if (bold !== undefined) nodes.push(<strong key={key}>{renderInline(bold)}</strong>);
    else if (italic !== undefined) nodes.push(<em key={key}>{renderInline(italic)}</em>);
    else nodes.push(<a href={href} target="_blank" rel="noreferrer" key={key}>{label}</a>);
    last = index + match[0].length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}
