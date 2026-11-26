"""Dépendances et règles partagées par les cas d'usage, assemblées par le bootstrap."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime

from invoicing.application.ports import (
    Channel,
    Clock,
    DocumentRenderer,
    Extractor,
    Store,
    Transaction,
)
from invoicing.domain.audit import AuditData, AuditEvent
from invoicing.domain.calculation import CalculationRules
from invoicing.domain.collection import CollectionRules
from invoicing.domain.controls import ControlRules
from invoicing.domain.referentials import Issuer, Referentials
from invoicing.domain.users import User


class NotFoundError(Exception):
    """Ressource inconnue."""


@dataclass(frozen=True, slots=True)
class NumberingFormats:
    """Formats lus dans config/numerotation.yaml."""

    invoice: str = "FA-{annee}-{sequence:05d}"
    credit_note: str = "AV-{annee}-{sequence:05d}"


@dataclass(frozen=True, slots=True)
class Context:
    """Tout ce dont un cas d'usage a besoin, sans savoir quel adaptateur est derrière."""

    store: Store
    clock: Clock
    extractor: Extractor
    channel: Channel
    referentials: Referentials
    issuer: Issuer
    calculation: CalculationRules
    controls: ControlRules
    collection: CollectionRules
    numbering: NumberingFormats
    separation_of_duties: bool
    active_channels: tuple[str, ...]
    config_sha256: str
    demo_mode: bool
    renderer: DocumentRenderer | None = None

    def now(self) -> datetime:
        """Instant courant selon l'horloge injectée."""
        return self.clock.now()


def new_id(prefix: str) -> str:
    """Identifiant opaque et unique, préfixé par le type d'entité pour la lisibilité."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


@dataclass(frozen=True, slots=True)
class Operation:
    """Une action d'un utilisateur, dans une seule transaction."""

    ctx: Context
    tx: Transaction
    user: User

    def audit(
        self,
        action: str,
        entity: tuple[str, str],
        before: AuditData | None = None,
        after: AuditData | None = None,
    ) -> None:
        """Écrit l'entrée d'audit dans la même transaction que le changement d'état."""
        kind, entity_id = entity
        event = AuditEvent(self.ctx.now(), self.user.id, action, kind, entity_id, before, after)
        self.tx.append_audit(event)


@contextmanager
def operation(ctx: Context, user: User) -> Iterator[Operation]:
    """Ouvre une transaction : tout ce qui est écrit dedans réussit ou échoue ensemble."""
    with ctx.store.transaction() as tx:
        yield Operation(ctx, tx, user)
