from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable


class PermissionTier(str, Enum):
    READ = "read"          # read-only, auto-allowed
    ACTION = "action"       # changes state, needs one confirmation
    CRITICAL = "critical"   # significant/irreversible impact, needs explicit double confirmation


@dataclass
class Tool:
    name: str
    description: str
    tier: PermissionTier
    parameters: dict
    handler: Callable[..., Any] = field(repr=False)

    def to_anthropic_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }

    def run(self, **kwargs) -> str:
        return self.handler(**kwargs)
