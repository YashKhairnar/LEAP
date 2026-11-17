"""Import a version of the lab's Colab workshop notebook (.ipynb) into workshop content.

Run from backend:
    .venv/bin/python scripts/import_workshop_notebook.py analogy app/workshop/notebooks/source/analogy.ipynb

Writes app/workshop/notebooks/<version>.json. The notebook's text is copied as written. Only the
Colab-specific parts (saving a copy in Drive, the Research ID form, how to run a cell, the upload
widget, the Drive-saving finish step) are replaced with the same adapted blocks the original
workshop uses, so every version behaves the same on this platform. Cell code must match the
original workshop's code exactly; the importer stops if it doesn't.
"""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.workshop.content import (  # noqa: E402
    ASIDE, BOX, CELL, DEFAULT_INSTRUCTIONS, H, IMPORTED_VERSIONS, LIST, NOTEBOOK_DIR, P, PRIMARY, QUESTIONS_BLOCK, TABLE,
)

BOX_COLORS = {
    "#8430ce": "analogy",  # purple: analogy / Java connection / looking back
    "#1a73e8": "see",      # blue: what you should see, info boxes
    "#0d652d": "yourturn", # green: YOUR TURN header for a cell
    "#188038": "plain",    # green: how to run each cell
    "#5f6368": "plain",    # grey: worked examples, lists
    "#e8710a": "check",    # orange: check your understanding, checklist
    "#d93025": "warning",  # red
}
INLINE = {"b": "**", "strong": "**", "i": "*", "em": "*", "code": "`"}


class Node:
    def __init__(self, tag: str, attrs: dict[str, str] | None = None):
        self.tag, self.attrs, self.children = tag, attrs or {}, []

    def find_all(self, tag: str) -> list["Node"]:
        found = []
        for child in self.children:
            if isinstance(child, Node):
                if child.tag == tag:
                    found.append(child)
                found.extend(child.find_all(tag))
        return found


class TreeBuilder(HTMLParser):
    VOID = {"br", "hr", "img"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("root")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {key: value or "" for key, value in attrs})
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse(html: str) -> Node:
    builder = TreeBuilder()
    builder.feed(html)
    return builder.root


def inline(node: Node | str) -> str:
    """HTML inline content → the workshop's inline markup."""
    if isinstance(node, str):
        return re.sub(r"[ \t\r\n]+", " ", node)
    if node.tag == "br":
        return "\n"
    inner = "".join(inline(child) for child in node.children)
    if node.tag == "a":
        return f"[{inner.strip()}]({node.attrs.get('href', '')})"
    marker = INLINE.get(node.tag)
    if marker and inner.strip():
        # Keep surrounding spaces outside the marker so **bold** stays valid markup.
        lead = inner[: len(inner) - len(inner.lstrip(" "))]
        trail = inner[len(inner.rstrip(" ")):]
        return f"{lead}{marker}{inner.strip(' ')}{marker}{trail}"
    return inner


def text_of(node: Node) -> str:
    return inline(node).strip(" ").replace(" \n", "\n")


def is_blank(text: str) -> bool:
    return not text.replace("\xa0", "").strip()


def is_title(node: Node, text: str) -> bool:
    """A row that is entirely bold, like "What you should see"."""
    stripped = text.strip()
    return stripped.startswith("**") and stripped.endswith("**") and stripped.count("**") == 2


def table_items(table: Node) -> list[dict[str, Any]]:
    """A table is either a run of coloured boxes (a narrow colour bar per box) or a data table."""
    rows = [row for row in table.find_all("tr")]
    first_cells = rows[0].find_all("td") if rows else []
    if not first_cells or first_cells[0].attrs.get("width") != "8":
        header = [text_of(cell).replace("**", "") for cell in first_cells]
        body = [[text_of(cell).replace("**", "") for cell in row.find_all("td")] for row in rows[1:]]
        return [{"kind": "table", "columns": header, "rows": body}]
    boxes: list[dict[str, Any]] = []
    for row in rows:
        cells = row.find_all("td")
        if cells and cells[0].attrs.get("width") == "8":
            boxes.append({"kind": "box", "variant": BOX_COLORS.get(cells[0].attrs.get("bgcolor", "").lower(), "plain"),
                          "title": None, "items": []})
            cells = cells[1:]
        if not cells or not boxes:
            continue
        box, cell = boxes[-1], cells[0]
        code_only = cell.attrs.get("bgcolor", "").lower() == "#ffffff" and cell.find_all("code") and all(
            isinstance(child, Node) and child.tag == "code" or (isinstance(child, str) and not child.strip())
            for child in cell.children)
        if code_only:
            line = "".join("".join(inline(grand) for grand in code.children) for code in cell.find_all("code"))
            if box["items"] and box["items"][-1].startswith("code:"):
                box["items"][-1] += "\n" + line
            else:
                box["items"].append("code:" + line)
            continue
        text = text_of(cell)
        if is_blank(text):
            continue
        if box["title"] is None and not box["items"] and is_title(cell, text):
            box["title"] = text.strip().strip("*")
        else:
            box["items"].append(text)
    for box in boxes:  # trim blank lines Colab adds to the end of code samples
        box["items"] = [item.rstrip("\n") if item.startswith("code:") else item for item in box["items"]]
    return boxes


def markdown_items(source: str) -> list[dict[str, Any]]:
    """One notebook markdown cell → a list of raw items in reading order."""
    items: list[dict[str, Any]] = []
    for index, part in enumerate(re.split(r"```(?:python)?\n(.*?)```", source, flags=re.S)):
        if index % 2 == 1:
            items.append({"kind": "fence", "code": part.rstrip("\n")})
            continue
        for chunk in re.split(r"\n\s*---\s*\n", part):
            root = parse(chunk)
            for node in root.children:
                if isinstance(node, str):
                    if node.strip():
                        items.append({"kind": "p", "text": inline(node).strip()})
                    continue
                if node.tag in {"h1", "h2", "h3", "h4"}:
                    items.append({"kind": node.tag, "text": text_of(node).replace("**", "")})
                elif node.tag == "p":
                    text = text_of(node)
                    if not is_blank(text):
                        items.append({"kind": "p", "text": text})
                elif node.tag == "table":
                    items.extend(table_items(node))
                elif node.tag in {"ul", "ol"}:
                    items.append({"kind": "list", "ordered": node.tag == "ol",
                                  "items": [text_of(li) for li in node.find_all("li")]})
                elif not is_blank(text_of(node)):
                    items.append({"kind": "p", "text": text_of(node)})
    return items


# Notebook cells left out on purpose, by version and cell index (0-based), with the reason.
SKIPPED_CELLS = {
    "analogy": {
        59: "Step 5: an earlier copy of cell 62 (Cell 13's 'What you should see', 'Looking back' and the q5 "
            "questions) placed after Cell 12. Cell 62 is kept.",
    },
}


def notebook_items(notebook: dict[str, Any], version_id: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for index, cell in enumerate(notebook["cells"]):
        if index in SKIPPED_CELLS.get(version_id, {}):
            print(f"Skipping notebook cell {index}: {SKIPPED_CELLS[version_id][index]}")
            continue
        source = "".join(cell["source"])
        if cell["cell_type"] == "markdown":
            items.extend(markdown_items(source))
        else:
            items.append({"kind": "code", "code": source})
    return items


def notebook_code(code: str) -> str:
    """The code learners copy, without the notebook's "YOUR TURN" / "Paste the code here" header comments."""
    lines = [line.rstrip() for line in code.strip("\n").splitlines()
             if not line.lstrip().startswith("# YOUR TURN") and not line.lstrip().startswith("# ✍️")]
    return "\n".join(lines).strip("\n")


def without_comments(code: str) -> str:
    """Code for comparison: trailing comments and blank lines removed (comment wording may differ)."""
    lines = [re.sub(r"\s+#.*$", "", line).rstrip() for line in code.splitlines() if not line.lstrip().startswith("#")]
    return "\n".join(line for line in lines if line)


def box_block(item: dict[str, Any]) -> dict[str, Any]:
    return BOX(item["variant"], item["title"], *item["items"])


def find_primary_block(stage_id: str, predicate) -> dict[str, Any]:
    return next(block for block in PRIMARY.stage(stage_id).blocks if predicate(block))


def convert(version_id: str, notebook: dict[str, Any]) -> dict[str, Any]:
    items = notebook_items(notebook, version_id)
    primary_cells = list(PRIMARY.cells)
    stages: list[dict[str, Any]] = []
    stage: dict[str, Any] | None = None
    pending_turn: dict[str, Any] | None = None
    pending_code: str | None = None
    cell_index = 0
    skip_next_box = False

    def add(block: dict[str, Any]) -> None:
        stage["blocks"].append(block)

    for position, item in enumerate(items):
        kind = item["kind"]
        if kind == "h1":
            title = item["text"]
            primary_stage = None
            if title.startswith("Before You Start"):
                primary_stage = PRIMARY.stages[0]
                title = "Before You Start"
            elif title.startswith("Step "):
                primary_stage = PRIMARY.stages[int(title.split()[1].rstrip(":"))]
            elif title.startswith("You Did It"):
                primary_stage = PRIMARY.stages[-1]
            if primary_stage is not None:
                stage = {"stage_id": primary_stage.stage_id, "nav_label": primary_stage.nav_label,
                         "short_label": primary_stage.short_label, "title": title,
                         "blocks": [], "cells": [], "questions": []}
                stages.append(stage)
                if primary_stage.stage_id == "start":
                    add(find_primary_block("start", lambda block: block["type"] == "banner"))
                continue
            add(H(item["text"], 2))
            continue
        if stage is None:
            continue  # the title banner before the first heading; the original's banner is used instead
        if stage["stage_id"] == "finish":
            continue  # the finish page is the same adapted page in every version
        if skip_next_box and kind == "box":
            skip_next_box = False
            continue
        if kind == "h3":
            heading = item["text"]
            if heading.startswith("Set up your notebook"):
                # Adapted: no Google Drive copy and no Research ID form; work saves under the research ID.
                add(H("Your work is saved as you go"))
                add(find_primary_block("start", lambda block: block["type"] == "box" and "saved under your research ID" in " ".join(block["items"])))
                skip_next_box = True
                continue
            if heading.startswith("How to run each cell"):
                add(H("How to run each cell"))
                add(find_primary_block("start", lambda block: block["type"] == "box" and "do these three things" in " ".join(block["items"])))
                skip_next_box = True
                continue
            add(H(heading))
            continue
        if kind == "p":
            add(P(item["text"]))
            if "csed-research-lab.org" in item["text"]:
                add({"type": "dataset_download"})
            continue
        if kind == "list":
            add(LIST(*item["items"], ordered=item["ordered"]))
            continue
        if kind == "table":
            add(TABLE(item["columns"], item["rows"]))
            continue
        if kind == "fence":
            pending_code = item["code"]
            continue
        if kind == "code":
            code = item["code"]
            if "#@title" in code or "@param" in code:
                continue  # Colab form cells: Research ID and "Your answers" boxes
            if "YOUR TURN – Practice cell" in code:
                pending_code = code
                continue
            if pending_code is None:
                continue  # an empty cell Colab adds after the practice cell
            expected = primary_cells[cell_index]
            source_code = notebook_code(pending_code)
            if without_comments(source_code) != without_comments(expected.code):
                raise SystemExit(f"{version_id}: code for {expected.label} ({expected.cell_id}) differs from the original workshop:\n"
                                 f"{source_code}\n---\n{expected.code}")
            label = expected.label
            title = expected.title
            header = re.match(r"#\s*✍?️?\s*YOUR TURN – (Cell \d+)", pending_code.lstrip())
            if header:
                label = header.group(1)
            instructions = list(DEFAULT_INSTRUCTIONS)
            if pending_turn is not None:
                match = re.match(r"YOUR TURN – (.+?): (.+)", pending_turn["title"] or "")
                if match:
                    label, title = match.group(1), match.group(2)
                rows = [row for row in pending_turn["items"] if not row.startswith("code:")]
                if rows:
                    instructions = [row.replace("Click ▶ to run it", "Click ▶ Run to run it") for row in rows]
            stage["cells"].append({"cell_id": expected.cell_id, "stage_id": stage["stage_id"], "label": label, "title": title,
                                   "code": source_code, "kind": expected.kind, "instructions": instructions})
            add(CELL(expected.cell_id))
            cell_index += 1
            pending_turn = None
            pending_code = None
            continue
        if kind == "box":
            title = item["title"] or ""
            if item["variant"] == "yourturn":
                pending_turn = item
                continue
            if title.startswith("Three rules that save you trouble"):
                add(find_primary_block("start", lambda block: block.get("title") == "Three rules that save you trouble"))
                continue
            if title.startswith("Check your understanding"):
                for row in item["items"]:
                    match = re.match(r"\*\*(q\d_\d):\*\*\s*(.+)", row)
                    if match:
                        stage["questions"].append({"question_id": match.group(1), "stage_id": stage["stage_id"], "prompt": match.group(2).strip()})
                    elif stage["questions"] and not row.startswith("*Type your answers"):
                        # A question that continues on the next line of the box.
                        stage["questions"][-1]["prompt"] += " " + row.strip()
                add(QUESTIONS_BLOCK)
                continue
            block = box_block(item)
            if title.startswith("Got an error?"):
                # Adapted: the platform's code-safety check blocks these characters.
                block["items"].append("Also leave out the characters `/` and `\\` in your reviews.")
            add(block)
            continue
    finish = PRIMARY.stages[-1]
    stages[-1]["blocks"] = list(finish.blocks)
    if cell_index != len(primary_cells):
        raise SystemExit(f"{version_id}: found {cell_index} cells, expected {len(primary_cells)}")
    return {"version_id": version_id, "source": "Colab notebook export (.ipynb)", "stages": stages}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", choices=sorted(IMPORTED_VERSIONS))
    parser.add_argument("notebook", type=Path)
    args = parser.parse_args()
    notebook = json.loads(args.notebook.read_text(encoding="utf-8"))
    content = convert(args.version, notebook)
    output = NOTEBOOK_DIR / f"{args.version}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(content, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    cells = sum(len(stage["cells"]) for stage in content["stages"])
    questions = sum(len(stage["questions"]) for stage in content["stages"])
    print(f"Wrote {output}: {len(content['stages'])} stages, {cells} cells, {questions} questions")


if __name__ == "__main__":
    main()
