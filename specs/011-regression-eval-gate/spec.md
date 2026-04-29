# Spec - Regression Eval Gate

Execute Step 4 from `docs/07-product-execution-plan.md`: add a small offline eval gate so drafting changes can fail for clear quality regressions before the phone workflow begins.

## Scope

In scope:

- a committed regression eval suite
- deterministic draft/final edit-distance checks
- simple rule-level phrase checks
- prompt-contract checks for eval cases with structured requests
- a repeatable CLI for local and CI usage
- CI integration for drafting, feedback, eval, and core voice-memory changes
- docs, tests, roadmap, and delivery workflow updates

Out of scope:

- model-backed eval generation
- automatic grading by an LLM
- Telegram bot flows
- automatic promotion of private `data/working/feedback/` records into committed evals

## Requirements

1. The eval suite must be inspectable JSON committed outside ignored `data/`.
2. The eval runner must return a non-zero exit code when a case fails.
3. The runner must report edit-distance metrics for every case.
4. Rule-level failures must be understandable without opening code.
5. Prompt-contract checks must verify reference retrieval and required context inclusion for cases with requests.
6. CI must run the eval slice on relevant drafting or voice-memory PRs and on pushes to `main`.
7. Docs must explain thresholds, suite location, CI behavior, and how to add real cases.

## Acceptance Criteria

- `python3 scripts/run_regression_evals.py --help` works.
- `python3 scripts/run_regression_evals.py` passes on the seed suite.
- Unit tests cover passing seed behavior, metric failures, and rule failures.
- CI smoke checks include the new CLI.
- Roadmap and execution plan mark Step 4 complete and point future work at Step 5.
