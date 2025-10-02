from pathlib import Path
from sysconf.config.parser import SystemConfigParser
from sysconf.config.serialization import YamlDeserializer
from sysconf.config.system_config import SystemConfig


def load_config_from_file(path: Path) -> SystemConfig:
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

    yaml_data = YamlDeserializer().get_data_from_file(path)
    parser = SystemConfigParser.get_parser(yaml_data)
    system_config = parser.parse_data(yaml_data)
    return system_config