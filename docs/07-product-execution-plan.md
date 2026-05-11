# Product Execution Plan

## Purpose

This is the canonical step-by-step plan for turning `tone-of-voice` from a memory foundation into a working product.

Future sessions should treat this file as the numbered source of truth for implementation order. A good handoff prompt is:

`Execute Step N from docs/07-product-execution-plan.md in tone-of-voice.`

## Working Rules

- Ship one numbered step per pull request.
- Keep `docs/05-roadmap.md`, `docs/06-delivery-workflow.md`, and feature memory in sync when product behavior or workflow changes.
- Preserve human approval in every drafting and publishing flow.
- Prefer the smallest implementation that makes the next learning loop possible.
- Do not jump to the bot before the local drafting and feedback loops work.

## Step 1 - Reference Library And Refresh Loop

Status: complete

### Goal

Create the missing memory layers between the raw Telegram corpus and the current voice snapshot.

### Deliverables

- `docs/10-reference-library.md`
- `docs/11-refresh-log.md`
- `docs/12-stop-list.md`
- `docs/13-drafting-recipes.md`
- a durable tagging scheme for examples by platform, post type, mood, depth, and topic
- an explicit refresh workflow for adding new published posts without rewriting the whole profile

### Implementation Notes

- Seed the reference library with a first curated set from the current Telegram corpus.
- Keep entries compact and retrieval-friendly.
- Record only high-signal examples; this is a library, not a dump.

### Done When

- a future session can retrieve examples for a request like "Telegram launch note with playful confidence"
- the refresh workflow says exactly when to update the snapshot, refresh log, and reference library
- README and roadmap mention the new memory artifacts

## Step 2 - Local Drafting MVP

Status: complete

### Goal

Make the repository usable from a laptop: idea in, platform selected, draft out.

### Deliverables

- a draft request schema with fields such as platform, angle, constraints, source notes, and optional call to action
- a local drafting entrypoint such as `scripts/draft_post.py`
- prompt assembly that pulls from the voice core, platform playbook, stop-list, drafting recipes, and 3 to 5 relevant references
- output storage for generated drafts and inputs, for example under `data/working/drafts/`
- usage docs for the drafting command

### Implementation Notes

- The first version does not need to publish anywhere.
- It must produce one solid draft per request with minimal manual setup.
- If a model backend decision is still open at implementation time, choose the simplest option already available in the author's workflow and document it in the same PR.

### Done When

- one command can generate a Telegram, Threads, or LinkedIn draft from structured input
- the generated draft keeps enough context to understand which references and rules were used
- the flow is quick enough that the author would realistically use it before asking for a manual rewrite

### Status Notes

- `scripts/draft_post.py` accepts a structured JSON request and supports Telegram, Threads, and LinkedIn.
- Prompt assembly pulls from the durable voice docs, stop-list, drafting recipes, and selected reference examples.
- Generated run artifacts preserve the request, context files, selected references, prompt path, backend/model metadata, and draft text when generation runs.
- `--dry-run` writes inspectable prompt artifacts without requiring model credentials.

## Step 3 - Feedback Capture And Edit Metrics

Status: complete

### Goal

Teach the system from the author's edits instead of only from source posts.

### Deliverables

- a draft-versus-final storage schema
- a place to save approved drafts, edited drafts, and final published text
- edit-distance metrics and basic revision-quality metrics
- a repeatable script to summarize the most common edits and tone corrections

### Implementation Notes

- Start with explicit manual capture; automation can come later.
- Separate raw draft text from normalized analysis outputs.
- Design for Telegram first, but do not hard-code the model to Telegram-only fields.

### Done When

- a session can inspect recent draft/final pairs and see what changed
- the repository can compute trends such as edit distance and recurring tone fixes
- the feedback storage is stable enough to become the basis for evals

### Status Notes

- `scripts/capture_feedback.py` accepts a manual JSON feedback record and optionally reuses a local draft artifact from Step 2.
- Raw feedback records are written to `data/working/feedback/raw/`.
- Normalized analysis records are written to `data/working/feedback/analysis/`.
- `scripts/summarize_feedback.py` reports aggregate edit-distance metrics, platform/post type counts, recent records, and common tone correction tags.
- `docs/14-feedback-capture.md` documents the schema and workflow.

## Step 4 - Regression Eval Gate

Status: complete

### Goal

Prevent silent quality drift when prompts, rules, or drafting logic change.

### Deliverables

- a small offline eval set built from real draft/final examples
- evaluation scripts for edit distance and rule-level failures
- a CI workflow or extension that runs the eval slice on relevant PRs
- durable docs that explain what counts as a failing regression

### Implementation Notes

- Keep the first eval set small and inspectable.
- Measure only what we can interpret and act on.
- This step should gate drafting changes, not ordinary doc-only refreshes.

### Done When

- a drafting-related PR can fail for clear voice-quality regressions
- the repo has a written threshold for acceptable movement in metrics
- future prompt tuning can happen with less guesswork

### Status Notes

- `scripts/run_regression_evals.py` runs the default offline suite at `evals/regression/step4-seed.json`.
- The eval runner checks draft-to-final edit distance, rule-level phrase failures, and prompt assembly contracts for cases with requests.
- The seed suite is intentionally small and mirrors the Step 3 feedback example until real feedback records are deliberately promoted into committed eval cases.
- CI runs the eval slice on pushes to `main` and on PRs touching drafting logic, feedback metrics, eval code, eval suites, or core voice-memory docs.
- `docs/15-regression-evals.md` documents thresholds and maintenance.

## Step 5 - Telegram Bot Product

Status: complete

### Goal

Turn the local drafting flow into a phone-usable product for day-to-day work.

### Deliverables

- Telegram bot handlers for draft, revise, approve, final-capture, and stat flows
- a clean handoff from idea capture to generated draft
- storage for bot session state, review history, and captured final feedback
- deployment setup and smoke checks on the same AWS host family used by `<sibling Telegram project>`
- operator docs for restart, config, and failure recovery

### Implementation Notes

- Keep the human in the loop; no auto-publishing in the first bot release.
- The bot should optimize for speed, clarity, and low-friction iteration from a phone.
- Reuse existing Telethon and sibling-host knowledge where it reduces risk.
- Treat learning as feedback-memory retrieval from captured final versions, not model fine-tuning.

### Done When

- the author can send an idea from a phone and receive a draft in Telegram
- revision requests can loop without losing the original context
- the author can capture the final manually edited post and inspect score trend from Telegram
- the deployment is boring enough to trust for regular use

### Status Notes

- `src/tone_of_voice/bot.py` implements the Telegram draft, revise, approve, final, stat, status, cancel, and help flows.
- `scripts/run_telegram_bot.py` runs the live Telethon bot.
- `scripts/smoke_telegram_bot.py` runs the bot draft loop offline in dry-run mode.
- `docs/16-telegram-bot-product.md` documents runtime env, storage, smoke checks, and recovery.
- `/final` stores pasted final text or a readable Telegram post link as draft/final feedback.
- `/stat` reports fit-score trend plus the learning signal used by subsequent drafts.
- `deploy/systemd/tone-of-voice-telegram-bot.service.example` provides the first host service template.
- Production is enabled on the target AWS host as `tone-of-voice-telegram-bot.service`.
- The first live smoke in `<your group>` confirmed both Telegram delivery and Anthropic draft generation.
- The runner ignores stale Telegram updates by default so a host restart does not reply to old queued `/draft` messages.
- `.github/workflows/deploy.yml` and `scripts/deploy_release.sh` provide the production deploy path through AWS SSM and systemd.

## Step 6 - RAG Style Memory And Experiment Harness

Status: complete

### Goal

Turn the current bot from a prompt wrapper with heuristic reference selection into
a measurable retrieval-augmented writing pipeline.

### Deliverables

- a local style-memory index built from the reference library, voice rules, and
  captured draft/final feedback
- a retrieval interface that can rank style memory by platform, topic, post type,
  mood, and positive/corrective signal
- drafting support for comparing the current heuristic reference selection with
  RAG-style and hybrid retrieval strategies
- an offline experiment runner that compares retrieval variants on inspectable
  seed cases
- experiment reports with precision/recall-style retrieval metrics and a clear
  keep/reject decision for each variant
- docs that explain the RAG pipeline, experiment loop, and how this maps to the
  AI Engineer gap-skills sprint

### Implementation Notes

- Keep the first retriever local-first and CI-friendly. A lightweight Python
  index is enough for the first learning loop; Chroma, LlamaIndex, LangChain,
  Ragas, or MLflow can be added once the local contracts are stable.
- Borrow the useful part of Margin's model: corrections and highlights become
  scoped style signals, not vague prose feedback.
- Treat generated examples, final edits, stop-list items, and positive style
  samples as different memory types with explicit metadata.
- Keep model calls out of the first experiment gate. The first A/B loop should
  measure retrieval behavior deterministically before comparing generated text.
- Preserve the existing human-in-the-loop bot workflow.

### Done When

- one command can build an inspectable style-memory index
- one command can query the index for a draft request and show why records were
  selected
- CI can run the retrieval experiment suite without model credentials
- draft artifacts record which retrieval strategy was used
- the roadmap, delivery workflow, and README describe the new RAG/eval surface

### Status Notes

- `src/tone_of_voice/style_memory.py` builds and queries a local style-memory
  index from references, voice docs, stop rules, recipes, and local feedback.
- `scripts/build_style_memory_index.py` writes the inspectable index artifact.
- `scripts/query_style_memory.py` queries the index directly or from a draft
  request.
- `src/tone_of_voice/retrieval_experiments.py` and
  `scripts/run_retrieval_experiments.py` compare `heuristic`, `style_memory`,
  and `hybrid` retrieval variants.
- `evals/retrieval/style-memory-seed.json` is the first deterministic retrieval
  experiment suite.
- `scripts/draft_post.py` and `scripts/run_telegram_bot.py` can opt into
  `style_memory`, `hybrid`, or `llama_index` retrieval strategies.
- Draft artifacts record `retrieval_strategy` and `style_memory_matches`.
- `docs/17-rag-style-memory.md` documents the pipeline, commands, and portfolio
  framing, including the next sequence: generated-output A/B tests, Ragas or
  judge-based evals, and only then cross-platform expansion.
- The first LlamaIndex-backed path builds `Document` records from style memory,
  persists a local `VectorStoreIndex`, and evaluates the `llama_index` variant
  beside `heuristic`, `style_memory`, and `hybrid`.
- `src/tone_of_voice/generated_output_experiments.py` and
  `scripts/run_generated_output_experiments.py` add the first offline
  generated-output A/B harness for comparing draft text variants, selected
  variants, final edits, prompt metadata, and correction tags.
- The regression, retrieval, and generated-output harnesses now share
  repository-local path handling and CLI/report-writing helpers.

## Step 7 - Cross-Platform Expansion

Status: planned

### Goal

Make the product useful beyond Telegram while keeping one recognizable voice core.

### Deliverables

- Threads and LinkedIn ingestion inputs
- stronger platform-specific retrieval for references and recipes
- per-platform feedback and eval slices
- docs for when to draft natively for each platform versus adapting from Telegram

### Implementation Notes

- Start with semi-manual ingestion if APIs are messy.
- Preserve one shared voice core and separate only what genuinely differs by platform.
- Do not let Threads punchiness flatten LinkedIn clarity or Telegram intimacy.

### Done When

- the system can generate platform-native drafts for Telegram, Threads, and LinkedIn
- feedback metrics can be filtered by platform
- the product has a credible path to learning cross-platform without collapsing into generic copy

## Milestone View

- After Step 2: usable desktop MVP
- After Step 3: learning loop starts
- After Step 4: drafting changes become safer
- After Step 5: usable phone product
- After Step 6: measurable RAG-backed writing pipeline
- After Step 7: full cross-platform product
