# pyright: strict

from abc import ABCMeta
from enum import Enum, EnumMeta

from sysconf.system.error_handler import FailureResolution


class ABCEnumMeta(ABCMeta, EnumMeta):
    pass


class ChoicePromptOptionEnum(FailureResolution, Enum, metaclass=ABCEnumMeta):

    def __init__(self, key: str, prompt: str) -> None:
        self.key = key
        self.prompt = prompt

    def get_key(self) -> str:
        return self.key

    def get_prompt(self) -> str:
        return self.prompt
