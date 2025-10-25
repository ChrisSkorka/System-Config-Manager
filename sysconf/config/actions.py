# pyright: strict

from abc import abstractmethod
from typing import Self

from sysconf.config.serialization import YamlSerializable
from sysconf.system.executor import SystemExecutor


class Action:
    """
    An action that can be run/executed on the system.
    """

    @abstractmethod
    def render(self) -> YamlSerializable:
        """
        Render the action into a serializable format.

        Returns:
            A string representation of the action.
        """
        pass  # pragma: no cover

    @abstractmethod
    def run(self, executor: SystemExecutor) -> None:
        """
        Execute the action.

        This will perform actual action including executing system commands.
        """
        pass  # pragma: no cover# pragma: no cover


class ShellAction(Action):
    """
    An action that executes a shell command/script.
    """

    @classmethod
    def create_from_serialized(cls, data: YamlSerializable) -> Self:
        assert isinstance(data, str), \
            'ShellAction data must be a string/text script'

        return cls(data)

    def __init__(self, script: str) -> None:
        super().__init__()

        self.script = script

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ShellAction):
            return False

        return self.script == value.script

    def render(self) -> str:
        return self.script

    def run(self, executor: SystemExecutor) -> None:
        executor.shell(self.script)
