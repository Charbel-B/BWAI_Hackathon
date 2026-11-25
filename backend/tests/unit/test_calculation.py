from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from invoicing.domain.calculation import CalculationRules, compute_invoice
from invoicing.domain.invoice import LineInput

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


def test_non_liable_customer_pays_no_vat() -> None:
    _, totals = compute_invoice([line("3", "1000", rate="0")], Decimal(0), RULES)
    assert totals.vat_total == 0
    assert totals.gross_total == 3000


def test_half_franc_is_rounded_up() -> None:
    _, totals = compute_invoice([line("1", "2.5", rate="0")], Decimal(0), RULES)
    assert totals.net_total == 3


def test_vat_is_split_by_rate() -> None:
    _, totals = compute_invoice([line("1", "1000"), line("1", "1000", rate="0")], Decimal(0), RULES)
    assert [(v.rate, v.amount) for v in totals.vat_breakdown] == [(D(0), D(0)), (D(18), D(180))]


amounts = st.decimals(min_value=Decimal("0.01"), max_value=Decimal(10**6), places=2)


@given(st.lists(st.tuples(amounts, amounts), min_size=1, max_size=8), st.sampled_from(["0", "0.1"]))
def test_gross_is_always_net_plus_vat(pairs: list[tuple[Decimal, Decimal]], rate: str) -> None:
    lines = [line(str(q), str(p)) for q, p in pairs]
    _, totals = compute_invoice(lines, Decimal(rate), RULES)
    assert totals.gross_total == totals.net_total + totals.vat_total
    assert totals.net_total == totals.net_total.to_integral_value()


@given(st.lists(st.tuples(amounts, amounts), min_size=1, max_size=5))
def test_same_input_same_output(pairs: list[tuple[Decimal, Decimal]]) -> None:
    lines = [line(str(q), str(p)) for q, p in pairs]
    assert compute_invoice(lines, Decimal(0), RULES) == compute_invoice(lines, Decimal(0), RULES)
