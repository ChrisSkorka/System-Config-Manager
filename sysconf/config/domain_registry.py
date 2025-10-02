from typing import Iterable

from sysconf.config.domains import Domain
from sysconf.domains.gsettings import GSettings


domains: Iterable[Domain] = [
    GSettings(),
]

domains_by_key: dict[str, Domain] = {
    domain.get_key(): domain
    for domain
    in domains
}

# todo: check for key clashes
