# pyright: strict

from sysconf.config.serialization import YamlSerializable


class MockDomainConfig:

    def __init__(self, data: YamlSerializable) -> None:
        self.data = data

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, MockDomainConfig):
            return False

        return self.data == value.data

    @classmethod
    def create_from_data(cls, data: YamlSerializable) -> 'MockDomainConfig':
        return cls(data=data)

    @classmethod
    def default(
        cls,
        data: YamlSerializable | None = None,
    ) -> 'MockDomainConfig':

        data = data or ['item1', 'item2']

        return cls(data=data)
