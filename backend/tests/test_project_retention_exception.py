"""Test #6: Project-level retention exception / balance computation.

Retention balance = SUM(HOLD) - SUM(RELEASE) - SUM(REVERSAL).
Releasing more than held results in a negative balance (no silent cap),
so callers must guard against over-release.
"""
import uuid
from decimal import Decimal

import pytest

from app.models.billing import RetentionEntry, RetentionEntryType
from app.models.project import Project
from app.models.contract import Contract
from app.services.retention_service import get_balance


async def _setup_contract(db):
    project = Project(
        internal_project_code=f"P-{uuid.uuid4().hex[:8]}",
        project_name="Test Project",
    )
    db.add(project)
    await db.flush()

    contract = Contract(
        project_id=project.id,
        external_contract_no=f"C-{uuid.uuid4().hex[:8]}",
        contract_name="Test Contract",
    )
    db.add(contract)
    await db.commit()
    return project, contract


def _hold(db, project, contract, amount, description=None):
    entry = RetentionEntry(
        project_id=project.id,
        contract_id=contract.id,
        entry_type=RetentionEntryType.HOLD,
        amount=Decimal(amount),
        description=description,
    )
    db.add(entry)
    return entry


def _release(db, project, contract, amount, description=None):
    entry = RetentionEntry(
        project_id=project.id,
        contract_id=contract.id,
        entry_type=RetentionEntryType.RELEASE,
        amount=Decimal(amount),
        description=description,
    )
    db.add(entry)
    return entry


def _reversal(db, project, contract, amount, reversal_of_id=None, description=None):
    entry = RetentionEntry(
        project_id=project.id,
        contract_id=contract.id,
        entry_type=RetentionEntryType.REVERSAL,
        amount=Decimal(amount),
        reversal_of_id=reversal_of_id,
        description=description,
    )
    db.add(entry)
    return entry


@pytest.mark.asyncio
async def test_balance_sum_of_holds(db):
    project, contract = await _setup_contract(db)

    _hold(db, project, contract, "1000", "hold 1")
    _hold(db, project, contract, "2000", "hold 2")
    await db.commit()

    balance = await get_balance(contract.id, db)
    assert balance == Decimal("3000")


@pytest.mark.asyncio
async def test_balance_decreases_on_release(db):
    project, contract = await _setup_contract(db)

    _hold(db, project, contract, "3000")
    _release(db, project, contract, "1000")
    await db.commit()

    balance = await get_balance(contract.id, db)
    assert balance == Decimal("2000")


@pytest.mark.asyncio
async def test_balance_subtracts_reversal(db):
    project, contract = await _setup_contract(db)

    h = _hold(db, project, contract, "3000")
    await db.flush()
    _release(db, project, contract, "1000")
    _reversal(db, project, contract, "500", reversal_of_id=h.id)
    await db.commit()

    # balance = SUM(HOLD) - SUM(RELEASE) - SUM(REVERSAL) = 3000 - 1000 - 500 = 1500
    balance = await get_balance(contract.id, db)
    assert balance == Decimal("1500")


@pytest.mark.asyncio
async def test_empty_balance_is_zero(db):
    project, contract = await _setup_contract(db)
    balance = await get_balance(contract.id, db)
    assert balance == Decimal("0")


@pytest.mark.asyncio
async def test_releasing_more_than_held_yields_negative_balance(db):
    project, contract = await _setup_contract(db)

    _hold(db, project, contract, "1000")
    _release(db, project, contract, "1500")
    await db.commit()

    balance = await get_balance(contract.id, db)
    # The service does not silently cap at zero; it surfaces the over-release
    # as a negative balance so callers can detect the problem.
    assert balance == Decimal("-500")
    assert balance < Decimal("0")
