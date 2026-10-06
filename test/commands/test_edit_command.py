# pyright: strict

import shutil
import sys

from argparse import ArgumentParser, Namespace
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from textwrap import dedent
from unittest.mock import call, patch

from sysconf.commands.apply_command import ApplyCommand, ApplyFailureResolution
from sysconf.commands.command import Command
from sysconf.commands.edit_command import EditCommand
from sysconf.commands.preview_command import PreviewCommand
from sysconf.config.actions import ShellAction
from sysconf.config.parser import SystemConfigRenderer
from sysconf.config.serialization import YamlSerializer
from sysconf.config.settings import ToolSettings
from sysconf.config.system_config import RunActionsResult, SystemConfig
from sysconf.system.editor import EditResult, EditorLauncher, EditorResolver
from sysconf.system.file import FileReader
from sysconf.utils.config_loader import ConfigReader
from sysconf.utils.config_location import ConfigLocationWriter
from sysconf.utils.validation import ValidationError
from test.datasets import datasets
from test.system.mock_editor import MockEditorLauncher, MockWhich
from test.system.mock_system_executor import MockRaisingSystemExecutor, MockSystemExecutor
from test.system.mock_system_manager import MockSystemManager
from test.test_case import TestCase
from test.utils.mock_config_writer import MockConfigWriter
from test.utils.mock_context import MockContext
from test.utils.mock_defaults import MockDefaults
from test.utils.mock_file import MockFileReader, MockFileWriter
from test.utils.mock_path import MockPath, dpath, fpath


OLD_PATH = fpath('/config/.history/current.yaml')
NEW_PATH = fpath('/manual/config.yaml')

PATHS_BY_NAME = {
    'code': '/usr/bin/code',
    'nano': '/usr/bin/nano',
}
CODE = ('/usr/bin/code', '--wait')
NANO = ('/usr/bin/nano',)

CODE_SETTINGS = ToolSettings(editor='code --wait')
NANO_SETTINGS = ToolSettings(editor='nano')
EMPTY_CONFIG = SystemConfig.create_from_entries((), (), (), ())
OLD_CONFIG = SystemConfig.create_from_entries(
    (ShellAction('echo old'),), (), (), (), CODE_SETTINGS)
NEW_CONFIG = SystemConfig.create_from_entries(
    (ShellAction('echo new'),), (), (), (), CODE_SETTINGS)
NANO_CONFIG = SystemConfig.create_from_entries(
    (ShellAction('echo old'),), (), (), (), NANO_SETTINGS)

OLD_CONFIG_YAML = dedent('''\
    version: 1
    system-config-manager:
      editor: code --wait
    before:
      - echo old
    config: []
    ''')
NEW_CONFIG_YAML = dedent('''\
    version: 1
    system-config-manager:
      editor: code --wait
    before:
      - echo new
    config: []
    ''')

FILE_READER = FileReader()
EDITOR_RESOLVER = EditorResolver('linux', MockWhich(PATHS_BY_NAME))
EDITOR_LAUNCHER = EditorLauncher(MockSystemExecutor())


class NextCommand (Enum):
    """The command a test expects `run` to return."""

    SELF = auto()
    APPLY = auto()
    NONE = auto()


class MockConfigReader (ConfigReader):
    """
    Load the configured old config, and the configured new config or raise
    the configured validation error, recording each path loaded.
    """

    @classmethod
    def create(
        cls,
        old_config: SystemConfig,
        new_config: SystemConfig | ValidationError,
    ) -> 'MockConfigReader':
        file_reader = FileReader()

        return cls(
            file_reader=file_reader,
            old_config=old_config,
            new_config=new_config,
        )

    def __init__(
        self,
        file_reader: FileReader,
        old_config: SystemConfig,
        new_config: SystemConfig | ValidationError,
    ) -> None:
        super().__init__(file_reader)

        self.old_config = old_config
        self.new_config = new_config
        self.loaded_paths: list[Path] = []

    def load(self, path: Path) -> SystemConfig:
        self.loaded_paths.append(path)

        if isinstance(self.new_config, ValidationError):
            raise self.new_config

        return self.new_config

    def load_or_default(self, path: Path) -> SystemConfig:
        self.loaded_paths.append(path)
        return self.old_config


def unexpected_edit_command_factory() -> EditCommand:
    raise AssertionError(
        'The edit command factory is not expected to be called',
    )


def unexpected_preview_command_factory() -> PreviewCommand:
    raise AssertionError(
        'The preview command factory is not expected to be called',
    )


def unexpected_apply_command_factory() -> ApplyCommand:
    raise AssertionError(
        'The apply command factory is not expected to be called',
    )


def make_apply_command() -> ApplyCommand:
    """Build an apply command for the edited config."""

    result = RunActionsResult[ApplyFailureResolution](NEW_CONFIG)
    manager = MockSystemManager[ApplyFailureResolution].default(
        result=result,
        old_config=OLD_CONFIG,
        new_config=NEW_CONFIG,
    )
    config_writer = MockConfigWriter.create()
    defaults = MockDefaults()
    file_reader = MockFileReader({})
    file_writer = MockFileWriter()
    config_location_writer = ConfigLocationWriter(
        defaults=defaults,
        file_reader=file_reader,
        file_writer=file_writer,
    )

    return ApplyCommand(
        manager=manager,
        old_path=OLD_PATH,
        new_path=NEW_PATH,
        config_writer=config_writer,
        config_location_writer=config_location_writer,
        should_override_config_path=False,
        edit_command_factory=unexpected_edit_command_factory,
    )


def make_edit_command(
    old_path: Path = OLD_PATH,
    new_path: Path = NEW_PATH,
    file_reader: FileReader = FILE_READER,
    editor_resolver: EditorResolver = EDITOR_RESOLVER,
    editor_launcher: EditorLauncher = EDITOR_LAUNCHER,
) -> EditCommand:
    """Build an edit command from shared collaborators, for equality checks."""

    config_reader = ConfigReader(file_reader)

    return EditCommand(
        config_reader=config_reader,
        old_path=old_path,
        new_path=new_path,
        editor_resolver=editor_resolver,
        editor_launcher=editor_launcher,
        preview_command_factory=unexpected_preview_command_factory,
        apply_command_factory=unexpected_apply_command_factory,
    )


class TestEditCommand(TestCase):
    """Test the edit command."""

    def test_get_name(self) -> None:
        """Test that get_name returns the correct command name."""

        # Arrange (no setup required)

        # Act
        result = EditCommand.get_name()

        # Assert
        self.assertEqual(result, 'edit')

    def test_get_subparser(self) -> None:
        """Test that get_subparser creates a subparser correctly."""

        # Arrange
        parser = ArgumentParser()
        subparsers = parser.add_subparsers()

        # Act
        actual = EditCommand.get_subparser(subparsers)

        # Assert
        self.assertEqual(actual.prog, 'sysconf edit')
        self.assertIn('Edit the configuration', parser.format_help())

    def test_add_arguments(self) -> None:
        """Test that add_arguments adds the expected arguments to the parser."""

        # Arrange
        parser = ArgumentParser()

        # Act
        result_parser = EditCommand.add_arguments(parser)

        # Assert
        self.assertIs(result_parser, parser)

        args = parser.parse_args(['test.yaml', '--last-config', 'old.yaml'])
        self.assertEqual(args.config_file, Path('test.yaml'))
        self.assertEqual(args.last_config, Path('old.yaml'))

    @dataclass
    class CreateFromArgumentsDataset:
        fixture_defaults: MockDefaults
        fixture_files: dict[str, str]
        input_parsed_arguments: Namespace
        expected_old_path: Path
        expected_new_path: Path
        expected_should_override_config_path: bool

    @datasets({
        'config file given': CreateFromArgumentsDataset(
            fixture_defaults=MockDefaults(
                old_config_path=OLD_PATH,
            ),
            fixture_files={
                '/config/.history/current.yaml': OLD_CONFIG_YAML,
                '/manual/config.yaml': NEW_CONFIG_YAML,
            },
            input_parsed_arguments=Namespace(
                config_file=NEW_PATH,
                last_config=None,
            ),
            expected_old_path=OLD_PATH,
            expected_new_path=NEW_PATH,
            expected_should_override_config_path=True,
        ),
        'config file from the config location': CreateFromArgumentsDataset(
            fixture_defaults=MockDefaults(
                old_config_path=OLD_PATH,
                new_config_path=fpath('/config/config/config.yaml'),
                config_location_path=dpath('/config/config'),
            ),
            fixture_files={
                '/config/.history/current.yaml': OLD_CONFIG_YAML,
                '/config/config/config.yaml': NEW_CONFIG_YAML,
            },
            input_parsed_arguments=Namespace(
                config_file=None,
                last_config=None,
            ),
            expected_old_path=OLD_PATH,
            expected_new_path=fpath('/config/config/config.yaml'),
            expected_should_override_config_path=False,
        ),
        'old config given': CreateFromArgumentsDataset(
            fixture_defaults=MockDefaults(
                old_config_path=MockPath('/config/.history/current.yaml'),
            ),
            fixture_files={
                '/manual/old.yaml': OLD_CONFIG_YAML,
                '/manual/config.yaml': NEW_CONFIG_YAML,
            },
            input_parsed_arguments=Namespace(
                config_file=NEW_PATH,
                last_config=fpath('/manual/old.yaml'),
            ),
            expected_old_path=fpath('/manual/old.yaml'),
            expected_new_path=NEW_PATH,
            expected_should_override_config_path=True,
        ),
    })
    def test_create_from_arguments(
        self,
        dataset: CreateFromArgumentsDataset,
    ) -> None:
        """
        Test that the command edits the resolved config with the platform's
        editor, and previews and applies it for the same paths.
        """

        # Arrange
        file_reader = MockFileReader(dataset.fixture_files)
        system_executor = MockSystemExecutor()
        context = MockContext.create(
            defaults=dataset.fixture_defaults,
            file_reader=file_reader,
            system_executor=system_executor,
        )
        config_reader = ConfigReader(file_reader)
        editor_resolver = EditorResolver(sys.platform, shutil.which)
        editor_launcher = EditorLauncher(system_executor)
        expected = EditCommand(
            config_reader=config_reader,
            old_path=dataset.expected_old_path,
            new_path=dataset.expected_new_path,
            editor_resolver=editor_resolver,
            editor_launcher=editor_launcher,
            preview_command_factory=unexpected_preview_command_factory,
            apply_command_factory=unexpected_apply_command_factory,
        )
        expected_preview_command = PreviewCommand.create_from_context(
            context=context,
            old_path=dataset.expected_old_path,
            new_path=dataset.expected_new_path,
        )
        expected_apply_command = ApplyCommand.create_from_context(
            context=context,
            old_path=dataset.expected_old_path,
            new_path=dataset.expected_new_path,
            should_override_config_path=dataset.expected_should_override_config_path,
        )

        # Act
        actual = EditCommand.create_from_arguments(
            context=context,
            parsed_arguments=dataset.input_parsed_arguments,
        )

        # Assert
        self.assertEqual(expected, actual)

        actual_preview_command = actual.preview_command_factory()
        self.assertEqual(
            expected_preview_command.manager,
            actual_preview_command.manager,
        )

        actual_apply_command = actual.apply_command_factory()
        self.assertEqual(
            expected_apply_command.manager,
            actual_apply_command.manager,
        )
        self.assertEqual(
            expected_apply_command.old_path,
            actual_apply_command.old_path,
        )
        self.assertEqual(
            expected_apply_command.new_path,
            actual_apply_command.new_path,
        )
        self.assertEqual(
            expected_apply_command.should_override_config_path,
            actual_apply_command.should_override_config_path,
        )

    @dataclass
    class RunDataset:
        fixture_new_config: SystemConfig | ValidationError
        fixture_user_inputs: tuple[str, ...]
        expected_next_command: NextCommand
        fixture_old_config: SystemConfig = field(
            default_factory=lambda: OLD_CONFIG)
        expected_editor_command: tuple[str, ...] = CODE
        expected_preview_runs: int = 0
        expected_prints: list[str] = field(default_factory=lambda: [])

    @datasets({
        'apply with y': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('y',),
            expected_next_command=NextCommand.APPLY,
            expected_prints=[
                'Apply changes:',
                '[y] Apply config',
                '[p] Preview actions',
                '[e] Edit config',
                '[n] Exit without applying',
            ],
        ),
        'apply with yes': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('yes',),
            expected_next_command=NextCommand.APPLY,
        ),
        'apply with apply': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('apply',),
            expected_next_command=NextCommand.APPLY,
        ),
        'apply with a': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('a',),
            expected_next_command=NextCommand.APPLY,
        ),
        'apply with padded uppercase y': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=(' Y ',),
            expected_next_command=NextCommand.APPLY,
        ),
        'edit with e': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('e',),
            expected_next_command=NextCommand.SELF,
        ),
        'edit with edit': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('edit',),
            expected_next_command=NextCommand.SELF,
        ),
        'exit with n': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('n',),
            expected_next_command=NextCommand.NONE,
            expected_prints=['The edited config was not applied.'],
        ),
        'exit with no': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('no',),
            expected_next_command=NextCommand.NONE,
            expected_prints=['The edited config was not applied.'],
        ),
        'exit with x': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('x',),
            expected_next_command=NextCommand.NONE,
            expected_prints=['The edited config was not applied.'],
        ),
        'exit with exit': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('exit',),
            expected_next_command=NextCommand.NONE,
            expected_prints=['The edited config was not applied.'],
        ),
        'preview with p then apply': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('p', 'y'),
            expected_next_command=NextCommand.APPLY,
            expected_preview_runs=1,
            expected_prints=['Planned actions:'],
        ),
        'preview with preview twice then exit': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('preview', 'preview', 'n'),
            expected_next_command=NextCommand.NONE,
            expected_preview_runs=2,
            expected_prints=[
                'Planned actions:',
                'The edited config was not applied.',
            ],
        ),
        'invalid choice then apply': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('z', 'y'),
            expected_next_command=NextCommand.APPLY,
            expected_prints=['Invalid choice. Please try again.'],
        ),
        'five invalid choices': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('z',) * 5,
            expected_next_command=NextCommand.NONE,
            expected_prints=['The edited config was not applied.'],
        ),
        'four invalid choices and a preview then apply': RunDataset(
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('z', 'z', 'p', 'z', 'z', 'y'),
            expected_next_command=NextCommand.APPLY,
            expected_preview_runs=1,
        ),
        'unchanged config': RunDataset(
            fixture_new_config=OLD_CONFIG,
            fixture_user_inputs=(),
            expected_next_command=NextCommand.NONE,
            expected_prints=['# No changes required.'],
        ),
        'only settings changed': RunDataset(
            fixture_new_config=NANO_CONFIG,
            fixture_user_inputs=('y',),
            expected_next_command=NextCommand.APPLY,
        ),
        'no old config': RunDataset(
            fixture_old_config=EMPTY_CONFIG,
            fixture_new_config=NEW_CONFIG,
            fixture_user_inputs=('y',),
            expected_next_command=NextCommand.APPLY,
            expected_editor_command=NANO,
        ),
        'invalid config edited again': RunDataset(
            fixture_new_config=ValidationError('Unknown domain: not-a-domain'),
            fixture_user_inputs=('e',),
            expected_next_command=NextCommand.SELF,
            expected_prints=[
                'The config is invalid:',
                'Unknown domain: not-a-domain',
                '[e] Edit config',
                '[a] Abort',
            ],
        ),
        'invalid choice for an invalid config then edit': RunDataset(
            fixture_new_config=ValidationError('Unknown domain: not-a-domain'),
            fixture_user_inputs=('x', 'e'),
            expected_next_command=NextCommand.SELF,
            expected_prints=['Invalid choice. Please try again.'],
        ),
    })
    def test_run_returns(self, dataset: RunDataset) -> None:
        """
        Test that the config is edited with the last applied editor and the
        user's choice decides the next command.
        """

        # Arrange
        config_reader = MockConfigReader.create(
            old_config=dataset.fixture_old_config,
            new_config=dataset.fixture_new_config,
        )
        which = MockWhich(PATHS_BY_NAME)
        editor_resolver = EditorResolver('linux', which)
        edit_results = (EditResult.CLOSED,)
        editor_launcher = MockEditorLauncher(edit_results)

        preview_result = RunActionsResult[None](NEW_CONFIG)
        preview_manager = MockSystemManager[None].default(result=preview_result)
        system_config_renderer = SystemConfigRenderer()
        yaml_serializer = YamlSerializer()
        preview_command = PreviewCommand(
            manager=preview_manager,
            system_config_renderer=system_config_renderer,
            yaml_serializer=yaml_serializer,
        )
        apply_command = make_apply_command()

        def preview_command_factory() -> PreviewCommand:
            return preview_command

        def apply_command_factory() -> ApplyCommand:
            return apply_command

        edit_command = EditCommand(
            config_reader=config_reader,
            old_path=OLD_PATH,
            new_path=NEW_PATH,
            editor_resolver=editor_resolver,
            editor_launcher=editor_launcher,
            preview_command_factory=preview_command_factory,
            apply_command_factory=apply_command_factory,
        )
        next_commands: dict[NextCommand, Command | None] = {
            NextCommand.SELF: edit_command,
            NextCommand.APPLY: apply_command,
            NextCommand.NONE: None,
        }
        expected_next_command = next_commands[dataset.expected_next_command]

        # Act
        with patch('builtins.input', side_effect=dataset.fixture_user_inputs) as mock_input, \
                patch('builtins.print') as mock_print:
            actual = edit_command.run()

        # Assert
        self.assertIs(expected_next_command, actual)
        self.assertEqual(
            editor_launcher.calls,
            [(dataset.expected_editor_command, NEW_PATH)],
        )
        self.assertEqual(config_reader.loaded_paths, [OLD_PATH, NEW_PATH])
        self.assertEqual(
            mock_input.call_count,
            len(dataset.fixture_user_inputs),
        )
        self.assertEqual(
            preview_manager.run_actions_calls,
            dataset.expected_preview_runs,
        )
        for expected_print in dataset.expected_prints:
            self.assertIn(call(expected_print), mock_print.call_args_list)

    @dataclass
    class RaiseDataset:
        fixture_edit_results: tuple[EditResult, ...]
        fixture_new_config: SystemConfig | ValidationError
        expected_message: str
        fixture_old_config: SystemConfig = field(
            default_factory=lambda: OLD_CONFIG)
        fixture_paths_by_name: dict[str, str] = field(
            default_factory=lambda: dict(PATHS_BY_NAME))
        fixture_user_inputs: tuple[str, ...] = ()

    @datasets({
        'editor exits with an error': RaiseDataset(
            fixture_edit_results=(EditResult.CANCELLED,),
            fixture_new_config=NEW_CONFIG,
            expected_message='The editor exited with an error, '
            + 'the edited config was not applied',
        ),
        'invalid config aborted': RaiseDataset(
            fixture_edit_results=(EditResult.CLOSED,),
            fixture_new_config=ValidationError('Unknown domain: not-a-domain'),
            fixture_user_inputs=('a',),
            expected_message='The invalid config was not applied',
        ),
        'five invalid choices for an invalid config': RaiseDataset(
            fixture_edit_results=(EditResult.CLOSED,),
            fixture_new_config=ValidationError('Unknown domain: not-a-domain'),
            fixture_user_inputs=('x',) * 5,
            expected_message='The invalid config was not applied',
        ),
        'no editor found': RaiseDataset(
            fixture_old_config=EMPTY_CONFIG,
            fixture_paths_by_name={},
            fixture_edit_results=(),
            fixture_new_config=NEW_CONFIG,
            expected_message='No editor found (tried editor, nano, vim, vi), '
            + "set one with 'system-config-manager.editor' in your config",
        ),
        'configured editor not found': RaiseDataset(
            fixture_paths_by_name={},
            fixture_edit_results=(),
            fixture_new_config=NEW_CONFIG,
            expected_message="Editor 'code' from "
            + "'system-config-manager.editor' was not found",
        ),
    })
    def test_run_raises(self, dataset: RaiseDataset) -> None:
        """Test that a failed edit or an aborted invalid config is not applied."""

        # Arrange
        config_reader = MockConfigReader.create(
            old_config=dataset.fixture_old_config,
            new_config=dataset.fixture_new_config,
        )
        which = MockWhich(dataset.fixture_paths_by_name)
        editor_resolver = EditorResolver('linux', which)
        editor_launcher = MockEditorLauncher(dataset.fixture_edit_results)
        edit_command = EditCommand(
            config_reader=config_reader,
            old_path=OLD_PATH,
            new_path=NEW_PATH,
            editor_resolver=editor_resolver,
            editor_launcher=editor_launcher,
            preview_command_factory=unexpected_preview_command_factory,
            apply_command_factory=unexpected_apply_command_factory,
        )

        # Act & Assert
        with patch('builtins.input', side_effect=dataset.fixture_user_inputs) as mock_input, \
                patch('builtins.print'):
            with self.assertRaises(ValidationError) as context:
                edit_command.run()

        self.assertEqual(str(context.exception), dataset.expected_message)
        self.assertEqual(
            mock_input.call_count,
            len(dataset.fixture_user_inputs),
        )

    @dataclass
    class EqualityDataset:
        input_command: EditCommand
        input_other: object
        expected_equal: bool

    @datasets({
        'same collaborators and paths': EqualityDataset(
            input_command=make_edit_command(),
            input_other=make_edit_command(),
            expected_equal=True,
        ),
        'different old path': EqualityDataset(
            input_command=make_edit_command(),
            input_other=make_edit_command(
                old_path=Path('/other/current.yaml'),
            ),
            expected_equal=False,
        ),
        'different new path': EqualityDataset(
            input_command=make_edit_command(),
            input_other=make_edit_command(new_path=Path('/other/config.yaml')),
            expected_equal=False,
        ),
        'different config reader': EqualityDataset(
            input_command=make_edit_command(),
            input_other=make_edit_command(file_reader=FileReader()),
            expected_equal=False,
        ),
        'different editor resolver': EqualityDataset(
            input_command=make_edit_command(),
            input_other=make_edit_command(
                editor_resolver=EditorResolver(
                    'win32',
                    EDITOR_RESOLVER.which,
                ),
            ),
            expected_equal=False,
        ),
        'different editor launcher': EqualityDataset(
            input_command=make_edit_command(),
            input_other=make_edit_command(
                editor_launcher=EditorLauncher(
                    MockRaisingSystemExecutor(RuntimeError('boom')),
                ),
            ),
            expected_equal=False,
        ),
        'not an edit command': EqualityDataset(
            input_command=make_edit_command(),
            input_other='edit',
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that commands compare by paths and collaborators."""

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(dataset.input_command, dataset.input_other)
        else:
            self.assertNotEqual(dataset.input_command, dataset.input_other)
