# Plan: Generated Output A/B Tests

## Approach

1. Create a generated-output experiment module:
   - parse a committed offline suite
   - validate variant names and required final text
   - compute draft-to-final edit metrics with the existing feedback metric code
   - build prompt bundles per strategy to record reference and style-memory
     metadata without calling a model
2. Add a CLI wrapper:
   - load a suite
   - evaluate requested variants
   - print a compact markdown report
   - optionally write JSON results under `data/working/evals/`
3. Seed one inspectable generated-output A/B case.
4. Add unit tests around parsing, aggregation, winner selection, and failure
   behavior.
5. Update docs and CI path filters so the new eval surface is discoverable.

## Design Notes

- The first suite stores generated draft text as fixture data. Model calls stay
  outside CI and can be performed manually through existing drafting commands.
- Human preference and final edit distance are separate signals. A variant can
  be selected by the author even if another draft has lower edit distance.
- This layer prepares the ground for judge/Ragas evals, but does not attempt to
  score subjective voice quality automatically yet.
