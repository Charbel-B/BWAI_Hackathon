"""Journal d'audit en ajout seul : chaque entrée est chaînée à la précédente par empreinte.

Modifier ou supprimer une entrée casse la chaîne, ce que verify_chain détecte.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime

GENESIS_HASH = "0" * 64

type AuditData = Mapping[str, str | int | None]


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Ce qui s'est passé, avant chaînage."""

    at: datetime
    user_id: str
    action: str
    entity: str
    entity_id: str
    before: AuditData | None
    after: AuditData | None


@dataclass(frozen=True, slots=True)
class AuditEntry:
    """Entrée chaînée. `hash` couvre le contenu de l'entrée et `prev_hash`."""

    seq: int
    event: AuditEvent
    prev_hash: str
    hash: str


def entry_hash(seq: int, event: AuditEvent, prev_hash: str) -> str:
    """Empreinte SHA-256 d'une sérialisation canonique (clés triées, sans espaces)."""
    payload = {
        "seq": seq,
        "at": event.at.isoformat(),
        "user_id": event.user_id,
        "action": event.action,
        "entity": event.entity,
        "entity_id": event.entity_id,
        "before": dict(event.before) if event.before is not None else None,
        "after": dict(event.after) if event.after is not None else None,
        "prev_hash": prev_hash,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


def chain(seq: int, event: AuditEvent, prev_hash: str) -> AuditEntry:
    """Construit l'entrée suivante de la chaîne."""
    return AuditEntry(seq, event, prev_hash, entry_hash(seq, event, prev_hash))


def verify_chain(entries: Sequence[AuditEntry]) -> int | None:
    """Numéro de la première entrée altérée, ou None si la chaîne est intacte."""
    prev = GENESIS_HASH
    for entry in entries:
        if entry.prev_hash != prev or entry.hash != entry_hash(entry.seq, entry.event, prev):
            return entry.seq
        prev = entry.hash
    return None
