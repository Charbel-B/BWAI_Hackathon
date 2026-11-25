"""Moteur de calcul : montants exacts en Decimal, arrondis lus dans config/calcul.yaml.

Ordre : remise de ligne, puis remise globale répartie par taux de TVA, puis TVA par taux.
La TVA de chaque ligne est donnée à titre indicatif ; le total de TVA est calculé par taux,
sur la base remisée, ce qui évite le cumul des écarts d'arrondi ligne à ligne.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from invoicing.domain.invoice import ZERO, InvoiceLine, LineInput, Totals, VatAmount

HUNDRED = Decimal(100)


@dataclass(frozen=True, slots=True)
class CalculationRules:
    """Règles lues dans config/calcul.yaml."""

    rounding_mode: str = ROUND_HALF_UP
    rounding_unit: Decimal = Decimal(1)
    default_vat_rate: Decimal = Decimal(18)

    def round(self, amount: Decimal) -> Decimal:
        """Arrondit au niveau configuré (au franc par défaut)."""
        return amount.quantize(self.rounding_unit, rounding=self.rounding_mode)


def compute_invoice(
    lines: Sequence[LineInput],
    global_discount_rate: Decimal,
    rules: CalculationRules,
) -> tuple[tuple[InvoiceLine, ...], Totals]:
    """Calcule les lignes et les totaux. Même entrée, même sortie, toujours."""
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


def _compute_line(line: LineInput, rules: CalculationRules) -> InvoiceLine:
    line_net = rules.round(line.quantity * line.unit_price_net * (1 - line.discount_rate))
    return InvoiceLine(line, line_net, rules.round(line_net * line.vat_rate / HUNDRED))
