import uuid
from dataclasses import dataclass
from app.db.session import get_db

SINGLE_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


@dataclass
class CurrentUser:
    id: uuid.UUID
    display_name: str = "Local User"


def get_current_user():
    return CurrentUser(id=SINGLE_USER_ID, display_name="Local User")


def require_role(*roles):
    """No-op dependency — single user has all roles."""
    return get_current_user()


def require_category(*cats):
    """No-op dependency."""
    return get_current_user()


def require_admin():
    """No-op dependency."""
    return get_current_user()


async def require_project_member(project_id=None, current=None, db=None):
    """No-op dependency — single local user has access to all projects."""
    return get_current_user()


__all__ = [
    "get_db", "get_current_user", "require_role", "require_category",
    "require_admin", "CurrentUser", "require_project_member", "SINGLE_USER_ID",
]