"""Tests par propriétés (Hypothesis) sur la normalisation déterministe."""

from datetime import date
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from invoicing.extraction.normalization import (
    normalize_date,
    normalize_decimal,
    normalize_rate,
    normalize_tax_id,
)


@given(amount=st.integers(min_value=0, max_value=10_000_000))
def test_normalize_decimal_preserves_non_negative_fcfa_integers(amount: int) -> None:
    formatted = f"{amount:,}".replace(",", " ") + " FCFA"
    assert normalize_decimal(formatted) == str(amount)


@given(pct=st.integers(min_value=0, max_value=100))
def test_normalize_rate_maps_percentages_to_unit_interval(pct: int) -> None:
    result = normalize_rate(f"{pct} %")
    assert result is not None
    value = Decimal(result)
    assert Decimal(0) <= value <= Decimal(1)
    assert value == Decimal(pct) / Decimal(100)


@given(digits=st.text(alphabet="0123456789", min_size=13, max_size=13))
def test_normalize_tax_id_roundtrips_13_digits(digits: str) -> None:
    assert normalize_tax_id(f"IFU {digits}") == digits


@given(d=st.dates(min_value=date(2020, 1, 1), max_value=date(2030, 12, 31)))
def test_normalize_date_roundtrips_dmy_and_iso(d: date) -> None:
    assert normalize_date(d.isoformat()) == d.isoformat()
    assert normalize_date(d.strftime("%d/%m/%Y")) == d.isoformat()
