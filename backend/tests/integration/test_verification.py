"""Vérification publique par QR code : authentique, annulée, altérée, inconnue."""

import json
import sqlite3
from typing import Any

from tests.integration.conftest import Api


def _validated(api: Api, piece: str) -> dict[str, Any]:
    draft = api.import_piece(api.login("operateur"), piece)["invoice"]
    validator = api.login("validateur")
    response = api.post(f"/invoices/{draft['id']}/validate", validator, version=draft["version"])
    body: dict[str, Any] = response.json()
    return body


def _verify(api: Api, invoice_id: str, code: str) -> dict[str, Any]:
    body: dict[str, Any] = api.client.get(f"/api/v1/public/verify/{invoice_id}?code={code}").json()
    return body


def test_validated_invoice_is_authentic_without_login(api: Api, clean_piece: str) -> None:
    invoice = _validated(api, clean_piece)
    assert invoice["verification_code"]
    result = _verify(api, invoice["id"], invoice["verification_code"])
    assert result["verdict"] == "AUTHENTIC"
    assert result["number"] == "FA-2026-00001"
    assert result["gross_total"] == "180540"
    assert result["journal_intact"] is True


def test_wrong_code_reveals_nothing(api: Api, clean_piece: str) -> None:
    invoice = _validated(api, clean_piece)
    result = _verify(api, invoice["id"], "0000000000000000")
    assert result == {
        "verdict": "UNKNOWN",
        "number": None,
        "customer_name": None,
        "issue_date": None,
        "gross_total": None,
        "validated_at": None,
        "content_sha256": None,
        "journal_intact": None,
    }
    assert _verify(api, "INV-inconnu", "x")["verdict"] == "UNKNOWN"


def test_draft_has_no_verification_code(api: Api, clean_piece: str) -> None:
    draft = api.import_piece(api.login("operateur"), clean_piece)["invoice"]
    assert draft["verification_code"] is None


def test_fully_credited_invoice_is_reported_cancelled(api: Api, clean_piece: str) -> None:
    invoice = _validated(api, clean_piece)
    validator = api.login("validateur")
    note = api.post(
        f"/invoices/{invoice['id']}/credit-notes", validator, json={"reason": "erreur"}
    ).json()
    api.post(f"/credit-notes/{note['id']}/validate", validator, version=note["version"])
    assert _verify(api, invoice["id"], invoice["verification_code"])["verdict"] == "CANCELLED"


def test_invoice_modified_in_database_is_reported_altered(api: Api, clean_piece: str) -> None:
    invoice = _validated(api, clean_piece)
    with sqlite3.connect(api.settings.database_path) as conn:
        (raw,) = conn.execute("SELECT body FROM invoices WHERE id = ?", (invoice["id"],)).fetchone()
        body = json.loads(raw)
        body["totals"]["gross_total"] = "1"
        body["totals"]["net_total"] = "1"
        body["totals"]["vat_total"] = "0"
        conn.execute("UPDATE invoices SET body = ? WHERE id = ?", (json.dumps(body), invoice["id"]))
    assert _verify(api, invoice["id"], invoice["verification_code"])["verdict"] == "ALTERED"
