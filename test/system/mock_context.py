# pyright: strict

from sysconf.system.context import Context
from test.system.mock_file import MockFileReader, MockFileWriter
from test.system.mock_path_service import MockPathService
from test.system.mock_system_executor import MockSystemExecutor


def mock_context() -> Context:
    """Create a context where each collaborator is a fresh mock."""

    file_reader = MockFileReader({})
    file_writer = MockFileWriter()
    path_service = MockPathService()
    system_executor = MockSystemExecutor()

    return Context(
        file_reader=file_reader,
        file_writer=file_writer,
        path_service=path_service,
        system_executor=system_executor,
    )
