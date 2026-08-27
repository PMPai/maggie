"""add groups, group_roles, user_groups tables and seed default groups"""
import uuid
from alembic import op
import sqlalchemy as sa

revision = "020"
down_revision = "019"
branch_labels = None
depends_on = None

DEFAULT_GROUPS = [
    ("管理员群组", "ADMIN", "系统管理员和合同管理员", True, ["SYSTEM_ADMIN", "CONTRACT_ADMIN"]),
    ("财务群组", "FINANCE", "财务复核、财务人员、造价复核", True, ["FINANCE_REVIEWER", "FINANCE_USER", "COST_REVIEWER"]),
    ("项目组长群组", "LEADER", "项目负责人", True, ["PROJECT_MANAGER"]),
    ("项目人员群组", "LEADER", "项目人员", True, ["PROJECT_USER"]),
    ("审计群组", "AUDITOR", "审计人员", True, ["AUDITOR"]),
    ("只读群组", "VIEWER", "只读用户", True, ["VIEWER"]),
]

ROLE_TO_GROUP = {
    "SYSTEM_ADMIN": "管理员群组",
    "CONTRACT_ADMIN": "管理员群组",
    "FINANCE_REVIEWER": "财务群组",
    "FINANCE_USER": "财务群组",
    "COST_REVIEWER": "财务群组",
    "PROJECT_MANAGER": "项目组长群组",
    "PROJECT_USER": "项目人员群组",
    "AUDITOR": "审计群组",
    "VIEWER": "只读群组",
}


def upgrade():
    conn = op.get_bind()

    conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'groupcategory'"))
    exists = conn.execute(sa.text("SELECT 1 FROM pg_type WHERE typname = 'groupcategory'")).fetchone()
    if not exists:
        op.execute("CREATE TYPE groupcategory AS ENUM ('ADMIN', 'FINANCE', 'LEADER', 'AUDITOR', 'VIEWER')")

    op.execute("""
        CREATE TABLE groups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL REFERENCES organizations(id),
            name VARCHAR(128) NOT NULL,
            category groupcategory NOT NULL,
            description VARCHAR(512),
            status VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
            is_default BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_groups_org_name UNIQUE (organization_id, name)
        )
    """)
    op.execute("CREATE INDEX ix_groups_organization_id ON groups (organization_id)")

    op.execute("""
        CREATE TABLE group_roles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
            role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_group_roles UNIQUE (group_id, role_id)
        )
    """)

    op.execute("""
        CREATE TABLE user_groups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
            organization_id UUID NOT NULL REFERENCES organizations(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_user_groups UNIQUE (user_id, group_id)
        )
    """)

    orgs = conn.execute(sa.text("SELECT id FROM organizations WHERE status = 'ACTIVE'")).fetchall()

    for org_id, in orgs:
        for group_name, category, description, is_default, role_names in DEFAULT_GROUPS:
            group_id = uuid.uuid4()
            conn.execute(
                sa.text("""
                    INSERT INTO groups (id, organization_id, name, category, description, status, is_default)
                    VALUES (:id, :org_id, :name, :category, :description, 'ACTIVE', :is_default)
                """),
                {"id": group_id, "org_id": org_id, "name": group_name, "category": category,
                 "description": description, "is_default": is_default}
            )

            role_rows = conn.execute(
                sa.text("SELECT id, name FROM roles WHERE name::text = ANY(:names)"),
                {"names": role_names}
            ).fetchall()

            for role_id, role_name in role_rows:
                conn.execute(
                    sa.text("INSERT INTO group_roles (id, group_id, role_id) VALUES (:id, :gid, :rid)"),
                    {"id": uuid.uuid4(), "gid": group_id, "rid": role_id}
                )

    users = conn.execute(sa.text("SELECT id, organization_id FROM users WHERE status = 'ACTIVE'")).fetchall()

    for user_id, u_org_id in users:
        user_roles = conn.execute(
            sa.text("""
                SELECT r.name FROM user_roles ur
                JOIN roles r ON r.id = ur.role_id
                WHERE ur.user_id = :uid
            """),
            {"uid": user_id}
        ).fetchall()

        assigned_groups = set()
        for role_name, in user_roles:
            group_name = ROLE_TO_GROUP.get(role_name)
            if group_name:
                assigned_groups.add(group_name)

        for group_name in assigned_groups:
            group_row = conn.execute(
                sa.text("SELECT id FROM groups WHERE organization_id = :org_id AND name = :name"),
                {"org_id": u_org_id, "name": group_name}
            ).fetchone()
            if group_row:
                existing = conn.execute(
                    sa.text("SELECT 1 FROM user_groups WHERE user_id = :uid AND group_id = :gid"),
                    {"uid": user_id, "gid": group_row[0]}
                ).fetchone()
                if not existing:
                    conn.execute(
                        sa.text("INSERT INTO user_groups (id, user_id, group_id, organization_id) VALUES (:id, :uid, :gid, :org_id)"),
                        {"id": uuid.uuid4(), "uid": user_id, "gid": group_row[0], "org_id": u_org_id}
                    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS user_groups CASCADE")
    op.execute("DROP TABLE IF EXISTS group_roles CASCADE")
    op.execute("DROP TABLE IF EXISTS groups CASCADE")
    op.execute("DROP TYPE IF EXISTS groupcategory")