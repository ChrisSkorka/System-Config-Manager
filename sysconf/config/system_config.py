# pyright: strict

from typing import Iterable, Sequence
from sysconf.config.domains import ConfigEntryId, DomainAction, DomainConfigEntry, NoDomainAction
from sysconf.system.executor import CommandException, SystemExecutor
from sysconf.utils.diff import Diff


class SystemConfig:
    """
    Represents the entire system configuration by aggregating multiple domain configurations.
    """

    def __init__(
        self,
        config_entries: dict[ConfigEntryId, DomainConfigEntry],
    ) -> None:
        super().__init__()

        self.config_entries = config_entries

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SystemConfig):
            return False

        return self.config_entries == other.config_entries

    def __repr__(self) -> str:
        return f'SystemConfig({self.config_entries})'

    @classmethod
    def create_from_config_entries(
        cls,
        entries: Sequence[DomainConfigEntry],
    ) -> 'SystemConfig':
        map_ids_to_entries: dict[ConfigEntryId, DomainConfigEntry] = {
            entry.get_id(): entry
            for entry in entries
        }

        assert len(map_ids_to_entries) == len(entries), \
            'Duplicate ConfigEntryId found in config entries'

        return cls(
            config_entries=map_ids_to_entries,
        )


class SystemManager:
    """
    Manages the application of system configurations across multiple domains.
    """

    def __init__(self, old_config: SystemConfig, new_config: SystemConfig):
        self.old_config = old_config
        self.new_config = new_config

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, SystemManager):
            return False
        return self.old_config == value.old_config \
            and self.new_config == value.new_config

    def get_actions(self) -> Iterable[DomainAction]:
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
    
    def run_actions(self, executor: SystemExecutor) -> None:
        """
        Get and run all actions required to transition from the old 
        configuration to the new configuration.

        Notes:
        - If an action fails, the user may choose to continue with the remaining
          actions
        - Actions that are NoOp (NoDomainAction) are not run or printed
        """

        actions = self.get_actions()

        if not actions:
            print('# No changes required.')
            return

        for action in actions:
            if not isinstance(action, NoDomainAction):
                print(f'# {action.get_description()}')

                try:
                    action.run(executor)
                except CommandException as e:
                    print(f'An error occurred while executing the command:')
                    print(e.cmdline)
                    print(
                        f'Process exited with code {e.process.returncode}, see output above.',
                    )

                    should_continue = self.get_user_confirmation(
                        'Do you want to continue with the remaining tasks?',
                    )
                    if not should_continue:
                        return
                    else:
                        continue

    def get_user_confirmation(self, prompt: str) -> bool:
        """
        Promt the user for a yes/no confirmation to a prompt.

        Notes:
        - Accepts 'y', 'yes', 'n', 'no' (case insensitive)
        - Allows up to 3 attempts
        - Defaults to false ('no') if no valid input is given in the 3 attempts
        """

        for _ in range(3):  # allow up to 3 attempts
            user_input = input(f'{prompt} (y/n): ').strip().lower()
            if user_input in ('y', 'yes'):
                return True
            elif user_input in ('n', 'no', ''):
                return False

        return False
