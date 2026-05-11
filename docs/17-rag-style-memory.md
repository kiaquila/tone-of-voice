# RAG Style Memory

## Purpose

This layer turns the bot's voice memory into an inspectable retrieval-augmented
pipeline. The goal is not to add buzzword RAG. The goal is to make drafting
quality easier to debug:

1. build a style-memory index
2. retrieve relevant examples, rules, and feedback signals for a request
3. assemble the prompt with recorded retrieval strategy
4. compare retrieval variants before trusting a generation change
5. capture final edits and feed them back into future memory

## Memory Types

The first index includes:

- `reference_example` records from `docs/10-reference-library.md`
- `voice_principle` records from `docs/00-principles.md`
- `voice_snapshot` records from `docs/01-current-voice-snapshot.md`
- `platform_playbook` records from `docs/04-platform-adaptation.md`
- `stop_rule` corrective records from `docs/12-stop-list.md`
- `drafting_recipe` records from `docs/13-drafting-recipes.md`
- `feedback_final` and `feedback_correction` records from local draft/final
  feedback when available

Feedback records borrow the useful part of margin-style annotation workflows:
a concrete text fragment becomes a scoped style signal. Positive final versions
are examples to imitate. Corrective records are guardrails.

## Data Flow and Privacy

The style-memory index ingests broader data than what is sent to the model.
Two boundaries matter:

- Feedback dirs are auto-discovered from `data/working/feedback` and
  `data/working/bot/feedback` whenever `build_style_memory_index` runs without
  an explicit `feedback_dirs` argument.
- `feedback_final` records (your previous final post text) are ingested into
  the index but are EXCLUDED from the drafting prompt context by default.
  This avoids self-imitation drift and unnecessary data flow to model
  providers. The allowlist of source types eligible for the drafting prompt
  lives in `tone_of_voice.drafting.PROMPT_CONTEXT_SOURCE_TYPES` and includes
  reference examples, voice principles and snapshots, platform playbooks,
  stop-list rules, drafting recipes, and `feedback_correction` signals.
- `feedback_correction` records ARE included in the prompt context. They act
  as guardrails by telling the model which past tone or structure mistakes
  must be avoided.

The retrieval experiment in `evaluate_retrieval_suite` calls
`build_style_memory_index` with `feedback_dirs=[]` so the offline harness
remains deterministic regardless of locally captured feedback. See
`src/tone_of_voice/retrieval_experiments.py` (`evaluate_retrieval_suite`).

## Margin-Inspired Annotation Model

The Margin-inspired part is the memory shape, not the full product UI. The first
implementation already separates:

- positive examples worth imitating
- corrective signals that should become guardrails
- source text or final text that provides evidence
- scope such as general voice, platform-specific writing, or a specific post
  type

Future annotation records should use this shape:

- `fragment`: the highlighted source text, final edit, or problematic draft
  excerpt
- `polarity`: `positive` or `corrective`
- `scope`: `general`, `telegram`, `threads`, `linkedin`, or a narrower workflow
- `post_type`: optional, for cases like `tool_breakdown` or `project_update`
- `topics`: optional retrieval tags
- `rule`: the reusable writing lesson
- `evidence_count`: how many times this signal has repeated
- `source`: the post, draft artifact, feedback record, or note it came from

Not yet implemented:

- a reader-style UI for selecting fragments
- multi-highlight review sessions
- human preference labels between generated variants
- promotion from ad hoc notes into durable memory through an approval screen

## Commands

Build the local index:

```bash
python3 scripts/build_style_memory_index.py
```

Build both the JSON style-memory artifact and the persistent LlamaIndex vector
index:

```bash
python3 scripts/build_style_memory_index.py --llama-index
```

Query the index directly:

```bash
python3 scripts/query_style_memory.py "multi-agent setup costs" --build --platform telegram --topic agents --topic cost --post-type tool_breakdown
```

Query from a draft request:

```bash
python3 scripts/query_style_memory.py --request examples/draft-request.telegram.json --build
```

Query through the persistent LlamaIndex path:

```bash
python3 scripts/query_style_memory.py "multi-agent setup costs" --build --backend llama_index --source-type reference_example
```

Run retrieval experiments:

```bash
python3 scripts/run_retrieval_experiments.py
```

Run generated-output A/B experiments:

```bash
python3 scripts/run_generated_output_experiments.py
```

Write a structured report:

```bash
python3 scripts/run_retrieval_experiments.py --json-output data/working/evals/retrieval-latest.json
python3 scripts/run_generated_output_experiments.py --json-output data/working/evals/generated-output-latest.json
```

Use RAG-style retrieval while drafting:

```bash
python3 scripts/draft_post.py examples/draft-request.telegram.json --dry-run --retrieval-strategy style_memory
```

Use the LlamaIndex-backed retrieval strategy:

```bash
python3 scripts/draft_post.py examples/draft-request.telegram.json --dry-run --retrieval-strategy llama_index
```

Run the Telegram bot with the same retrieval strategy:

```bash
python3 scripts/run_telegram_bot.py --allowed-chat-id <your-chat-id> --retrieval-strategy hybrid
```

The same behavior can be enabled with:

```bash
export TONE_OF_VOICE_RETRIEVAL_STRATEGY=hybrid
```

## Retrieval Strategies

- `heuristic`: the original reference selection based on platform, recipe,
  post type, topics, mood, and lexical overlap.
- `style_memory`: retrieves reference examples through the style-memory index
  and adds a `Retrieved Style Memory` prompt section with examples, rules, and
  corrective signals.
- `hybrid`: interleaves style-memory retrieval with heuristic references for
  coverage.
- `llama_index`: builds LlamaIndex `Document` objects from the style-memory
  records, stores a persistent `VectorStoreIndex`, retrieves with a local
  deterministic embedding, and applies metadata filters such as source type
  before ranking.

The default remains `heuristic` so production behavior does not change unless a
request, CLI flag, or environment variable opts into the new path.

## Experiment Suite

The retrieval suite lives at:

- `evals/retrieval/style-memory-seed.json`

It compares variants on inspectable cases with expected reference records. The
runner reports:

- precision at k
- recall at k
- mean reciprocal rank
- failed cases per variant
- the current winner

The seed suite currently uses `k=3`. That is intentional: drafting asks for
3 to 5 reference examples, and the lower bound keeps the retrieval eval strict.
A relevant style signal should fit into the compact prompt context instead of
only appearing after extra padding.

This is deliberately an offline retrieval A/B harness. It does not call a model.
Once the retrieval variants are stable, generated-text A/B tests can add model
outputs, draft/final edit distance, and human preference labels on top.

## Generated Output A/B Suite

The first generated-output suite lives at:

- `evals/generated-output/step6-followup-seed.json`

It compares saved draft text variants for the same request across retrieval
strategies. The default suite is fixture-based and does not call a model, so it
can run in CI. The runner records:

- draft-to-final edit metrics
- selected variant and best-by-edit-distance variant
- prompt reference ids and retrieved style-memory record ids
- manual preference labels
- common tone correction and structural notes

Use the existing drafting command to generate real candidate drafts, then copy
the inspected outputs into a generated-output suite when they are safe to commit
or into an ignored local suite under `data/working/evals/` for private review.

The default suite is intentionally a shape-only baseline: it has a single case
with `max_char_percent_changed` and `max_word_percent_changed` set to `100.0`,
so only the `min_prompt_references=3` gate fires in CI. Real drift detection
arrives once manual A/B drafts populate additional cases. The winner is chosen
by objective edit metrics first (`best_by_edit_count`, then median word/char
change); the human `selected_count` is only a tie-breaker.

## CI Behavior

`baseline-checks` now runs:

```bash
python scripts/run_retrieval_experiments.py
python scripts/run_generated_output_experiments.py
```

That makes retrieval and generated-output regressions visible before a prompt
or bot change merges.

## Portfolio Framing

This step is useful for the Plata AI Engineer gap-skills sprint because it
creates a concrete AI/ML pipeline:

- ingestion: voice docs, curated references, draft/final feedback
- retrieval: local TF-IDF-style ranked memory plus an opt-in LlamaIndex
  `VectorStoreIndex` path with persistent storage and metadata filters
- generation: Anthropic prompt assembly with recorded retrieval strategy
- evaluation: deterministic retrieval and generated-output experiments in CI
- feedback: final edits become future memory records

The first implementation is still local-first and CI-friendly. Future PRs can
swap the deterministic embedding for a stronger local or provider embedding,
then add Ragas or MLflow on top of the generated-output contracts.

## Next Implementation Sequence

1. Add generated-output A/B tests. - first offline harness complete
   - Compare drafts generated with different retrieval strategies, not only
     which references were selected.
   - Record edit distance, selected/final variant, manual preference, and common
     correction tags.

2. Add Ragas or a lightweight judge-based eval layer.
   - Use it after real generated drafts and final edits exist.
   - Evaluate generated output quality, context relevance, and whether retrieved
     memory was actually useful.

3. Then continue Step 7 cross-platform expansion.
   - Expand LinkedIn and Threads on top of the retrieval and eval surface rather
     than stretching the Telegram bot before the RAG loop is measurable.
