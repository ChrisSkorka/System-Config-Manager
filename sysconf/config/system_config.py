# pyright: strict

from typing import Iterable, Self, Sequence
from sysconf.config.domains import ConfigEntryId, DomainAction, DomainConfigEntry, NoDomainAction
from sysconf.config.actions import Action
from sysconf.system.error_handler import ErrorHandler
from sysconf.system.executor import SystemExecutor
from sysconf.utils.diff import Diff


class SystemConfig:
    """
    Represents the entire system configuration by aggregating multiple domain configurations.
    """

    @classmethod
    def create_from_entries(
        cls,
        before_actions: Sequence[Action],
        after_actions: Sequence[Action],
        config_entries: Sequence[DomainConfigEntry],
    ) -> 'SystemConfig':
        map_ids_to_entries: dict[ConfigEntryId, DomainConfigEntry] = {
            entry.get_id(): entry
            for entry in config_entries
        }

        assert len(map_ids_to_entries) == len(config_entries), \
            'Duplicate ConfigEntryId found in config entries'

        return cls(
            before_actions=tuple(before_actions),
            after_actions=tuple(after_actions),
            config_entries=map_ids_to_entries,
        )

    def __init__(
        self,
        before_actions: tuple[Action, ...],
        after_actions: tuple[Action, ...],
        config_entries: dict[ConfigEntryId, DomainConfigEntry],
    ) -> None:
        super().__init__()

        self.before_actions = before_actions
        self.after_actions = after_actions
        self.config_entries = config_entries

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SystemConfig):
            return False

        return self.config_entries == other.config_entries

    def __repr__(self) -> str:
        return f'SystemConfig({self.config_entries})'


class SystemManager:
    """
    Manages the application of system configurations across multiple domains.
    """

    def __init__(
        self,
        old_config: SystemConfig,
        new_config: SystemConfig,
        executor: SystemExecutor,
        error_handler: ErrorHandler,
    ) -> None:
        self.old_config = old_config
        self.new_config = new_config
        self.executor = executor
        self.error_handler = error_handler

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, SystemManager):
            return False
        return self.old_config == value.old_config \
            and self.new_config == value.new_config

    def get_domain_actions(self) -> Iterable[DomainAction]:
        """
        Plan the actions required to transition from the old configuration to the new configuration.
        Returns:
            A list of actions to be performed.
        """
        actions: list[DomainAction] = []

        domain_diff = Diff[ConfigEntryId].create_from_iterables(
            self.old_config.config_entries.keys(),
            self.new_config.config_entries.keys(),
        )

        # remove domains
        # removals occur in reverse order to compared to when they were added
        for entry_id in reversed(domain_diff.exclusive_old):

            old_entry = self.old_config.config_entries[entry_id]
            domain = old_entry.get_domain()
            action = domain.get_action(old_entry, None)
            actions.append(action)

        # add & update domains
        # add & update are combined so we can process them in the order they're
        # listed in the new config
        for key in domain_diff.new:

            old_entry = self.old_config.config_entries[key] \
                if key in self.old_config.config_entries \
                else None
            new_entry = self.new_config.config_entries[key]

            domain = new_entry.get_domain()
            if old_entry is not None:
                assert domain == old_entry.get_domain()

            action = domain.get_action(old_entry, new_entry)
            actions.append(action)

        return actions

    def run_actions(self) -> SystemConfig:
        """
        Get and run all actions required to transition from the old 
        configuration to the new configuration.

        Notes:
        - If an action fails, the user may choose to continue with the remaining
          actions
        - Actions that are NoOp (NoDomainAction) are not run or printed
        """

        diff_before_actions = Diff[Action].create_from_iterables(
            self.old_config.before_actions,
            self.new_config.before_actions,
        )
        diff_after_actions = Diff[Action].create_from_iterables(
            self.old_config.after_actions,
            self.new_config.after_actions,
        )
        actions = self.get_domain_actions()

        has_changes = diff_before_actions.old != diff_before_actions.new \
            or diff_after_actions.old != diff_after_actions.new \
            or any(not isinstance(action, NoDomainAction) for action in actions)

        if not has_changes:
            print('# No changes required.')
            return self.old_config

        config_interpolator = SystemConfigInterpolator.create_from_system_config(
            self.old_config,
        )

        try:
            for action_entry in diff_before_actions.get_entries():
                if action_entry.new_item is not None:
                    new_action = action_entry.new_item
                    status = self.error_handler.try_run(
                        lambda: new_action.run(self.executor),
                    )
                    match status:
                        case ErrorHandler.Status.SUCCESS:
                            pass
                        case ErrorHandler.Status.FAILED:
                            return config_interpolator.get_system_config()
                        case ErrorHandler.Status.SKIPPED:
                            continue

                config_interpolator.update_before_action(
                    action_entry.old_item,
                    action_entry.new_item,
                )

            for action in actions:
                if not isinstance(action, NoDomainAction):
                    print(f'# {action.get_description()}')

                    status = self.error_handler.try_run(
                        lambda: action.run(self.executor),
                    )
                    match status:
                        case ErrorHandler.Status.SUCCESS:
                            pass
                        case ErrorHandler.Status.FAILED:
                            return config_interpolator.get_system_config()
                        case ErrorHandler.Status.SKIPPED:
                            continue

                config_interpolator.update_config_entry(
                    action.get_old_entry(),
                    action.get_new_entry(),
                )

            for action_entry in diff_after_actions.get_entries():
                if action_entry.new_item is not None:
                    new_action = action_entry.new_item
                    status = self.error_handler.try_run(
                        lambda: new_action.run(self.executor),
                    )
                    match status:
                        case ErrorHandler.Status.SUCCESS:
                            pass
                        case ErrorHandler.Status.FAILED:
                            return config_interpolator.get_system_config()
                        case ErrorHandler.Status.SKIPPED:
                            continue

                config_interpolator.update_after_action(
                    action_entry.old_item,
                    action_entry.new_item,
                )

        except KeyboardInterrupt:
            print('System Configuration Update interrupted by user.')
        except Exception as e:
            print('An unexpected error occurred during the configuration update:')
            print(e)

        return config_interpolator.get_system_config()


# todo generalise into generic interpolator & move to new file
class SystemConfigInterpolator:
    """
    Interpolates from one SystemConfig to another one entry at a time.

    This maintains the current state/config of the system at any time as actions
    are run one by one.

    Notes:
    - Only supports a monotonic transition from the one config to new (no backtracking)
    - Internally this will remove or move items from the old list and move them
      or add new ones to the new list
    """

    def __init__(
        self,
        old_before_actions: list[Action],
        new_before_actions: list[Action],
        old_after_actions: list[Action],
        new_after_actions: list[Action],
        old_config_entries: list[DomainConfigEntry],
        new_config_entries: list[DomainConfigEntry],
    ) -> None:
        super().__init__()

        self.old_before_actions = old_before_actions
        self.new_before_actions = new_before_actions
        self.old_after_actions = old_after_actions
        self.new_after_actions = new_after_actions
        self.old_config_entries = old_config_entries
        self.new_config_entries = new_config_entries

    @classmethod
    def create_from_system_config(cls, system_config: SystemConfig) -> Self:
        return cls(
            old_before_actions=list(system_config.before_actions),
            new_before_actions=[],
            old_after_actions=list(system_config.after_actions),
            new_after_actions=[],
            old_config_entries=list(system_config.config_entries.values()),
            new_config_entries=[],
        )

    def update_before_action(
        self,
        old_action: Action | None,
        new_action: Action | None,
    ) -> None:
        """
        Update the current before actions by applying the given action diff to
        the current configuration.
        """

        assert old_action is not None or new_action is not None, \
            f'Cannot update before actions with actions: ' \
            + f'old_action={old_action}, new_action={new_action}'

        if old_action is not None:
            assert old_action in self.old_before_actions, \
                f'Cannot remove {old_action}, it\'s not found in old before actions'

            self.old_before_actions.remove(old_action)

        if new_action is not None:
            assert new_action not in self.new_before_actions, \
                f'Cannot add {new_action}, it already exists in new before actions'

            self.new_before_actions.append(new_action)

    def update_after_action(
        self,
        old_action: Action | None,
        new_action: Action | None,
    ) -> None:
        """
        Update the current after actions by applying the given action diff to
        the current configuration.
        """

        assert old_action is not None or new_action is not None, \
            f'Cannot update after actions with actions: ' \
            + f'old_action={old_action}, new_action={new_action}'

        if old_action is not None:
            assert old_action in self.old_after_actions, \
                f'Cannot remove {old_action}, it\'s not found in old after actions'

            self.old_after_actions.remove(old_action)

        if new_action is not None:
            assert new_action not in self.new_after_actions, \
                f'Cannot add {new_action}, it already exists in new after actions'

            self.new_after_actions.append(new_action)

    def update_config_entry(
        self,
        old_entry: DomainConfigEntry | None,
        new_entry: DomainConfigEntry | None,
    ) -> None:
        """
        Update the current configuration by applying the given entry diff to
        the current configuration.
        """

        assert old_entry is not None or new_entry is not None, \
            f'Cannot update confugation with entries: ' \
            + f'old_entry={old_entry}, new_entry={new_entry}'

        if old_entry is not None:
            assert old_entry in self.old_config_entries, \
                f'Cannot remove {old_entry}, it\'s not found in old config entries'

            self.old_config_entries.remove(old_entry)

        if new_entry is not None:
            assert new_entry not in self.new_config_entries, \
                f'Cannot add {new_entry}, it already exists in new config entries'

            self.new_config_entries.append(new_entry)

    def get_system_config(self) -> SystemConfig:
        """
        Get a SystemConfig instance representing the current configuration state.
        """

        before_actions = tuple(self.new_before_actions) + \
            tuple(self.old_before_actions)
        after_actions = tuple(self.new_after_actions) + \
            tuple(self.old_after_actions)
        config_entries = tuple(self.new_config_entries) + \
            tuple(self.old_config_entries)

        return SystemConfig.create_from_entries(
            before_actions=before_actions,
            after_actions=after_actions,
            config_entries=config_entries,
        )
