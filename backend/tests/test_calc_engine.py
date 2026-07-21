import pytest
from decimal import Decimal
from app.services.calc_engine import (
    ItemInput, LineInput, RuleInput, calc_line_current, calc_application,
    check_quantity_limit, OverclaimError, CalculationMethod, TaxMode,
    RoundingPolicy, ValidationIssueCode, LineResult, ApplicationTotals
)


class TestContractItemSum:
    """Test #1: Contract item amount sum"""

    def test_quantity_line_amount(self):
        item = ItemInput(
            item_id="i1", calculation_method=CalculationMethod.QUANTITY,
            unit_price=Decimal("1000"), contract_quantity=Decimal("10"),
            is_heading=False, is_billable=True, retention_applicable=True,
        )
        line = LineInput(
            contract_item_id="i1", previous_approved_quantity=Decimal("0"),
            current_claimed_quantity=Decimal("5"), current_approved_quantity=Decimal("5"),
            unit_price_snapshot=Decimal("1000"),
        )
        result = calc_line_current(item, line, [], Decimal("0.05"), TaxMode.EXCLUSIVE, RoundingPolicy.ROUND_HALF_UP)
        assert result.current_completed_amount == Decimal("5000.00")

    def test_multiple_lines_sum(self):
        lines_input = [
            (Decimal("1000"), Decimal("5"), Decimal("5000")),
            (Decimal("500"), Decimal("10"), Decimal("5000")),
            (Decimal("200"), Decimal("3"), Decimal("600")),
        ]
        results = []
        for price, qty, expected in lines_input:
            item = ItemInput(
                item_id="x", calculation_method=CalculationMethod.QUANTITY,
                unit_price=price, contract_quantity=qty * 2, is_heading=False,
                is_billable=True, retention_applicable=False,
            )
            line = LineInput(
                contract_item_id="x", previous_approved_quantity=Decimal("0"),
                current_claimed_quantity=qty, current_approved_quantity=qty,
                unit_price_snapshot=price,
            )
            r = calc_line_current(item, line, [], Decimal("0.05"), TaxMode.EXCLUSIVE, RoundingPolicy.ROUND_HALF_UP)
            results.append(r)
        total = sum((r.current_completed_amount for r in results), Decimal("0"))
        assert total == Decimal("10600.00")


class TestOverclaim:
    """Test #3: Over-quantity blocked"""

    def test_overclaim_raises(self):
        with pytest.raises(OverclaimError) as exc:
            check_quantity_limit(
                contract_quantity=Decimal("100"),
                approved_variation_qty=Decimal("0"),
                previous_approved_quantity=Decimal("80"),
                current_claimed_quantity=Decimal("30"),
            )
        assert "exceeds available" in str(exc.value)

    def test_exact_quantity_ok(self):
        check_quantity_limit(
            contract_quantity=Decimal("100"),
            approved_variation_qty=Decimal("0"),
            previous_approved_quantity=Decimal("80"),
            current_claimed_quantity=Decimal("20"),
        )


class TestRetention:
    """Test #5: Retention calculation"""

    def test_retention_held_10_percent(self):
        item = ItemInput(
            item_id="i1", calculation_method=CalculationMethod.QUANTITY,
            unit_price=Decimal("10000"), contract_quantity=Decimal("100"),
            is_heading=False, is_billable=True, retention_applicable=True,
        )
        line = LineInput(
            contract_item_id="i1", previous_approved_quantity=Decimal("0"),
            current_claimed_quantity=Decimal("10"), current_approved_quantity=Decimal("10"),
            unit_price_snapshot=Decimal("10000"),
        )
        rules = [RuleInput(rule_type="RETENTION_HOLD", rate=Decimal("0.10"), calculation_base="CURRENT_PERIOD")]
        result = calc_line_current(item, line, rules, Decimal("0.05"), TaxMode.EXCLUSIVE, RoundingPolicy.ROUND_HALF_UP)
        assert result.current_completed_amount == Decimal("100000.00")
        assert result.retention_held == Decimal("10000.00")
        assert result.taxable_amount == Decimal("90000.00")

    def test_retention_exempt(self):
        item = ItemInput(
            item_id="i1", calculation_method=CalculationMethod.QUANTITY,
            unit_price=Decimal("10000"), contract_quantity=Decimal("100"),
            is_heading=False, is_billable=True, retention_applicable=False,
        )
        line = LineInput(
            contract_item_id="i1", previous_approved_quantity=Decimal("0"),
            current_claimed_quantity=Decimal("10"), current_approved_quantity=Decimal("10"),
            unit_price_snapshot=Decimal("10000"),
        )
        result = calc_line_current(item, line, [], Decimal("0.05"), TaxMode.EXCLUSIVE, RoundingPolicy.ROUND_HALF_UP)
        assert result.retention_held == Decimal("0")


class TestTaxRounding:
    """Test #8: Tax and rounding"""

    def test_exclusive_tax_5_percent(self):
        item = ItemInput(
            item_id="i1", calculation_method=CalculationMethod.QUANTITY,
            unit_price=Decimal("1000"), contract_quantity=Decimal("10"),
            is_heading=False, is_billable=True, retention_applicable=False,
        )
        line = LineInput(
            contract_item_id="i1", previous_approved_quantity=Decimal("0"),
            current_claimed_quantity=Decimal("1"), current_approved_quantity=Decimal("1"),
            unit_price_snapshot=Decimal("1000"),
        )
        result = calc_line_current(item, line, [], Decimal("0.05"), TaxMode.EXCLUSIVE, RoundingPolicy.ROUND_HALF_UP)
        assert result.tax_amount == Decimal("50.00")
        assert result.net_amount == Decimal("1050.00")

    def test_inclusive_tax(self):
        item = ItemInput(
            item_id="i1", calculation_method=CalculationMethod.QUANTITY,
            unit_price=Decimal("1050"), contract_quantity=Decimal("10"),
            is_heading=False, is_billable=True, retention_applicable=False,
        )
        line = LineInput(
            contract_item_id="i1", previous_approved_quantity=Decimal("0"),
            current_claimed_quantity=Decimal("1"), current_approved_quantity=Decimal("1"),
            unit_price_snapshot=Decimal("1050"),
        )
        result = calc_line_current(item, line, [], Decimal("0.05"), TaxMode.INCLUSIVE, RoundingPolicy.ROUND_HALF_UP)
        # 1050 inc tax -> tax = 1050 - 1050/1.05 = 1050 - 1000 = 50
        assert result.tax_amount == Decimal("50.00")

    def test_application_totals_25_032_period2(self):
        """Verify 25-032 period 2: 施工 401,792 / 保留 74,600 / 未税 327,192 / 税 16,360 / 含税 343,552"""
        line_result = LineResult(
            contract_item_id="p2", current_completed_amount=Decimal("401792.00"),
            cumulative_approved_quantity=Decimal("0"), retention_held=Decimal("74600.00"),
            retention_released=Decimal("0"), deduction_amount=Decimal("0"),
            taxable_amount=Decimal("327192.00"), tax_amount=Decimal("16360.00"),
            net_amount=Decimal("343552.00"),
        )
        totals = calc_application(
            lines=[line_result],
            retention_released_amount=Decimal("0"),
            deduction_amount=Decimal("0"),
            tax_rate=Decimal("0.05"),
            tax_mode=TaxMode.EXCLUSIVE,
            rounding_policy=RoundingPolicy.ROUND_HALF_UP,
        )
        assert totals.gross_completed_amount == Decimal("401792.00")
        assert totals.retention_held_amount == Decimal("74600.00")
        assert totals.taxable_amount == Decimal("327192.00")
        assert totals.tax_amount == Decimal("16360.00")
        assert totals.invoice_amount == Decimal("343552.00")
