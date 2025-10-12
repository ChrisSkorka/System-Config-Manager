# pyright: strict


from typing import Callable, Iterable, Self
from sysconf.config.domains import Domain, DomainAction, DomainConfig, DomainManager
from sysconf.config.serialization import YamlSerializable
from sysconf.utils.diff import Diff


Path = tuple[str, ...]  # (keys, ...)
Value = str
PathValuePair = tuple[Path, Value]
ActionFactory = Callable[[Path, Value], DomainAction]


class ListDomain(Domain):

    def __init__(
        self,
        key: str,
        add_action_factory: ActionFactory,
        remove_action_factory: ActionFactory,
    ) -> None:
        super().__init__()

        self._key = key
        self.add_action_factory = add_action_factory
        self.remove_action_factory = remove_action_factory

    def get_key(self) -> str:
        return self._key

    def get_domain_config(self, data: YamlSerializable) -> 'ListConfig':
        return ListConfig.create_from_data(data)

    def get_domain_manager(self, old_config: DomainConfig, new_config: DomainConfig) -> 'ListManager':
        assert isinstance(old_config, ListConfig)
        assert isinstance(new_config, ListConfig)

        return ListManager(
            old_config,
            new_config,
            self.add_action_factory,
            self.remove_action_factory,
        )


class ListConfig(DomainConfig):

    def __init__(self, values: tuple[PathValuePair, ...]) -> None:
        super().__init__()

        self.values: tuple[PathValuePair, ...] = values

    @classmethod
    def create_from_data(cls, data: YamlSerializable) -> Self:
        if data is None:
            return cls(())

        assert isinstance(data, list) or isinstance(data, dict)

        values: tuple[PathValuePair, ...] = tuple(
            cls.get_key_value_pairs((), data),
        )
        return cls(values)

    @staticmethod
    def get_key_value_pairs(keys: tuple[str, ...], value: YamlSerializable) -> Iterable[PathValuePair]:

        # base case:
        if isinstance(value, list):

            # todo: validate that all items are scalar

            yield from (
                (keys, str(item))
                for item in value
            )

        # recursive case:
        elif isinstance(value, dict):
            for key in value:
                yield from ListConfig.get_key_value_pairs(
                    keys + (key,),
                    value[key],
                )

        else:
            raise ValueError(
                f'Invalid value type for list config: {type(value)} ({value}). '
                + 'Scalar values can only occur immediately inside a list'
            )

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, ListConfig):
            return False
        return self.values == value.values


class ListManager(DomainManager):

    def __init__(
        self,
        old: ListConfig,
        new: ListConfig,
        add_action_factory: ActionFactory,
        remove_action_factory: ActionFactory,
    ) -> None:
        super().__init__()

        self.old = old
        self.new = new
        self.add_action_factory = add_action_factory
        self.remove_action_factory = remove_action_factory

    def get_actions(self) -> Iterable[DomainAction]:
        diff: Diff[PathValuePair] = Diff[PathValuePair].create_from_iterables(
            self.old.values,
            self.new.values,
        )

        # removals first, in reverse order
        for keys, item in reversed(diff.exclusive_old):
            yield self.remove_action_factory(keys, item)

        # additions next, in normal order
        for keys, item in diff.exclusive_new:
            yield self.add_action_factory(keys, item)
