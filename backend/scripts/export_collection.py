"""Export explicitly selected participants; refuse overwrites and unvalidated data.

Run from backend: .venv/bin/python scripts/export_collection.py --help
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.collection.export import build_collection_export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--learner-ids", type=Path, required=True, help="JSON array of approved learner IDs (not login codes)")
    parser.add_argument("--mode", choices=["development", "pilot", "study"], default="pilot")
    parser.add_argument("--output", type=Path, required=True, help="New directory; existing paths are never overwritten")
    parser.add_argument("--split-seed", default="leap-split-v1")
    parser.add_argument("--audit-only", action="store_true", help="Report issues without writing files")
    args = parser.parse_args()
    selected = json.loads(args.learner_ids.read_text())
    if not isinstance(selected, list) or any(not isinstance(item, str) or not item for item in selected):
        parser.error("learner-ids must contain a JSON array of nonempty strings")
    bundle = build_collection_export(set(selected), args.mode, args.split_seed)
    print(json.dumps(bundle["manifest"], indent=2))
    if args.audit_only:
        return
    if bundle["manifest"]["issues"] or bundle["manifest"]["empty_splits"] or bundle["manifest"]["missing_allowlisted_learners"]:
        parser.error("Export quality gates failed. Inspect the audit; do not silently discard broken histories.")
    args.output.mkdir(parents=True, exist_ok=False)
    for name, data in {"transitions": bundle["records"], "manifest": bundle["manifest"], "events": bundle["events"], "assessments": bundle["assessments"], "code_executions": bundle["code_executions"]}.items():
        with (args.output / f"{name}.json").open("x") as file:
            json.dump(data, file, indent=2)


if __name__ == "__main__":
    main()
