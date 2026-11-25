"""Parcours complet et garanties du contrat (cycle-de-vie.md, api.md)."""

from typing import Any

from tests.integration.conftest import Api

UNKNOWN_CUSTOMER_PIECE = """Commande CMD-2026-900 du 21/11/2026
Client : Société Inconnue SARL
- 3 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA
"""


def _validate(api: Api, invoice: dict[str, Any]) -> dict[str, Any]:
    token = api.login("validateur")
    response = api.post(f"/invoices/{invoice['id']}/validate", token, version=invoice["version"])
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def test_clean_piece_goes_from_import_to_paid(api: Api, clean_piece: str) -> None:
    operator = api.login("operateur")
    imported = api.import_piece(operator, clean_piece)
    draft = imported["invoice"]
    assert draft["status"] == "DRAFT"
    assert draft["number"] is None
    assert draft["totals"]["gross_total"] == "180540"
    assert draft["blocking_count"] == 0

    validated = _validate(api, draft)
    assert validated["number"] == "FA-2026-00001"
    assert validated["config_sha256"]

    issued = api.post(f"/invoices/{draft['id']}/dispatch", operator, json={"channel": "whatsapp"})
    assert issued.json()["status"] == "ISSUED"
    assert issued.json()["dispatches"][0]["is_simulated"] is True

    partial = api.post(f"/invoices/{draft['id']}/payments", operator, json={"amount": "80540"})
    assert partial.json()["payment_status"] == "PARTIALLY_PAID"
    paid = api.post(f"/invoices/{draft['id']}/payments", operator, json={"amount": "100000"})
    assert paid.json()["payment_status"] == "PAID"
    assert paid.json()["balance"]["amount_due"] == "0"


def test_payment_above_balance_is_refused(api: Api, clean_piece: str) -> None:
    operator = api.login("operateur")
    draft = api.import_piece(operator, clean_piece)["invoice"]
    _validate(api, draft)
    response = api.post(f"/invoices/{draft['id']}/payments", operator, json={"amount": "999999"})
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_INPUT"


def test_unknown_customer_blocks_validation_until_resolved(api: Api) -> None:
    operator = api.login("operateur")
    draft = api.import_piece(operator, UNKNOWN_CUSTOMER_PIECE)["invoice"]
    codes = {a["code"] for a in draft["anomalies"]}
    assert "UNKNOWN_CUSTOMER" in codes

    blocked = api.post(
        f"/invoices/{draft['id']}/validate", api.login("validateur"), version=draft["version"]
    )
    assert blocked.status_code == 422
    assert blocked.json()["code"] == "VALIDATION_BLOCKED"
    assert blocked.json()["anomalies"]

    current = draft
    for anomaly in draft["anomalies"]:
        if anomaly["severity"] == "BLOCKING":
            path = f"/invoices/{draft['id']}/anomalies/{anomaly['id']}/resolve"
            body = {"justification": "client créé hors référentiel, vérifié par téléphone"}
            current = api.post(path, operator, version=current["version"], json=body).json()
    assert current["blocking_count"] == 0
    assert _validate(api, current)["status"] == "VALIDATED"


def test_correcting_a_field_recomputes_the_draft(api: Api, clean_piece: str) -> None:
    operator = api.login("operateur")
    imported = api.import_piece(operator, clean_piece)
    doc_id, invoice = imported["document"]["id"], imported["invoice"]
    review = {"action": "correct", "value": "40"}
    api.post(f"/source-documents/{doc_id}/fields/lines[0].quantity/review", operator, json=review)

    updated = api.get(f"/invoices/{invoice['id']}", operator).json()
    assert updated["version"] == invoice["version"] + 1
    assert updated["lines"][0]["quantity"] == "40"
    assert {a["code"] for a in updated["anomalies"]} == {"AMOUNT_MISMATCH"}


def test_operator_cannot_validate_and_author_cannot_validate_own_draft(
    api: Api, clean_piece: str
) -> None:
    validator = api.login("validateur")
    draft = api.import_piece(validator, clean_piece)["invoice"]
    own = api.post(f"/invoices/{draft['id']}/validate", validator, version=draft["version"])
    assert own.status_code == 403

    operator = api.login("operateur")
    other = api.import_piece(operator, clean_piece.replace("CMD-2026-001", "CMD-2026-002"))
    response = api.post(f"/invoices/{other['invoice']['id']}/validate", operator, version=1)
    assert response.status_code == 403


def test_stale_version_is_refused_and_number_has_no_gap(api: Api, clean_piece: str) -> None:
    operator, validator = api.login("operateur"), api.login("validateur")
    first = api.import_piece(operator, clean_piece)["invoice"]
    stale = api.post(f"/invoices/{first['id']}/validate", validator, version=first["version"] + 5)
    assert stale.status_code == 409
    assert stale.json()["code"] == "VERSION_CONFLICT"

    second = api.import_piece(operator, clean_piece.replace("CMD-2026-001", "CMD-2026-003"))
    assert _validate(api, first)["number"] == "FA-2026-00001"
    assert _validate(api, second["invoice"])["number"] == "FA-2026-00002"


def test_same_file_twice_is_flagged_as_duplicate(api: Api, clean_piece: str) -> None:
    operator = api.login("operateur")
    api.import_piece(operator, clean_piece)
    again = api.import_piece(operator, clean_piece)["invoice"]
    assert "DUPLICATE_DOCUMENT" in {a["code"] for a in again["anomalies"]}


def test_idempotency_replays_and_rejects_reused_key(api: Api, clean_piece: str) -> None:
    operator = api.login("operateur")
    draft = api.import_piece(operator, clean_piece)["invoice"]
    _validate(api, draft)
    path = f"/invoices/{draft['id']}/payments"
    first = api.post(path, operator, key="same", json={"amount": "1000"})
    replay = api.post(path, operator, key="same", json={"amount": "1000"})
    assert replay.headers["idempotent-replayed"] == "true"
    assert replay.json() == first.json()
    assert len(replay.json()["payments"]) == 1

    reused = api.post(path, operator, key="same", json={"amount": "2000"})
    assert reused.status_code == 409
    assert reused.json()["code"] == "IDEMPOTENCY_KEY_REUSED"

    missing = api.client.post(
        f"/api/v1{path}", headers={"Authorization": f"Bearer {operator}"}, json={"amount": "1"}
    )
    assert missing.status_code == 422


def test_full_credit_note_cancels_invoice(api: Api, clean_piece: str) -> None:
    operator, validator = api.login("operateur"), api.login("validateur")
    draft = api.import_piece(operator, clean_piece)["invoice"]
    _validate(api, draft)
    credit = api.post(f"/invoices/{draft['id']}/credit-notes", validator, json={"reason": "erreur"})
    assert credit.status_code == 201
    note = credit.json()
    validated = api.post(f"/credit-notes/{note['id']}/validate", validator, version=note["version"])
    assert validated.json()["number"] == "AV-2026-00001"

    invoice = api.get(f"/invoices/{draft['id']}", operator).json()
    assert invoice["status"] == "CANCELLED"
    assert invoice["balance"]["amount_due"] == "0"

    again = api.post(f"/invoices/{draft['id']}/credit-notes", validator, json={"reason": "bis"})
    assert again.status_code == 409


def test_partial_credit_note_reduces_balance(api: Api, clean_piece: str) -> None:
    operator, validator = api.login("operateur"), api.login("validateur")
    draft = api.import_piece(operator, clean_piece)["invoice"]
    _validate(api, draft)
    body = {"reason": "sacs abîmés", "lines": [{"line_index": 0, "quantity": "2"}]}
    note = api.post(f"/invoices/{draft['id']}/credit-notes", validator, json=body).json()
    assert note["totals"]["gross_total"] == "12980"
    api.post(f"/credit-notes/{note['id']}/validate", validator, version=note["version"])
    invoice = api.get(f"/invoices/{draft['id']}", operator).json()
    assert invoice["status"] == "VALIDATED"
    assert invoice["balance"]["amount_due"] == "167560"


def test_discarded_draft_consumes_no_number(api: Api, clean_piece: str) -> None:
    operator = api.login("operateur")
    first = api.import_piece(operator, clean_piece)["invoice"]
    discarded = api.post(f"/invoices/{first['id']}/discard", operator, version=first["version"])
    assert discarded.json()["status"] == "DISCARDED"
    again = api.post(
        f"/invoices/{first['id']}/discard", operator, version=discarded.json()["version"]
    )
    assert again.json()["code"] == "INVALID_TRANSITION"

    second = api.import_piece(operator, clean_piece.replace("CMD-2026-001", "CMD-2026-004"))
    assert _validate(api, second["invoice"])["number"] == "FA-2026-00001"


def test_audit_chain_is_intact_and_listed(api: Api, clean_piece: str) -> None:
    operator = api.login("operateur")
    draft = api.import_piece(operator, clean_piece)["invoice"]
    _validate(api, draft)
    validator = api.login("validateur")
    entries = api.get(f"/audit-log?entity_id={draft['id']}", validator).json()
    assert [e["action"] for e in entries] == ["invoice.drafted", "invoice.validated"]
    assert api.get("/audit-log/verify", validator).json()["intact"] is True


def test_authentication_and_roles(api: Api) -> None:
    assert api.client.get("/api/v1/auth/me").status_code == 401
    bad = api.client.post("/api/v1/auth/login", json={"username": "operateur", "password": "x"})
    assert bad.status_code == 401
    operator = api.login("operateur")
    assert api.get("/auth/me", operator).json()["role"] == "OPERATOR"
    assert api.get("/audit-log", operator).status_code == 403
    assert api.post("/admin/reset", operator).status_code == 403


def test_admin_reset_empties_demo_data(api: Api, clean_piece: str) -> None:
    operator = api.login("operateur")
    api.import_piece(operator, clean_piece)
    assert api.post("/admin/reset", api.login("admin")).status_code == 204
    assert api.get("/invoices", operator).json() == []


def test_document_text_and_file_are_served(api: Api, clean_piece: str) -> None:
    operator = api.login("operateur")
    doc_id = api.import_piece(operator, clean_piece)["document"]["id"]
    document = api.get(f"/source-documents/{doc_id}", operator).json()
    assert document["text"].startswith("Commande CMD-2026-001")
    assert api.get(f"/source-documents/{doc_id}/file", operator).text == clean_piece
    assert api.get("/source-documents/DOC-inconnu", operator).status_code == 404
