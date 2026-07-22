"""contracts, contract_versions, contract_items, payment_rules"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.models.contract import TaxMode, RoundingPolicy, ContractVersionType, ContractVersionStatus, CalculationMethod, PaymentRuleType

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "contracts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("project_id", UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_contract_no", sa.String(64), nullable=False),
        sa.Column("contract_name", sa.String(256), nullable=False),
        sa.Column("customer_company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id")),
        sa.Column("contractor_company_id", UUID(as_uuid=True), sa.ForeignKey("companies.id")),
        sa.Column("signed_date", sa.Date),
        sa.Column("effective_date", sa.Date),
        sa.Column("currency", sa.String(8), nullable=False, server_default="TWD"),
        sa.Column("tax_mode", sa.Enum(TaxMode), nullable=False, server_default="EXCLUSIVE"),
        sa.Column("tax_rate", sa.Numeric(10, 6), nullable=False, server_default="0.05"),
        sa.Column("rounding_policy", sa.Enum(RoundingPolicy), nullable=False, server_default="ROUND_HALF_UP"),
        sa.Column("rounding_granularity", sa.Numeric(18, 2), nullable=False, server_default="1"),
        sa.Column("original_amount_ex_tax", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("original_tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("original_amount_inc_tax", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="DRAFT"),
        sa.Column("active_version_id", UUID(as_uuid=True)),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_contracts_project_id", "contracts", ["project_id"])
    op.create_index("ix_contracts_organization_id", "contracts", ["organization_id"])

    op.create_table(
        "contract_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version_no", sa.Integer, nullable=False),
        sa.Column("version_type", sa.Enum(ContractVersionType), nullable=False),
        sa.Column("effective_date", sa.Date),
        sa.Column("amount_ex_tax", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("amount_inc_tax", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.Enum(ContractVersionStatus), nullable=False, server_default="DRAFT"),
        sa.Column("change_reason", sa.Text),
        sa.Column("source_document_id", UUID(as_uuid=True)),
        sa.Column("approved_by", UUID(as_uuid=True)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("contract_id", "version_no", name="uq_contract_versions"),
        sa.CheckConstraint("amount_ex_tax + tax_amount = amount_inc_tax", name="ck_contract_version_amounts"),
    )
    op.create_index("ix_contract_versions_contract_id", "contract_versions", ["contract_id"])

    op.create_table(
        "contract_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("contract_version_id", UUID(as_uuid=True), sa.ForeignKey("contract_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_item_id", UUID(as_uuid=True), sa.ForeignKey("contract_items.id")),
        sa.Column("line_no", sa.String(32), nullable=False),
        sa.Column("item_code", sa.String(64)),
        sa.Column("source_description", sa.Text, nullable=False),
        sa.Column("normalized_description", sa.Text),
        sa.Column("unit", sa.String(32)),
        sa.Column("contract_quantity", sa.Numeric(18, 4), nullable=False, server_default="0"),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("line_amount", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("calculation_method", sa.Enum(CalculationMethod), nullable=False, server_default="QUANTITY"),
        sa.Column("tax_category", sa.String(32), nullable=False, server_default="STANDARD"),
        sa.Column("retention_applicable", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("retention_exempt_reason", sa.Text),
        sa.Column("is_heading", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_billable", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("source_page", sa.Integer),
        sa.Column("source_bbox_json", JSONB),
        sa.Column("extraction_confidence", sa.Numeric(5, 2)),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_contract_items_contract_version_id", "contract_items", ["contract_version_id"])

    op.create_table(
        "payment_rules",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("contract_version_id", UUID(as_uuid=True), sa.ForeignKey("contract_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_item_id", UUID(as_uuid=True), sa.ForeignKey("contract_items.id")),
        sa.Column("rule_type", sa.Enum(PaymentRuleType), nullable=False),
        sa.Column("rule_name", sa.String(128), nullable=False),
        sa.Column("rate", sa.Numeric(10, 6), nullable=False, server_default="0"),
        sa.Column("condition_code", sa.String(64)),
        sa.Column("condition_description", sa.Text),
        sa.Column("calculation_base", sa.String(32), nullable=False, server_default="CURRENT_PERIOD"),
        sa.Column("release_sequence", sa.Integer),
        sa.Column("effective_from", sa.Date),
        sa.Column("effective_to", sa.Date),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_by", UUID(as_uuid=True)),
        sa.Column("updated_by", UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_payment_rules_contract_version_id", "payment_rules", ["contract_version_id"])

    op.create_foreign_key(
        "fk_contracts_active_version_id",
        "contracts",
        "contract_versions",
        ["active_version_id"],
        ["id"],
    )


def downgrade():
    op.drop_constraint("fk_contracts_active_version_id", "contracts", type_="foreignkey")
    op.drop_table("payment_rules")
    op.drop_table("contract_items")
    op.drop_table("contract_versions")
    op.drop_table("contracts")
