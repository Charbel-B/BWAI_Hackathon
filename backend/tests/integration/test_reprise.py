"""Reprise après interruption : rien n'est perdu, rien n'est fait deux fois."""

from pathlib import Path

from fastapi.testclient import TestClient

from invoicing.bootstrap import create_app
from tests.integration.conftest import Api, build_api


def test_retry_after_lost_response_records_one_payment(api: Api, clean_piece: str) -> None:
    operator = api.login("operateur")
    draft = api.import_piece(operator, clean_piece)["invoice"]
    api.post(f"/invoices/{draft['id']}/validate", api.login("validateur"), version=1)
    path = f"/invoices/{draft['id']}/payments"
    api.post(path, operator, key="coupure-1", json={"amount": "50000"})
    # La réponse s'est perdue : le client renvoie exactement la même requête.
    retry = api.post(path, operator, key="coupure-1", json={"amount": "50000"})
    assert retry.headers["idempotent-replayed"] == "true"
    assert len(retry.json()["payments"]) == 1
    assert retry.json()["balance"]["amount_due"] == "130540"


def test_restart_keeps_data_and_numbering_continues(tmp_path: Path, clean_piece: str) -> None:
    client, settings = build_api(tmp_path)
    with client:
        api = Api(client, settings)
        first = api.import_piece(api.login("operateur"), clean_piece)["invoice"]
        api.post(f"/invoices/{first['id']}/validate", api.login("validateur"), version=1)

    # Redémarrage : nouvelle application sur la même base, jetons perdus.
    with TestClient(create_app(settings)) as restarted:
        again = Api(restarted, settings)
        operator = again.login("operateur")
        kept = again.get(f"/invoices/{first['id']}", operator).json()
        assert kept["number"] == "FA-2026-00001"
        assert kept["status"] == "VALIDATED"
        second = again.import_piece(operator, clean_piece.replace("CMD-2026-001", "CMD-2026-002"))
        validated = again.post(
            f"/invoices/{second['invoice']['id']}/validate", again.login("validateur"), version=1
        ).json()
        assert validated["number"] == "FA-2026-00002"
        assert again.get("/audit-log/verify", again.login("validateur")).json()["intact"] is True
