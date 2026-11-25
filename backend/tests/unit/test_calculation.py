"""Tests unitaires et tests par propriétés (Hypothesis) du moteur de calcul."""

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from invoicing.domain.calculation import CalculationRules, compute_invoice
from invoicing.domain.errors import InvariantViolationError
from invoicing.domain.invoice import LineInput
from invoicing.infrastructure.business_config import load_business_config
from invoicing.settings import REPO_ROOT

RULES = CalculationRules()
D = Decimal


def line(qty: str, price: str, rate: str = "18", discount: str = "0") -> LineInput:
    return LineInput(
        "x", Decimal(qty), Decimal(price), Decimal(rate), discount_rate=Decimal(discount)
    )


def test_simple_invoice() -> None:
    _, totals = compute_invoice([line("20", "5500"), line("10", "4300")], Decimal(0), RULES)
    assert (totals.net_total, totals.vat_total, totals.gross_total) == (
        D(153000),
        D(27540),
        D(180540),
    )


def test_line_then_global_discount() -> None:
    lines, totals = compute_invoice([line("10", "1000", discount="0.1")], Decimal("0.05"), RULES)
    assert lines[0].line_net == 9000
    assert totals.net_total == 8550
    assert totals.global_discount_amount == 450


def test_global_then_line_discount_order_from_config() -> None:
    rules = CalculationRules(discount_order=("globale", "ligne"))
    lines, totals = compute_invoice([line("1", "333", discount="0.1")], Decimal("0.05"), rules)
    # 333 * 0.95 = 316.35 -> 316 (remise globale = 17) ; 316 * 0.90 = 284.4 -> 284
    assert lines[0].line_net == 284
    assert lines[0].line_gross == lines[0].line_net + lines[0].line_vat
    assert totals.net_total == 284
    assert totals.global_discount_amount == 17
    assert totals.gross_total == totals.net_total + totals.vat_total


def test_non_liable_customer_pays_no_vat() -> None:
    _, totals_rate_zero = compute_invoice([line("3", "1000", rate="0")], Decimal(0), RULES)
    assert totals_rate_zero.vat_total == 0
    assert totals_rate_zero.gross_total == 3000

    _, totals_flag = compute_invoice(
        [line("3", "1000", rate="18")], Decimal(0), RULES, vat_liable=False
    )
    assert totals_flag.vat_total == 0
    assert totals_flag.gross_total == 3000


def test_half_franc_is_rounded_up() -> None:
    _, totals = compute_invoice([line("1", "2.5", rate="0")], Decimal(0), RULES)
    assert totals.net_total == 3


def test_decimal_quantity_computes_exact_totals() -> None:
    lines, totals = compute_invoice([line("2.5", "5500"), line("1.25", "4000")], Decimal(0), RULES)
    assert lines[0].line_net == 13750
    assert lines[1].line_net == 5000
    assert totals.net_total == 18750
    assert totals.vat_total == 3375
    assert totals.gross_total == 22125


def test_empty_invoice_and_invalid_rules_are_rejected() -> None:
    with pytest.raises(InvariantViolationError, match="au moins une ligne"):
        compute_invoice([], Decimal(0), RULES)
    with pytest.raises(InvariantViolationError, match="remise globale"):
        compute_invoice([line("1", "1000")], Decimal("1.2"), RULES)
    with pytest.raises(InvariantViolationError, match="ordre_des_remises"):
        CalculationRules(discount_order=("invalide",))


def test_vat_is_split_by_rate() -> None:
    _, totals = compute_invoice([line("1", "1000"), line("1", "1000", rate="0")], Decimal(0), RULES)
    assert [(v.rate, v.amount) for v in totals.vat_breakdown] == [(D(0), D(0)), (D(18), D(180))]


def test_rules_are_loaded_from_calcul_yaml() -> None:
    rules = load_business_config(REPO_ROOT / "config").calculation_rules()
    assert rules.rounding_mode == "ROUND_HALF_UP"
    assert rules.rounding_unit == Decimal(1)
    assert rules.default_vat_rate == Decimal(18)
    assert rules.discount_order == ("ligne", "globale")


amounts = st.decimals(min_value=Decimal("0.01"), max_value=Decimal(10**6), places=2)


@given(
    st.lists(st.tuples(amounts, amounts), min_size=1, max_size=8),
    st.sampled_from(["0", "0.1"]),
    st.sampled_from([("ligne", "globale"), ("globale", "ligne")]),
)
def test_gross_is_always_net_plus_vat(
    pairs: list[tuple[Decimal, Decimal]],
    rate: str,
    order: tuple[str, ...],
) -> None:
    lines = [line(str(q), str(p)) for q, p in pairs]
    computed, totals = compute_invoice(lines, Decimal(rate), CalculationRules(discount_order=order))
    assert totals.gross_total == totals.net_total + totals.vat_total
    assert totals.net_total == totals.net_total.to_integral_value()
    assert all(c.line_gross == c.line_net + c.line_vat for c in computed)


@given(st.lists(st.tuples(amounts, amounts), min_size=1, max_size=5))
def test_same_input_same_output(pairs: list[tuple[Decimal, Decimal]]) -> None:
    lines = [line(str(q), str(p)) for q, p in pairs]
    assert compute_invoice(lines, Decimal(0), RULES) == compute_invoice(lines, Decimal(0), RULES)
