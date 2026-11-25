"""Facture, lignes, totaux et anomalies, selon docs/contrats/modele-de-domaine.md."""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from invoicing.domain.errors import InvariantViolationError

ZERO = Decimal(0)


class InvoiceStatus(StrEnum):
    """Statut de cycle de vie, stocké. Voir docs/contrats/cycle-de-vie.md."""

    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    ISSUED = "ISSUED"
    DISCARDED = "DISCARDED"
    CANCELLED = "CANCELLED"


class Severity(StrEnum):
    """Gravité d'une anomalie. BLOCKING empêche la validation tant qu'elle est ouverte."""

    BLOCKING = "BLOCKING"
    WARNING = "WARNING"


@dataclass(frozen=True, slots=True)
class LineInput:
    """Ligne telle que saisie ou extraite, avant calcul."""

    label: str
    quantity: Decimal
    unit_price_net: Decimal
    vat_rate: Decimal
    item_id: str | None = None
    unit: str | None = None
    discount_rate: Decimal = ZERO

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise InvariantViolationError(f"{self.label} : la quantité doit être positive")
        if self.unit_price_net < 0:
            raise InvariantViolationError(f"{self.label} : prix unitaire négatif")
        if not ZERO <= self.discount_rate <= 1:
            raise InvariantViolationError(f"{self.label} : remise hors de [0, 1]")


@dataclass(frozen=True, slots=True)
class InvoiceLine:
    """Ligne calculée par le moteur : les montants ne sont jamais saisis."""

    source: LineInput
    line_net: Decimal
    line_vat: Decimal

    @property
    def line_gross(self) -> Decimal:
        """Montant TTC indicatif de la ligne (HT + TVA)."""
        return self.line_net + self.line_vat


@dataclass(frozen=True, slots=True)
class VatAmount:
    """Montant de TVA pour un taux donné."""

    rate: Decimal
    base: Decimal
    amount: Decimal


@dataclass(frozen=True, slots=True)
class Totals:
    """Totaux stockés. Le crédité, le payé et le solde sont dérivés (voir settlement)."""

    net_total: Decimal
    vat_total: Decimal
    gross_total: Decimal
    vat_breakdown: tuple[VatAmount, ...] = ()
    global_discount_amount: Decimal = ZERO

    def __post_init__(self) -> None:
        if self.net_total + self.vat_total != self.gross_total:
            raise InvariantViolationError("TTC différent de HT + TVA")


EMPTY_TOTALS = Totals(ZERO, ZERO, ZERO)


@dataclass(frozen=True, slots=True)
class Resolution:
    """Levée d'une anomalie par un humain, toujours justifiée."""

    by: str
    at: datetime
    justification: str

    def __post_init__(self) -> None:
        if not self.justification.strip():
            raise InvariantViolationError("une résolution d'anomalie exige une justification")


@dataclass(frozen=True, slots=True)
class Anomaly:
    """Écart détecté par les contrôles. Son identifiant est stable entre deux recalculs."""

    id: str
    code: str
    severity: Severity
    field: str | None
    message: str
    resolution: Resolution | None = None

    @property
    def is_open_blocking(self) -> bool:
        """Vrai si l'anomalie empêche encore la validation."""
        return self.severity is Severity.BLOCKING and self.resolution is None


@dataclass(frozen=True, slots=True)
class DraftContent:
    """Contenu métier d'une facture, construit à partir des champs revus de la pièce."""

    customer_id: str | None
    customer_name: str | None
    reference: str | None
    issue_date: date | None
    due_date: date | None
    global_discount_rate: Decimal
    lines: tuple[LineInput, ...]
    declared_net: Decimal | None = None
    declared_gross: Decimal | None = None


@dataclass(frozen=True, slots=True)
class Invoice:
    """Facture. Depuis VALIDATED, plus aucun champ métier ne change (correction par avoir)."""

    id: str
    source_document_id: str
    status: InvoiceStatus
    content: DraftContent
    lines: tuple[InvoiceLine, ...]
    totals: Totals
    anomalies: tuple[Anomaly, ...]
    version: int
    created_by: str
    created_at: datetime
    number: str | None = None
    validated_by: str | None = None
    validated_at: datetime | None = None
    config_sha256: str | None = None

    def __post_init__(self) -> None:
        numbered = self.status in (
            InvoiceStatus.VALIDATED,
            InvoiceStatus.ISSUED,
            InvoiceStatus.CANCELLED,
        )
        if numbered != (self.number is not None):
            raise InvariantViolationError("seule une facture validée porte un numéro")
        if self.version < 1:
            raise InvariantViolationError("la version commence à 1")

    @property
    def open_blocking_anomalies(self) -> tuple[Anomaly, ...]:
        """Anomalies bloquantes non résolues."""
        return tuple(a for a in self.anomalies if a.is_open_blocking)
