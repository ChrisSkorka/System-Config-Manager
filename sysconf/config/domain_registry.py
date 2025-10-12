# pyright: strict

from sysconf.config.domains import Domain
from sysconf.domains.builtins import builtin_domains

domains: list[Domain] = [
    *builtin_domains,
]

domains_by_key: dict[str, Domain] = {
    domain.get_key(): domain
    for domain
    in domains
}

# todo: check for key clashes
