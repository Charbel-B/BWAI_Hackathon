"""Stockage SQLite. Chaque entité est un document JSON ; les colonnes servent aux recherches.

`BEGIN IMMEDIATE` prend le verrou d'écriture dès l'ouverture : deux validations simultanées
s'exécutent l'une après l'autre, et la seconde voit la version déjà incrémentée par la
première. Le compteur de numéros vit dans la même transaction que la validation.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from invoicing.application.ports import StoredResponse
from invoicing.domain.audit import GENESIS_HASH, AuditEntry, AuditEvent, chain
from invoicing.domain.documents import SourceDocument
from invoicing.domain.invoice import Invoice, InvoiceStatus
from invoicing.domain.settlement import CreditNote, Dispatch, Payment

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, sha TEXT, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS document_files (id TEXT PRIMARY KEY, content BLOB NOT NULL);
CREATE TABLE IF NOT EXISTS invoices (
    id TEXT PRIMARY KEY, document_id TEXT, status TEXT, created_at TEXT, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS credit_notes (id TEXT PRIMARY KEY, invoice_id TEXT, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS payments (id TEXT PRIMARY KEY, invoice_id TEXT, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dispatches (id TEXT PRIMARY KEY, invoice_id TEXT, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sequences (series TEXT, year INTEGER, value INTEGER NOT NULL,
    PRIMARY KEY (series, year));
CREATE TABLE IF NOT EXISTS audit_log (seq INTEGER PRIMARY KEY, entity_id TEXT, body TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS idempotency (key TEXT PRIMARY KEY, body TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit_log
    BEGIN SELECT RAISE(ABORT, 'journal en ajout seul'); END;
CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit_log
    WHEN (SELECT value FROM sequences WHERE series = '__reset__') IS NULL
    BEGIN SELECT RAISE(ABORT, 'journal en ajout seul'); END;
"""
_DATA_TABLES = (
    "documents",
    "document_files",
    "invoices",
    "credit_notes",
    "payments",
    "dispatches",
    "sequences",
    "idempotency",
)

_DOC = TypeAdapter(SourceDocument)
_INV = TypeAdapter(Invoice)
_CRN = TypeAdapter(CreditNote)
_PAY = TypeAdapter(Payment)
_DSP = TypeAdapter(Dispatch)
_AUD = TypeAdapter(AuditEntry)
_IDEM = TypeAdapter(StoredResponse)


def _json(adapter: TypeAdapter[Any], value: object) -> str:
    return adapter.dump_json(value).decode()


class SqliteTransaction:
    """Implémentation du port Transaction sur une connexion ouverte."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._c = conn

    def _one(self, sql: str, *args: object) -> str | None:
        row = self._c.execute(sql, args).fetchone()
        return None if row is None else str(row[0])

    def _all(self, sql: str, *args: object) -> list[str]:
        return [str(r[0]) for r in self._c.execute(sql, args).fetchall()]

    def get_document(self, document_id: str) -> SourceDocument | None:
        body = self._one("SELECT body FROM documents WHERE id = ?", document_id)
        return None if body is None else _DOC.validate_json(body)

    def documents_by_sha(self, file_sha256: str) -> list[SourceDocument]:
        rows = self._all("SELECT body FROM documents WHERE sha = ? ORDER BY rowid", file_sha256)
        return [_DOC.validate_json(b) for b in rows]

    def save_document(self, document: SourceDocument) -> None:
        self._c.execute(
            "INSERT OR REPLACE INTO documents (id, sha, body) VALUES (?, ?, ?)",
            (document.id, document.file_sha256, _json(_DOC, document)),
        )

    def save_document_content(self, document_id: str, content: bytes) -> None:
        self._c.execute("INSERT INTO document_files VALUES (?, ?)", (document_id, content))

    def get_document_content(self, document_id: str) -> bytes | None:
        row = self._c.execute("SELECT content FROM document_files WHERE id = ?", (document_id,))
        found = row.fetchone()
        return None if found is None else bytes(found[0])

    def get_invoice(self, invoice_id: str) -> Invoice | None:
        body = self._one("SELECT body FROM invoices WHERE id = ?", invoice_id)
        return None if body is None else _INV.validate_json(body)

    def list_invoices(self, status: InvoiceStatus | None = None) -> list[Invoice]:
        sql = "SELECT body FROM invoices"
        rows = (
            self._all(sql + " WHERE status = ? ORDER BY created_at DESC", status.value)
            if status
            else self._all(sql + " ORDER BY created_at DESC")
        )
        return [_INV.validate_json(b) for b in rows]

    def invoices_for_document(self, document_id: str) -> list[Invoice]:
        rows = self._all("SELECT body FROM invoices WHERE document_id = ?", document_id)
        return [_INV.validate_json(b) for b in rows]

    def save_invoice(self, invoice: Invoice) -> None:
        self._c.execute(
            "INSERT OR REPLACE INTO invoices VALUES (?, ?, ?, ?, ?)",
            (
                invoice.id,
                invoice.source_document_id,
                invoice.status.value,
                invoice.created_at.isoformat(),
                _json(_INV, invoice),
            ),
        )

    def get_credit_note(self, credit_note_id: str) -> CreditNote | None:
        body = self._one("SELECT body FROM credit_notes WHERE id = ?", credit_note_id)
        return None if body is None else _CRN.validate_json(body)

    def credit_notes_for(self, invoice_id: str) -> list[CreditNote]:
        sql = "SELECT body FROM credit_notes WHERE invoice_id = ? ORDER BY rowid"
        return [_CRN.validate_json(b) for b in self._all(sql, invoice_id)]

    def save_credit_note(self, credit_note: CreditNote) -> None:
        self._c.execute(
            "INSERT OR REPLACE INTO credit_notes VALUES (?, ?, ?)",
            (credit_note.id, credit_note.invoice_id, _json(_CRN, credit_note)),
        )

    def payments_for(self, invoice_id: str) -> list[Payment]:
        sql = "SELECT body FROM payments WHERE invoice_id = ? ORDER BY rowid"
        return [_PAY.validate_json(b) for b in self._all(sql, invoice_id)]

    def add_payment(self, payment: Payment) -> None:
        self._c.execute(
            "INSERT INTO payments VALUES (?, ?, ?)",
            (payment.id, payment.invoice_id, _json(_PAY, payment)),
        )

    def dispatches_for(self, invoice_id: str) -> list[Dispatch]:
        sql = "SELECT body FROM dispatches WHERE invoice_id = ? ORDER BY rowid"
        return [_DSP.validate_json(b) for b in self._all(sql, invoice_id)]

    def add_dispatch(self, dispatch: Dispatch) -> None:
        self._c.execute(
            "INSERT INTO dispatches VALUES (?, ?, ?)",
            (dispatch.id, dispatch.invoice_id, _json(_DSP, dispatch)),
        )

    def next_sequence(self, series: str, year: int) -> int:
        self._c.execute(
            "INSERT INTO sequences VALUES (?, ?, 1) "
            "ON CONFLICT (series, year) DO UPDATE SET value = value + 1",
            (series, year),
        )
        value = self._one("SELECT value FROM sequences WHERE series = ? AND year = ?", series, year)
        return int(value or 0)

    def append_audit(self, event: AuditEvent) -> AuditEntry:
        last = self._one("SELECT body FROM audit_log ORDER BY seq DESC LIMIT 1")
        previous = None if last is None else _AUD.validate_json(last)
        seq = 1 if previous is None else previous.seq + 1
        entry = chain(seq, event, GENESIS_HASH if previous is None else previous.hash)
        self._c.execute(
            "INSERT INTO audit_log VALUES (?, ?, ?)", (seq, event.entity_id, _json(_AUD, entry))
        )
        return entry

    def audit_entries(self, entity_id: str | None = None) -> list[AuditEntry]:
        if entity_id is None:
            rows = self._all("SELECT body FROM audit_log ORDER BY seq")
        else:
            rows = self._all(
                "SELECT body FROM audit_log WHERE entity_id = ? ORDER BY seq", entity_id
            )
        return [_AUD.validate_json(b) for b in rows]

    def stored_response(self, key: str) -> StoredResponse | None:
        body = self._one("SELECT body FROM idempotency WHERE key = ?", key)
        return None if body is None else _IDEM.validate_json(body)

    def store_response(self, key: str, response: StoredResponse) -> None:
        self._c.execute(
            "INSERT OR IGNORE INTO idempotency VALUES (?, ?)", (key, _json(_IDEM, response))
        )

    def reset(self) -> None:
        self._c.execute("INSERT INTO sequences VALUES ('__reset__', 0, 1)")
        self._c.execute("DELETE FROM audit_log")
        for table in _DATA_TABLES:
            self._c.execute(f"DELETE FROM {table}")  # noqa: S608 - noms de table constants


class SqliteStore:
    """Fabrique de transactions SQLite, et mémoire d'idempotence sur la même base."""

    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(_SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._path, timeout=10, isolation_level=None)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def transaction(self) -> Iterator[SqliteTransaction]:
        """Ouvre une transaction d'écriture ; validée en sortie, annulée sur exception."""
        conn = self._connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield SqliteTransaction(conn)
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        finally:
            conn.close()

    def get(self, key: str) -> StoredResponse | None:
        """Réponse déjà rendue pour cette clé d'idempotence."""
        with self.transaction() as tx:
            return tx.stored_response(key)

    def save(self, key: str, response: StoredResponse) -> None:
        """Mémorise la réponse ; la première réponse enregistrée l'emporte."""
        with self.transaction() as tx:
            tx.store_response(key, response)
