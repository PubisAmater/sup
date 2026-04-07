import enum


class RoleEnum(str, enum.Enum):
    SUPERADMIN = "superadmin"
    CEO = "ceo"
    CEO_1 = "ceo_1"
    CEO_2 = "ceo_2"
    MIDDLE = "middle"
    LINE = "line"


ROLE_HIERARCHY: dict[RoleEnum, int] = {
    RoleEnum.SUPERADMIN: 0,
    RoleEnum.CEO: 1,
    RoleEnum.CEO_1: 2,
    RoleEnum.CEO_2: 3,
    RoleEnum.MIDDLE: 4,
    RoleEnum.LINE: 5,
}


def has_permission(user_role: RoleEnum, required_role: RoleEnum) -> bool:
    return ROLE_HIERARCHY.get(user_role, 99) <= ROLE_HIERARCHY.get(required_role, 99)
