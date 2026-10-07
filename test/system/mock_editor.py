# pyright: strict

from pathlib import Path

from sysconf.system.editor import EditResult, EditorLauncher
from test.system.mock_system_executor import MockSystemExecutor


class MockWhich:
    """Resolve executables from a fixed set of names to their paths."""

    def __init__(self, paths_by_name: dict[str, str]) -> None:
        self.paths_by_name = paths_by_name

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, MockWhich):
            return False

        return self.paths_by_name == value.paths_by_name

    def __call__(self, name: str) -> str | None:
        return self.paths_by_name.get(name)


class MockEditorLauncher (EditorLauncher):
    """Return the configured edit results one after the other on each edit."""

    def __init__(self, results: tuple[EditResult, ...]) -> None:
        super().__init__(MockSystemExecutor())

        self.results = results
        self.calls: list[tuple[tuple[str, ...], Path]] = []

    def edit(self, editor_command: tuple[str, ...], path: Path) -> EditResult:
        result = self.results[len(self.calls)]
        self.calls.append((editor_command, path))
        return result
