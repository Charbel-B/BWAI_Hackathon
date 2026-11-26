"""Tests d'intégration de la route GET /api/v1/invoices/{id}/pdf."""

from tests.integration.conftest import Api


def test_api_endpoint_returns_valid_pdf_for_draft_and_validated_invoice(
    api: Api, clean_piece: str
) -> None:
    operator = api.login("operateur")
    validator = api.login("validateur")
    draft = api.import_piece(operator, clean_piece)["invoice"]

    draft_pdf = api.get(f"/invoices/{draft['id']}/pdf", operator)
    assert draft_pdf.status_code == 200
    assert draft_pdf.headers["content-type"] == "application/pdf"
    assert draft_pdf.content.startswith(b"%PDF-1.4")
    assert b"BROUILLON" in draft_pdf.content
    assert b"180 540 FCFA" in draft_pdf.content

    validated = api.post(
        f"/invoices/{draft['id']}/validate", validator, version=draft["version"]
    ).json()
    final_pdf = api.get(f"/invoices/{draft['id']}/pdf", operator)
    assert final_pdf.status_code == 200
    assert validated["number"].encode("ascii") in final_pdf.content
    assert b"180 540 FCFA" in final_pdf.content
    assert b"BROUILLON" not in final_pdf.content
