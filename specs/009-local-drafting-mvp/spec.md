# Spec - 009 Local Drafting MVP

## Summary

Execute Step 2 from `docs/07-product-execution-plan.md`: make the repository usable from a laptop so a structured idea can become a platform-specific draft with the voice memory attached.

## Scope

This change includes:

- a draft request schema for local JSON inputs
- a local CLI entrypoint for drafting
- prompt assembly from the durable voice docs and reference library
- selection of 3 to 5 relevant reference examples
- artifact storage for the input, selected context, prompt, and generated draft
- usage docs and tests for the local flow

This change does not include:

- Telegram bot handlers
- automated publishing
- feedback capture or edit-distance metrics
- CI eval gates for generated draft quality

## Requirements

1. A user must be able to run one local command with a structured request file.
2. The command must support Telegram, Threads, and LinkedIn as target platforms.
3. Prompt assembly must include the voice core, platform playbook, stop-list, drafting recipes, and 3 to 5 reference examples.
4. The output artifact must preserve the original request, selected references, context files, model/backend metadata, prompt path, and draft text when generation runs.
5. The first implementation must keep human approval in the loop and must not publish anywhere.
6. If no model credentials are configured, the command must still support a dry-run mode that writes the prompt artifact for inspection.

## Acceptance Criteria

- `python scripts/draft_post.py --help` works.
- `python scripts/draft_post.py examples/draft-request.telegram.json --dry-run` writes a prompt and JSON artifact under `data/working/drafts/`.
- Unit tests cover request validation, reference parsing, reference selection, prompt assembly, response text extraction, and artifact writing.
- Roadmap and README mark Step 2 as implemented and point future work at Step 3.
