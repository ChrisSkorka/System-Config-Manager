# pyright: strict

from pathlib import PurePath

from sysconf.system.file import FileReader, FileWriter
from sysconf.system.path_service import PathService
from sysconf.utils.validation import validate
from sysconf.storage.defaults import Defaults


class ConfigLocationReader:
    """
    Resolve where the user's to be read configuration lives.

    The location is recorded at the config location path, which is either:
    - a file whose contents are the path to the configuration file,
    - a directory holding the configuration itself.
    """

    def __init__(
        self,
        defaults: Defaults,
        file_reader: FileReader,
        path_service: PathService,
    ) -> None:
        self.defaults = defaults
        self.file_reader = file_reader
        self.path_service = path_service

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ConfigLocationReader):
            return False

        return (
            self.defaults == value.defaults
            and self.file_reader == value.file_reader
            and self.path_service == value.path_service
        )

    def get_config_path(self) -> PurePath:
        """
        Get the path of the configuration recorded at the config location.

        Returns:
            PurePath: The path of the recorded configuration.
        """

        location_path = self.defaults.get_config_location_path()

        if self.path_service.is_dir(location_path):
            return self.defaults.get_new_config_path()

        is_location_file = self.path_service.is_file(location_path)
        validate(
            is_location_file,
            f'No config location recorded at {location_path}, \n'
            + ConfigLocationReader.get_init_message(),
        )

        recorded_path = self.file_reader \
            .get_file_contents(location_path) \
            .strip()

        validate(
            bool(recorded_path),
            f'The config location {location_path} is empty, \n'
            + ConfigLocationReader.get_init_message(),
        )

        config_path = PurePath(recorded_path)

        return self.path_service.expand_user(config_path)

    @staticmethod
    def get_init_message() -> str:
        """
        Get the message to show the user when the config location cannot be resolved.
        """

        # todo: when `sysconf init` is implemented, update this message
        return 'run `sysconf apply <path/to/config.yaml>` for an initial sync ' \
            + 'and to record where your configuration lives'


class ConfigLocationWriter:
    """
    Record where the user's source of truth configuration lives, so that later
    invocations can find it again without being given the path.
    """

    def __init__(
        self,
        defaults: Defaults,
        file_reader: FileReader,
        file_writer: FileWriter,
        path_service: PathService,
    ) -> None:
        self.defaults = defaults
        self.file_reader = file_reader
        self.file_writer = file_writer
        self.path_service = path_service

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, ConfigLocationWriter):
            return False

        return (
            self.defaults == value.defaults
            and self.file_reader == value.file_reader
            and self.file_writer == value.file_writer
            and self.path_service == value.path_service
        )

    def record_config_path(self, argument_path: PurePath) -> bool:
        """
        Record the given path as the config location, unless the location is a
        directory holding the configuration itself.

        Args:
            argument_path (PurePath): The path given on the command line.
        Returns:
            bool: True if the config path was recorded, False otherwise.
        """

        location_path = self.defaults.get_config_location_path()

        if self.path_service.is_dir(location_path):
            return False

        expanded_path = self.path_service.expand_user(argument_path)
        absolute_path = self.path_service.resolve(expanded_path)

        if self.path_service.is_file(location_path):
            recorded_path = self.file_reader \
                .get_file_contents(location_path) \
                .strip()

            if recorded_path == str(absolute_path):
                return False

        self.file_writer.write_file_contents(
            location_path,
            f'{absolute_path}\n',
        )

        return True
