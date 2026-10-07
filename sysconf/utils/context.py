# pyright: strict

from sysconf.system.executor import SystemExecutor
from sysconf.system.file import FileReader, FileWriter
from sysconf.system.path_service import PathService


class Context:
    """Provide the collaborators commands use to interact with the system."""

    def __init__(
        self,
        file_reader: FileReader,
        file_writer: FileWriter,
        path_service: PathService,
        system_executor: SystemExecutor,
    ) -> None:
        self.file_reader = file_reader
        self.file_writer = file_writer
        self.path_service = path_service
        self.system_executor = system_executor

    def get_file_reader(self) -> FileReader:
        return self.file_reader

    def get_file_writer(self) -> FileWriter:
        return self.file_writer

    def get_path_service(self) -> PathService:
        return self.path_service

    def get_system_executor(self) -> SystemExecutor:
        return self.system_executor
