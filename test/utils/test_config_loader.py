# pyright: strict

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

from sysconf.config.actions import ShellAction
from sysconf.config.system_config import SystemConfig
from sysconf.system.file import FileReader
from sysconf.utils.config_loader import ConfigReader
from sysconf.utils.validation import ValidationError
from test.datasets import datasets
from test.test_case import TestCase
from test.utils.mock_file import MockFileReader
from test.utils.mock_path import MockPath, fpath


class TestLoadConfigFromFile(TestCase):

    @dataclass
    class LoadConfigDataset:
        input_file_reader: FileReader
        input_path: Path

    @datasets({
        'minimal valid config': LoadConfigDataset(
            input_file_reader=MockFileReader({
                '/tmp/config.yaml': dedent('''\
                    version: "1"
                    config: []
                    domains: {}
                    ''').strip(),
            }),
            input_path=Path('/tmp/config.yaml'),
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
            input_path=Path('/tmp/config.yaml'),
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
            input_path=Path('/tmp/config.yaml'),
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
            input_path=Path('/tmp/config.yaml'),
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
            input_path=Path('/tmp/config.yaml'),
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
            input_path=Path('/tmp/config.yaml'),
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
            input_path=Path('/tmp/config.yaml'),
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
            input_path=Path('/tmp/config.yaml'),
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
            input_path=Path('config.yaml'),
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
            input_path=Path('~/.config/config.yaml'),
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
            input_path=Path('/tmp/test.yaml'),
        ),
    })
    def test_load_config_returns_system_config(self, dataset: LoadConfigDataset) -> None:
        """Test that load_config_from_file returns a SystemConfig object."""
        # Arrange
        config_reader = ConfigReader(dataset.input_file_reader)

        # Act
        result = config_reader.load(dataset.input_path)

        # Assert
        self.assertIsInstance(result, SystemConfig)

    @dataclass
    class ErrorCaseDataset:
        input_file_reader: FileReader
        input_path: Path
        expected_exception: type[Exception]

    @datasets({
        'invalid YAML': ErrorCaseDataset(
            input_file_reader=MockFileReader({
                '/tmp/invalid.yaml': dedent('''\
                    version: "1"
                      invalid: yaml: content:
                    ''').strip(),
            }),
            input_path=Path('/tmp/invalid.yaml'),
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
            input_path=Path('/tmp/unknown_domain.yaml'),
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
            input_path=Path('/tmp/no_version.yaml'),
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
            input_path=Path('/tmp/bad_version.yaml'),
            expected_exception=ValidationError,
        ),
        'missing file': ErrorCaseDataset(
            input_file_reader=MockFileReader({}),
            input_path=Path('/tmp/missing.yaml'),
            expected_exception=KeyError,
        ),
    })
    def test_load_config_raises_on_error(self, dataset: ErrorCaseDataset) -> None:
        """Test that load_config_from_file raises appropriate exceptions."""
        # Arrange
        config_reader = ConfigReader(dataset.input_file_reader)

        # Act & Assert
        with self.assertRaises(dataset.expected_exception):
            config_reader.load(dataset.input_path)


CONFIG_YAML = dedent('''\
    version: "1"
    before:
      - echo before
    config: []
    ''')
CONFIG = SystemConfig.create_from_entries(
    (ShellAction('echo before'),),
    (),
    (),
    (),
)
EMPTY_CONFIG = SystemConfig.create_from_entries((), (), (), ())


class TestConfigReader(TestCase):
    """Test loading configs with a fixed file reader."""

    @dataclass
    class LoadDataset:
        fixture_files: dict[str, str]
        input_path: Path
        expected: SystemConfig

    @datasets({
        'valid config': LoadDataset(
            fixture_files={'/config/config.yaml': CONFIG_YAML},
            input_path=fpath('/config/config.yaml'),
            expected=CONFIG,
        ),
    })
    def test_load_returns(self, dataset: LoadDataset) -> None:
        """Test that the config file is read and parsed."""

        # Arrange
        file_reader = MockFileReader(dataset.fixture_files)
        config_reader = ConfigReader(file_reader)

        # Act
        actual = config_reader.load(dataset.input_path)

        # Assert
        self.assertEqual(dataset.expected, actual)

    @dataclass
    class LoadErrorDataset:
        fixture_files: dict[str, str]
        input_path: Path
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
            input_path=fpath('/config/config.yaml'),
            expected_exception_message='Undefined domain: not-a-domain',
        ),
    })
    def test_load_raises(self, dataset: LoadErrorDataset) -> None:
        """Test that an invalid config is rejected."""

        # Arrange
        file_reader = MockFileReader(dataset.fixture_files)
        config_reader = ConfigReader(file_reader)

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
        input_path: Path
        expected: SystemConfig

    @datasets({
        'file exists': LoadOrDefaultDataset(
            fixture_files={'/config/current.yaml': CONFIG_YAML},
            input_path=fpath('/config/current.yaml'),
            expected=CONFIG,
        ),
        'file does not exist': LoadOrDefaultDataset(
            fixture_files={},
            input_path=MockPath('/config/current.yaml'),
            expected=EMPTY_CONFIG,
        ),
    })
    def test_load_or_default(self, dataset: LoadOrDefaultDataset) -> None:
        """Test that a missing config file loads as an empty config."""

        # Arrange
        file_reader = MockFileReader(dataset.fixture_files)
        config_reader = ConfigReader(file_reader)

        # Act
        actual = config_reader.load_or_default(dataset.input_path)

        # Assert
        self.assertEqual(dataset.expected, actual)
