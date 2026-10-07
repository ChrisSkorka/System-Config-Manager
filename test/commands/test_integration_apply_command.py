# pyright: strict

from argparse import Namespace
from dataclasses import dataclass
import io
from textwrap import dedent
from unittest.mock import _Call, call  # type: ignore
from unittest.mock import patch

from sysconf.commands.apply_command import ApplyCommand
from sysconf.system.executor import LiveSystemExecutor
from sysconf.system.file import FileReader
from test.datasets import datasets
from test.system.mock_subprocess import create_mock_run
from test.test_case import TestCase
from test.utils.mock_context import MockContext
from test.utils.mock_defaults import MockDefaults
from test.utils.mock_file import MockFileReader, MockFileWriter
from test.utils.mock_path import MockPath, dpath, fpath


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
        input_parsed_arguments: Namespace
        expected_stdout: str
        expected_subprocess_calls: list[_Call]

    @datasets({
        'empty, no changes': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                '/configs/config-old.yaml': dedent('''\
                    version: 1
                    config: []
                '''),
                '/configs/config-new.yaml': dedent('''\
                    version: 1
                    config: []
                '''),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('/configs/config-old.yaml'),
                config_file=fpath('/configs/config-new.yaml'),
            ),
            expected_stdout='# No system config changes. '
            '(no differential commands to run)\n',
            expected_subprocess_calls=[],
        ),
        'simple, empty last config': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                '/configs/config-old.yaml': dedent('''\
                    version: 1
                    config: []
                '''),
                '/configs/config-new.yaml': dedent('''\
                    version: 1
                    config:
                      - gsettings:
                          org.schema:
                            key: value
                '''),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('/configs/config-old.yaml'),
                config_file=fpath('/configs/config-new.yaml'),
            ),
            expected_stdout=dedent('''\
                # Add gsettings: key = value
                $ gsettings set org.schema key \\"value\\"

            '''),
            expected_subprocess_calls=[
                call(('gsettings', 'set', 'org.schema', 'key', '"value"')),
            ],
        ),
        'no last config yet': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                '/configs/config-new.yaml': dedent('''\
                    version: 1
                    config:
                      - gsettings:
                          org.schema:
                            key: value
                '''),
            }),
            input_parsed_arguments=Namespace(
                last_config=None,
                config_file=fpath('/configs/config-new.yaml'),
            ),
            expected_stdout=dedent('''\
                # Add gsettings: key = value
                $ gsettings set org.schema key \\"value\\"

            '''),
            expected_subprocess_calls=[
                call(('gsettings', 'set', 'org.schema', 'key', '"value"')),
            ],
        ),
        'add, change, remove': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                '/configs/config-old.yaml': dedent('''\
                    version: 1
                    config:
                      - gsettings:
                          org.schema:
                            updated: old-value
                            removed: removed-value
                '''),
                '/configs/config-new.yaml': dedent('''\
                    version: 1
                    config:
                      - gsettings:
                          org.schema:
                            updated: new-value
                            added: added-value
                '''),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('/configs/config-old.yaml'),
                config_file=fpath('/configs/config-new.yaml'),
            ),
            expected_stdout=dedent('''\
                # Remove gsettings: removed = removed-value
                $ gsettings reset org.schema removed

                # Update gsettings: updated = old-value -> new-value
                $ gsettings set org.schema updated \\"new-value\\"

                # Add gsettings: added = added-value
                $ gsettings set org.schema added \\"added-value\\"

            '''),
            expected_subprocess_calls=[
                call(('gsettings', 'reset', 'org.schema', 'removed')),
                call(('gsettings', 'set', 'org.schema', 'updated', '"new-value"')),
                call(('gsettings', 'set', 'org.schema', 'added', '"added-value"')),
            ],
        ),
        'dconf add, change and remove': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                '/configs/config-old.yaml': dedent('''\
                    version: 1
                    config:
                      - dconf:
                          /org/gnome/updated: old-value
                          /org/gnome/removed: removed-value
                '''),
                '/configs/config-new.yaml': dedent('''\
                    version: 1
                    config:
                      - dconf:
                          /org/gnome/updated: new-value
                          /org/gnome/added: added-value
                '''),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('/configs/config-old.yaml'),
                config_file=fpath('/configs/config-new.yaml'),
            ),
            expected_stdout=dedent('''\
                # Remove dconf: /org/gnome/removed = removed-value
                $ dconf reset /org/gnome/removed

                # Update dconf: /org/gnome/updated = old-value -> new-value
                $ dconf write /org/gnome/updated \\"new-value\\"

                # Add dconf: /org/gnome/added = added-value
                $ dconf write /org/gnome/added \\"added-value\\"

            '''),
            expected_subprocess_calls=[
                call(('dconf', 'reset', '/org/gnome/removed')),
                call(('dconf', 'write', '/org/gnome/updated', '"new-value"')),
                call(('dconf', 'write', '/org/gnome/added', '"added-value"')),
            ],
        ),
        'dconf encodes non string values': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                '/configs/config-old.yaml': dedent('''\
                    version: 1
                    config: []
                '''),
                '/configs/config-new.yaml': dedent('''\
                    version: 1
                    config:
                      - dconf:
                          /org/gnome/enabled: true
                          /org/gnome/speed: -0.2
                '''),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('/configs/config-old.yaml'),
                config_file=fpath('/configs/config-new.yaml'),
            ),
            expected_stdout=dedent('''\
                # Add dconf: /org/gnome/enabled = True
                $ dconf write /org/gnome/enabled true

                # Add dconf: /org/gnome/speed = -0.2
                $ dconf write /org/gnome/speed -0.2

            '''),
            expected_subprocess_calls=[
                call(('dconf', 'write', '/org/gnome/enabled', 'true')),
                call(('dconf', 'write', '/org/gnome/speed', '-0.2')),
            ],
        ),
        'user defined list domain add and remove': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                '/configs/config-old.yaml': dedent('''\
                    version: 1
                    domains:
                      my-packages:
                        type: list
                        add: my-pm install $value
                        remove: my-pm remove $value
                    config:
                      - my-packages:
                          - removed-package
                '''),
                '/configs/config-new.yaml': dedent('''\
                    version: 1
                    domains:
                      my-packages:
                        type: list
                        add: my-pm install $value
                        remove: my-pm remove $value
                    config:
                      - my-packages:
                          - added-package
                '''),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('/configs/config-old.yaml'),
                config_file=fpath('/configs/config-new.yaml'),
            ),
            expected_stdout=dedent('''\
                # Remove my-packages: removed-package
                $ my-pm remove removed-package

                # Add my-packages: added-package
                $ my-pm install added-package

            '''),
            expected_subprocess_calls=[
                call('my-pm remove removed-package', shell=True),
                call('my-pm install added-package', shell=True),
            ],
        ),
        'user defined list domain with keyed paths': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                '/configs/config-old.yaml': dedent('''\
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
                '''),
                '/configs/config-new.yaml': dedent('''\
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
                '''),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('/configs/config-old.yaml'),
                config_file=fpath('/configs/config-new.yaml'),
            ),
            expected_stdout=dedent('''\
                # Remove user-groups: alice = sudo
                $ gpasswd -d "alice" "sudo"

                # Add user-groups: alice = docker
                $ usermod -aG "docker" "alice"

            '''),
            expected_subprocess_calls=[
                call('gpasswd -d "alice" "sudo"', shell=True),
                call('usermod -aG "docker" "alice"', shell=True),
            ],
        ),
        'user defined map domain add, update and remove': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                '/configs/config-old.yaml': dedent('''\
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
                '''),
                '/configs/config-new.yaml': dedent('''\
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
                '''),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('/configs/config-old.yaml'),
                config_file=fpath('/configs/config-new.yaml'),
            ),
            expected_stdout=dedent('''\
                # Remove my-config: removed = removed-value
                $ my-cfg unset "removed"

                # Update my-config: updated = old-value -> new-value
                $ my-cfg set "updated" "new-value"

                # Add my-config: added = added-value
                $ my-cfg set "added" "added-value"

            '''),
            expected_subprocess_calls=[
                call('my-cfg unset "removed"', shell=True),
                call('my-cfg set "updated" "new-value"', shell=True),
                call('my-cfg set "added" "added-value"', shell=True),
            ],
        ),
        'before and after scripts run around the changes': RunSuccessDataset(
            fixture_file_reader=MockFileReader({
                '/configs/config-old.yaml': dedent('''\
                    version: 1
                    config: []
                '''),
                '/configs/config-new.yaml': dedent('''\
                    version: 1
                    before:
                      - echo starting
                    after:
                      - echo finished
                    config:
                      - gsettings:
                          org.schema:
                            key: value
                '''),
            }),
            input_parsed_arguments=Namespace(
                last_config=fpath('/configs/config-old.yaml'),
                config_file=fpath('/configs/config-new.yaml'),
            ),
            expected_stdout=dedent('''\
                $ echo starting

                # Add gsettings: key = value
                $ gsettings set org.schema key \\"value\\"

                $ echo finished

            '''),
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

        # The config location is a directory, so nothing is recorded and
        # nothing extra is printed
        defaults = MockDefaults(
            old_config_path=MockPath('/config/.history/current.yaml'),
            config_location_path=dpath('/config/config'),
        )
        file_writer = MockFileWriter()
        system_executor = LiveSystemExecutor()
        context = MockContext.create(
            defaults=defaults,
            file_reader=dataset.fixture_file_reader,
            file_writer=file_writer,
            system_executor=system_executor,
        )

        with patch('subprocess.run', mock_run), \
                patch('sys.stdout', mock_stdout):

            # Act
            command = ApplyCommand.create_from_arguments(
                context=context,
                parsed_arguments=dataset.input_parsed_arguments,
            )
            command.run()

        # Assert
        self.assertEqual(mock_stdout.getvalue(), dataset.expected_stdout)
        mock_run.assert_has_calls(dataset.expected_subprocess_calls)

    @dataclass
    class RunRecordsConfigLocationDataset:
        fixture_defaults: MockDefaults
        fixture_location_files: dict[str, str]
        expected_stdout: str
        expected_recorded_contents: str | None

    @datasets({
        'nothing recorded yet': RunRecordsConfigLocationDataset(
            fixture_defaults=MockDefaults(
                old_config_path=MockPath('/config/.history/current.yaml'),
                config_location_path=MockPath('/config/config'),
            ),
            fixture_location_files={},
            expected_stdout='Saved "/configs/config-new.yaml" as your config location\n'
            + '# No system config changes. (no differential commands to run)\n',
            expected_recorded_contents='/configs/config-new.yaml\n',
        ),
        'a different location is recorded': RunRecordsConfigLocationDataset(
            fixture_defaults=MockDefaults(
                old_config_path=MockPath('/config/.history/current.yaml'),
                config_location_path=fpath('/config/config'),
            ),
            fixture_location_files={
                '/config/config': '/configs/other.yaml\n',
            },
            expected_stdout='Saved "/configs/config-new.yaml" as your config location\n'
            + '# No system config changes. (no differential commands to run)\n',
            expected_recorded_contents='/configs/config-new.yaml\n',
        ),
        'config location is a directory': RunRecordsConfigLocationDataset(
            fixture_defaults=MockDefaults(
                old_config_path=MockPath('/config/.history/current.yaml'),
                config_location_path=dpath('/config/config'),
            ),
            fixture_location_files={},
            expected_stdout='# No system config changes. '
            '(no differential commands to run)\n',
            expected_recorded_contents=None,
        ),
    })
    def test_run_records_the_config_location(
        self,
        dataset: RunRecordsConfigLocationDataset,
    ) -> None:
        """Test that applying a given config records where that config lives."""

        # Arrange
        mock_run = create_mock_run()
        mock_stdout = io.StringIO()
        file_writer = MockFileWriter()
        file_reader = MockFileReader({
            '/configs/config-old.yaml': dedent('''\
                version: 1
                config: []
            '''),
            '/configs/config-new.yaml': dedent('''\
                version: 1
                config: []
            '''),
            **dataset.fixture_location_files,
        })
        system_executor = LiveSystemExecutor()
        context = MockContext.create(
            defaults=dataset.fixture_defaults,
            file_reader=file_reader,
            file_writer=file_writer,
            system_executor=system_executor,
        )
        old_config_path = fpath('/configs/config-old.yaml')
        new_config_path = fpath('/configs/config-new.yaml')
        parsed_arguments = Namespace(
            last_config=old_config_path,
            config_file=new_config_path,
        )

        with patch('subprocess.run', mock_run), \
                patch('sys.stdout', mock_stdout):

            # Act
            command = ApplyCommand.create_from_arguments(
                context=context,
                parsed_arguments=parsed_arguments,
            )
            command.run()

        # Assert
        self.assertEqual(mock_stdout.getvalue(), dataset.expected_stdout)
        self.assertEqual(
            file_writer.written_files.get('/config/config'),
            dataset.expected_recorded_contents,
        )
