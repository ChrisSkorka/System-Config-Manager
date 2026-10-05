# pyright: strict

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, call, patch

from sysconf.commands.comparative_config_command_parser import ComparativeConfigCommandParser
from sysconf.commands.preview_command import PreviewCommand
from sysconf.config.system_config import SystemConfig, SystemManager
from sysconf.system.error_handler import FailingErrorHandler
from sysconf.system.executor import PreviewSystemExecutor
from sysconf.system.file import FileReader
from sysconf.utils.config_loader import ConfigReader
from test.datasets import datasets
from test.domains.mock_domain_action import MockDomainAction
from test.system.mock_system_manager import MockSystemManager
from test.test_case import TestCase
from test.utils.mock_context import MockContext
from test.utils.mock_defaults import MockDefaults
from test.utils.mock_file import MockFileReader, MockFileWriter
from test.utils.mock_path import MockPath, fpath


FILE_READER = FileReader()

OLD_CONFIG_YAML = dedent('''
    version: "1"
    config: []
''').lstrip()
NEW_CONFIG_YAML = dedent('''
    version: "1"
    config:
      - apt:
          - git
''').lstrip()
EMPTY_CONFIG = SystemConfig.create_from_entries((), (), (), ())
CONFIG_READER = ConfigReader(
    MockFileReader({
        '/old.yaml': OLD_CONFIG_YAML,
        '/new.yaml': NEW_CONFIG_YAML,
    }),
)
OLD_CONFIG = CONFIG_READER.load(Path('/old.yaml'))
NEW_CONFIG = CONFIG_READER.load(Path('/new.yaml'))


class TestPreviewCommand(TestCase):

    def test_get_name(self) -> None:
        """Test that get_name returns the correct command name."""

        # Arrange (no setup required)

        # Act
        result = PreviewCommand.get_name()

        # Assert
        self.assertIsInstance(result, str)

    def test_get_subparser(self) -> None:
        """Test that get_subparser creates a subparser correctly."""

        # Arrange
        parser = ArgumentParser()
        subparsers = parser.add_subparsers()

        # Act
        actual = PreviewCommand.get_subparser(subparsers)

        # Assert
        self.assertIsInstance(actual, ArgumentParser)

        help_text = actual.format_help()
        self.assertIn('not execute', help_text)

    def test_add_arguments(self) -> None:
        """Test that add_arguments adds the expected arguments to the parser."""

        # Arrange
        parser = ArgumentParser()

        # Act
        result_parser = PreviewCommand.add_arguments(parser)

        # Assert
        self.assertIs(result_parser, parser)

        # Test that we can parse arguments (this validates the arguments were added)
        args = parser.parse_args(['test.yaml', '--last-config', 'old.yaml'])
        self.assertEqual(args.config_file, Path('test.yaml'))
        self.assertEqual(args.last_config, Path('old.yaml'))

    @dataclass
    class CreateFromArgumentsDataset:
        fixture_comparative_parser: ComparativeConfigCommandParser
        input_parsed_arguments: Namespace
        expected_old_path: Path
        expected_new_path: Path

    @datasets({
        'both paths provided': CreateFromArgumentsDataset(
            fixture_comparative_parser=ComparativeConfigCommandParser(
                old_path=fpath('/manual/old.yaml'),
                new_path=fpath('/manual/new.yaml'),
                file_reader=FILE_READER,
            ),
            input_parsed_arguments=Namespace(
                config_file=fpath('/manual/new.yaml'),
                last_config=fpath('/manual/old.yaml'),
            ),
            expected_old_path=fpath('/manual/old.yaml'),
            expected_new_path=fpath('/manual/new.yaml'),
        ),
        'no old config': CreateFromArgumentsDataset(
            fixture_comparative_parser=ComparativeConfigCommandParser(
                old_path=MockPath('/default/old.yaml'),
                new_path=fpath('/default/new.yaml'),
                file_reader=FILE_READER,
            ),
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_old_path=MockPath('/default/old.yaml'),
            expected_new_path=fpath('/default/new.yaml'),
        ),
    })
    @patch('sysconf.commands.preview_command.PreviewCommand.create_from_context')
    @patch('sysconf.commands.comparative_config_command_parser.ComparativeConfigCommandParser.create_from_arguments')
    def test_create_from_arguments(
        self,
        dataset: CreateFromArgumentsDataset,
        mock_create_from_arguments: MagicMock,
        mock_create_from_context: MagicMock,
    ) -> None:
        """Test that the parsed paths are passed on to create_from_context."""

        # Arrange
        mock_create_from_arguments.return_value = dataset.fixture_comparative_parser
        context = MockContext.create()

        # Act
        actual = PreviewCommand.create_from_arguments(
            context=context,
            parsed_arguments=dataset.input_parsed_arguments,
        )

        # Assert
        self.assertIs(actual, mock_create_from_context.return_value)
        mock_create_from_arguments.assert_called_once_with(
            context=context,
            parsed_arguments=dataset.input_parsed_arguments,
        )
        mock_create_from_context.assert_called_once_with(
            context=context,
            old_path=dataset.expected_old_path,
            new_path=dataset.expected_new_path,
        )

    @dataclass
    class CreateFromContextDataset:
        fixture_files: dict[str, str]
        input_old_path: Path
        input_new_path: Path
        expected_old_config: SystemConfig
        expected_new_config: SystemConfig

    @datasets({
        'old config exists': CreateFromContextDataset(
            fixture_files={
                '/manual/old.yaml': OLD_CONFIG_YAML,
                '/manual/new.yaml': NEW_CONFIG_YAML,
            },
            input_old_path=fpath('/manual/old.yaml'),
            input_new_path=fpath('/manual/new.yaml'),
            expected_old_config=OLD_CONFIG,
            expected_new_config=NEW_CONFIG,
        ),
        'no old config': CreateFromContextDataset(
            fixture_files={
                '/manual/new.yaml': NEW_CONFIG_YAML,
            },
            input_old_path=MockPath('/manual/old.yaml'),
            input_new_path=fpath('/manual/new.yaml'),
            expected_old_config=EMPTY_CONFIG,
            expected_new_config=NEW_CONFIG,
        ),
    })
    def test_create_from_context(self, dataset: CreateFromContextDataset) -> None:
        """Test that the configs are loaded into a manager that only previews."""

        # Arrange
        defaults = MockDefaults(
            old_config_path=MockPath('/config/.history/current.yaml'),
        )
        file_reader = MockFileReader(dataset.fixture_files)
        file_writer = MockFileWriter()
        context = MockContext.create(
            defaults=defaults,
            file_reader=file_reader,
            file_writer=file_writer,
        )
        executor = PreviewSystemExecutor()
        error_handler = FailingErrorHandler()
        expected_manager = SystemManager(
            old_config=dataset.expected_old_config,
            new_config=dataset.expected_new_config,
            executor=executor,
            error_handler=error_handler,
        )

        # Act
        actual = PreviewCommand.create_from_context(
            context=context,
            old_path=dataset.input_old_path,
            new_path=dataset.input_new_path,
        )

        # Assert
        self.assertEqual(expected_manager, actual.manager)
        self.assertIsInstance(actual.manager.executor, PreviewSystemExecutor)
        self.assertIsInstance(
            actual.manager.error_handler,
            FailingErrorHandler,
        )
        self.assertEqual(defaults.get_old_config_path(), actual.current_path)
        self.assertIs(file_writer, actual.file_writer)

    @dataclass
    class RunDataset:
        fixture_system_manager: MockSystemManager[None]
        expected_prints: list[str]

    @datasets({
        'no changes required': RunDataset(
            fixture_system_manager=MockSystemManager[None]
            .default(get_actions=[]),
            expected_prints=['# No changes required.'],
        ),
        'gsettings add and update': RunDataset(
            fixture_system_manager=MockSystemManager[None].default(get_actions=[
                MockDomainAction(
                    'Update gsettings: theme = old_value -> new_value'),
                MockDomainAction('Add gsettings: font-size = 12'),
            ]),
            expected_prints=[
                '# Update gsettings: theme = old_value -> new_value',
                '# Add gsettings: font-size = 12',
            ],
        ),
        'gsettings remove': RunDataset(
            fixture_system_manager=MockSystemManager[None].default(get_actions=[
                MockDomainAction('Remove gsettings: font-size'),
            ]),
            expected_prints=[
                '# Remove gsettings: font-size',
            ],
        ),
        'dconf add and remove': RunDataset(
            fixture_system_manager=MockSystemManager[None].default(get_actions=[
                MockDomainAction('Remove dconf: /path/to/key2'),
                MockDomainAction(
                    'Update dconf: /path/to/key1 = old_value -> new_value'),
                MockDomainAction('Add dconf: /path/to/key3 = new_value3'),
            ]),
            expected_prints=[
                '# Remove dconf: /path/to/key2',
                '# Update dconf: /path/to/key1 = old_value -> new_value',
                '# Add dconf: /path/to/key3 = new_value3',
            ],
        ),
        'mixed domains': RunDataset(
            fixture_system_manager=MockSystemManager[None].default(get_actions=[
                MockDomainAction(
                    'Update gsettings: theme = old_value -> new_value'),
                MockDomainAction('Add dconf: /path/to/key = dconf_value'),
            ]),
            expected_prints=[
                '# Update gsettings: theme = old_value -> new_value',
                '# Add dconf: /path/to/key = dconf_value',
            ],
        ),
    })
    def test_run(
        self,
        dataset: RunDataset,
    ) -> None:
        """Test that run executes the correct commands and produces expected output."""

        # Arrange
        preview_command = PreviewCommand(
            manager=dataset.fixture_system_manager,
            system_config_renderer=MagicMock(),
            yaml_serializer=MagicMock(),
            current_path=MockPath(
                '/tmp/current.yaml',
                is_file=False,
                exists=False,
            ),
            file_writer=MagicMock(),
        )

        # Act
        with patch('builtins.print') as mock_print:
            preview_command.run()

        # Assert
        mock_print.assert_has_calls(
            [call(p) for p in dataset.expected_prints],
            any_order=False,
        )
