# pyright: strict

from sysconf.config.domains import Domain, DomainConfig, DomainManager
from sysconf.domains.builtins import builtin_domains

domains: list[Domain[DomainConfig, DomainManager]] = [
    *builtin_domains,
]

domains_by_key: dict[str, Domain[DomainConfig, DomainManager]] = {
    domain.get_key(): domain
    for domain
    in domains
}

# todo: check for key clashes
