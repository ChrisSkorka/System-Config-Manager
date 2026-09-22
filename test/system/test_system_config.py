# pyright: strict

from dataclasses import dataclass
from typing import Sequence
from unittest.mock import call, patch

from sysconf.config.actions import Action, ShellAction
from sysconf.config.domains import ConfigEntryId, Domain, DomainConfigEntry
from sysconf.config.system_config import SystemConfig, SystemConfigTransitioner, SystemManager
from sysconf.domains.user_domains import UserDomain
from sysconf.system.error_handler import ErrorHandler
from sysconf.utils.transition import SequenceTransitioner
from test.datasets import datasets
from test.domains.mock_domain_config_entry import MockDomainConfigEntry
from test.domains.mock_user_domain import MockUserDomain
from test.system.mock_error_handler import (
    MockFailErrorHandler,
    MockSequencedErrorHandler,
    MockSuccessErrorHandler,
)
from test.system.mock_system_executor import (
    MockRaisingSystemExecutor,
    MockSystemExecutor,
)
from test.test_case import TestCase


ENTRY_A = MockDomainConfigEntry(('a',), MockUserDomain('test-a'))
ENTRY_B = MockDomainConfigEntry(('b',), MockUserDomain('test-b'))
DOMAIN_A = MockUserDomain('test-a')
DOMAIN_B = MockUserDomain('test-b')
BEFORE_ACTION = ShellAction('echo before')
AFTER_ACTION = ShellAction('echo after')


def make_system_config(
    before_actions: tuple[Action, ...] = (),
    after_actions: tuple[Action, ...] = (),
    config_entries: Sequence[DomainConfigEntry] = (),
    user_domains: Sequence[UserDomain] = (),
) -> SystemConfig:
    """Build a SystemConfig from its parts, defaulting each to empty."""

    return SystemConfig.create_from_entries(
        before_actions=before_actions,
        after_actions=after_actions,
        config_entries=config_entries,
        user_domains=user_domains,
    )


class TestSystemConfig(TestCase):
    """Test the aggregate system configuration value object."""

    @dataclass
    class CreateFromEntriesDataset:
        input_before_actions: tuple[ShellAction, ...]
        input_after_actions: tuple[ShellAction, ...]
        input_entries: list[MockDomainConfigEntry]
        input_user_domains: list[MockUserDomain]
        expected: SystemConfig

    @datasets({
        'empty config': CreateFromEntriesDataset(
            input_before_actions=(),
            input_after_actions=(),
            input_entries=[],
            input_user_domains=[],
            expected=SystemConfig(
                before_actions=(),
                after_actions=(),
                config_entries={},
                user_domains={},
            ),
        ),
        'config with entries actions and domains': CreateFromEntriesDataset(
            input_before_actions=(ShellAction('echo before'),),
            input_after_actions=(ShellAction('echo after'),),
            input_entries=[
                MockDomainConfigEntry(('a',), MockUserDomain('d1')),
                MockDomainConfigEntry(('b',), MockUserDomain('d2')),
            ],
            input_user_domains=[MockUserDomain('d1'), MockUserDomain('d2')],
            expected=SystemConfig(
                before_actions=(ShellAction('echo before'),),
                after_actions=(ShellAction('echo after'),),
                config_entries={
                    ('a',): MockDomainConfigEntry(('a',), MockUserDomain('d1')),
                    ('b',): MockDomainConfigEntry(('b',), MockUserDomain('d2')),
                },
                user_domains={
                    'd1': MockUserDomain('d1'),
                    'd2': MockUserDomain('d2'),
                },
            ),
        ),
    })
    def test_creates_correct_config(self, dataset: CreateFromEntriesDataset) -> None:
        # Act
        result = SystemConfig.create_from_entries(
            before_actions=dataset.input_before_actions,
            after_actions=dataset.input_after_actions,
            config_entries=dataset.input_entries,
            user_domains=dataset.input_user_domains,
        )

        # Assert
        self.assertEqual(dataset.expected, result)

    def test_raises_on_duplicate_id(self) -> None:
        domain = MockUserDomain('d')
        entries = [
            MockDomainConfigEntry(('a',), domain),
            MockDomainConfigEntry(('a',), domain),
        ]

        with self.assertRaises(AssertionError) as ctx:
            SystemConfig.create_from_entries(
                before_actions=(),
                after_actions=(),
                config_entries=entries,
                user_domains=[domain],
            )

        self.assertIn('Duplicate ConfigEntryId', str(ctx.exception))

    @dataclass
    class EqualityDataset:
        input_a: SystemConfig
        input_b: object
        expected_equal: bool

    @datasets({
        'equal empty configs': EqualityDataset(
            input_a=SystemConfig(
                before_actions=(),
                after_actions=(),
                config_entries={},
                user_domains={},
            ),
            input_b=SystemConfig(
                before_actions=(),
                after_actions=(),
                config_entries={},
                user_domains={},
            ),
            expected_equal=True,
        ),
        'equal with entries and domains': EqualityDataset(
            input_a=SystemConfig(
                before_actions=(),
                after_actions=(),
                config_entries={('a',): MockDomainConfigEntry(
                    ('a',), MockUserDomain('d'))},
                user_domains={'d': MockUserDomain('d')},
            ),
            input_b=SystemConfig(
                before_actions=(),
                after_actions=(),
                config_entries={('a',): MockDomainConfigEntry(
                    ('a',), MockUserDomain('d'))},
                user_domains={'d': MockUserDomain('d')},
            ),
            expected_equal=True,
        ),
        'different config entries': EqualityDataset(
            input_a=SystemConfig(
                before_actions=(),
                after_actions=(),
                config_entries={('a',): MockDomainConfigEntry(
                    ('a',), MockUserDomain('d'))},
                user_domains={},
            ),
            input_b=SystemConfig(
                before_actions=(),
                after_actions=(),
                config_entries={('b',): MockDomainConfigEntry(
                    ('b',), MockUserDomain('d'))},
                user_domains={},
            ),
            expected_equal=False,
        ),
        'different before actions': EqualityDataset(
            input_a=SystemConfig(
                before_actions=(ShellAction('echo a'),),
                after_actions=(),
                config_entries={},
                user_domains={},
            ),
            input_b=SystemConfig(
                before_actions=(ShellAction('echo b'),),
                after_actions=(),
                config_entries={},
                user_domains={},
            ),
            expected_equal=False,
        ),
        'different after actions': EqualityDataset(
            input_a=SystemConfig(
                before_actions=(),
                after_actions=(ShellAction('echo a'),),
                config_entries={},
                user_domains={},
            ),
            input_b=SystemConfig(
                before_actions=(),
                after_actions=(ShellAction('echo b'),),
                config_entries={},
                user_domains={},
            ),
            expected_equal=False,
        ),
        'different domains': EqualityDataset(
            input_a=SystemConfig(
                before_actions=(),
                after_actions=(),
                config_entries={},
                user_domains={'d1': MockUserDomain('d1')},
            ),
            input_b=SystemConfig(
                before_actions=(),
                after_actions=(),
                config_entries={},
                user_domains={'d2': MockUserDomain('d2')},
            ),
            expected_equal=False,
        ),
        'not a SystemConfig': EqualityDataset(
            input_a=SystemConfig(
                before_actions=(),
                after_actions=(),
                config_entries={},
                user_domains={},
            ),
            input_b='not a SystemConfig',
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        self.assertEqual(dataset.expected_equal,
                         dataset.input_a == dataset.input_b)

    @dataclass
    class ReprDataset:
        input_config: SystemConfig
        expected_repr: str

    @datasets({
        'empty config': ReprDataset(
            input_config=make_system_config(),
            expected_repr='SystemConfig({})',
        ),
        'config with one entry': ReprDataset(
            input_config=make_system_config(config_entries=[ENTRY_A]),
            expected_repr="SystemConfig({('a',): MockDomainConfigEntry(('a',))})",
        ),
    })
    def test_repr(self, dataset: ReprDataset) -> None:
        """Test that the repr shows the config entries."""

        # Act & Assert
        self.assertEqual(repr(dataset.input_config), dataset.expected_repr)


class TestSystemManager(TestCase):
    """Test planning and running the actions between two configurations."""

    @dataclass
    class GetDomainActionsDataset:
        input_old_entries: list[MockDomainConfigEntry]
        input_new_entries: list[MockDomainConfigEntry]
        expected_descriptions: list[str]

    @datasets({
        'empty configs produces no actions': GetDomainActionsDataset(
            input_old_entries=[],
            input_new_entries=[],
            expected_descriptions=[],
        ),
        'add single entry': GetDomainActionsDataset(
            input_old_entries=[],
            input_new_entries=[MockDomainConfigEntry(
                ('a',), MockUserDomain('d'))],
            expected_descriptions=['None→a'],
        ),
        'remove single entry': GetDomainActionsDataset(
            input_old_entries=[MockDomainConfigEntry(
                ('a',), MockUserDomain('d'))],
            input_new_entries=[],
            expected_descriptions=['a→None'],
        ),
        'update entry with same id': GetDomainActionsDataset(
            input_old_entries=[MockDomainConfigEntry(
                ('a',), MockUserDomain('d'))],
            input_new_entries=[MockDomainConfigEntry(
                ('a',), MockUserDomain('d'))],
            expected_descriptions=['a→a'],
        ),
        'multiple removals are in reversed order': GetDomainActionsDataset(
            input_old_entries=[
                MockDomainConfigEntry(('a',), MockUserDomain('d')),
                MockDomainConfigEntry(('b',), MockUserDomain('d')),
                MockDomainConfigEntry(('c',), MockUserDomain('d')),
            ],
            input_new_entries=[],
            expected_descriptions=['c→None', 'b→None', 'a→None'],
        ),
        'mixed: removals first reversed then new order': GetDomainActionsDataset(
            input_old_entries=[
                MockDomainConfigEntry(('a',), MockUserDomain('d')),
                MockDomainConfigEntry(('b',), MockUserDomain('d')),
                MockDomainConfigEntry(('c',), MockUserDomain('d')),
            ],
            input_new_entries=[
                MockDomainConfigEntry(('c',), MockUserDomain('d')),
                MockDomainConfigEntry(('d',), MockUserDomain('d')),
            ],
            expected_descriptions=['b→None', 'a→None', 'c→c', 'None→d'],
        ),
    })
    def test_get_domain_actions(self, dataset: GetDomainActionsDataset) -> None:
        # Arrange
        old_config = SystemConfig.create_from_entries(
            before_actions=(),
            after_actions=(),
            config_entries=dataset.input_old_entries,
            user_domains=[],
        )
        new_config = SystemConfig.create_from_entries(
            before_actions=(),
            after_actions=(),
            config_entries=dataset.input_new_entries,
            user_domains=[],
        )
        manager = SystemManager(
            old_config=old_config,
            new_config=new_config,
            executor=MockSystemExecutor(),
            error_handler=MockSuccessErrorHandler(),
        )

        # Act
        actions = list(manager.get_domain_actions())

        # Assert
        self.assertEqual(
            dataset.expected_descriptions,
            [a.get_description() for a in actions],
        )

    @dataclass
    class RunActionsDataset:
        input_old_config: SystemConfig
        input_new_config: SystemConfig
        input_error_handler: ErrorHandler
        expected: SystemConfig

    @datasets({
        'no changes returns new config': RunActionsDataset(
            input_old_config=SystemConfig.create_from_entries(
                before_actions=(), after_actions=(), config_entries=(), user_domains=()),
            input_new_config=SystemConfig.create_from_entries(
                before_actions=(), after_actions=(), config_entries=(), user_domains=()),
            input_error_handler=MockSuccessErrorHandler(),
            expected=SystemConfig.create_from_entries(
                before_actions=(), after_actions=(), config_entries=(), user_domains=()),
        ),
        'all actions succeed returns new config': RunActionsDataset(
            input_old_config=SystemConfig.create_from_entries(
                before_actions=(),
                after_actions=(),
                config_entries=[MockDomainConfigEntry(
                    ('a',), MockUserDomain('test-a'))],
                user_domains=[MockUserDomain('test-a')],
            ),
            input_new_config=SystemConfig.create_from_entries(
                before_actions=(),
                after_actions=(),
                config_entries=[MockDomainConfigEntry(
                    ('b',), MockUserDomain('test-b'))],
                user_domains=[MockUserDomain('test-b')],
            ),
            input_error_handler=MockSuccessErrorHandler(),
            expected=SystemConfig.create_from_entries(
                before_actions=(),
                after_actions=(),
                config_entries=[MockDomainConfigEntry(
                    ('b',), MockUserDomain('test-b'))],
                user_domains=[MockUserDomain('test-b')],
            ),
        ),
        'first domain action fails returns old config state': RunActionsDataset(
            input_old_config=SystemConfig.create_from_entries(
                before_actions=(),
                after_actions=(),
                config_entries=[MockDomainConfigEntry(
                    ('a',), MockUserDomain('test-a'))],
                user_domains=[MockUserDomain('test-a')],
            ),
            input_new_config=SystemConfig.create_from_entries(
                before_actions=(),
                after_actions=(),
                config_entries=[MockDomainConfigEntry(
                    ('b',), MockUserDomain('test-b'))],
                user_domains=[MockUserDomain('test-b')],
            ),
            input_error_handler=MockFailErrorHandler(),
            expected=SystemConfig.create_from_entries(
                before_actions=(),
                after_actions=(),
                config_entries=[MockDomainConfigEntry(
                    ('a',), MockUserDomain('test-a'))],
                user_domains=[MockUserDomain('test-a')],
            ),
        ),
    })
    def test_run_actions(self, dataset: RunActionsDataset) -> None:
        # Arrange
        manager = SystemManager(
            old_config=dataset.input_old_config,
            new_config=dataset.input_new_config,
            executor=MockSystemExecutor(),
            error_handler=dataset.input_error_handler,
        )

        # Act
        with patch('builtins.print'):
            result = manager.run_actions()

        # Assert
        self.assertEqual(dataset.expected, result)

    @dataclass
    class BeforeAndAfterActionsDataset:
        input_old_config: SystemConfig
        input_new_config: SystemConfig
        expected: SystemConfig
        expected_scripts: list[str]

    @datasets({
        'before action added': BeforeAndAfterActionsDataset(
            input_old_config=make_system_config(),
            input_new_config=make_system_config(
                before_actions=(BEFORE_ACTION,)),
            expected=make_system_config(before_actions=(BEFORE_ACTION,)),
            expected_scripts=['echo before'],
        ),
        'after action added': BeforeAndAfterActionsDataset(
            input_old_config=make_system_config(),
            input_new_config=make_system_config(after_actions=(AFTER_ACTION,)),
            expected=make_system_config(after_actions=(AFTER_ACTION,)),
            expected_scripts=['echo after'],
        ),
        'before action removed is not run': BeforeAndAfterActionsDataset(
            input_old_config=make_system_config(
                before_actions=(BEFORE_ACTION,)),
            input_new_config=make_system_config(),
            expected=make_system_config(),
            expected_scripts=[],
        ),
        'after action removed is not run': BeforeAndAfterActionsDataset(
            input_old_config=make_system_config(after_actions=(AFTER_ACTION,)),
            input_new_config=make_system_config(),
            expected=make_system_config(),
            expected_scripts=[],
        ),
        'unchanged before action is re-run when the config changes': BeforeAndAfterActionsDataset(
            input_old_config=make_system_config(
                before_actions=(BEFORE_ACTION,),
                config_entries=[ENTRY_A],
                user_domains=[DOMAIN_A],
            ),
            input_new_config=make_system_config(
                before_actions=(BEFORE_ACTION,),
                config_entries=[ENTRY_B],
                user_domains=[DOMAIN_B],
            ),
            expected=make_system_config(
                before_actions=(BEFORE_ACTION,),
                config_entries=[ENTRY_B],
                user_domains=[DOMAIN_B],
            ),
            expected_scripts=['echo before'],
        ),
        'before and after around a domain change': BeforeAndAfterActionsDataset(
            input_old_config=make_system_config(
                config_entries=[ENTRY_A],
                user_domains=[DOMAIN_A],
            ),
            input_new_config=make_system_config(
                before_actions=(BEFORE_ACTION,),
                after_actions=(AFTER_ACTION,),
                config_entries=[ENTRY_B],
                user_domains=[DOMAIN_B],
            ),
            expected=make_system_config(
                before_actions=(BEFORE_ACTION,),
                after_actions=(AFTER_ACTION,),
                config_entries=[ENTRY_B],
                user_domains=[DOMAIN_B],
            ),
            expected_scripts=['echo before', 'echo after'],
        ),
    })
    def test_run_actions_with_before_and_after_actions(
        self,
        dataset: BeforeAndAfterActionsDataset,
    ) -> None:
        """Test the resulting config and the scripts that were executed."""

        # Arrange
        executor = MockSystemExecutor()
        manager = SystemManager(
            old_config=dataset.input_old_config,
            new_config=dataset.input_new_config,
            executor=executor,
            error_handler=MockSuccessErrorHandler(),
        )

        # Act
        with patch('builtins.print'):
            actual = manager.run_actions()

        # Assert
        self.assertEqual(dataset.expected, actual)
        self.assertEqual(
            executor.shell_mock.call_args_list,
            [call(script) for script in dataset.expected_scripts],
        )

    @dataclass
    class ErrorRecoveryDataset:
        input_statuses: tuple[ErrorHandler.Status, ...]
        expected: SystemConfig
        expected_handler_calls: int

    @datasets({
        'before action fails, nothing is committed': ErrorRecoveryDataset(
            input_statuses=(ErrorHandler.Status.FAILED,),
            expected=make_system_config(
                config_entries=[ENTRY_A],
                user_domains=[DOMAIN_A],
            ),
            expected_handler_calls=1,
        ),
        'before action skipped, remaining changes are committed': ErrorRecoveryDataset(
            input_statuses=(
                ErrorHandler.Status.SKIPPED,
                ErrorHandler.Status.SUCCESS,
                ErrorHandler.Status.SUCCESS,
                ErrorHandler.Status.SUCCESS,
            ),
            expected=make_system_config(
                after_actions=(AFTER_ACTION,),
                config_entries=[ENTRY_B],
                user_domains=[DOMAIN_B],
            ),
            expected_handler_calls=4,
        ),
        'remove action fails, only the before action is committed': ErrorRecoveryDataset(
            input_statuses=(
                ErrorHandler.Status.SUCCESS,
                ErrorHandler.Status.FAILED,
            ),
            expected=make_system_config(
                before_actions=(BEFORE_ACTION,),
                config_entries=[ENTRY_A],
                user_domains=[DOMAIN_A],
            ),
            expected_handler_calls=2,
        ),
        'remove action skipped, the old entry is retained': ErrorRecoveryDataset(
            input_statuses=(
                ErrorHandler.Status.SUCCESS,
                ErrorHandler.Status.SKIPPED,
                ErrorHandler.Status.SUCCESS,
                ErrorHandler.Status.SUCCESS,
            ),
            expected=make_system_config(
                before_actions=(BEFORE_ACTION,),
                after_actions=(AFTER_ACTION,),
                config_entries=[ENTRY_B, ENTRY_A],
                user_domains=[DOMAIN_B, DOMAIN_A],
            ),
            expected_handler_calls=4,
        ),
        'add action fails, the removal is still committed': ErrorRecoveryDataset(
            input_statuses=(
                ErrorHandler.Status.SUCCESS,
                ErrorHandler.Status.SUCCESS,
                ErrorHandler.Status.FAILED,
            ),
            expected=make_system_config(
                before_actions=(BEFORE_ACTION,),
            ),
            expected_handler_calls=3,
        ),
        'after action fails, all config changes are committed': ErrorRecoveryDataset(
            input_statuses=(
                ErrorHandler.Status.SUCCESS,
                ErrorHandler.Status.SUCCESS,
                ErrorHandler.Status.SUCCESS,
                ErrorHandler.Status.FAILED,
            ),
            expected=make_system_config(
                before_actions=(BEFORE_ACTION,),
                config_entries=[ENTRY_B],
                user_domains=[DOMAIN_B],
            ),
            expected_handler_calls=4,
        ),
        'after action skipped, it is not committed': ErrorRecoveryDataset(
            input_statuses=(
                ErrorHandler.Status.SUCCESS,
                ErrorHandler.Status.SUCCESS,
                ErrorHandler.Status.SUCCESS,
                ErrorHandler.Status.SKIPPED,
            ),
            expected=make_system_config(
                before_actions=(BEFORE_ACTION,),
                config_entries=[ENTRY_B],
                user_domains=[DOMAIN_B],
            ),
            expected_handler_calls=4,
        ),
        'everything succeeds': ErrorRecoveryDataset(
            input_statuses=(ErrorHandler.Status.SUCCESS,),
            expected=make_system_config(
                before_actions=(BEFORE_ACTION,),
                after_actions=(AFTER_ACTION,),
                config_entries=[ENTRY_B],
                user_domains=[DOMAIN_B],
            ),
            expected_handler_calls=4,
        ),
    })
    def test_run_actions_error_recovery(self, dataset: ErrorRecoveryDataset) -> None:
        """Test the partially applied config returned for each failure point."""

        # Arrange
        error_handler = MockSequencedErrorHandler(*dataset.input_statuses)
        manager = SystemManager(
            old_config=make_system_config(
                config_entries=[ENTRY_A],
                user_domains=[DOMAIN_A],
            ),
            new_config=make_system_config(
                before_actions=(BEFORE_ACTION,),
                after_actions=(AFTER_ACTION,),
                config_entries=[ENTRY_B],
                user_domains=[DOMAIN_B],
            ),
            executor=MockSystemExecutor(),
            error_handler=error_handler,
        )

        # Act
        with patch('builtins.print'):
            actual = manager.run_actions()

        # Assert
        self.assertEqual(dataset.expected, actual)
        self.assertEqual(error_handler.calls, dataset.expected_handler_calls)

    @dataclass
    class UnexpectedErrorDataset:
        fixture_exception: BaseException
        expected_prints: list[str]

    @datasets({
        'unexpected exception': UnexpectedErrorDataset(
            fixture_exception=RuntimeError('boom'),
            expected_prints=[
                'An unexpected error occurred during the configuration update:',
            ],
        ),
        'keyboard interrupt': UnexpectedErrorDataset(
            fixture_exception=KeyboardInterrupt(),
            expected_prints=[
                'System Configuration Update interrupted by user.',
            ],
        ),
    })
    def test_run_actions_with_unexpected_errors(self, dataset: UnexpectedErrorDataset) -> None:
        """Test that the error is reported and the old config is returned."""

        # Arrange
        manager = SystemManager(
            old_config=make_system_config(
                config_entries=[ENTRY_A],
                user_domains=[DOMAIN_A],
            ),
            new_config=make_system_config(
                before_actions=(BEFORE_ACTION,),
                config_entries=[ENTRY_A],
                user_domains=[DOMAIN_A],
            ),
            executor=MockRaisingSystemExecutor(dataset.fixture_exception),
            error_handler=MockSuccessErrorHandler(),
        )

        # Act
        with patch('builtins.print') as mock_print:
            actual = manager.run_actions()

        # Assert
        self.assertEqual(
            make_system_config(
                config_entries=[ENTRY_A],
                user_domains=[DOMAIN_A],
            ),
            actual,
        )
        mock_print.assert_has_calls(
            [call(text) for text in dataset.expected_prints],
            any_order=False,
        )

    @dataclass
    class EqualityDataset:
        input_manager: SystemManager
        input_other: object
        expected_equal: bool

    @datasets({
        'same configs': EqualityDataset(
            input_manager=SystemManager(
                old_config=make_system_config(config_entries=[ENTRY_A]),
                new_config=make_system_config(config_entries=[ENTRY_B]),
                executor=MockSystemExecutor(),
                error_handler=MockSuccessErrorHandler(),
            ),
            input_other=SystemManager(
                old_config=make_system_config(config_entries=[ENTRY_A]),
                new_config=make_system_config(config_entries=[ENTRY_B]),
                executor=MockSystemExecutor(),
                error_handler=MockFailErrorHandler(),
            ),
            expected_equal=True,
        ),
        'different old config': EqualityDataset(
            input_manager=SystemManager(
                old_config=make_system_config(config_entries=[ENTRY_A]),
                new_config=make_system_config(config_entries=[ENTRY_B]),
                executor=MockSystemExecutor(),
                error_handler=MockSuccessErrorHandler(),
            ),
            input_other=SystemManager(
                old_config=make_system_config(),
                new_config=make_system_config(config_entries=[ENTRY_B]),
                executor=MockSystemExecutor(),
                error_handler=MockSuccessErrorHandler(),
            ),
            expected_equal=False,
        ),
        'not a system manager': EqualityDataset(
            input_manager=SystemManager(
                old_config=make_system_config(),
                new_config=make_system_config(),
                executor=MockSystemExecutor(),
                error_handler=MockSuccessErrorHandler(),
            ),
            input_other='manager',
            expected_equal=False,
        ),
    })
    def test_equality(self, dataset: EqualityDataset) -> None:
        """Test that managers compare by their old and new configs only."""

        # Act & Assert
        if dataset.expected_equal:
            self.assertEqual(dataset.input_manager, dataset.input_other)
        else:
            self.assertNotEqual(dataset.input_manager, dataset.input_other)


class TestSystemConfigTransitioner(TestCase):
    """Test the incremental transition between two configurations."""

    @dataclass
    class GetSystemConfigDataset:
        input_old_entries: list[MockDomainConfigEntry]
        input_updates: list[tuple[MockDomainConfigEntry |
                                  None, MockDomainConfigEntry | None]]
        expected_entry_ids: list[ConfigEntryId]

    @datasets({
        'initial state returns old entries in order': GetSystemConfigDataset(
            input_old_entries=[
                MockDomainConfigEntry(('a',), MockUserDomain('d')),
                MockDomainConfigEntry(('b',), MockUserDomain('d')),
            ],
            input_updates=[],
            expected_entry_ids=[('a',), ('b',)],
        ),
        'after adding entry new comes first': GetSystemConfigDataset(
            input_old_entries=[MockDomainConfigEntry(
                ('a',), MockUserDomain('d'))],
            input_updates=[
                (None, MockDomainConfigEntry(('b',), MockUserDomain('d')))],
            expected_entry_ids=[('b',), ('a',)],
        ),
        'after removing entry it is gone': GetSystemConfigDataset(
            input_old_entries=[
                MockDomainConfigEntry(('a',), MockUserDomain('d')),
                MockDomainConfigEntry(('b',), MockUserDomain('d')),
            ],
            input_updates=[(MockDomainConfigEntry(
                ('a',), MockUserDomain('d')), None)],
            expected_entry_ids=[('b',)],
        ),
        'after updating entry new version replaces old': GetSystemConfigDataset(
            input_old_entries=[MockDomainConfigEntry(
                ('a',), MockUserDomain('d'))],
            input_updates=[
                (
                    MockDomainConfigEntry(('a',), MockUserDomain('d')),
                    MockDomainConfigEntry(('a',), MockUserDomain('d2')),
                ),
            ],
            expected_entry_ids=[('a',)],
        ),
        'after removing all entries result is empty': GetSystemConfigDataset(
            input_old_entries=[
                MockDomainConfigEntry(('a',), MockUserDomain('d')),
                MockDomainConfigEntry(('b',), MockUserDomain('d')),
            ],
            input_updates=[
                (MockDomainConfigEntry(('a',), MockUserDomain('d')), None),
                (MockDomainConfigEntry(('b',), MockUserDomain('d')), None),
            ],
            expected_entry_ids=[],
        ),
    })
    def test_get_system_config_entry_ids(self, dataset: GetSystemConfigDataset) -> None:
        # Arrange
        old_config = SystemConfig.create_from_entries(
            before_actions=(),
            after_actions=(),
            config_entries=dataset.input_old_entries,
            user_domains=[MockUserDomain('d'), MockUserDomain('d2')],
        )
        new_config = SystemConfig.create_from_entries(
            before_actions=(), after_actions=(), config_entries=(), user_domains=())
        transitioner = SystemConfigTransitioner.create_from_system_configs(
            old_config, new_config)

        # Act
        for old_entry, new_entry in dataset.input_updates:
            transitioner.update_config_entry(old_entry, new_entry)
        result = transitioner.get_system_config()

        # Assert
        self.assertEqual(dataset.expected_entry_ids,
                         list(result.config_entries.keys()))

    @dataclass
    class DomainResolutionDataset:
        input_entries: list[DomainConfigEntry]
        input_old_domains: dict[str, UserDomain]
        input_new_domains: dict[str, UserDomain]
        input_builtin_domains: dict[str, Domain]
        expected_domains: dict[str, UserDomain]
        expected_new_instance_keys: list[str]

    @datasets({
        'used new domain is included': DomainResolutionDataset(
            input_entries=[MockDomainConfigEntry(('a',), MockUserDomain('test-domain'))],
            input_old_domains={},
            input_new_domains={'test-domain': MockUserDomain('test-domain')},
            input_builtin_domains={},
            expected_domains={'test-domain': MockUserDomain('test-domain')},
            expected_new_instance_keys=[],
        ),
        'unused new domain is excluded': DomainResolutionDataset(
            input_entries=[MockDomainConfigEntry(('a',), MockUserDomain('used'))],
            input_old_domains={},
            input_new_domains={'used': MockUserDomain('used'), 'unused': MockUserDomain('unused')},
            input_builtin_domains={},
            expected_domains={'used': MockUserDomain('used')},
            expected_new_instance_keys=[],
        ),
        'used old domain not in new not builtin is included': DomainResolutionDataset(
            input_entries=[MockDomainConfigEntry(('a',), MockUserDomain('old-domain'))],
            input_old_domains={'old-domain': MockUserDomain('old-domain')},
            input_new_domains={},
            input_builtin_domains={},
            expected_domains={'old-domain': MockUserDomain('old-domain')},
            expected_new_instance_keys=[],
        ),
        'used old domain in new uses new instance': DomainResolutionDataset(
            input_entries=[MockDomainConfigEntry(('a',), MockUserDomain('shared'))],
            input_old_domains={'shared': MockUserDomain('shared')},
            input_new_domains={'shared': MockUserDomain('shared')},
            input_builtin_domains={},
            expected_domains={'shared': MockUserDomain('shared')},
            expected_new_instance_keys=['shared'],
        ),
        'used old domain in builtin is excluded': DomainResolutionDataset(
            input_entries=[MockDomainConfigEntry(('a',), MockUserDomain('builtin-domain'))],
            input_old_domains={'builtin-domain': MockUserDomain('builtin-domain')},
            input_new_domains={},
            input_builtin_domains={'builtin-domain': MockUserDomain('builtin-domain')},
            expected_domains={},
            expected_new_instance_keys=[],
        ),
    })
    def test_domain_resolution(self, dataset: DomainResolutionDataset) -> None:
        # Arrange
        no_actions: list[Action] = []
        transitioner = SystemConfigTransitioner(
            before_actions_transitioner=SequenceTransitioner[Action].create_from_old_items(no_actions),
            after_actions_transitioner=SequenceTransitioner[Action].create_from_old_items(no_actions),
            config_entries_transitioner=SequenceTransitioner[DomainConfigEntry].create_from_old_items(dataset.input_entries),
            old_domains=dataset.input_old_domains,
            new_domains=dataset.input_new_domains,
            builtin_domains=dataset.input_builtin_domains,
        )

        # Act
        result = transitioner.get_system_config()

        # Assert
        self.assertEqual(dataset.expected_domains, result.domains)
        for key in dataset.expected_new_instance_keys:
            self.assertIs(dataset.input_new_domains[key], result.domains[key])
