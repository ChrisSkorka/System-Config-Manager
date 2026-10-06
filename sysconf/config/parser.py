# pyright: strict

from abc import ABC, abstractmethod
from typing import Iterable, Type, cast

from sysconf.config import domain_registry
from sysconf.config.actions import Action, ShellAction
from sysconf.config.domains import Domain, DomainConfigEntry
from sysconf.config.serialization import YamlSerializable
from sysconf.config.settings import ToolSettings
from sysconf.config.system_config import SystemConfig
from sysconf.domains.user_domains import UserDomain, UserListDomain, UserMapDomain
from sysconf.utils.validation import ValidationError, validate, validate_type


VERSION_1 = '1'


class SystemConfigParser(ABC):
    """
    Abstract base class for system configuration parsers.

    A parser converts the deserialized data (dicts, lists, scalars) into a SystemConfig object.
    """

    def __init__(self, domains_by_key: dict[str, Domain]):
        super().__init__()

        self.domains_by_key = domains_by_key

    @abstractmethod
    def parse_data(self, data: YamlSerializable) -> SystemConfig:
        """
        Parse the given data into a SystemConfig object.

        Also performs schema validation.
        Args:
            data (YamlSerializable): The data to parse.
        Returns:
            SystemConfig: The parsed & validated system configuration.
        """
        pass  # pragma: no cover

    @staticmethod
    def get_parsers_by_version() -> dict[str, Type['SystemConfigParser']]:
        """
        Get a mapping of version strings to parser classes.
        """
        return {
            VERSION_1: SystemConfigParserV1,
        }

    @staticmethod
    def get_parser(data: YamlSerializable) -> 'SystemConfigParser':
        """
        Get the appropriate parser for the given data based on its version.

        This validates the 'version' key but does not validate the rest of the data, the returned
        parser is responsible for validating the rest of the data.

        Args:
            data (YamlSerializable): The data to get the parser for.
        Returns:
            SystemConfigParser: The appropriate parser for the given data.
        """

        # validate version key exists
        assert validate_type(
            data,
            dict,
            'Config must be a mapping at the top level',
        )
        validate(
            'version' in data,
            "Config must contain a 'version' key",
        )

        version = str(data['version'])
        parsers = SystemConfigParser.get_parsers_by_version()

        # validate version is supported
        validate(
            version in parsers,
            f"Unsupported version: {version}, supported versions: {list(parsers.keys())}",
        )

        return parsers[version](domain_registry.domains_by_key)


class SystemConfigParserV1(SystemConfigParser):
    """
    System configuration parser for version 1.
    """

    def parse_data(self, data: YamlSerializable) -> SystemConfig:

        assert validate_type(
            data,
            dict,
            'Config must be a mapping at the top level',
        )

        # version is not part of the config data
        data = {k: v for k, v in data.items() if k != 'version'}

        validate(
            'config' in data,
            'Config must contain a \'config\' key',
        )
        settings_data = data.get('system-config-manager') or {}
        user_domains = data.get('domains') or {}
        before_scripts = data.get('before') or []
        after_scripts = data.get('after') or []
        config_items = data['config'] or []

        # validate data
        assert validate_type(
            user_domains,
            dict,
            'domains must be a mapping of domain keys to domain specifications',
        )
        for domain_key, domain_spec in user_domains.items():
            assert validate_type(
                domain_key,
                str,
                'domain keys must be strings',
            )
            assert validate_type(
                domain_spec,
                dict,
                'domain specifications must be mappings',
            )
            validate(
                'type' in domain_spec,
                'domain specifications must contain a `type` key',
            )

        assert validate_type(
            before_scripts,
            list,
            'before scripts must be a list',
        )

        assert validate_type(
            after_scripts,
            list,
            'after scripts must be a list',
        )

        assert validate_type(
            config_items,
            list,
            'config must be a list of domain mappings',
        )
        for config_item in config_items:
            assert validate_type(
                config_item,
                dict,
                'each config item must be a mapping of domain keys to domain data',
            )

        assert validate_type(
            settings_data,
            dict,
            f"'{'system-config-manager'}' must be a mapping",
        )
        for setting_key in settings_data.keys():
            validate(
                setting_key in ('editor',),
                f"Unknown '{'system-config-manager'}' setting: {setting_key}",
            )
        editor = settings_data.get('editor')
        if editor is not None:
            assert validate_type(
                editor,
                str,
                f"'{'system-config-manager'}.{'editor'}' must be a string",
            )
            validate(
                bool(editor.strip()),
                f"'{'system-config-manager'}.{'editor'}' must not be empty",
            )

        # parse settings
        settings = ToolSettings(editor=editor)

        # parse user domains
        user_domains_by_key: dict[str, UserDomain] = {}
        for domain_key, domain_spec in user_domains.items():
            assert validate_type(
                domain_spec,
                dict,
                f'Domain \'{domain_key}\' specification must be a mapping',
            )
            domain_type = str(domain_spec['type'])

            match domain_type:
                case 'list':
                    add_script = domain_spec.get('add')
                    remove_script = domain_spec.get('remove')
                    path_depth = domain_spec.get('depth', 0)
                    assert validate_type(
                        add_script,
                        str,
                        f'Invalid \'add\' for domain \'{domain_key}\'',
                    )
                    assert validate_type(
                        remove_script,
                        str,
                        f'Invalid \'remove\' for domain \'{domain_key}\'',
                    )
                    assert validate_type(
                        path_depth,
                        int,
                        f'Invalid \'depth\' for domain \'{domain_key}\'',
                    )

                    domain = UserListDomain.create_from_specs(
                        key=domain_key,
                        path_depth=path_depth,
                        add_script=add_script,
                        remove_script=remove_script,
                    )

                    user_domains_by_key[domain_key] = domain
                case 'map':
                    add_script = domain_spec.get('add')
                    update_script = domain_spec.get('update')
                    remove_script = domain_spec.get('remove')
                    path_depth = domain_spec.get('depth', 1)
                    assert validate_type(
                        add_script,
                        str,
                        f'Invalid \'add\' for domain \'{domain_key}\'',
                    )
                    assert validate_type(
                        update_script,
                        str,
                        f'Invalid \'update\' for domain \'{domain_key}\'',
                    )
                    assert validate_type(
                        remove_script,
                        str,
                        f'Invalid \'remove\' for domain \'{domain_key}\'',
                    )
                    assert validate_type(
                        path_depth,
                        int,
                        f'Invalid \'depth\' for domain \'{domain_key}\'',
                    )

                    domain = UserMapDomain.create_from_specs(
                        key=domain_key,
                        path_depth=path_depth,
                        add_script=add_script,
                        update_script=update_script,
                        remove_script=remove_script,
                    )

                    user_domains_by_key[domain_key] = domain
                case _:
                    raise ValidationError(
                        f'Invalid domain type: {domain_type}',
                    )

        domains = {
            **self.domains_by_key,
            **user_domains_by_key,
        }

        # parse before and after scripts
        before_actions: Iterable[Action] = tuple(
            ShellAction.create_from_serialized(script)
            for script in before_scripts
        )
        after_actions: Iterable[Action] = tuple(
            ShellAction.create_from_serialized(script)
            for script in after_scripts
        )

        # parse domain data
        config_entries: Iterable[DomainConfigEntry] = tuple(
            entry
            for config_item in config_items
            if isinstance(config_item, dict)
            for domain_key, entries in config_item.items()
            for entry in domains[domain_key].get_config_entries(
                entries,
            )
        )

        return SystemConfig.create_from_entries(
            before_actions,
            after_actions,
            config_entries,
            tuple(user_domains_by_key.values()),
            settings,
        )


class SystemConfigRenderer:
    """
    Renders a SystemConfig object into a serializable format (e.g., dicts, lists, scalars).
    """

    def render_config(self, system_config: SystemConfig) -> YamlSerializable:
        """
        Render the given SystemConfig object into a serializable format.

        Args:
            system_config (SystemConfig): The system configuration to render.
        Returns:
            YamlSerializable: The rendered configuration data.
        """

        # render settings
        settings: dict[str, YamlSerializable] = {
            'editor': system_config.settings.editor
        }

        # render domains
        domains = {
            domain.get_key(): {
                'type': 'list',
                'depth': domain.path_depth,
                'add': domain.add_script,
                'remove': domain.remove_script,
            } if isinstance(domain, UserListDomain)
            else {
                'type': 'map',
                'depth': domain.path_depth,
                'add': domain.add_script,
                'update': domain.update_script,
                'remove': domain.remove_script,
            } if isinstance(domain, UserMapDomain)
            else None
            for domain in system_config.domains.values()
        }

        # render before and after scripts
        before_items = [
            action.render()
            for action in system_config.before_actions
        ]
        after_items = [
            action.render()
            for action in system_config.after_actions
        ]

        # render each domain's entries
        entries_grouped_by_domain = self.get_entries_grouped_by_domain(
            system_config.config_entries.values(),
        )
        config_items: list[dict[str, YamlSerializable]] = [
            {domain.get_key(): domain.render_config_entries(entries)}
            for domain, entries in entries_grouped_by_domain
        ]

        return cast(
            dict[str, YamlSerializable],
            {
                'version': VERSION_1,
                'system-config-manager': settings,
                'before': before_items,
                'after': after_items,
                'config': config_items,
                'domains': domains,
            },
        )

    def get_entries_grouped_by_domain(
        self,
        entries: Iterable[DomainConfigEntry],
    ) -> tuple[tuple[Domain, list[DomainConfigEntry]], ...]:
        """
        Group the given configuration entries by their domain.

        Notes:
        - The order of entries is preserved.
        - Domains may appear multiple times if their entries are not contiguous.
        """

        entries_grouped_by_domain: list[tuple[Domain,
                                              list[DomainConfigEntry]]] = []

        for entry in entries:
            # get the domain of the last group (if it exists)
            current_domain: Domain | None = entries_grouped_by_domain[-1][0] \
                if entries_grouped_by_domain \
                else None

            # if the entry's domain is different from the current domain,
            # start a new group
            if current_domain != entry.get_domain():
                entries_grouped_by_domain.append((
                    entry.get_domain(),
                    [],
                ))

            entries_grouped_by_domain[-1][1].append(entry)

        return tuple(entries_grouped_by_domain)
