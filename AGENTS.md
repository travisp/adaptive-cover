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
- If poetry is installed, which it should be, all commands should be prefixed with `poetry run`

## Pull request message

Include a brief summary of changes and testing results. Mention any linting or
tests that could not be run.
