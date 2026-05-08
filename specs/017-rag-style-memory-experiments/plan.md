# Plan: RAG Style Memory And Experiments

## Approach

1. Add a local style-memory module with records, index serialization, query
   objects, ranking, and prompt-ready match blocks.
2. Add CLI commands for building and querying the index.
3. Add a retrieval experiment module and seed suite that compares current
   heuristic reference selection with style-memory and hybrid variants.
4. Integrate retrieval strategy selection into prompt assembly, draft artifacts,
   and the Telegram bot runner.
5. Update CI to run the retrieval experiment slice and smoke-check new CLI help.
6. Update roadmap, README, delivery workflow, bot docs, and a new RAG style
   memory doc.

## Design Notes

- The first retriever uses a local TF-IDF-style score with metadata boosts. This
  keeps CI deterministic and makes the experiment loop visible before adding a
  vector database.
- The index separates positive and corrective signals so final versions and
  stop-list rules do not collapse into the same kind of context.
- The default retrieval strategy stays `heuristic`; new behavior is opt-in via
  request JSON, CLI flag, or environment variable.
- The retrieval experiment suite evaluates retrieval only. Generated text A/B
  tests can be added once enough real final feedback exists.
