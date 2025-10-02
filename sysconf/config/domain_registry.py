from typing import Iterable

from sysconf.config.domains import Domain
from sysconf.domains.gsettings import GSettings


domains: Iterable[Domain] = [
    GSettings(),
]

# todo: check for path clashes
