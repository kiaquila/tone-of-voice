# Regression Evals

## Purpose

The regression eval gate protects the drafting loop from silent quality drift when prompts, voice-memory rules, reference retrieval, or feedback metrics change.

It is intentionally small and deterministic at this stage. The first gate does not call a model. It checks an inspectable draft/final eval slice, runs rule-level assertions, and dry-runs prompt assembly for cases that include a structured request.

## Eval Suite Location

The default suite lives at:

- `evals/regression/step4-seed.json`

Each case can include:

- `draft_text`
- `final_text`
- platform and post type metadata
- threshold overrides for draft-to-final edit distance
- banned or required phrase checks
- an optional structured draft request for prompt-contract checks

The current seed case mirrors `examples/feedback-capture.telegram.json` because real captured feedback records under `data/working/feedback/` are ignored by git. Replace or extend the seed with deliberately selected real draft/final pairs once they are safe to commit.

## What The Gate Checks

For every case, the gate computes:

- character percent changed
- word percent changed
- character edit distance
- word edit distance

It fails when a case exceeds its configured thresholds.

For rule-level checks, the gate can fail when:

- draft text contains a banned phrase
- final text contains a banned phrase
- final text is missing a required phrase

For cases with a `request`, the gate also builds the prompt bundle and fails when:

- fewer than the minimum number of references are selected
- required context files are missing from the prompt

## Current Thresholds

The seed suite defaults are:

- max character percent changed: `70.0`
- max word percent changed: `75.0`
- max rule failures: `0`
- minimum prompt references: `3`

These thresholds are deliberately interpretable. Tighten them only after the eval set contains enough real examples to make regressions meaningful.

## Commands

Run the default eval suite:

```bash
python3 scripts/run_regression_evals.py
```

Write structured output:

```bash
python3 scripts/run_regression_evals.py --json-output data/working/evals/latest.json
```

Use a custom suite:

```bash
python3 scripts/run_regression_evals.py --suite evals/regression/step4-seed.json
```

## CI Behavior

The CI `baseline-checks` job runs the regression eval slice:

- on every push to `main`
- on pull requests that touch drafting logic, feedback metrics, eval code, eval suites, or core voice-memory docs

Doc-only refreshes outside the drafting/eval surface skip the eval slice. Unit tests and CLI smoke checks still run as usual.

## Adding New Cases

Prefer small, high-signal cases:

- one Telegram project update with a real draft/final pair
- one concise opinion post where the hook changed materially
- one tool/setup breakdown where specificity matters

Do not dump the whole feedback corpus into evals. The suite should stay readable enough that a failed case tells the next session what changed and why it matters.
