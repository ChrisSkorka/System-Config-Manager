# pyright: strict

import subprocess

from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent
from unittest.mock import patch

from sysconf.cli import main
from sysconf.system.executor import CommandException, SystemExecutor
from sysconf.system.file import FileReader, FileWriter
from sysconf.utils.defaults import Defaults
from test.datasets import datasets
from test.system.mock_editor import MockWhich
from test.test_case import TestCase
from test.utils.mock_context import MockContext


EDITOR_PATH = '/usr/bin/editor'
FALLBACK_EDITOR_PATHS = {
    'editor': EDITOR_PATH,
    'nano': EDITOR_PATH,
    'notepad': EDITOR_PATH,
}

BROKEN_CONFIG = dedent('''\
    version: 1
    domains:
      my-packages:
        type: list
        add: install $value
        remove: uninstall $value
    config:
      - my-packages:
          - a
          - broken
    ''')
FIXED_CONFIG = dedent('''\
    version: 1
    domains:
      my-packages:
        type: list
        add: install $value
        remove: uninstall $value
    config:
      - my-packages:
          - a
          - fixed
    ''')
INVALID_CONFIG = dedent('''\
    version: 1
    config: [a, b
    ''')

PARTIAL_CURRENT_CONFIG = dedent('''\
    version: '1'
    before: []
    after: []
    config:
    - my-packages:
      - a
    domains:
      my-packages:
        type: list
        depth: 0
        add: install $value
        remove: uninstall $value
    ''')
FIXED_CURRENT_CONFIG = dedent('''\
    version: '1'
    before: []
    after: []
    config:
    - my-packages:
      - a
      - fixed
    domains:
      my-packages:
        type: list
        depth: 0
        add: install $value
        remove: uninstall $value
    ''')


class DirectoryDefaults (Defaults):
    """Keep this tool's config directory in the given directory."""

    def __init__(self, config_dir: Path) -> None:
        super().__init__()

        self.config_dir = config_dir

    def get_config_dir(self) -> Path:
        return self.config_dir


class ScriptedSystemExecutor (SystemExecutor):
    """
    Stand in for the user's editor and the system's shell.

    - Each command is an editor run, which saves the next edited config
    - Each shell script is recorded, and the configured failing scripts raise
    """

    def __init__(
        self,
        edited_configs: tuple[str, ...],
        failing_scripts: tuple[str, ...],
        file_writer: FileWriter,
    ) -> None:
        self.edited_configs = edited_configs
        self.failing_scripts = failing_scripts
        self.file_writer = file_writer
        self.edits = 0
        self.scripts: list[str] = []

    def command(self, *command: str) -> None:
        path = Path(command[-1])
        contents = self.edited_configs[self.edits]
        self.edits += 1

        self.file_writer.write_file_contents(path, contents)

    def shell(self, script: str) -> None:
        self.scripts.append(script)

        if script in self.failing_scripts:
            process = subprocess.CompletedProcess[bytes](
                args=script,
                returncode=1,
            )
            raise CommandException(script, process)


def read_optional(path: Path) -> str | None:
    """Read the file, None when it does not exist."""

    if not path.exists():
        return None

    return path.read_text(encoding='utf-8')


class TestIntegrationEditCommand (TestCase):
    """
    Tests that `sysconf edit` works almost end to end, including the cli loop
    that runs each next command.

    The config files are real files in a temporary directory, the editor,
    shell and user input are simulated.
    """

    @dataclass
    class RunDataset:
        fixture_current_config: str | None
        fixture_edited_configs: tuple[str, ...]
        fixture_failing_scripts: tuple[str, ...]
        fixture_user_inputs: tuple[str, ...]
        expected_scripts: list[str]
        expected_current_config: str | None
        expected_location_recorded: bool

    @datasets({
        'failed action aborted': RunDataset(
            fixture_current_config=None,
            fixture_edited_configs=(BROKEN_CONFIG,),
            fixture_failing_scripts=('install broken',),
            fixture_user_inputs=('y', 'a'),
            expected_scripts=['install a', 'install broken'],
            expected_current_config=PARTIAL_CURRENT_CONFIG,
            expected_location_recorded=True,
        ),
        'failed action edited and applied': RunDataset(
            fixture_current_config=None,
            fixture_edited_configs=(BROKEN_CONFIG, FIXED_CONFIG),
            fixture_failing_scripts=('install broken',),
            fixture_user_inputs=('y', 'e', 'y'),
            expected_scripts=['install a', 'install broken', 'install fixed'],
            expected_current_config=FIXED_CURRENT_CONFIG,
            expected_location_recorded=True,
        ),
        'failed action edited and exited': RunDataset(
            fixture_current_config=None,
            fixture_edited_configs=(BROKEN_CONFIG, FIXED_CONFIG),
            fixture_failing_scripts=('install broken',),
            fixture_user_inputs=('y', 'e', 'n'),
            expected_scripts=['install a', 'install broken'],
            expected_current_config=PARTIAL_CURRENT_CONFIG,
            expected_location_recorded=True,
        ),
        'invalid config edited and applied': RunDataset(
            fixture_current_config=None,
            fixture_edited_configs=(INVALID_CONFIG, FIXED_CONFIG),
            fixture_failing_scripts=(),
            fixture_user_inputs=('e', 'y'),
            expected_scripts=['install a', 'install fixed'],
            expected_current_config=FIXED_CURRENT_CONFIG,
            expected_location_recorded=True,
        ),
        'partially applied config edited and applied': RunDataset(
            fixture_current_config=PARTIAL_CURRENT_CONFIG,
            fixture_edited_configs=(FIXED_CONFIG,),
            fixture_failing_scripts=(),
            fixture_user_inputs=('y',),
            expected_scripts=['install fixed'],
            expected_current_config=FIXED_CURRENT_CONFIG,
            expected_location_recorded=True,
        ),
        'unchanged config': RunDataset(
            fixture_current_config=FIXED_CURRENT_CONFIG,
            fixture_edited_configs=(FIXED_CONFIG,),
            fixture_failing_scripts=(),
            fixture_user_inputs=(),
            expected_scripts=[],
            expected_current_config=FIXED_CURRENT_CONFIG,
            expected_location_recorded=False,
        ),
    })
    def test_run(self, dataset: RunDataset) -> None:
        """
        Test the scripts run, the recorded current config and config location
        after the user's choices.
        """

        with TemporaryDirectory() as directory:

            # Arrange
            base_path = Path(directory).resolve()
            config_path = base_path / 'manual' / 'config.yaml'
            defaults = DirectoryDefaults(base_path / 'system-config-manager')
            current_path = defaults.get_old_config_path()
            location_path = defaults.get_config_location_path()

            file_reader = FileReader()
            file_writer = FileWriter()
            file_writer.write_file_contents(config_path, '')
            if dataset.fixture_current_config is not None:
                file_writer.write_file_contents(
                    current_path,
                    dataset.fixture_current_config,
                )

            system_executor = ScriptedSystemExecutor(
                edited_configs=dataset.fixture_edited_configs,
                failing_scripts=dataset.fixture_failing_scripts,
                file_writer=file_writer,
            )
            context = MockContext.create(
                defaults=defaults,
                file_reader=file_reader,
                file_writer=file_writer,
                system_executor=system_executor,
            )
            which = MockWhich(FALLBACK_EDITOR_PATHS)
            argv = ['sysconf', 'edit', str(config_path)]
            expected_location = f'{config_path}\n' \
                if dataset.expected_location_recorded \
                else None

            # Act
            with patch('sys.argv', argv), \
                    patch('sysconf.cli.Context', return_value=context), \
                    patch('shutil.which', which), \
                    patch('builtins.input', side_effect=dataset.fixture_user_inputs) as mock_input, \
                    patch('builtins.print'):
                main()

            # Assert
            self.assertEqual(system_executor.scripts, dataset.expected_scripts)
            self.assertEqual(
                system_executor.edits,
                len(dataset.fixture_edited_configs),
            )
            self.assertEqual(
                mock_input.call_count,
                len(dataset.fixture_user_inputs),
            )
            self.assertEqual(
                read_optional(current_path),
                dataset.expected_current_config,
            )
            self.assertEqual(read_optional(location_path), expected_location)
