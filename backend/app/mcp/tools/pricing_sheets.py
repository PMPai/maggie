"""MCP tools for pricing sheet (计价单) CRUD."""
from uuid import UUID
from decimal import Decimal


def register_pricing_sheet_tools(mcp):
    from app.db.session import async_session_factory
    from app.models.contract import Contract, ContractVersion, ContractItem, ContractVersionStatus
    from app.models.collection import Collection, CollectionStatus
    from sqlalchemy import select
    from datetime import datetime, timezone

    @mcp.tool()
    async def list_pricing_sheets(project_id: str) -> list[dict]:
        """List all 计价单 (pricing sheets) for a project."""
        async with async_session_factory() as db:
            result = await db.execute(
                select(Contract, ContractVersion)
                .join(ContractVersion, Contract.active_version_id == ContractVersion.id)
                .where(Contract.project_id == UUID(project_id), Contract.deleted_at.is_(None),
                       ContractVersion.version_type == "QUOTATION")
            )
            return [
                {
                    "contract_id": str(c.id),
                    "version_id": str(v.id),
                    "name": c.contract_name,
                    "status": v.status,
                }
                for c, v in result.all()
            ]

    @mcp.tool()
    async def create_pricing_sheet(project_id: str, name: str = "计价单") -> dict:
        """Create a new 计价单 (pricing sheet)."""
        async with async_session_factory() as db:
            contract = Contract(
                project_id=UUID(project_id),
                external_contract_no=f"PS-{UUID(int=0).hex[:8]}",
                contract_name=name,
                currency="TWD", tax_mode="EXCLUSIVE", tax_rate=Decimal("0.05"),
                status="DRAFT",
            )
            db.add(contract)
            await db.flush()
            version = ContractVersion(
                contract_id=contract.id, version_no=1,
                version_type="QUOTATION", status=ContractVersionStatus.DRAFT,
                amount_ex_tax=Decimal("0"), tax_amount=Decimal("0"), amount_inc_tax=Decimal("0"),
            )
            db.add(version)
            contract.active_version_id = version.id
            await db.commit()
            await db.refresh(contract)
            await db.refresh(version)
            return {"contract_id": str(contract.id), "version_id": str(version.id)}

    @mcp.tool()
    async def add_pricing_sheet_item(version_id: str, name: str, quantity: float, unit_price: float,
                                      unit_cost: float | None = None, unit: str = "",
                                      payment_date: str | None = None) -> dict:
        """Add an item to a pricing sheet."""
        async with async_session_factory() as db:
            from datetime import date as date_type
            item = ContractItem(
                contract_version_id=UUID(version_id),
                line_no=f"ITEM-{UUID(int=0).hex[:4]}",
                source_description=name, unit=unit,
                contract_quantity=Decimal(str(quantity)),
                unit_price=Decimal(str(unit_price)),
                unit_cost=Decimal(str(unit_cost)) if unit_cost else None,
                line_amount=Decimal(str(quantity)) * Decimal(str(unit_price)),
                calculation_method="QUANTITY",
                expected_payment_date=date_type.fromisoformat(payment_date) if payment_date else None,
            )
            db.add(item)
            await db.commit()
            await db.refresh(item)
            return {"id": str(item.id), "line_amount": str(item.line_amount)}

    @mcp.tool()
    async def update_pricing_sheet_item(item_id: str, name: str | None = None, quantity: float | None = None,
                                         unit_price: float | None = None, unit_cost: float | None = None,
                                         payment_date: str | None = None) -> dict:
        """Update a pricing sheet item."""
        async with async_session_factory() as db:
            from datetime import date as date_type
            result = await db.execute(select(ContractItem).where(ContractItem.id == UUID(item_id)))
            item = result.scalar_one_or_none()
            if not item:
                return {"error": "Item not found"}
            if name is not None:
                item.source_description = name
            if quantity is not None:
                item.contract_quantity = Decimal(str(quantity))
            if unit_price is not None:
                item.unit_price = Decimal(str(unit_price))
            if unit_cost is not None:
                item.unit_cost = Decimal(str(unit_cost))
            if payment_date is not None:
                item.expected_payment_date = date_type.fromisoformat(payment_date)
            item.line_amount = (item.contract_quantity or 0) * (item.unit_price or 0)
            await db.commit()
            return {"id": str(item.id), "line_amount": str(item.line_amount)}

    @mcp.tool()
    async def delete_pricing_sheet_item(item_id: str) -> dict:
        """Delete a pricing sheet item."""
        async with async_session_factory() as db:
            result = await db.execute(select(ContractItem).where(ContractItem.id == UUID(item_id)))
            item = result.scalar_one_or_none()
            if not item:
                return {"error": "Item not found"}
            await db.delete(item)
            await db.commit()
            return {"deleted": True}

    @mcp.tool()
    async def approve_pricing_sheet(contract_id: str, version_id: str) -> dict:
        """Approve a 计价单, transitioning it to a signed contract (SIGNED_CONTRACT) and auto-generating PLANNED collections."""
        async with async_session_factory() as db:
            cid, vid = UUID(contract_id), UUID(version_id)
            result = await db.execute(select(Contract).where(Contract.id == cid))
            contract = result.scalar_one_or_none()
            if not contract:
                return {"error": "Contract not found"}
            result = await db.execute(select(ContractVersion).where(ContractVersion.id == vid))
            version = result.scalar_one_or_none()
            if not version:
                return {"error": "Version not found"}

            version.status = ContractVersionStatus.APPROVED
            version.approved_at = datetime.now(timezone.utc)
            if version.version_type == "QUOTATION":
                version.version_type = "SIGNED_CONTRACT"
            contract.active_version_id = vid
            contract.status = "ACTIVE"

            # Auto-generate PLANNED collections
            items_result = await db.execute(
                select(ContractItem).where(
                    ContractItem.contract_version_id == vid,
                    ContractItem.expected_payment_date.isnot(None),
                    ContractItem.is_billable == True,
                )
            )
            for item in items_result.scalars().all():
                col = Collection(
                    project_id=contract.project_id, contract_id=cid,
                    receipt_no=f"PLN-{cid.hex[:8]}-{item.id.hex[:8]}",
                    receipt_date=item.expected_payment_date,
                    amount_received=item.line_amount or Decimal("0"),
                    status=CollectionStatus.PLANNED,
                )
                db.add(col)

            await db.commit()
            return {"status": "approved", "version_type": version.version_type}
