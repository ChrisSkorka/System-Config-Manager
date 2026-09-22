# pyright: strict

from argparse import Namespace
from dataclasses import dataclass
import io
from unittest.mock import MagicMock, _Call, call  # type: ignore
from unittest.mock import patch
from sysconf.system.file import FileReader
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
                'configs/config-old.yaml': unindent("""
                    version: 1
                    config: []
                """),
                'configs/config-new.yaml': unindent("""
                    version: 1
                    config: []
                """),
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
                'configs/config-old.yaml': unindent("""
                    version: 1
                    config: []
                """),
                'configs/config-new.yaml': unindent("""
                    version: 1
                    config:
                      - gsettings:
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
                $ gsettings set org.schema key \\"value\\"

            """) + '\n',
            expected_subprocess_calls=[
                call(('gsettings', 'set', 'org.schema', 'key', '"value"')),
            ],
        ),
        'add, change, remove': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                'configs/config-old.yaml': unindent("""
                    version: 1
                    config:
                      - gsettings:
                          org.schema:
                            updated: old-value
                            removed: removed-value
                """),
                'configs/config-new.yaml': unindent("""
                    version: 1
                    config:
                      - gsettings:
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
                # Remove gsettings: removed = removed-value
                $ gsettings reset org.schema removed

                # Update gsettings: updated = old-value -> new-value
                $ gsettings set org.schema updated \\"new-value\\"

                # Add gsettings: added = added-value
                $ gsettings set org.schema added \\"added-value\\"

            """) + '\n',
            expected_subprocess_calls=[
                call(('gsettings', 'reset', 'org.schema', 'removed')),
                call(('gsettings', 'set', 'org.schema', 'updated', '"new-value"')),
                call(('gsettings', 'set', 'org.schema', 'added', '"added-value"')),
            ],
        ),
        'dconf add, change and remove': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                'configs/config-old.yaml': unindent("""
                    version: 1
                    config:
                      - dconf:
                          /org/gnome/updated: old-value
                          /org/gnome/removed: removed-value
                """),
                'configs/config-new.yaml': unindent("""
                    version: 1
                    config:
                      - dconf:
                          /org/gnome/updated: new-value
                          /org/gnome/added: added-value
                """),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('configs/config-old.yaml'),
                config_file=fpath('configs/config-new.yaml'),
            ),
            expected_stdout=unindent("""
                # Remove dconf: /org/gnome/removed = removed-value
                $ dconf reset /org/gnome/removed

                # Update dconf: /org/gnome/updated = old-value -> new-value
                $ dconf write /org/gnome/updated \\"new-value\\"

                # Add dconf: /org/gnome/added = added-value
                $ dconf write /org/gnome/added \\"added-value\\"

            """) + '\n',
            expected_subprocess_calls=[
                call(('dconf', 'reset', '/org/gnome/removed')),
                call(('dconf', 'write', '/org/gnome/updated', '"new-value"')),
                call(('dconf', 'write', '/org/gnome/added', '"added-value"')),
            ],
        ),
        'dconf encodes non string values': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                'configs/config-old.yaml': unindent("""
                    version: 1
                    config: []
                """),
                'configs/config-new.yaml': unindent("""
                    version: 1
                    config:
                      - dconf:
                          /org/gnome/enabled: true
                          /org/gnome/speed: -0.2
                """),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('configs/config-old.yaml'),
                config_file=fpath('configs/config-new.yaml'),
            ),
            expected_stdout=unindent("""
                # Add dconf: /org/gnome/enabled = True
                $ dconf write /org/gnome/enabled true

                # Add dconf: /org/gnome/speed = -0.2
                $ dconf write /org/gnome/speed -0.2

            """) + '\n',
            expected_subprocess_calls=[
                call(('dconf', 'write', '/org/gnome/enabled', 'true')),
                call(('dconf', 'write', '/org/gnome/speed', '-0.2')),
            ],
        ),
        'user defined list domain add and remove': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                'configs/config-old.yaml': unindent("""
                    version: 1
                    domains:
                      my-packages:
                        type: list
                        add: my-pm install $value
                        remove: my-pm remove $value
                    config:
                      - my-packages:
                          - removed-package
                """),
                'configs/config-new.yaml': unindent("""
                    version: 1
                    domains:
                      my-packages:
                        type: list
                        add: my-pm install $value
                        remove: my-pm remove $value
                    config:
                      - my-packages:
                          - added-package
                """),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('configs/config-old.yaml'),
                config_file=fpath('configs/config-new.yaml'),
            ),
            expected_stdout=unindent("""
                # Remove my-packages: removed-package
                $ my-pm remove removed-package

                # Add my-packages: added-package
                $ my-pm install added-package

            """) + '\n',
            expected_subprocess_calls=[
                call('my-pm remove removed-package', shell=True),
                call('my-pm install added-package', shell=True),
            ],
        ),
        'user defined list domain with keyed paths': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                'configs/config-old.yaml': unindent("""
                    version: 1
                    domains:
                      user-groups:
                        type: list
                        depth: 1
                        add: usermod -aG "$value" "$key"
                        remove: gpasswd -d "$key" "$value"
                    config:
                      - user-groups:
                          alice:
                            - sudo
                """),
                'configs/config-new.yaml': unindent("""
                    version: 1
                    domains:
                      user-groups:
                        type: list
                        depth: 1
                        add: usermod -aG "$value" "$key"
                        remove: gpasswd -d "$key" "$value"
                    config:
                      - user-groups:
                          alice:
                            - docker
                """),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('configs/config-old.yaml'),
                config_file=fpath('configs/config-new.yaml'),
            ),
            expected_stdout=unindent("""
                # Remove user-groups: alice = sudo
                $ gpasswd -d "alice" "sudo"

                # Add user-groups: alice = docker
                $ usermod -aG "docker" "alice"

            """) + '\n',
            expected_subprocess_calls=[
                call('gpasswd -d "alice" "sudo"', shell=True),
                call('usermod -aG "docker" "alice"', shell=True),
            ],
        ),
        'user defined map domain add, update and remove': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                'configs/config-old.yaml': unindent("""
                    version: 1
                    domains:
                      my-config:
                        type: map
                        depth: 1
                        add: my-cfg set "$key" "$value"
                        update: my-cfg set "$key" "$value"
                        remove: my-cfg unset "$key"
                    config:
                      - my-config:
                          updated: old-value
                          removed: removed-value
                """),
                'configs/config-new.yaml': unindent("""
                    version: 1
                    domains:
                      my-config:
                        type: map
                        depth: 1
                        add: my-cfg set "$key" "$value"
                        update: my-cfg set "$key" "$value"
                        remove: my-cfg unset "$key"
                    config:
                      - my-config:
                          updated: new-value
                          added: added-value
                """),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('configs/config-old.yaml'),
                config_file=fpath('configs/config-new.yaml'),
            ),
            expected_stdout=unindent("""
                # Remove my-config: removed = removed-value
                $ my-cfg unset "removed"

                # Update my-config: updated = old-value -> new-value
                $ my-cfg set "updated" "new-value"

                # Add my-config: added = added-value
                $ my-cfg set "added" "added-value"

            """) + '\n',
            expected_subprocess_calls=[
                call('my-cfg unset "removed"', shell=True),
                call('my-cfg set "updated" "new-value"', shell=True),
                call('my-cfg set "added" "added-value"', shell=True),
            ],
        ),
        'before and after scripts run around the changes': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                'configs/config-old.yaml': unindent("""
                    version: 1
                    config: []
                """),
                'configs/config-new.yaml': unindent("""
                    version: 1
                    before:
                      - echo starting
                    after:
                      - echo finished
                    config:
                      - gsettings:
                          org.schema:
                            key: value
                """),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('configs/config-old.yaml'),
                config_file=fpath('configs/config-new.yaml'),
            ),
            expected_stdout=unindent("""
                $ echo starting

                # Add gsettings: key = value
                $ gsettings set org.schema key \\"value\\"

                $ echo finished

            """) + '\n',
            expected_subprocess_calls=[
                call('echo starting', shell=True),
                call(('gsettings', 'set', 'org.schema', 'key', '"value"')),
                call('echo finished', shell=True),
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
        mock_file_writer = MagicMock()

        with patch('subprocess.run', mock_run), \
                patch('sys.stdout', mock_stdout), \
                patch('sysconf.commands.comparative_config_command_parser.FileReader', dataset.fixture_file_reader), \
                patch('sysconf.commands.apply_command.FileWriter', mock_file_writer):

            # Act
            command: ApplyCommand = ApplyCommand.create_from_arguments(
                dataset.input_parsed_arguments,
            )
            command.run()

        # Assert
        self.assertEqual(mock_stdout.getvalue(), dataset.expected_stdout)
        mock_run.assert_has_calls(dataset.expected_subprocess_calls)
