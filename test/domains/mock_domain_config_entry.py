# pyright: strict

from sysconf.config.domains import ConfigEntryId, Domain, DomainConfigEntry


class MockDomainConfigEntry(DomainConfigEntry):

    def __init__(self, entry_id: ConfigEntryId, domain: Domain) -> None:
        self._id = entry_id
        self._domain = domain

    def get_id(self) -> ConfigEntryId:
        return self._id

    def get_domain(self) -> Domain:
        return self._domain

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, MockDomainConfigEntry)
            and self._id == other._id
            and self._domain == other._domain
        )

    def __hash__(self) -> int:
        return hash(self._id)

    def __repr__(self) -> str:
        return f'MockDomainConfigEntry({self._id!r})'
