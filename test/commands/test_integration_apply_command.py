# pyright: strict

from argparse import Namespace
from dataclasses import dataclass
import io
from unittest.mock import _Call, call  # type: ignore
from unittest.mock import patch
from sysconf.utils.file import FileReader
from test.commands.test_apply_command import ApplyCommand
from test.datasets import datasets
from test.helper import unindent
from test.system.mock_subprocess import create_mock_run
from test.test_case import TestCase
from test.utils.mock_file import MockFileReader
from test.utils.mock_path import fpath


class TestIntegrationApplyCommand (TestCase):
    """
    Tests that the `sysconf apply` command works almost end to end.

    This will mock the system boundary (files, subprocess calls and stdout), 
    but otherwise within python everything is run end to end.

    This test should be as reflective of real world performance as possible 
    without actually running system commands or altering the file system.
    """

    @dataclass
    class RunSuccessDataset:
        fixture_file_reader: FileReader
        # todo: mock defaults
        input_parsed_arguments: Namespace
        expected_stdout: str
        expected_subprocess_calls: list[_Call]

    @datasets({
        'empty, no changes': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                'configs/config-old.yaml': """version: 1""",
                'configs/config-new.yaml': """version: 1""",
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('configs/config-old.yaml'),
                config_file=fpath('configs/config-new.yaml'),
            ),
            expected_stdout='# No changes required.\n',
            expected_subprocess_calls=[],
        ),
        'simple, empty last config': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                'configs/config-old.yaml': """version: 1""",
                'configs/config-new.yaml': unindent("""
                    version: 1
                    gsettings:
                        org.schema:
                            key: value
                """),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('configs/config-old.yaml'),
                config_file=fpath('configs/config-new.yaml'),
            ),
            expected_stdout=unindent("""
                # Add gsettings: key = value
                gsettings set org.schema key 'value'

            """),
            expected_subprocess_calls=[],
        ),
        'add, change, remove': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                'configs/config-old.yaml': unindent("""
                    version: 1
                    gsettings:
                        org.schema:
                            updated: old-value
                            removed: removed-value
                """),
                'configs/config-new.yaml': unindent("""
                    version: 1
                    gsettings:
                        org.schema:
                            updated: new-value
                            added: added-value
                """),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('configs/config-old.yaml'),
                config_file=fpath('configs/config-new.yaml'),
            ),
            expected_stdout=unindent("""
                # Remove gsettings: removed
                gsettings reset org.schema removed
                # Update gsettings: updated = old-value -> new-value
                gsettings set org.schema updated 'new-value'
                # Add gsettings: added = added-value
                gsettings set org.schema added 'added-value'
                
            """),
            expected_subprocess_calls=[
                call(('gsettings', 'reset', 'org.schema', 'removed')),
                call(('gsettings', 'set', 'org.schema', 'updated', '\'new-value\'')),
                call(('gsettings', 'set', 'org.schema', 'added', '\'added-value\'')),
            ],
        ),
    })
    def test_run_success(
        self,
        dataset: RunSuccessDataset,
    ) -> None:
        # Arrange
        mock_run = create_mock_run()
        mock_stdout = io.StringIO()

        with patch('subprocess.run', mock_run), \
                patch('sys.stdout', mock_stdout), \
                patch('sysconf.commands.comparative_config_command_parser.FileReader', dataset.fixture_file_reader):

            # Act
            command: ApplyCommand = ApplyCommand.create_from_arguments(
                dataset.input_parsed_arguments,
            )
            command.run()

        # Assert
        self.assertEqual(mock_stdout.getvalue(), dataset.expected_stdout)
        mock_run.assert_has_calls(dataset.expected_subprocess_calls)
