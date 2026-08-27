from app.models.identity import UserRoleEnum, GroupCategory


ROLE_TO_CATEGORY: dict[UserRoleEnum, GroupCategory] = {
    UserRoleEnum.SYSTEM_ADMIN: GroupCategory.ADMIN,
    UserRoleEnum.CONTRACT_ADMIN: GroupCategory.ADMIN,
    UserRoleEnum.FINANCE_REVIEWER: GroupCategory.FINANCE,
    UserRoleEnum.FINANCE_USER: GroupCategory.FINANCE,
    UserRoleEnum.COST_REVIEWER: GroupCategory.FINANCE,
    UserRoleEnum.PROJECT_MANAGER: GroupCategory.LEADER,
    UserRoleEnum.PROJECT_USER: GroupCategory.LEADER,
    UserRoleEnum.AUDITOR: GroupCategory.AUDITOR,
    UserRoleEnum.VIEWER: GroupCategory.VIEWER,
}


CATEGORY_ROLES: dict[GroupCategory, list[UserRoleEnum]] = {
    GroupCategory.ADMIN: [UserRoleEnum.SYSTEM_ADMIN, UserRoleEnum.CONTRACT_ADMIN],
    GroupCategory.FINANCE: [UserRoleEnum.FINANCE_REVIEWER, UserRoleEnum.FINANCE_USER, UserRoleEnum.COST_REVIEWER],
    GroupCategory.LEADER: [UserRoleEnum.PROJECT_MANAGER, UserRoleEnum.PROJECT_USER],
    GroupCategory.AUDITOR: [UserRoleEnum.AUDITOR],
    GroupCategory.VIEWER: [UserRoleEnum.VIEWER],
}


DEFAULT_GROUPS: dict[GroupCategory, dict[str, str | list[UserRoleEnum]]] = {
    GroupCategory.ADMIN: {"name": "管理员群组", "roles": CATEGORY_ROLES[GroupCategory.ADMIN]},
    GroupCategory.FINANCE: {"name": "财务群组", "roles": CATEGORY_ROLES[GroupCategory.FINANCE]},
    GroupCategory.LEADER: {"name": "项目组长群组", "roles": [UserRoleEnum.PROJECT_MANAGER]},
    GroupCategory.AUDITOR: {"name": "审计群组", "roles": CATEGORY_ROLES[GroupCategory.AUDITOR]},
    GroupCategory.VIEWER: {"name": "只读群组", "roles": CATEGORY_ROLES[GroupCategory.VIEWER]},
}


def roles_to_categories(roles: list[UserRoleEnum]) -> set[GroupCategory]:
    categories = set()
    for r in roles:
        cat = ROLE_TO_CATEGORY.get(r)
        if cat:
            categories.add(cat)
    return categories


def has_category(roles: list[UserRoleEnum], *cats: GroupCategory) -> bool:
    user_cats = roles_to_categories(roles)
    return any(c in user_cats for c in cats)


def is_admin(roles: list[UserRoleEnum]) -> bool:
    return has_category(roles, GroupCategory.ADMIN)