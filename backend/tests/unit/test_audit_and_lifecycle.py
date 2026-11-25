from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from invoicing.domain import lifecycle
from invoicing.domain.audit import GENESIS_HASH, AuditEvent, chain, verify_chain
from invoicing.domain.errors import (
    InvariantViolationError,
    SeparationOfDutiesError,
    ValidationBlockedError,
)
from invoicing.domain.invoice import (
    EMPTY_TOTALS,
    Anomaly,
    DraftContent,
    Invoice,
    InvoiceStatus,
    Resolution,
    Severity,
)
from invoicing.infrastructure.referentials_csv import ReferentialError, load_referentials

AT = datetime(2026, 11, 26, 8, tzinfo=UTC)


def _event(action: str) -> AuditEvent:
    return AuditEvent(AT, "USR-a", action, "invoice", "INV-1", None, {"status": "DRAFT"})


def test_tampered_audit_entry_is_detected() -> None:
    first = chain(1, _event("a"), GENESIS_HASH)
    second = chain(2, _event("b"), first.hash)
    assert verify_chain([first, second]) is None
    forged = replace(second, event=_event("falsifié"))
    assert verify_chain([first, forged]) == 2


def _draft(anomalies: tuple[Anomaly, ...] = ()) -> Invoice:
    content = DraftContent(None, None, None, None, None, Decimal(0), ())
    return Invoice(
        "INV-1", "DOC-1", InvoiceStatus.DRAFT, content, (), EMPTY_TOTALS, anomalies, 1, "USR-a", AT
    )


def test_author_cannot_validate_when_separation_is_on() -> None:
    stamp = lifecycle.ValidationStamp("USR-a", AT, "FA-2026-00001", "sha")
    with pytest.raises(SeparationOfDutiesError):
        lifecycle.validate(_draft(), stamp, separation_of_duties=True)
    assert lifecycle.validate(_draft(), stamp, separation_of_duties=False).number == "FA-2026-00001"


def test_warning_does_not_block_validation_but_blocking_does() -> None:
    stamp = lifecycle.ValidationStamp("USR-b", AT, "FA-2026-00001", "sha")
    warning = Anomaly("UNUSUAL_PRICE:x", "UNUSUAL_PRICE", Severity.WARNING, "x", "m")
    assert lifecycle.validate(_draft((warning,)), stamp, True).status is InvoiceStatus.VALIDATED
    blocking = replace(warning, severity=Severity.BLOCKING)
    with pytest.raises(ValidationBlockedError):
        lifecycle.validate(_draft((blocking,)), stamp, True)


def test_only_validated_invoice_has_a_number() -> None:
    with pytest.raises(InvariantViolationError):
        replace(_draft(), number="FA-2026-00001")


def test_resolution_survives_recompute() -> None:
    anomaly = Anomaly("HIGH_AMOUNT:-", "HIGH_AMOUNT", Severity.BLOCKING, None, "m")
    resolved = lifecycle.resolve_anomaly(
        _draft((anomaly,)), anomaly.id, Resolution("USR-a", AT, "accord direction")
    )
    merged = lifecycle.merge_anomalies(resolved.anomalies, (anomaly,))
    assert merged[0].resolution is not None


def test_referential_with_missing_column_is_refused(tmp_path: Path) -> None:
    (tmp_path / "articles.csv").write_text("id,designation\nART-001,x\n", encoding="utf-8")
    with pytest.raises(ReferentialError):
        load_referentials(tmp_path)


def test_referential_with_duplicate_id_is_refused(tmp_path: Path) -> None:
    header = "id,designation,unite,prix_unitaire_ht,taux_tva\n"
    (tmp_path / "articles.csv").write_text(header + "A,x,u,1,18\nA,y,u,1,18\n", encoding="utf-8")
    with pytest.raises(ReferentialError):
        load_referentials(tmp_path)


def test_missing_referential_files_give_empty_referentials(tmp_path: Path) -> None:
    assert load_referentials(tmp_path).customers == ()
