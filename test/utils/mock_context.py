# pyright: strict

from sysconf.system.executor import SystemExecutor
from sysconf.system.file import FileReader, FileWriter
from sysconf.utils.context import Context
from sysconf.utils.defaults import Defaults
from test.system.mock_system_executor import MockSystemExecutor
from test.utils.mock_defaults import MockDefaults
from test.utils.mock_file import MockFileReader, MockFileWriter


class MockContext (Context):
    """Provide the given collaborators instead of the live system ones."""

    @classmethod
    def create(
        cls,
        defaults: Defaults | None = None,
        file_reader: FileReader | None = None,
        file_writer: FileWriter | None = None,
        system_executor: SystemExecutor | None = None,
    ) -> 'MockContext':
        """Create a context, defaulting each collaborator to a fresh mock."""

        defaults = defaults or MockDefaults()
        file_reader = file_reader or MockFileReader({})
        file_writer = file_writer or MockFileWriter()
        system_executor = system_executor or MockSystemExecutor()

        return cls(
            defaults=defaults,
            file_reader=file_reader,
            file_writer=file_writer,
            system_executor=system_executor,
        )

    def __init__(
        self,
        defaults: Defaults,
        file_reader: FileReader,
        file_writer: FileWriter,
        system_executor: SystemExecutor,
    ) -> None:
        super().__init__()

        self.defaults = defaults
        self.file_reader = file_reader
        self.file_writer = file_writer
        self.system_executor = system_executor

    def get_defaults(self) -> Defaults:
        return self.defaults

    def get_file_reader(self) -> FileReader:
        return self.file_reader

    def get_file_writer(self) -> FileWriter:
        return self.file_writer

    def get_system_executor(self) -> SystemExecutor:
        return self.system_executor
