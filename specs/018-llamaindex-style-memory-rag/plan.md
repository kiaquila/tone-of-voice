# Plan: LlamaIndex Style Memory RAG

## Approach

1. Apply critic hardening to the existing retrieval layer:
   - document the `k=3` eval rationale
   - use content hashes for the style-memory prompt cache fingerprint
   - add a seed case that separates `style_memory` from `hybrid`
   - expand CI path filters for bot/config/eval/dependency changes
2. Add a LlamaIndex adapter module:
   - convert `StyleMemoryRecord` values into `Document` objects
   - use a deterministic local embedding for CI and offline use
   - persist and reload `VectorStoreIndex` storage with a content fingerprint
   - apply metadata filters when retrieval is source-type constrained
3. Wire `llama_index` into drafting and retrieval experiments.
4. Expose the path through build/query CLI flags.
5. Update docs so the next implementation sequence remains generated-output
   A/B tests, then judge evals, then cross-platform expansion.

## Design Notes

- The embedding is deliberately local and deterministic. It proves the
  LlamaIndex contracts without introducing API keys or model downloads into CI.
- `heuristic`, `style_memory`, and `hybrid` remain available because the
  LlamaIndex path is experimental and must earn its way through evals.
- The production default remains `heuristic`.
