# General Instructions

## Do's & Don't's

### Do

- Do use easy to verify commands like `grep`, `find`, `jq`, etc
- Do figure out correct and complete typing, or ask user for options to avoid type ignore
- Add `# pyright: strict` to the start of every file (if an existing file is missing it, ask the user if it should be added)
- Check `./Makefile` for how to run & test this project
- Tests use `@datasets` & `@dataclass` for data driven tests (see existing tests for examples)
- Use `make typecheck` for pyright checks
- Use git stash when managing the worktree instead of commits or branches

### Don't

- Don't use complex `python -c ...` commands
- Don't add type ignore or other type/pyright exclusion comments
- Don't write one test function per test
- Don't install dependencies & software (even if just for validating something) without explicit permission to install it.
- Don't create branches, commits, or push without explicit approval
- Don't leak info from real configs or conversations into this project or tests

## Project Overview

- Represent a OS's configuration (installed packages, config files, settings, etc) as a config file
- Diff new configs to current and apply differential actions to the systems
