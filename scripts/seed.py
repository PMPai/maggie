"""Seed sample data for 25-032 and 24-023. Run: python scripts/seed.py"""
import asyncio
import json
import uuid
from pathlib import Path
from decimal import Decimal
from datetime import date
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.identity import Organization, User, Role, UserRole, UserRoleEnum
from app.models.project import Project, ProjectMember, ProjectMemberRoleEnum, Company
from app.models.contract import Contract, ContractVersion, ContractItem, PaymentRule, ContractVersionStatus, TaxMode, RoundingPolicy, CalculationMethod
from app.models.billing import PaymentApplication, PaymentApplicationLine, ApplicationStatus

SAMPLE_DIR = Path(__file__).parent.parent / "sample-data"


def _date(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


async def seed_project(data: dict, org_id: uuid.UUID, user_id: uuid.UUID):
    async with async_session_factory() as db:
        # Create project
        proj = Project(
            organization_id=org_id,
            internal_project_code=data["project"]["internal_project_code"],
            project_name=data["project"]["project_name"],
            description=data["project"].get("description"),
            currency=data["project"]["currency"],
            default_tax_rate=Decimal(data["project"]["default_tax_rate"]),
            created_by=user_id, updated_by=user_id,
        )
        db.add(proj)
        await db.flush()

        # Add user as project member
        member = ProjectMember(project_id=proj.id, user_id=user_id, project_role=ProjectMemberRoleEnum.PROJECT_MANAGER, created_by=user_id, updated_by=user_id)
        db.add(member)

        # Create contract
        c = data["contract"]
        contract = Contract(
            organization_id=org_id, project_id=proj.id,
            external_contract_no=c["external_contract_no"], contract_name=c["contract_name"],
            currency=c["currency"], tax_mode=TaxMode(c["tax_mode"]), tax_rate=Decimal(c["tax_rate"]),
            rounding_policy=RoundingPolicy(c["rounding_policy"]),
            created_by=user_id, updated_by=user_id,
        )
        db.add(contract)
        await db.flush()

        # Create versions
        for v in data["versions"]:
            version = ContractVersion(
                organization_id=org_id, contract_id=contract.id, version_no=v["version_no"],
                version_type=v["version_type"], amount_ex_tax=Decimal(v["amount_ex_tax"]),
                tax_amount=Decimal(v["tax_amount"]), amount_inc_tax=Decimal(v["amount_inc_tax"]),
                status=ContractVersionStatus(v["status"]), change_reason=v.get("change_reason"),
                created_by=user_id, updated_by=user_id,
            )
            db.add(version)
            await db.flush()
            if v["status"] == "APPROVED":
                contract.active_version_id = version.id
                contract.original_amount_ex_tax = Decimal(v["amount_ex_tax"])
                contract.original_tax_amount = Decimal(v["tax_amount"])
                contract.original_amount_inc_tax = Decimal(v["amount_inc_tax"])
                contract.status = "ACTIVE"

            # Create items for v1
            if v["version_no"] == 1:
                # Build line_no -> item_id map for parent linking
                line_map = {}
                for item_data in data.get("items_v1", []):
                    parent_id = line_map.get(item_data.get("parent_line_no")) if item_data.get("parent_line_no") else None
                    item = ContractItem(
                        organization_id=org_id, contract_version_id=version.id,
                        parent_item_id=parent_id, line_no=item_data["line_no"],
                        item_code=item_data.get("item_code"),
                        source_description=item_data["source_description"],
                        unit=item_data.get("unit"),
                        contract_quantity=Decimal(item_data.get("contract_quantity", "0")),
                        unit_price=Decimal(item_data.get("unit_price", "0")),
                        line_amount=Decimal(item_data.get("line_amount", "0")),
                        calculation_method=CalculationMethod(item_data.get("calculation_method", "QUANTITY")),
                        is_heading=item_data.get("is_heading", False),
                        is_billable=item_data.get("is_billable", True),
                        retention_applicable=True,
                        sort_order=len(line_map),
                        created_by=user_id, updated_by=user_id,
                    )
                    db.add(item)
                    await db.flush()
                    line_map[item_data["line_no"]] = item.id

                # Create payment rules
                for pr in data.get("payment_rules", []):
                    rule = PaymentRule(
                        organization_id=org_id, contract_version_id=version.id,
                        rule_type=pr["rule_type"], rule_name=pr["rule_name"],
                        rate=Decimal(pr["rate"]), calculation_base=pr["calculation_base"],
                        condition_code=pr.get("condition_code"),
                        created_by=user_id, updated_by=user_id,
                    )
                    db.add(rule)

        # Create applications
        for app_data in data.get("applications", []):
            app = PaymentApplication(
                organization_id=org_id, project_id=proj.id, contract_id=contract.id,
                contract_version_id=contract.active_version_id,
                application_no=app_data["application_no"], period_no=app_data["period_no"],
                period_start=_date(app_data.get("period_start")), period_end=_date(app_data.get("period_end")),
                application_date=_date(app_data.get("application_date")),
                status=ApplicationStatus(app_data["status"]),
                currency=contract.currency,
                gross_completed_amount=Decimal(app_data.get("gross_completed_amount", "0")),
                retention_held_amount=Decimal(app_data.get("retention_held_amount", "0")),
                taxable_amount=Decimal(app_data.get("taxable_amount", "0")),
                tax_amount=Decimal(app_data.get("tax_amount", "0")),
                invoice_amount=Decimal(app_data.get("invoice_amount", "0")),
                retention_released_amount=Decimal(app_data.get("retention_released_amount", "0")),
                deduction_amount=Decimal(app_data.get("deduction_amount", "0")),
                created_by=user_id, updated_by=user_id,
            )
            db.add(app)

        # Create deductions
        from app.models.deduction import Deduction, DeductionType, TaxTreatment, DeductionStatus
        for ded_data in data.get("deductions", []):
            ded = Deduction(
                organization_id=org_id, project_id=proj.id, contract_id=contract.id,
                deduction_no=ded_data["deduction_no"],
                deduction_type=DeductionType(ded_data["deduction_type"]),
                description=ded_data.get("description"),
                amount=Decimal(ded_data["amount"]),
                tax_treatment=TaxTreatment(ded_data.get("tax_treatment", "TAXABLE")),
                tax_amount=Decimal(ded_data.get("tax_amount", "0")),
                effective_date=_date(ded_data.get("effective_date")),
                status=DeductionStatus(ded_data.get("status", "APPROVED")),
                approved_by=user_id,
                created_by=user_id, updated_by=user_id,
            )
            db.add(ded)

        # Create invoices
        from app.models.invoice import Invoice, InvoiceType, InvoiceStatus
        for inv_data in data.get("invoices", []):
            inv = Invoice(
                organization_id=org_id, project_id=proj.id, contract_id=contract.id,
                invoice_no=inv_data["invoice_no"],
                invoice_type=InvoiceType(inv_data.get("invoice_type", "STANDARD")),
                issue_date=_date(inv_data.get("issue_date")),
                amount_ex_tax=Decimal(inv_data["amount_ex_tax"]),
                tax_amount=Decimal(inv_data["tax_amount"]),
                amount_inc_tax=Decimal(inv_data["amount_inc_tax"]),
                tax_rate=Decimal(inv_data.get("tax_rate", "0.05")),
                status=InvoiceStatus(inv_data.get("status", "ISSUED")),
                source=inv_data.get("source", "MANUAL"),
                created_by=user_id, updated_by=user_id,
            )
            db.add(inv)

        # Create collections
        from app.models.collection import Collection, CollectionStatus
        for col_data in data.get("collections", []):
            col = Collection(
                organization_id=org_id, project_id=proj.id, contract_id=contract.id,
                receipt_no=col_data["receipt_no"],
                receipt_date=_date(col_data.get("receipt_date")),
                amount_received=Decimal(col_data["amount_received"]),
                payment_method=col_data.get("payment_method", "BANK_TRANSFER"),
                status=CollectionStatus(col_data.get("status", "CONFIRMED")),
                created_by=user_id, updated_by=user_id,
            )
            db.add(col)

        await db.commit()
        print(f"Seeded: {data['project']['internal_project_code']}")


async def main():
    async with async_session_factory() as db:
        result = await db.execute(select(Organization).where(Organization.code == "MAGGIE"))
        org = result.scalar_one()
        result = await db.execute(select(User).where(User.email == "admin@maggie.local"))
        user = result.scalar_one()

    for f in ["25-032.json", "24-023.json"]:
        with open(SAMPLE_DIR / f, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        await seed_project(data, org.id, user.id)


if __name__ == "__main__":
    asyncio.run(main())
