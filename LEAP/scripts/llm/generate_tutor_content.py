"""Generate one tutoring question from saved LEAP context using local Ollama."""

import argparse
import json
from pathlib import Path

from leap.llm import OllamaTutorContentGenerator


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--context",
        type=Path,
        default=Path("outputs/llm/demo_context.json"),
    )
    parser.add_argument("--model", default="qwen3:8b")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("outputs/llm/demo_tutor_content.json"),
    )
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--max-retries", type=int, default=2)
    args = parser.parse_args()

    artifact = json.loads(args.context.read_text(encoding="utf-8"))
    messages = artifact.get("messages")
    if not isinstance(messages, list):
        raise TypeError(f"{args.context} does not contain a messages array")

    generator = OllamaTutorContentGenerator(
        model=args.model,
        timeout_seconds=args.timeout,
        max_retries=args.max_retries,
    )
    content = generator.generate(messages)
    output = {
        "model": args.model,
        "source_context": str(args.context),
        "selected_action": artifact.get("context", {}).get("selected_action"),
        "content": content,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
