# pyright: strict

from pathlib import PurePath

from sysconf.config.parser import SystemConfigRenderer
from sysconf.config.serialization import YamlSerializer
from sysconf.config.system_config import SystemConfig
from sysconf.system.file import FileWriter


class ConfigWriter:
    """
    Write the system configuration to file.
    """

    def __init__(
        self,
        system_config_renderer: SystemConfigRenderer,
        yaml_serializer: YamlSerializer,
        file_writer: FileWriter,
    ) -> None:
        self.system_config_renderer = system_config_renderer
        self.yaml_serializer = yaml_serializer
        self.file_writer = file_writer

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ConfigWriter):
            return False

        return (
            self.system_config_renderer == value.system_config_renderer
            and self.yaml_serializer == value.yaml_serializer
            and self.file_writer == value.file_writer
        )

    def write(self, config: SystemConfig, path: PurePath) -> None:
        """
        Write the system configuration to file.

        The changes have already been applied by the time this is called, so
        if the write fails the configuration is printed for the user to save
        instead of raising.

        Args:
            config (SystemConfig): The configuration to be written to file.
        """

        config_data = self.system_config_renderer.render_config(
            config,
        )
        yaml_string = self.yaml_serializer.get_serialized_data(
            config_data,
        )
        self.file_writer.write_file_contents(
            path,
            yaml_string,
        )
