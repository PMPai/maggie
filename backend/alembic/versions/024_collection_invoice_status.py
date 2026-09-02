"""update collection + invoice status enums

Revision ID: 024_collection_invoice_status
Revises: 023_add_unit_cost
Create Date: 2026-08-30
"""
from alembic import op

revision = "024_collection_invoice_status"
down_revision = "023_add_unit_cost"
branch_labels = None
depends_on = None


def _rename_enum_value_if_exists(type_name: str, old: str, new: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = '{type_name}')
                  AND enumlabel = '{old}'
            ) THEN
                EXECUTE 'ALTER TYPE {type_name} RENAME VALUE ''{old}'' TO ''{new}''';
            END IF;
        END $$;
        """
    )


def _add_enum_value_if_not_exists(type_name: str, value: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = '{type_name}')
                  AND enumlabel = '{value}'
            ) THEN
                EXECUTE 'ALTER TYPE {type_name} ADD VALUE ''{value}''';
            END IF;
        END $$;
        """
    )


def upgrade() -> None:
    # Collections: PENDING→PLANNED, REVERSED→CANCELLED
    _rename_enum_value_if_exists("collectionstatus", "PENDING", "PLANNED")
    _rename_enum_value_if_exists("collectionstatus", "REVERSED", "CANCELLED")
    _add_enum_value_if_not_exists("collectionstatus", "RECEIVED")

    # Invoices: DRAFT→PLANNED
    _rename_enum_value_if_exists("invoicestatus", "DRAFT", "PLANNED")
    _add_enum_value_if_not_exists("invoicestatus", "SENT")

    # Update any legacy rows before the view is recreated in 025.
    # Wrapped in DO blocks because the enum may already be in the final state.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'collectionstatus')
                  AND enumlabel = 'REVERSED'
            ) THEN
                UPDATE collections SET status='CANCELLED' WHERE status='REVERSED';
            END IF;
            IF EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'collectionstatus')
                  AND enumlabel = 'PENDING'
            ) THEN
                UPDATE collections SET status='PLANNED' WHERE status='PENDING';
            END IF;
            IF EXISTS (
                SELECT 1 FROM pg_enum
                WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = 'invoicestatus')
                  AND enumlabel = 'DRAFT'
            ) THEN
                UPDATE invoices SET status='PLANNED' WHERE status='DRAFT';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    pass
