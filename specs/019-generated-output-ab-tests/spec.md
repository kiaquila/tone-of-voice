# Spec: Generated Output A/B Tests

## Problem

Step 6 can compare retrieval strategies by selected memory records, but the
roadmap now needs a generated-output loop: compare actual drafts produced with
different retrieval strategies before trusting a generation behavior change.

## Scope

- Add an offline generated-output experiment suite format.
- Compare draft text variants by retrieval strategy against a final edited text.
- Record the human-selected variant, edit-distance metrics, preference signal,
  tone correction tags, and prompt/retrieval metadata.
- Add a CLI that prints a readable report and can write structured JSON.
- Keep CI-friendly behavior: no model calls in the default suite.

## Non-Goals

- Add Ragas or judge-based scoring.
- Replace the deterministic retrieval experiment gate.
- Change the production Telegram bot default retrieval strategy.
- Add Threads or LinkedIn ingestion.

## Acceptance Criteria

- `scripts/run_generated_output_experiments.py` evaluates the default suite
  without model credentials.
- The report compares `heuristic`, `style_memory`, `hybrid`, and `llama_index`
  draft outputs when they are present in a case.
- Results include draft-to-final edit metrics, selected variant, best-by-edit
  variant, common correction tags, and selected prompt metadata.
- The CI gate enforces `min_prompt_references=3` per variant against
  `build_prompt_bundle`; edit-distance thresholds default to permissive 100% so
  the first seed acts as a shape-only baseline until real generated drafts
  exist.
- Winner ranking uses objective edit metrics first (`best_by_edit_count`,
  `median_word_percent_changed`, `median_char_percent_changed`) and only uses
  the human `selected_count` as a tie-breaker, so the winner is not a
  re-broadcast of manual labels.
- Tests cover parsing, metric aggregation, winner selection, and failure cases.
- Roadmap, RAG docs, delivery workflow, and README describe the generated-output
  A/B layer as the current next step.

## Seed Maturity

The first seed `evals/generated-output/step6-followup-seed.json` is a single
shape-only case: it exercises the schema and the prompt-reference gate, not
real drift. New cases land when manual A/B drafts accumulate; until then the
edit thresholds stay permissive and the harness reports trivial aggregates.
