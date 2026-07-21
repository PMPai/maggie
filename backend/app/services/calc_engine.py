"""
Pure calculation engine for contract billing.
No DB imports. All money uses Decimal. Deterministic + unit-testable.
"""
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP, ROUND_DOWN, ROUND_HALF_EVEN
from enum import Enum


class TaxMode(str, Enum):
    EXCLUSIVE = "EXCLUSIVE"
    INCLUSIVE = "INCLUSIVE"
    MIXED = "MIXED"


class RoundingPolicy(str, Enum):
    ROUND_HALF_UP = "ROUND_HALF_UP"
    ROUND_DOWN = "ROUND_DOWN"
    BANKERS = "BANKERS"


class CalculationMethod(str, Enum):
    QUANTITY = "QUANTITY"
    LUMP_SUM = "LUMP_SUM"
    PERCENTAGE = "PERCENTAGE"
    MILESTONE = "MILESTONE"
    ALLOWANCE = "ALLOWANCE"
    ADJUSTMENT = "ADJUSTMENT"
    HEADING = "HEADING"


ROUNDING_MAP = {
    RoundingPolicy.ROUND_HALF_UP: ROUND_HALF_UP,
    RoundingPolicy.ROUND_DOWN: ROUND_DOWN,
    RoundingPolicy.BANKERS: ROUND_HALF_EVEN,
}


class OverclaimError(Exception):
    pass


class ValidationIssueCode(str, Enum):
    OVERCLAIM = "OVERCLAIM"
    NEGATIVE_QTY = "NEGATIVE_QTY"
    STALE_PRICE = "STALE_PRICE"
    PRIOR_MISMATCH = "PRIOR_MISMATCH"
    NON_BILLABLE = "NON_BILLABLE"
    HEADING_NOT_BILLABLE = "HEADING_NOT_BILLABLE"
    MISSING_RETENTION = "MISSING_RETENTION"
    TAX_MISMATCH = "TAX_MISMATCH"
    MISSING_MILESTONE = "MISSING_MILESTONE"
    MISSING_DOCUMENT = "MISSING_DOCUMENT"
    UNAPPROVED_VARIATION = "UNAPPROVED_VARIATION"
    DUPLICATE_PERIOD = "DUPLICATE_PERIOD"


@dataclass
class ValidationIssue:
    code: ValidationIssueCode
    field_name: str
    message: str
    severity: str = "ERROR"  # ERROR or WARNING


@dataclass
class ItemInput:
    item_id: str
    calculation_method: CalculationMethod
    unit_price: Decimal
    contract_quantity: Decimal
    is_heading: bool
    is_billable: bool
    retention_applicable: bool
    line_amount: Decimal = Decimal("0")  # for LUMP_SUM


@dataclass
class RuleInput:
    rule_type: str  # RETENTION_HOLD, RETENTION_RELEASE, etc.
    rate: Decimal
    calculation_base: str  # CURRENT_PERIOD, CUMULATIVE
    contract_item_id: str | None = None  # None = contract-level


@dataclass
class LineInput:
    contract_item_id: str
    previous_approved_quantity: Decimal
    current_claimed_quantity: Decimal
    current_approved_quantity: Decimal
    unit_price_snapshot: Decimal
    milestone_approved: bool = True
    user_explanation: str = ""
    direct_amount: Decimal | None = None  # for LUMP_SUM direct entry


@dataclass
class LineResult:
    contract_item_id: str
    current_completed_amount: Decimal
    cumulative_approved_quantity: Decimal
    retention_held: Decimal
    retention_released: Decimal
    deduction_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    net_amount: Decimal
    validation_issues: list[ValidationIssue] = field(default_factory=list)


@dataclass
class ApplicationTotals:
    gross_completed_amount: Decimal
    retention_held_amount: Decimal
    retention_released_amount: Decimal
    deduction_amount: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    invoice_amount: Decimal
    lines: list[LineResult]


def _round(value: Decimal, policy: RoundingPolicy, granularity: Decimal = Decimal("1")) -> Decimal:
    quant = granularity if granularity > 0 else Decimal("1")
    return value.quantize(quant, rounding=ROUNDING_MAP[policy])


def calc_line_current(
    item: ItemInput,
    line: LineInput,
    rules: list[RuleInput],
    tax_rate: Decimal,
    tax_mode: TaxMode,
    rounding_policy: RoundingPolicy,
    rounding_granularity: Decimal = Decimal("1"),
) -> LineResult:
    """Calculate a single billing line for the current period."""
    issues: list[ValidationIssue] = []

    # Validation
    if item.is_heading:
        issues.append(ValidationIssue(ValidationIssueCode.HEADING_NOT_BILLABLE, "calculation_method", "Heading items cannot be billed", "ERROR"))
    if not item.is_billable:
        issues.append(ValidationIssue(ValidationIssueCode.NON_BILLABLE, "is_billable", "Item is not billable", "ERROR"))
    if line.current_claimed_quantity < 0:
        issues.append(ValidationIssue(ValidationIssueCode.NEGATIVE_QTY, "current_claimed_quantity", "Quantity cannot be negative", "ERROR"))
    if line.unit_price_snapshot != item.unit_price:
        issues.append(ValidationIssue(ValidationIssueCode.STALE_PRICE, "unit_price_snapshot", "Price snapshot does not match contract version price", "ERROR"))

    # Calculate current completed amount based on method
    if item.calculation_method == CalculationMethod.QUANTITY:
        current_amount = line.current_approved_quantity * line.unit_price_snapshot
    elif item.calculation_method == CalculationMethod.LUMP_SUM:
        if line.direct_amount is not None:
            current_amount = line.direct_amount
        else:
            current_amount = (line.current_approved_quantity / Decimal("100")) * item.line_amount
    elif item.calculation_method == CalculationMethod.MILESTONE:
        if not line.milestone_approved:
            current_amount = Decimal("0")
            issues.append(ValidationIssue(ValidationIssueCode.MISSING_MILESTONE, "milestone", "Milestone not yet approved", "ERROR"))
        else:
            current_amount = item.line_amount
    elif item.calculation_method == CalculationMethod.PERCENTAGE:
        current_amount = (line.current_approved_quantity / Decimal("100")) * item.line_amount
    elif item.calculation_method == CalculationMethod.ADJUSTMENT:
        current_amount = line.direct_amount or (line.current_approved_quantity * line.unit_price_snapshot)
    else:
        current_amount = Decimal("0")

    current_amount = _round(current_amount, rounding_policy, Decimal("0.01"))

    # Retention
    retention_held = Decimal("0")
    if item.retention_applicable:
        for rule in rules:
            if rule.rule_type == "RETENTION_HOLD" and (rule.contract_item_id is None or rule.contract_item_id == item.item_id):
                base = current_amount  # CURRENT_PERIOD base
                retention_held += _round(base * rule.rate, rounding_policy, Decimal("0.01"))

    # Taxable amount (EXCLUSIVE mode: tax on top; INCLUSIVE: tax included)
    taxable_amount = current_amount - retention_held
    if tax_mode == TaxMode.INCLUSIVE:
        tax_amount = _round(taxable_amount - (taxable_amount / (Decimal("1") + tax_rate)), rounding_policy, Decimal("0.01"))
        invoice_portion = taxable_amount
    else:
        tax_amount = _round(taxable_amount * tax_rate, rounding_policy, Decimal("0.01"))
        invoice_portion = taxable_amount + tax_amount

    cumulative_qty = line.previous_approved_quantity + line.current_approved_quantity

    return LineResult(
        contract_item_id=line.contract_item_id,
        current_completed_amount=current_amount,
        cumulative_approved_quantity=cumulative_qty,
        retention_held=retention_held,
        retention_released=Decimal("0"),  # Release handled by ledger entries
        deduction_amount=Decimal("0"),  # Deductions handled at application level
        taxable_amount=taxable_amount,
        tax_amount=tax_amount,
        net_amount=invoice_portion,
        validation_issues=issues,
    )


def calc_application(
    lines: list[LineResult],
    retention_released_amount: Decimal,
    deduction_amount: Decimal,
    tax_rate: Decimal,
    tax_mode: TaxMode,
    rounding_policy: RoundingPolicy,
    rounding_granularity: Decimal = Decimal("1"),
) -> ApplicationTotals:
    """Aggregate line results into application totals."""
    gross = sum((l.current_completed_amount for l in lines), Decimal("0"))
    retention_held = sum((l.retention_held for l in lines), Decimal("0"))

    # Taxable = gross - retention_held - deductions + retention_released
    taxable = gross - retention_held + retention_released_amount - deduction_amount
    taxable = _round(taxable, rounding_policy, Decimal("0.01"))

    if tax_mode == TaxMode.INCLUSIVE:
        tax = _round(taxable - (taxable / (Decimal("1") + tax_rate)), rounding_policy, Decimal("0.01"))
        invoice = taxable
    else:
        tax = _round(taxable * tax_rate, rounding_policy, Decimal("0.01"))
        invoice = taxable + tax

    invoice = _round(invoice, rounding_policy, rounding_granularity)

    return ApplicationTotals(
        gross_completed_amount=gross,
        retention_held_amount=retention_held,
        retention_released_amount=retention_released_amount,
        deduction_amount=deduction_amount,
        taxable_amount=taxable,
        tax_amount=tax,
        invoice_amount=invoice,
        lines=lines,
    )


def check_quantity_limit(
    contract_quantity: Decimal,
    approved_variation_qty: Decimal,
    previous_approved_quantity: Decimal,
    current_claimed_quantity: Decimal,
) -> None:
    """Raise OverclaimError if cumulative claimed exceeds available quantity."""
    available = contract_quantity + approved_variation_qty
    cumulative = previous_approved_quantity + current_claimed_quantity
    if cumulative > available:
        raise OverclaimError(
            f"Cumulative quantity {cumulative} exceeds available {available} "
            f"(contract {contract_quantity} + variations {approved_variation_qty})"
        )
