# pyright: strict

from typing import cast

from sysconf.config.domains import Domain, DomainConfig, DomainManager
from sysconf.domains.apt import Apt
from sysconf.domains.dconf import DConf
from sysconf.domains.gsettings import GSettings

domains: list[Domain[DomainConfig, DomainManager]] = [
    cast(Domain[DomainConfig, DomainManager], GSettings()),
    cast(Domain[DomainConfig, DomainManager], DConf()),
    cast(Domain[DomainConfig, DomainManager], Apt()),
]

domains_by_key: dict[str, Domain[DomainConfig, DomainManager]] = {
    domain.get_key(): domain
    for domain
    in domains
}

# todo: check for key clashes
