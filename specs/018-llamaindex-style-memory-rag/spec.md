# Spec: LlamaIndex Style Memory RAG

## Problem

Step 6 established a deterministic local retrieval layer, but the next plan
requires a real LlamaIndex-backed path before generated-output A/B tests and
cross-platform expansion.

## Scope

- Add an opt-in `llama_index` retrieval strategy beside `heuristic`,
  `style_memory`, and `hybrid`.
- Build LlamaIndex `Document` objects from style-memory records.
- Persist a local `VectorStoreIndex` under `data/working/style-memory/`.
- Use metadata filters for source-type constrained retrieval.
- Keep the path CI-friendly with deterministic local embeddings and no model
  credentials.
- Harden the existing retrieval eval/cache layer based on critic follow-ups.

## Non-Goals

- Replace generation behavior by default.
- Add hosted vector databases.
- Add generated-output A/B tests or Ragas in this PR.
- Add LinkedIn/Threads ingestion.

## Acceptance Criteria

- `scripts/run_retrieval_experiments.py` evaluates `llama_index` as a variant.
- `scripts/draft_post.py ... --retrieval-strategy llama_index --dry-run` writes
  a prompt artifact with retrieved style memory.
- `scripts/query_style_memory.py --backend llama_index` returns matches from the
  persistent LlamaIndex path.
- CI path filters run the relevant evals when bot/config/eval/dependency files
  change.
- Docs explain that generated-output A/B tests remain the next step before
  judge evals and cross-platform expansion.
