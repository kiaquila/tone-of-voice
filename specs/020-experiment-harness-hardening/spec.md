# Spec: Experiment Harness Hardening

## Problem

The regression, retrieval, and generated-output experiment runners had three
near-identical CLI wrappers, repeated JSON output handling, repeated suite
parsing helpers, and expanding path-filter logic in CI. That made future eval
work easy to update inconsistently.

The follow-up audit also confirmed that `baseline-checks` is a required branch
protection context, so its trust boundary needs to stay explicit.

## Scope

- Extract shared experiment suite helpers into `tone_of_voice.experiments_common`.
- Extract shared CLI runner behavior into `tone_of_voice.experiments_cli`.
- Keep the three public scripts and their flags stable.
- Harden `--suite` and `--json-output` paths so experiment CLIs only read or
  write repository-local paths.
- Replace repeated CI path-filter blocks with a shared shell helper and per-slice
  outputs.
- Document the `baseline-checks` trust-boundary audit.

## Non-Goals

- Add new judge/Ragas scoring.
- Change generated-output winner semantics.
- Change the production bot retrieval default.
- Promote private or locally ignored draft artifacts into committed seed data.

## Acceptance Criteria

- `scripts/run_regression_evals.py`, `scripts/run_retrieval_experiments.py`, and
  `scripts/run_generated_output_experiments.py` still run with the same public
  flags.
- Repository-local `--json-output` paths are created as before.
- Parent-directory escape attempts through `--suite` or `--json-output` fail.
- CI detects eval-impacting paths once and uses that result for the three eval
  slices.
- Delivery docs state that `baseline-checks` is required by branch protection
  but should not own trusted policy decisions or secret-bearing work.
