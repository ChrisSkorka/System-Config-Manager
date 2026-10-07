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
- Use return values & exception instead side channels
- `__init__` methods only set the instances properties
- Use factory methods for computation & constructing objects when instantiating a class
- Short & concise comments, use dot point lists for relevant facts
- `__init__` receives finished dependencies; parsing & building them happens in `create_from_*` factories
  - e.g. `create_from_arguments` parses args, `__init__` never takes a parser to compute from
- Inject services through constructors (built in factories), don't instantiate services inside `run()`/business methods
- Return user choices/outcomes as result values (e.g. `TryRunResult`, `RunActionsResult`), not flags stored on a service for the caller to query afterwards
- `__eq__(self, value: object) -> bool` (not `Any`), narrow with `isinstance`
- Wrap multi-line boolean chains in `( ... )` with one operand per line, not `\` continuations
- Generic types use bound `TypeVar`s with explicit type args at use sites (e.g. `MockSystemManager[None]`), never fall back to `object`
- Leave changes unstaged unless asked, the user stages selectively to split commits

### Don't

- Don't use complex `python -c ...` commands
- Don't add type ignore or other type/pyright exclusion comments
- Don't write one test function per test
- Don't install dependencies & software (even if just for validating something) without explicit permission to install it.
- Don't create branches, commits, or push without explicit approval
- Don't leak info from real configs or conversations into this project or tests
- Don't add paragraph comments
- Don't use objects whose lifetime conveniently aligns with your use case as a side channel for data between distant places, instead architect better structure/stack traces
- Don't have multiple sources of truth for the same conceptual value 
  (does not apply to conceptually different variables that have the same value)
- Don't place expressions (or function calls) in function parameters, always extract params into variables first
- Don't perform computations or call methods/constructors from `__init__` (use factory methods instead)

### Formatting

- When finishing up work, run autopep8 first, then apply the rules below (autopep8 splits args & lists oddly):
  - `PYTHONPATH=~/.vscode/extensions/ms-python.autopep8-2026.4.0/bundled/libs python3 -m autopep8 --in-place --recursive sysconf test`
- Call args are either all on one line, or one per line with the closing bracket on its own line, e.g.:
  ```python
  asdf(
      val1,
      val2,
  )
  ```
- Always use trailing commas for multi-line args, lists, tuples, sets & dicts
- Always use keyword args, unless every arg is a variable named the same as its parameter (e.g. `f(path, config)` or `f(path=arg, config=default)` for `def f(path, config)`)

## Project Overview

- Represent a OS's configuration (installed packages, config files, settings, etc) as a config file
- Diff new configs to current and apply differential actions to the systems
