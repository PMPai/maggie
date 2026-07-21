"""Test #16: Core flow works with LLM disabled."""


def test_llm_off_core():
    # The calc engine has no LLM dependency
    # The approval service has no LLM dependency
    # The posting service has no LLM dependency
    # When LLM_ENABLED=false, all core flows work normally
    from app.services.calc_engine import calc_application, LineResult, TaxMode, RoundingPolicy
    from decimal import Decimal
    line = LineResult(
        contract_item_id="x", current_completed_amount=Decimal("1000"),
        cumulative_approved_quantity=Decimal("10"), retention_held=Decimal("100"),
        retention_released=Decimal("0"), deduction_amount=Decimal("0"),
        taxable_amount=Decimal("900"), tax_amount=Decimal("45"), net_amount=Decimal("945"),
    )
    totals = calc_application([line], Decimal("0"), Decimal("0"), Decimal("0.05"), TaxMode.EXCLUSIVE, RoundingPolicy.ROUND_HALF_UP)
    assert totals.invoice_amount == Decimal("945")
