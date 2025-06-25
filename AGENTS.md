# Agent Guidelines

This file defines conventions for automated tools contributing to this repository.

## Development workflow

- **Formatting and linting**: run `scripts/lint` to automatically format the
  codebase using `ruff`.
- **Testing**: run `scripts/test` to execute the pytest suite.
- Add or update tests when modifying functionality or fixing bugs.
- Include helpful comments for any complicated logic.
- Provide docstrings for all functions and classes.
- If these scripts fail because dependencies are missing or the environment lacks
  internet access, note it in the PR testing section.
- If uv is installed, prefix commands with `uv run`. So run `uv run scripts/lint` and `uv run scripts/test`. Alternatively, activate the `.venv` created by `scripts/setup`.

## Pull request message

Include a brief summary of changes and testing results. Mention any linting or
tests that could not be run.
