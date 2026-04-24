# Plan — 003 AI Review And OSV Scan

## Technical Approach

Add two workflows:

- `.github/workflows/osv-scan.yml`
- `.github/workflows/ai-review.yml`

The OSV workflow will scan `requirements.txt` directly because the repository currently uses a simple Python manifest rather than a dedicated lockfile.

The AI review workflow will:

- expose an `AI Review` check on PRs
- run a no-op explanatory pass when Claude review is not yet configured
- run Claude review once `AI_REVIEW_AGENT=claude` and `ANTHROPIC_API_KEY` are set

## Validation

- local repository validation remains green
- PR checks appear on GitHub
- `osv-scan` passes
- `AI Review` reports a clear state
