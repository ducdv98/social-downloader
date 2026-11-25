from dataclasses import dataclass, field
from enum import StrEnum


class ErrorCode(StrEnum):
    LINK_INVALID = "link.invalid"
    LINK_UNSUPPORTED = "link.unsupported"
    SERVICE_DISABLED = "service.disabled"


@dataclass(frozen=True)
class ExtractError:
    code: ErrorCode
    context: dict[str, str] = field(default_factory=dict)
