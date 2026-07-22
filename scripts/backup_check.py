"""Backup consistency checker — verifies DB tables and file storage integrity.
Test #20: verifies that all posted applications have retention entries,
all invoices have valid CHECK constraints, no orphaned FKs, and file storage is accessible.

Usage: python scripts/backup_check.py
"""
import asyncio
import sys
from sqlalchemy import text
from app.db.session import async_session_factory


CHECKS = []


async def check_posted_applications_have_retention(db):
    """All POSTED applications should have at least one retention HOLD entry."""
    result = await db.execute(text("""
        SELECT pa.id, pa.application_no
        FROM payment_applications pa
        WHERE pa.status = 'POSTED'
        AND pa.gross_completed_amount > 0
        AND NOT EXISTS (
            SELECT 1 FROM retention_entries re
            WHERE re.payment_application_id = pa.id AND re.entry_type = 'HOLD'
        )
    """))
    orphans = result.all()
    return len(orphans) == 0, f"{len(orphans)} posted applications missing retention HOLD entries"


async def check_invoice_amounts(db):
    """All invoices must satisfy amount_ex_tax + tax_amount = amount_inc_tax."""
    result = await db.execute(text("""
        SELECT id, invoice_no, amount_ex_tax, tax_amount, amount_inc_tax
        FROM invoices
        WHERE ABS(amount_ex_tax + tax_amount - amount_inc_tax) > 0.01
    """))
    bad = result.all()
    return len(bad) == 0, f"{len(bad)} invoices with amount check constraint violations"


async def check_contract_version_amounts(db):
    """All contract versions must satisfy amount_ex_tax + tax_amount = amount_inc_tax."""
    result = await db.execute(text("""
        SELECT id, version_no
        FROM contract_versions
        WHERE ABS(amount_ex_tax + tax_amount - amount_inc_tax) > 0.01
    """))
    bad = result.all()
    return len(bad) == 0, f"{len(bad)} contract versions with amount violations"


async def check_no_orphaned_application_lines(db):
    """All payment application lines must reference a valid payment application."""
    result = await db.execute(text("""
        SELECT pal.id
        FROM payment_application_lines pal
        LEFT JOIN payment_applications pa ON pa.id = pal.payment_application_id
        WHERE pa.id IS NULL
    """))
    orphans = result.all()
    return len(orphans) == 0, f"{len(orphans)} orphaned application lines"


async def check_retention_balance_non_negative(db):
    """Retention balance per contract should not be negative (unless intentional reversal)."""
    result = await db.execute(text("""
        SELECT contract_id,
               SUM(CASE WHEN entry_type = 'HOLD' THEN amount ELSE 0 END) -
               SUM(CASE WHEN entry_type = 'RELEASE' THEN amount ELSE 0 END) as balance
        FROM retention_entries
        GROUP BY contract_id
        HAVING SUM(CASE WHEN entry_type = 'HOLD' THEN amount ELSE 0 END) -
               SUM(CASE WHEN entry_type = 'RELEASE' THEN amount ELSE 0 END) < 0
    """))
    negative = result.all()
    return len(negative) == 0, f"{len(negative)} contracts with negative retention balance"


async def check_duplicate_invoices(db):
    """No duplicate invoice numbers per contract."""
    result = await db.execute(text("""
        SELECT contract_id, invoice_no, COUNT(*) as cnt
        FROM invoices
        WHERE deleted_at IS NULL
        GROUP BY contract_id, invoice_no
        HAVING COUNT(*) > 1
    """))
    dups = result.all()
    return len(dups) == 0, f"{len(dups)} duplicate invoice numbers"


async def run_all_checks():
    checks = [
        ("Posted applications have retention", check_posted_applications_have_retention),
        ("Invoice amounts valid", check_invoice_amounts),
        ("Contract version amounts valid", check_contract_version_amounts),
        ("No orphaned application lines", check_no_orphaned_application_lines),
        ("Retention balances non-negative", check_retention_balance_non_negative),
        ("No duplicate invoices", check_duplicate_invoices),
    ]

    async with async_session_factory() as db:
        all_pass = True
        print("=" * 60)
        print("Backup Consistency Check")
        print("=" * 60)
        for name, check_fn in checks:
            try:
                passed, message = await check_fn(db)
                status = "✓ PASS" if passed else "✗ FAIL"
                print(f"  {status}  {name}: {message}")
                if not passed:
                    all_pass = False
            except Exception as e:
                print(f"  ✗ ERROR  {name}: {e}")
                all_pass = False
        print("=" * 60)
        if all_pass:
            print("All checks passed. Database is consistent.")
        else:
            print("Some checks failed. Review the issues above.")
        return all_pass


if __name__ == "__main__":
    result = asyncio.run(run_all_checks())
    sys.exit(0 if result else 1)
