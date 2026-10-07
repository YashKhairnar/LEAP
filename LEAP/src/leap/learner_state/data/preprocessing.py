"""Cleaning operations for source-code submissions."""

from __future__ import annotations

import io
import re
import tokenize

import pandas as pd


def remove_comments(source: str) -> str:
    """Remove Python comments while preserving hashes inside string literals."""
    try:
        tokens = tokenize.generate_tokens(io.StringIO(source).readline)
        kept = [token for token in tokens if token.type != tokenize.COMMENT]
        return tokenize.untokenize(kept)
    except (IndentationError, tokenize.TokenError):
        # Student submissions are often incomplete or syntactically invalid.
        return _remove_comments_from_incomplete_code(source)


def _remove_comments_from_incomplete_code(source: str) -> str:
    cleaned: list[str] = []
    for line in source.split("\n"):
        in_single = False
        in_double = False
        escaped = False
        cut_at: int | None = None
        for index, character in enumerate(line):
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == "'" and not in_double:
                in_single = not in_single
            elif character == '"' and not in_single:
                in_double = not in_double
            elif character == "#" and not in_single and not in_double:
                cut_at = index
                break
        cleaned.append(line if cut_at is None else line[:cut_at])
    return "\n".join(cleaned)


def normalize_code(code: object) -> str:
    """Normalize line endings, indentation, comments, and blank lines."""
    normalized = str(code).replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.replace("\t", "    ")
    normalized = re.sub(r"^#!.*\n?", "", normalized)
    normalized = remove_comments(normalized)
    normalized = "\n".join(line.rstrip() for line in normalized.splitlines())
    normalized = re.sub(r"\n{2,}", "\n", normalized)
    return normalized.strip()


def prepare_dcu_submissions(frame: pd.DataFrame) -> pd.DataFrame:
    """Clean DCU submissions and return rows ready for trajectory grouping."""
    required = {"user", "module", "task", "date", "upload", "extension", "correct"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required DCU columns: {', '.join(sorted(missing))}")

    result = frame.drop(columns=["academic_year_0", "academic_year_1", "ip"], errors="ignore")
    result = result.dropna(subset=list(required)).rename(columns={"upload": "code"}).copy()
    result = result[result["extension"].eq("py")].copy()
    result["normalized_code"] = result["code"].map(normalize_code)
    result = result[result["normalized_code"].str.len().gt(0)].copy()
    result["unique_task_id"] = result["module"].astype(str) + "_" + result["task"].astype(str)
    result = result.sort_values(["user", "unique_task_id", "date"])
    result = result.drop_duplicates(
        subset=["user", "unique_task_id", "normalized_code"], keep="first"
    )
    return result.drop(columns=["task", "module", "extension"])

