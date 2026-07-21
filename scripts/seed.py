"""Seed sample data for 25-032 and 24-023. Run: python scripts/seed.py"""
import asyncio
import json
import uuid
from pathlib import Path
from decimal import Decimal
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.identity import Organization, User, Role, UserRole, UserRoleEnum
from app.models.project import Project, ProjectMember, ProjectMemberRoleEnum, Company
from app.models.contract import Contract, ContractVersion, ContractItem, PaymentRule, ContractVersionStatus, TaxMode, RoundingPolicy, CalculationMethod
from app.models.billing import PaymentApplication, PaymentApplicationLine, ApplicationStatus

SAMPLE_DIR = Path(__file__).parent.parent / "sample-data"


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
                period_start=app_data["period_start"], period_end=app_data["period_end"],
                application_date=app_data["application_date"],
                status=ApplicationStatus(app_data["status"]),
                currency=contract.currency,
                gross_completed_amount=Decimal(app_data.get("gross_completed_amount", "0")),
                retention_held_amount=Decimal(app_data.get("retention_held_amount", "0")),
                taxable_amount=Decimal(app_data.get("taxable_amount", "0")),
                tax_amount=Decimal(app_data.get("tax_amount", "0")),
                invoice_amount=Decimal(app_data.get("invoice_amount", "0")),
                created_by=user_id, updated_by=user_id,
            )
            db.add(app)

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
