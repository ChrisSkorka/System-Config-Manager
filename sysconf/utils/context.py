# pyright: strict

from sysconf.system.executor import LiveSystemExecutor, SystemExecutor
from sysconf.system.file import FileReader, FileWriter
from sysconf.utils.defaults import Defaults


class Context:

    def get_defaults(self) -> Defaults:
        return Defaults()

    def get_file_reader(self) -> FileReader:
        return FileReader()

    def get_file_writer(self) -> FileWriter:
        return FileWriter()

    def get_system_executor(self) -> SystemExecutor:
        return LiveSystemExecutor()
