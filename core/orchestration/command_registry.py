from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class CommandSpec:
    name: str
    handler: Callable[..., Any]
    description: str = ""


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, CommandSpec] = {}

    def register(self, name: str, handler: Callable[..., Any], description: str = "") -> None:
        self._commands[name] = CommandSpec(name=name, handler=handler, description=description)

    def get(self, name: str) -> CommandSpec | None:
        return self._commands.get(name)
