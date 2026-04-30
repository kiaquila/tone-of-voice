# Contributing

This is a personal project for tracking the maintainer's public writing voice. Issues and pull requests are welcome, but the maintainer may decline contributions that do not fit the project's direction.

## Development setup

```bash
pip install -e '.[dev]'
```

Run the tests and the linter:

```bash
pytest
ruff check
```

## Workflow

The project follows a specs-driven workflow:

- Substantial changes start as a numbered spec under `specs/` (see existing entries for the `spec.md` / `plan.md` / `tasks.md` format).
- Pull requests must pass the required CI gates: `baseline-checks`, `osv-scan`, `guard`, and `AI Review`.
- Bundle review-driven fixes against the same milestone into a single PR rather than opening many small follow-ups.

## Reporting issues

Open a GitHub issue with the smallest reproducer you can produce. Include CI run links and relevant log snippets. For security-sensitive reports, follow the [SECURITY.md](SECURITY.md) policy instead.
