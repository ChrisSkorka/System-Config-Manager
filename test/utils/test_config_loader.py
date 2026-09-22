# pyright: strict

from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent

from sysconf.config.system_config import SystemConfig
from sysconf.system.file import FileReader
from sysconf.utils.config_loader import load_config_from_file
from test.datasets import datasets
from test.test_case import TestCase
from test.utils.mock_file import MockFileReader


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
        # Act
        result = load_config_from_file(dataset.input_file_reader, dataset.input_path)

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
            expected_exception=Exception,
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
            expected_exception=Exception,
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
            expected_exception=Exception,
        ),
        'missing file': ErrorCaseDataset(
            input_file_reader=MockFileReader({}),
            input_path=Path('/tmp/missing.yaml'),
            expected_exception=KeyError,
        ),
    })
    def test_load_config_raises_on_error(self, dataset: ErrorCaseDataset) -> None:
        """Test that load_config_from_file raises appropriate exceptions."""
        # Act & Assert
        with self.assertRaises(dataset.expected_exception):
            load_config_from_file(dataset.input_file_reader, dataset.input_path)
