# pyright: strict

from pathlib import Path
from sysconf.config.parser import SystemConfigParser
from sysconf.config.serialization import YamlDeserializer
from sysconf.config.system_config import SystemConfig
from sysconf.system.file import FileReader


class ConfigReader:
    """Load configs from YAML files with a fixed file reader."""

    def __init__(self, file_reader: FileReader) -> None:
        self.file_reader = file_reader

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ConfigReader):
            return False

        return self.file_reader == value.file_reader

    def load(self, path: Path) -> SystemConfig:
        """
        Load a SystemConfig from a YAML file.

        Utility to:
        - Read the file
        - Deserialize the YAML content
        - Parse the data into a SystemConfig object

        Args:
            path (Path): Path to the YAML configuration file.
        Returns:
            SystemConfig: The parsed system configuration.
        """

        yaml_data = YamlDeserializer() \
            .get_data_from_file(self.file_reader, path)
        parser = SystemConfigParser.get_parser(yaml_data)
        system_config = parser.parse_data(yaml_data)
        return system_config

    def load_or_default(self, path: Path) -> SystemConfig:
        """
        Load the config from the file, empty when there is no file.

        Raises:
            ValidationError: If the config is invalid.
        """

        if not path.exists():
            return SystemConfig.create_from_entries((), (), (), ())

        return self.load(path)
