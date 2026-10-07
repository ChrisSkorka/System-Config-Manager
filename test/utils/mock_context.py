# pyright: strict

from sysconf.utils.context import Context
from test.system.mock_path_service import MockPathService
from test.system.mock_system_executor import MockSystemExecutor
from test.utils.mock_defaults import MockDefaults
from test.utils.mock_file import MockFileReader, MockFileWriter


def mock_context() -> Context:
    """Create a context where each collaborator is a fresh mock."""

    defaults = MockDefaults()
    file_reader = MockFileReader({})
    file_writer = MockFileWriter()
    path_service = MockPathService()
    system_executor = MockSystemExecutor()

    return Context(
        defaults=defaults,
        file_reader=file_reader,
        file_writer=file_writer,
        path_service=path_service,
        system_executor=system_executor,
    )
