"""Règles de transition du cycle de vie, selon docs/contrats/cycle-de-vie.md.

Chaque fonction rend un nouvel objet : rien n'est modifié en place.
"""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import datetime

from invoicing.domain.errors import (
    InvalidTransitionError,
    SeparationOfDutiesError,
    ValidationBlockedError,
    VersionConflictError,
)
from invoicing.domain.fingerprint import invoice_fingerprint
from invoicing.domain.invoice import (
    Anomaly,
    DraftContent,
    Invoice,
    InvoiceLine,
    InvoiceStatus,
    Resolution,
    Totals,
)

DISPATCHABLE = (InvoiceStatus.VALIDATED, InvoiceStatus.ISSUED)


def ensure_status(invoice: Invoice, allowed: Iterable[InvoiceStatus], action: str) -> None:
    """Refuse l'action si la facture n'est pas dans un des statuts autorisés."""
    allowed = tuple(allowed)
    if invoice.status not in allowed:
        raise InvalidTransitionError(f"{action} impossible depuis le statut {invoice.status}")


def ensure_version(invoice: Invoice, expected: int) -> None:
    """Refuse toute modification fondée sur une version périmée."""
    if invoice.version != expected:
        raise VersionConflictError(
            f"version envoyée {expected}, version courante {invoice.version}"
        )


def merge_anomalies(previous: Iterable[Anomaly], fresh: Iterable[Anomaly]) -> tuple[Anomaly, ...]:
    """Garde la résolution d'une anomalie qui réapparait à l'identique après recalcul."""
    resolved = {a.id: a.resolution for a in previous if a.resolution is not None}
    return tuple(replace(a, resolution=resolved.get(a.id)) for a in fresh)


def recompute_draft(
    invoice: Invoice,
    content: DraftContent,
    lines: tuple[InvoiceLine, ...],
    totals: Totals,
    anomalies: Iterable[Anomaly],
) -> Invoice:
    """Remplace le contenu d'un brouillon après correction ; la version augmente."""
    ensure_status(invoice, [InvoiceStatus.DRAFT], "Correction")
    return replace(
        invoice,
        content=content,
        lines=lines,
        totals=totals,
        anomalies=merge_anomalies(invoice.anomalies, anomalies),
        version=invoice.version + 1,
    )


def resolve_anomaly(invoice: Invoice, anomaly_id: str, resolution: Resolution) -> Invoice:
    """Lève une anomalie ouverte avec une justification."""
    ensure_status(invoice, [InvoiceStatus.DRAFT], "Résolution d'anomalie")
    if not any(a.id == anomaly_id and a.resolution is None for a in invoice.anomalies):
        raise InvalidTransitionError(f"anomalie {anomaly_id} inconnue ou déjà résolue")
    anomalies = tuple(
        replace(a, resolution=resolution) if a.id == anomaly_id else a for a in invoice.anomalies
    )
    return replace(invoice, anomalies=anomalies, version=invoice.version + 1)


@dataclass(frozen=True, slots=True)
class ValidationStamp:
    """Qui valide, quand, sous quel numéro et avec quelle configuration."""

    by: str
    at: datetime
    number: str
    config_sha256: str


def validate(invoice: Invoice, stamp: ValidationStamp, separation_of_duties: bool) -> Invoice:
    """Valide un brouillon. Le numéro est attribué par l'appelant dans la même transaction."""
    check_can_validate(invoice, stamp.by, separation_of_duties)
    validated = replace(
        invoice,
        status=InvoiceStatus.VALIDATED,
        number=stamp.number,
        validated_by=stamp.by,
        validated_at=stamp.at,
        config_sha256=stamp.config_sha256,
        version=invoice.version + 1,
    )
    return replace(validated, content_sha256=invoice_fingerprint(validated))


def check_can_validate(invoice: Invoice, by: str, separation_of_duties: bool) -> None:
    """Vérifie les conditions de validation avant de consommer un numéro."""
    ensure_status(invoice, [InvoiceStatus.DRAFT], "Validation")
    if separation_of_duties and by == invoice.created_by:
        raise SeparationOfDutiesError("le validateur ne peut pas être l'auteur du brouillon")
    if invoice.open_blocking_anomalies:
        raise ValidationBlockedError(invoice.open_blocking_anomalies)


def discard(invoice: Invoice) -> Invoice:
    """Abandonne un brouillon. Aucun numéro n'est consommé."""
    ensure_status(invoice, [InvoiceStatus.DRAFT], "Abandon")
    return replace(invoice, status=InvoiceStatus.DISCARDED, version=invoice.version + 1)


def mark_issued(invoice: Invoice) -> Invoice:
    """Passe la facture à ISSUED après une émission réussie."""
    ensure_status(invoice, DISPATCHABLE, "Émission")
    if invoice.status is InvoiceStatus.ISSUED:
        return invoice
    return replace(invoice, status=InvoiceStatus.ISSUED, version=invoice.version + 1)


def cancel(invoice: Invoice) -> Invoice:
    """Annule une facture entièrement couverte par des avoirs validés."""
    ensure_status(invoice, DISPATCHABLE, "Annulation")
    return replace(invoice, status=InvoiceStatus.CANCELLED, version=invoice.version + 1)
