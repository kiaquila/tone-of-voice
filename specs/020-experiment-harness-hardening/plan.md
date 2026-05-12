# Plan: Experiment Harness Hardening

## Approach

1. Add common experiment helpers:
   - repository-local path resolution
   - JSON suite loading
   - JSON report writing
   - shared parsing helpers for required text, optional text, mappings, and
     list normalization
2. Add a shared CLI runner that handles:
   - `--suite`
   - optional repeated `--variant`
   - `--json-output`
   - report printing and exit status
3. Rewire the three existing experiment scripts and modules to use the helpers
   without changing their external command names.
4. Consolidate CI eval path detection into one shell step with outputs for the
   regression, retrieval, and generated-output slices.
5. Record the trust-boundary audit in delivery docs and keep the generated-output
   seed expansion deferred until real draft/final pairs are safe to commit.

## Design Notes

- Path hardening is intentionally repository-local because the documented workflow
  already writes structured reports under ignored repo paths such as
  `data/working/evals/`.
- `baseline-checks` continues to run proposed PR code because that is the point
  of a repo-health CI gate. Trusted policy enforcement stays in workflows that
  run from the base branch.
