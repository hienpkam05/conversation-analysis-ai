from enum import StrEnum


class Region(StrEnum):
    NORTH = "north"
    CENTRAL = "central"
    SOUTH = "south"


class EntityStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CandidateStatus(StrEnum):
    NEW = "new"
    CONTACTED = "contacted"
    CLOSED = "closed"


def enum_values(enum_class: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_class]
