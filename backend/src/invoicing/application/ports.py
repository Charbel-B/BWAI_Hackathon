"""Ports : interfaces que l'infrastructure implémente. Le bootstrap branche les adaptateurs."""

from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from invoicing.domain.audit import AuditEntry, AuditEvent
from invoicing.domain.documents import SourceDocument
from invoicing.domain.extraction import ExtractedField
from invoicing.domain.invoice import Invoice, InvoiceStatus
from invoicing.domain.referentials import Customer
from invoicing.domain.settlement import CreditNote, Dispatch, Payment
from invoicing.domain.users import User


class Clock(Protocol):
    """Source unique de l'heure. Le cœur métier n'appelle jamais datetime.now()."""

    def now(self) -> datetime:
        """Instant courant, conscient du fuseau, en UTC."""
        ...


class Extractor(Protocol):
    """Lit une pièce source et rend ses champs au format du contrat."""

    @property
    def name(self) -> str:
        """Nom et version de l'extracteur, enregistrés avec chaque résultat."""
        ...

    def extract(self, content: bytes, media_type: str) -> Sequence[ExtractedField]:
        """Extrait les champs d'une pièce ; un champ introuvable est rendu MISSING."""
        ...


class Transaction(Protocol):
    """Accès aux données dans une transaction : tout est écrit, ou rien."""

    def get_document(self, document_id: str) -> SourceDocument | None: ...
    def documents_by_sha(self, file_sha256: str) -> list[SourceDocument]: ...
    def save_document(self, document: SourceDocument) -> None: ...
    def save_document_content(self, document_id: str, content: bytes) -> None: ...
    def get_document_content(self, document_id: str) -> bytes | None: ...
    def get_invoice(self, invoice_id: str) -> Invoice | None: ...
    def list_invoices(self, status: InvoiceStatus | None = None) -> list[Invoice]: ...
    def invoices_for_document(self, document_id: str) -> list[Invoice]: ...
    def save_invoice(self, invoice: Invoice) -> None: ...
    def get_credit_note(self, credit_note_id: str) -> CreditNote | None: ...
    def credit_notes_for(self, invoice_id: str) -> list[CreditNote]: ...
    def save_credit_note(self, credit_note: CreditNote) -> None: ...
    def payments_for(self, invoice_id: str) -> list[Payment]: ...
    def add_payment(self, payment: Payment) -> None: ...
    def dispatches_for(self, invoice_id: str) -> list[Dispatch]: ...
    def add_dispatch(self, dispatch: Dispatch) -> None: ...
    def next_sequence(self, series: str, year: int) -> int:
        """Valeur suivante du compteur ; annulée avec la transaction si elle échoue."""
        ...

    def append_audit(self, event: AuditEvent) -> AuditEntry: ...
    def audit_entries(self, entity_id: str | None = None) -> list[AuditEntry]: ...
    def reset(self) -> None:
        """Vide toutes les données (mode démonstration uniquement)."""
        ...


class Store(Protocol):
    """Fabrique de transactions."""

    def transaction(self) -> AbstractContextManager[Transaction]: ...


@dataclass(frozen=True, slots=True)
class SentMessage:
    """Résultat d'une émission sur un canal."""

    recipient: str
    message: str


class Channel(Protocol):
    """Canal d'émission (WhatsApp, SMS, courriel). Simulé dans ce prototype."""

    def send(self, invoice: Invoice, customer: Customer | None, channel: str) -> SentMessage: ...


class DocumentRenderer(Protocol):
    """Produit le HTML et le PDF d'un brouillon ou d'une facture."""

    def render_html(self, invoice: Invoice, customer: Customer | None) -> str: ...
    def render_pdf(self, invoice: Invoice, customer: Customer | None) -> bytes: ...


class UserDirectory(Protocol):
    """Comptes et jetons."""

    def authenticate(self, username: str, password: str) -> User | None: ...
    def issue_token(self, user: User) -> str: ...
    def resolve_token(self, token: str) -> User | None: ...


@dataclass(frozen=True, slots=True)
class StoredResponse:
    """Réponse mémorisée pour une clé d'idempotence."""

    fingerprint: str
    status_code: int
    body: bytes
    media_type: str


class IdempotencyStore(Protocol):
    """Mémoire des requêtes déjà traitées."""

    def get(self, key: str) -> StoredResponse | None: ...
    def save(self, key: str, response: StoredResponse) -> None: ...
