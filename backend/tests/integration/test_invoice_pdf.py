"""Tests d'intégration de la route GET /api/v1/invoices/{id}/pdf."""

from tests.integration.conftest import Api


def test_api_endpoint_returns_valid_pdf_with_qr_verification_code(
    api: Api, clean_piece: str
) -> None:
    operator = api.login("operateur")
    validator = api.login("validateur")
    draft = api.import_piece(operator, clean_piece)["invoice"]

    assert api.client.get(f"/api/v1/invoices/{draft['id']}/pdf").status_code == 401
    assert api.get("/invoices/INV-inconnu/pdf", operator).status_code == 404

    draft_pdf = api.get(f"/invoices/{draft['id']}/pdf", operator)
    assert draft_pdf.status_code == 200
    assert draft_pdf.headers["content-type"] == "application/pdf"
    assert draft_pdf.headers["cache-control"] == "no-store"
    assert draft_pdf.content.startswith(b"%PDF-1.4")
    assert b"BROUILLON" in draft_pdf.content
    assert b"/verifier/" not in draft_pdf.content
    assert b"180 540 FCFA" in draft_pdf.content

    validated = api.post(
        f"/invoices/{draft['id']}/validate", validator, version=draft["version"]
    ).json()
    final_pdf = api.get(f"/invoices/{draft['id']}/pdf", operator)
    assert final_pdf.status_code == 200
    assert validated["number"].encode("ascii") in final_pdf.content
    assert b"180 540 FCFA" in final_pdf.content
    assert b"BROUILLON" not in final_pdf.content

    code = validated["verification_code"]
    assert code is not None
    expected_path = f"/verifier/{draft['id']}?code={code}".encode("ascii")
    assert expected_path in final_pdf.content

    verdict = api.client.get(f"/api/v1/public/verify/{draft['id']}?code={code}")
    assert verdict.status_code == 200
    assert verdict.json()["verdict"] == "AUTHENTIC"
