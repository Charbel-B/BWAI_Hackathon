"""Moteur de calcul : montants exacts en Decimal, arrondis lus dans config/calcul.yaml.

L'ordre des remises (ligne puis globale par défaut), le mode et l'unité d'arrondi
proviennent exclusivement de la configuration métier.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from invoicing.domain.errors import InvariantViolationError
from invoicing.domain.invoice import ZERO, InvoiceLine, LineInput, Totals, VatAmount

HUNDRED = Decimal(100)
_VALID_DISCOUNT_ORDERS = frozenset({("ligne", "globale"), ("globale", "ligne")})


@dataclass(frozen=True, slots=True)
class CalculationRules:
    """Règles lues dans config/calcul.yaml."""

    rounding_mode: str = ROUND_HALF_UP
    rounding_unit: Decimal = Decimal(1)
    default_vat_rate: Decimal = Decimal(18)
    discount_order: tuple[str, ...] = ("ligne", "globale")

    def __post_init__(self) -> None:
        if self.discount_order not in _VALID_DISCOUNT_ORDERS:
            msg = f"ordre_des_remises invalide : {self.discount_order!r}"
            raise InvariantViolationError(msg)
        if self.rounding_unit <= 0:
            raise InvariantViolationError("l'unité d'arrondi doit être strictement positive")

    def round(self, amount: Decimal) -> Decimal:
        """Arrondit au niveau configuré (au franc par défaut)."""
        return amount.quantize(self.rounding_unit, rounding=self.rounding_mode)


def compute_invoice(
    lines: Sequence[LineInput],
    global_discount_rate: Decimal,
    rules: CalculationRules,
    *,
    vat_liable: bool = True,
) -> tuple[tuple[InvoiceLine, ...], Totals]:
    """Calcule les lignes et les totaux. Même entrée, même sortie, toujours."""
    if not lines:
        raise InvariantViolationError("une facture doit contenir au moins une ligne")
    if not (ZERO <= global_discount_rate <= Decimal(1)):
        raise InvariantViolationError("la remise globale doit être dans [0, 1]")

    effective_lines = tuple(_with_vat_liability(line, vat_liable) for line in lines)
    if rules.discount_order == ("globale", "ligne"):
        return _compute_global_then_line(effective_lines, global_discount_rate, rules)
    return _compute_line_then_global(effective_lines, global_discount_rate, rules)


def _with_vat_liability(line: LineInput, vat_liable: bool) -> LineInput:
    if vat_liable or line.vat_rate == ZERO:
        return line
    return LineInput(
        label=line.label,
        quantity=line.quantity,
        unit_price_net=line.unit_price_net,
        vat_rate=ZERO,
        item_id=line.item_id,
        unit=line.unit,
        discount_rate=line.discount_rate,
    )


def _compute_line_then_global(
    lines: tuple[LineInput, ...],
    global_discount_rate: Decimal,
    rules: CalculationRules,
) -> tuple[tuple[InvoiceLine, ...], Totals]:
    computed = tuple(_compute_line(line, rules) for line in lines)
    gross_net = sum((c.line_net for c in computed), ZERO)

    breakdown: list[VatAmount] = []
    for rate in sorted({line.vat_rate for line in lines}):
        rate_net = sum((c.line_net for c in computed if c.source.vat_rate == rate), ZERO)
        base = rules.round(rate_net * (1 - global_discount_rate))
        breakdown.append(VatAmount(rate, base, rules.round(base * rate / HUNDRED)))

    net_total = sum((v.base for v in breakdown), ZERO)
    vat_total = sum((v.amount for v in breakdown), ZERO)
    totals = Totals(
        net_total=net_total,
        vat_total=vat_total,
        gross_total=net_total + vat_total,
        vat_breakdown=tuple(breakdown),
        global_discount_amount=gross_net - net_total,
    )
    return computed, totals


def _compute_global_then_line(
    lines: tuple[LineInput, ...],
    global_discount_rate: Decimal,
    rules: CalculationRules,
) -> tuple[tuple[InvoiceLine, ...], Totals]:
    computed_list: list[InvoiceLine] = []
    global_discount_total = ZERO

    for line in lines:
        raw = rules.round(line.quantity * line.unit_price_net)
        after_global = rules.round(raw * (1 - global_discount_rate))
        global_discount_total += raw - after_global
        line_net = rules.round(after_global * (1 - line.discount_rate))
        line_vat = rules.round(line_net * line.vat_rate / HUNDRED)
        computed_list.append(InvoiceLine(line, line_net, line_vat))

    computed = tuple(computed_list)
    breakdown: list[VatAmount] = []
    for rate in sorted({line.vat_rate for line in lines}):
        rate_base = sum((c.line_net for c in computed if c.source.vat_rate == rate), ZERO)
        breakdown.append(VatAmount(rate, rate_base, rules.round(rate_base * rate / HUNDRED)))

    net_total = sum((v.base for v in breakdown), ZERO)
    vat_total = sum((v.amount for v in breakdown), ZERO)
    totals = Totals(
        net_total=net_total,
        vat_total=vat_total,
        gross_total=net_total + vat_total,
        vat_breakdown=tuple(breakdown),
        global_discount_amount=global_discount_total,
    )
    return computed, totals


def _compute_line(line: LineInput, rules: CalculationRules) -> InvoiceLine:
    line_net = rules.round(line.quantity * line.unit_price_net * (1 - line.discount_rate))
    return InvoiceLine(line, line_net, rules.round(line_net * line.vat_rate / HUNDRED))
