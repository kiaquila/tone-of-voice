# Plan — 008 Product Plan And Required Gates

## Approach

Make the current verbal assessment durable in the same place future sessions already read, then close the process gap between documentation and live GitHub protection.

The work splits into two parts:

1. Documentation alignment:
   - add a canonical product execution plan
   - update repository memory so future sessions know where to find and how to follow it
   - correct delivery docs to reflect the actual codex review gate
2. Repository enforcement:
   - inspect current branch protection on `main`
   - add `osv-scan` to the required checks
   - verify that the live settings match the docs

## Steps

1. Add `docs/07-product-execution-plan.md` with a numbered 6-step path from current foundation to full product.
2. Update `AGENTS.md`, `README.md`, and `docs/05-roadmap.md` so future sessions can reference the plan by step number.
3. Update `docs/06-delivery-workflow.md` to reflect the codex AI Review gate and the live required checks.
4. Apply branch protection on `main` so required checks are `baseline-checks`, `guard`, `AI Review`, and `osv-scan`, with `strict: false` and `enforce_admins: true`.
5. Verify the branch-protection settings with `gh api`.
6. Run the feature-memory guard against the dirty worktree.

## Risks

- The biggest risk is divergence between docs and repo settings. Mitigation: update both in the same change and verify live protection after applying it.
- Future sessions may still miss the plan if it lives only in one file. Mitigation: point `AGENTS.md`, `README.md`, and the roadmap at the same file.
