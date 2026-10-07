# pyright: strict

from pathlib import PurePath

from sysconf.config.parser import SystemConfigRenderer
from sysconf.config.serialization import YamlSerializer
from sysconf.config.system_config import SystemConfig
from sysconf.system.file import FileWriter
from sysconf.utils.config_writer import ConfigWriter
from test.utils.mock_file import MockFileWriter


class MockConfigWriter (ConfigWriter):
    """Record each config and path written instead of writing a file."""

    @classmethod
    def create(cls) -> 'MockConfigWriter':
        system_config_renderer = SystemConfigRenderer()
        yaml_serializer = YamlSerializer()
        file_writer = MockFileWriter()

        return cls(
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
            file_writer=file_writer,
        )

    def __init__(
        self,
        system_config_renderer: SystemConfigRenderer,
        yaml_serializer: YamlSerializer,
        file_writer: FileWriter,
    ) -> None:
        super().__init__(
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
            file_writer=file_writer,
        )

        self.written: list[tuple[SystemConfig, PurePath]] = []

    def write(self, config: SystemConfig, path: PurePath) -> None:
        self.written.append((config, path))
