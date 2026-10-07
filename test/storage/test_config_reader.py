# pyright: strict

from dataclasses import dataclass
from pathlib import PurePath
from textwrap import dedent

from sysconf.config.actions import ShellAction
from sysconf.config.system_config import SystemConfig
from sysconf.storage.config_reader import ConfigReader
from sysconf.system.file import FileReader
from sysconf.utils.validation import ValidationError
from test.datasets import datasets
from test.system.mock_file import MockFileReader
from test.system.mock_path_service import MockPathService
from test.test_case import TestCase


class TestLoadConfigFromFile(TestCase):

    @dataclass
    class LoadConfigDataset:
        input_file_reader: FileReader
        input_path: PurePath

    @datasets({
        'minimal valid config': LoadConfigDataset(
            input_file_reader=MockFileReader({
                '/tmp/config.yaml': dedent('''\
                    version: "1"
                    config: []
                    domains: {}
                    ''').strip(),
            }),
            input_path=PurePath('/tmp/config.yaml'),
        ),
        'all components empty': LoadConfigDataset(
            input_file_reader=MockFileReader({
                '/tmp/config.yaml': dedent('''\
                    version: "1"
                    before: []
                    after: []
                    config: []
                    domains: {}
                    ''').strip(),
            }),
            input_path=PurePath('/tmp/config.yaml'),
        ),
        'config with builtin domain entries': LoadConfigDataset(
            input_file_reader=MockFileReader({
                '/tmp/config.yaml': dedent('''\
                    version: "1"
                    before: []
                    after: []
                    config:
                      - apt:
                          - git
                          - vim
                    domains: {}
                    ''').strip(),
            }),
            input_path=PurePath('/tmp/config.yaml'),
        ),
        'config with before and after actions': LoadConfigDataset(
            input_file_reader=MockFileReader({
                '/tmp/config.yaml': dedent('''\
                    version: "1"
                    before:
                      - "echo before"
                    after:
                      - "echo after"
                    config: []
                    domains: {}
                    ''').strip(),
            }),
            input_path=PurePath('/tmp/config.yaml'),
        ),
        'config with user domains': LoadConfigDataset(
            input_file_reader=MockFileReader({
                '/tmp/config.yaml': dedent('''\
                    version: "1"
                    before: []
                    after: []
                    config: []
                    domains:
                      custom:
                        type: list
                        add: echo $value
                        remove: echo $value
                    ''').strip(),
            }),
            input_path=PurePath('/tmp/config.yaml'),
        ),
        'config with map domain': LoadConfigDataset(
            input_file_reader=MockFileReader({
                '/tmp/config.yaml': dedent('''\
                    version: "1"
                    before: []
                    after: []
                    config: []
                    domains:
                      custom:
                        type: map
                        add: echo add
                        update: echo update
                        remove: echo remove
                    ''').strip(),
            }),
            input_path=PurePath('/tmp/config.yaml'),
        ),
        'config with multiple domain entries': LoadConfigDataset(
            input_file_reader=MockFileReader({
                '/tmp/config.yaml': dedent('''\
                    version: "1"
                    before: []
                    after: []
                    config:
                    - apt:
                        - git
                        - vim
                    - snap:
                        - spotify
                    domains:
                    custom_domain:
                        type: map
                        add: echo add
                        update: echo update
                        remove: echo remove
                    ''').strip(),
            }),
            input_path=PurePath('/tmp/config.yaml'),
        ),
        'config with $pwd': LoadConfigDataset(
            input_file_reader=MockFileReader({
                '/tmp/config.yaml': dedent('''\
                    version: "1"
                    before: []
                    after: []
                    config:
                    - symlinks:
                        "/home/user/link": "$pwd/target"
                    domains: {}
                    ''').strip(),
            }),
            input_path=PurePath('/tmp/config.yaml'),
        ),
        'relative paths': LoadConfigDataset(
            input_file_reader=MockFileReader({
                'config.yaml': dedent('''\
                    version: "1"
                    before: []
                    after: []
                    config: []
                    domains: {}
                    ''').strip(),
            }),
            input_path=PurePath('config.yaml'),
        ),
        'home directory expansion': LoadConfigDataset(
            input_file_reader=MockFileReader({
                '~/.config/config.yaml': dedent('''\
                    version: "1"
                    before: []
                    after: []
                    config: []
                    domains: {}
                    ''').strip(),
            }),
            input_path=PurePath('~/.config/config.yaml'),
        ),
        'file reader path verification': LoadConfigDataset(
            input_file_reader=MockFileReader({
                '/tmp/test.yaml': dedent('''\
                    version: "1"
                    before: []
                    after: []
                    config: []
                    domains: {}
                    ''').strip(),
            }),
            input_path=PurePath('/tmp/test.yaml'),
        ),
    })
    def test_load_config_returns_system_config(self, dataset: LoadConfigDataset) -> None:
        """Test that load_config_from_file returns a SystemConfig object."""
        # Arrange
        path_service = MockPathService()
        config_reader = ConfigReader(dataset.input_file_reader, path_service)

        # Act
        result = config_reader.load(dataset.input_path)

        # Assert
        self.assertIsInstance(result, SystemConfig)

    @dataclass
    class ErrorCaseDataset:
        input_file_reader: FileReader
        input_path: PurePath
        expected_exception: type[Exception]

    @datasets({
        'invalid YAML': ErrorCaseDataset(
            input_file_reader=MockFileReader({
                '/tmp/invalid.yaml': dedent('''\
                    version: "1"
                      invalid: yaml: content:
                    ''').strip(),
            }),
            input_path=PurePath('/tmp/invalid.yaml'),
            expected_exception=ValidationError,
        ),
        'unknown domain': ErrorCaseDataset(
            input_file_reader=MockFileReader({
                '/tmp/unknown_domain.yaml': dedent('''\
                    version: "1"
                    config:
                      - not-a-domain:
                          - git
                    ''').strip(),
            }),
            input_path=PurePath('/tmp/unknown_domain.yaml'),
            expected_exception=ValidationError,
        ),
        'missing version': ErrorCaseDataset(
            input_file_reader=MockFileReader({
                '/tmp/no_version.yaml': dedent('''\
                    before: []
                    after: []
                    domains: {}
                    ''').strip(),
            }),
            input_path=PurePath('/tmp/no_version.yaml'),
            expected_exception=ValidationError,
        ),
        'invalid version': ErrorCaseDataset(
            input_file_reader=MockFileReader({
                '/tmp/bad_version.yaml': dedent('''\
                    version: "99"
                    before: []
                    after: []
                    domains: {}
                    ''').strip(),
            }),
            input_path=PurePath('/tmp/bad_version.yaml'),
            expected_exception=ValidationError,
        ),
        'missing file': ErrorCaseDataset(
            input_file_reader=MockFileReader({}),
            input_path=PurePath('/tmp/missing.yaml'),
            expected_exception=KeyError,
        ),
    })
    def test_load_config_raises_on_error(self, dataset: ErrorCaseDataset) -> None:
        """Test that load_config_from_file raises appropriate exceptions."""
        # Arrange
        path_service = MockPathService()
        config_reader = ConfigReader(dataset.input_file_reader, path_service)

        # Act & Assert
        with self.assertRaises(dataset.expected_exception):
            config_reader.load(dataset.input_path)


class TestConfigReader(TestCase):
    """Test loading configs with a fixed file reader."""

    @dataclass
    class LoadDataset:
        fixture_files: dict[str, str]
        input_path: PurePath
        expected: SystemConfig

    @datasets({
        'valid config': LoadDataset(
            fixture_files={
                '/config/config.yaml': dedent('''\
                    version: "1"
                    before:
                      - echo before
                    config: []
                    '''),
            },
            input_path=PurePath('/config/config.yaml'),
            expected=SystemConfig.create_from_entries(
                (ShellAction('echo before'),),
                (),
                (),
                (),
            ),
        ),
    })
    def test_load_returns(self, dataset: LoadDataset) -> None:
        """Test that the config file is read and parsed."""

        # Arrange
        file_reader = MockFileReader(dataset.fixture_files)
        fixture_paths = dataset.fixture_files.keys()
        path_service = MockPathService(files=fixture_paths)
        config_reader = ConfigReader(file_reader, path_service)

        # Act
        actual = config_reader.load(dataset.input_path)

        # Assert
        self.assertEqual(dataset.expected, actual)

    @dataclass
    class LoadErrorDataset:
        fixture_files: dict[str, str]
        input_path: PurePath
        expected_exception_message: str

    @datasets({
        'unknown domain': LoadErrorDataset(
            fixture_files={
                '/config/config.yaml': dedent('''\
                    version: "1"
                    config:
                      - not-a-domain:
                          - git
                    '''),
            },
            input_path=PurePath('/config/config.yaml'),
            expected_exception_message='Undefined domain: not-a-domain',
        ),
    })
    def test_load_raises(self, dataset: LoadErrorDataset) -> None:
        """Test that an invalid config is rejected."""

        # Arrange
        file_reader = MockFileReader(dataset.fixture_files)
        fixture_paths = dataset.fixture_files.keys()
        path_service = MockPathService(files=fixture_paths)
        config_reader = ConfigReader(file_reader, path_service)

        # Act & Assert
        with self.assertRaises(ValidationError) as context:
            config_reader.load(dataset.input_path)

        self.assertEqual(
            str(context.exception),
            dataset.expected_exception_message,
        )

    @dataclass
    class LoadOrDefaultDataset:
        fixture_files: dict[str, str]
        input_path: PurePath
        expected: SystemConfig

    @datasets({
        'file exists': LoadOrDefaultDataset(
            fixture_files={
                '/config/current.yaml': dedent('''\
                    version: "1"
                    before:
                      - echo before
                    config: []
                    '''),
            },
            input_path=PurePath('/config/current.yaml'),
            expected=SystemConfig.create_from_entries(
                (ShellAction('echo before'),),
                (),
                (),
                (),
            ),
        ),
        'file does not exist': LoadOrDefaultDataset(
            fixture_files={},
            input_path=PurePath('/config/current.yaml'),
            expected=SystemConfig.create_from_entries((), (), (), ()),
        ),
    })
    def test_load_or_default(self, dataset: LoadOrDefaultDataset) -> None:
        """Test that a missing config file loads as an empty config."""

        # Arrange
        file_reader = MockFileReader(dataset.fixture_files)
        fixture_paths = dataset.fixture_files.keys()
        path_service = MockPathService(files=fixture_paths)
        config_reader = ConfigReader(file_reader, path_service)

        # Act
        actual = config_reader.load_or_default(dataset.input_path)

        # Assert
        self.assertEqual(dataset.expected, actual)
