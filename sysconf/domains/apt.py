# pyright: strict

from typing import Self
from sysconf.config.domains import Domain, DomainAction, DomainConfig, DomainManager
from sysconf.config.serialization import YamlSerializable
from sysconf.system.executor import SystemExecutor
from sysconf.utils.diff import Diff


class Apt(Domain['AptConfig', 'AptManager']):
    """
    Domain for apt package manager, can install/remove packages.
    """

    def get_key(self) -> str:
        return 'apt'

    def get_domain_config(self, data: YamlSerializable) -> 'AptConfig':
        return AptConfig.create_from_data(data)

    def get_domain_manager(self, old_config: 'AptConfig', new_config: 'AptConfig') -> 'AptManager':
        return AptManager(old_config, new_config)


class AptConfig(DomainConfig):
    """
    Domain config for apt package manager.
    """

    def __init__(self, packages: tuple[str, ...]) -> None:
        super().__init__()

        self.packages: tuple[str, ...] = packages

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AptConfig):
            return False
        return self.packages == other.packages

    def __repr__(self) -> str:
        return f"AptConfig(packages={self.packages})"

    @classmethod
    def create_from_data(cls, data: YamlSerializable) -> Self:
        if data is None:
            return cls(packages=())

        assert isinstance(data, list)
        for package in data:
            assert isinstance(package, str)

        packages: tuple[str, ...] = tuple(str(p) for p in data)

        return cls(packages=packages)


class AptAction(DomainAction):
    """
    Action to apply apt package manager config changes.
    """

    def __init__(self, package: str) -> None:
        super().__init__()
        self.package = package


class AptInstallAction(AptAction):
    """
    Action to install a package using apt.
    """

    def __init__(self, package: str) -> None:
        super().__init__(package)

    def __repr__(self) -> str:
        return f"AptInstallAction(package={self.package})"

    def get_description(self) -> str:
        return f"APT install package {self.package}"

    def run(self, executor: SystemExecutor) -> None:
        executor.exec('sudo', 'apt-get', 'install', '-y', self.package)


class AptRemoveAction(AptAction):
    """
    Action to remove a package using apt.
    """

    def __init__(self, package: str) -> None:
        super().__init__(package)

    def __repr__(self) -> str:
        return f"AptRemoveAction(package={self.package})"

    def get_description(self) -> str:
        return f"APT remove package {self.package}"

    def run(self, executor: SystemExecutor) -> None:
        executor.exec('sudo', 'apt-get', 'remove', '-y', self.package)


class AptManager(DomainManager):
    """
    Manager to create apt actions based on config changes.
    """

    def __init__(
        self,
        old_config: AptConfig,
        new_config: AptConfig
    ) -> None:
        super().__init__()

        self.old_config = old_config
        self.new_config = new_config

    def get_actions(self) -> list[AptAction]:
        actions: list[AptAction] = []

        diff: Diff[str] = Diff[str].create_from_iterables(
            self.old_config.packages,
            self.new_config.packages,
        )

        # Packages to remove
        for package in diff.exclusive_a:
            actions.append(AptRemoveAction(package))

        # Packages to install
        for package in diff.exclusive_b:
            actions.append(AptInstallAction(package))

        return actions
