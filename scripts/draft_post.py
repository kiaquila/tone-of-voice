#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from tone_of_voice.config import load_project_env
from tone_of_voice.drafting import (
    DraftRequest,
    build_prompt_bundle,
    generate_with_anthropic_messages,
    write_draft_artifact,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a platform-specific draft from a structured JSON request."
    )
    parser.add_argument(
        "request",
        help="Path to a draft request JSON file. Use '-' to read JSON from stdin.",
    )
    parser.add_argument(
        "--output-dir",
        default="data/working/drafts",
        help="Directory for prompt and draft artifacts.",
    )
    parser.add_argument(
        "--env-file",
        help=(
            "Optional env file path. Defaults to .env, plus "
            "TONE_OF_VOICE_FALLBACK_ENV when set."
        ),
    )
    parser.add_argument(
        "--model",
        help=(
            "Model override. Defaults to request.model, "
            "TONE_OF_VOICE_ANTHROPIC_MODEL, ANTHROPIC_MODEL, or claude-sonnet-4-6."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Assemble and store the prompt without calling the model backend.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        help="Anthropic API timeout in seconds.",
    )
    return parser.parse_args()


def load_request(path: str) -> DraftRequest:
    if path == "-":
        return DraftRequest.from_mapping(json.load(sys.stdin))
    with open(path, encoding="utf-8") as fh:
        return DraftRequest.from_mapping(json.load(fh))


def main() -> int:
    args = parse_args()
    load_project_env(args.env_file)
    request = load_request(args.request)
    bundle = build_prompt_bundle(request, model=args.model)

    draft = None
    response_data = None
    backend = "prompt_only"
    if not args.dry_run:
        draft, response_data = generate_with_anthropic_messages(
            bundle,
            timeout=args.timeout,
        )
        backend = "anthropic_messages"

    artifact_path, prompt_path, artifact = write_draft_artifact(
        bundle,
        output_dir=args.output_dir,
        draft=draft,
        backend=backend,
        response_data=response_data,
    )

    print(f"Artifact: {artifact_path}")
    print(f"Prompt: {prompt_path}")
    print(
        "References: "
        + ", ".join(reference["ref_id"] for reference in artifact["references"])
    )

    if draft:
        print("")
        print(draft)
    else:
        print("")
        print(
            "Dry run complete. Export ANTHROPIC_API_KEY and rerun without --dry-run "
            "to generate a draft."
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
