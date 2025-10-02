from sysconf.config.domains import DomainConfig


class SystemConfig:
    """
    Represents the entire system configuration by aggregating multiple domain configurations.
    """

    def __init__(self, data: dict[str, DomainConfig]):
        self.data: dict[str, DomainConfig] = data
