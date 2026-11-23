from enum import StrEnum


class ErrorCode(StrEnum):
    LINK_INVALID = "link.invalid"
    LINK_UNSUPPORTED = "link.unsupported"
    SERVICE_DISABLED = "service.disabled"
