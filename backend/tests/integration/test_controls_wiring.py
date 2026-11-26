"""Tests d'intégration du branchement de QUANTITY_MISMATCH et DOCUMENT_INCONSISTENCY."""

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from invoicing.bootstrap import create_app
from invoicing.settings import REPO_ROOT, Settings
from tests.integration.conftest import Api


@pytest.fixture
def full_api(tmp_path: Path) -> Iterator[Api]:
    data = tmp_path / "data"
    shutil.copytree(REPO_ROOT / "data" / "referentiels", data / "referentiels")
    settings = Settings(data_dir=data, database_path=tmp_path / "wiring.sqlite3")
    with TestClient(create_app(settings)) as client:
        yield Api(client, settings)


def test_importing_p008_triggers_quantity_mismatch_and_clears_after_correction(
    full_api: Api,
) -> None:
    p008_text = (REPO_ROOT / "data" / "pieces" / "mise-au-point" / "p008.txt").read_text(
        encoding="utf-8"
    )
    operator = full_api.login("operateur")
    validator = full_api.login("validateur")

    imported = full_api.import_piece(operator, p008_text, "p008.txt")
    doc = imported["document"]
    draft = imported["invoice"]

    fields_by_name = {f["name"]: f for f in doc["fields"]}
    assert fields_by_name["lines[0].quantity"]["value"] == "10"
    assert fields_by_name["lines[0].delivered_quantity"]["value"] == "8"

    anomalies = {a["code"]: a for a in draft["anomalies"]}
    assert "QUANTITY_MISMATCH" in anomalies
    assert anomalies["QUANTITY_MISMATCH"]["severity"] == "BLOCKING"
    assert anomalies["QUANTITY_MISMATCH"]["field"] == "lines[0].quantity"

    blocked = full_api.post(
        f"/invoices/{draft['id']}/validate", validator, version=draft["version"]
    )
    assert blocked.status_code == 422
    assert blocked.json()["code"] == "VALIDATION_BLOCKED"

    # Aligner la quantité facturée sur la quantité livrée lève l'écart
    review = full_api.post(
        f"/source-documents/{doc['id']}/fields/lines[0].quantity/review",
        operator,
        json={"action": "correct", "value": "8"},
    )
    assert review.status_code == 200

    refreshed = full_api.get(f"/invoices/{draft['id']}", operator).json()
    assert "QUANTITY_MISMATCH" not in {a["code"] for a in refreshed["anomalies"]}
    assert refreshed["blocking_count"] == 0
    validated = full_api.post(
        f"/invoices/{draft['id']}/validate", validator, version=refreshed["version"]
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == "VALIDATED"


def test_same_reference_with_different_customer_triggers_document_inconsistency(
    full_api: Api,
) -> None:
    operator = full_api.login("operateur")
    first = (
        "Commande CMD-2026-500 du 20/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "- 10 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    second = (
        "Commande CMD-2026-500 du 20/11/2026\n"
        "Client : Menuiserie Houénou\n"
        "- 10 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    full_api.import_piece(operator, first, "commande-500.txt")
    draft = full_api.import_piece(operator, second, "livraison-500.txt")["invoice"]

    anomalies = {a["code"]: a for a in draft["anomalies"]}
    assert "DOCUMENT_INCONSISTENCY" in anomalies
    assert anomalies["DOCUMENT_INCONSISTENCY"]["severity"] == "BLOCKING"
    assert anomalies["DOCUMENT_INCONSISTENCY"]["field"] == "customer.name"


def test_related_quote_chronology_triggers_inconsistency_only_when_postdated(
    full_api: Api,
) -> None:
    operator = full_api.login("operateur")
    quote_later = (
        "Devis DEV-2026-600 du 25/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "- 5 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    order_earlier = (
        "Commande DEV-2026-600 du 20/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "- 5 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    full_api.import_piece(operator, quote_later, "devis-600.txt")
    inconsistent = full_api.import_piece(operator, order_earlier, "commande-600.txt")["invoice"]
    assert "DOCUMENT_INCONSISTENCY" in {a["code"] for a in inconsistent["anomalies"]}

    # Devis antérieur à la commande : chronologie cohérente (pas de DOCUMENT_INCONSISTENCY)
    quote_earlier = (
        "Devis DEV-2026-601 du 18/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "- 5 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    order_later = (
        "Commande DEV-2026-601 du 20/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "- 5 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    full_api.import_piece(operator, quote_earlier, "devis-601.txt")
    coherent = full_api.import_piece(operator, order_later, "commande-601.txt")["invoice"]
    assert "DOCUMENT_INCONSISTENCY" not in {a["code"] for a in coherent["anomalies"]}


def test_discarded_invoice_is_ignored_for_related_document_consistency(full_api: Api) -> None:
    operator = full_api.login("operateur")
    first = (
        "Commande CMD-2026-700 du 20/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "- 5 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    first_inv = full_api.import_piece(operator, first, "commande-700-a.txt")["invoice"]
    discarded = full_api.post(
        f"/invoices/{first_inv['id']}/discard", operator, version=first_inv["version"]
    )
    assert discarded.status_code == 200

    second = (
        "Commande CMD-2026-700 du 20/11/2026\n"
        "Client : Menuiserie Houénou\n"
        "- 5 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    second_inv = full_api.import_piece(operator, second, "commande-700-b.txt")["invoice"]
    assert "DOCUMENT_INCONSISTENCY" not in {a["code"] for a in second_inv["anomalies"]}


def test_order_then_later_delivery_note_is_coherent_but_earlier_bl_flags_inconsistency(
    full_api: Api,
) -> None:
    operator = full_api.login("operateur")
    order = (
        "Commande CMD-2026-800 du 20/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "- 5 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    later_bl = (
        "Bon de livraison CMD-2026-800 du 22/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "- 5 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    full_api.import_piece(operator, order, "commande-800.txt")
    bl_draft = full_api.import_piece(operator, later_bl, "bl-800.txt")["invoice"]
    assert "DOCUMENT_INCONSISTENCY" not in {a["code"] for a in bl_draft["anomalies"]}

    # Sens inverse invalide : BL daté avant la commande -> DOCUMENT_INCONSISTENCY
    earlier_bl = (
        "Bon de livraison CMD-2026-801 du 18/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "- 5 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    later_order = (
        "Commande CMD-2026-801 du 20/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "- 5 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    full_api.import_piece(operator, earlier_bl, "bl-801.txt")
    bad_order = full_api.import_piece(operator, later_order, "commande-801.txt")["invoice"]
    anomalies = {a["code"]: a for a in bad_order["anomalies"]}
    assert "DOCUMENT_INCONSISTENCY" in anomalies
    assert anomalies["DOCUMENT_INCONSISTENCY"]["field"] == "document.date"

    # Un nom de fichier contenant « bl » dans un mot (« cable ») n'est pas un BL
    earlier_cable = (
        "Commande CMD-2026-802 du 18/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "- 5 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    later_cable = (
        "Commande CMD-2026-802 du 20/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "- 5 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    full_api.import_piece(operator, earlier_cable, "cable-802.txt")
    ok_cable = full_api.import_piece(operator, later_cable, "suite-802.txt")["invoice"]
    assert "DOCUMENT_INCONSISTENCY" not in {a["code"] for a in ok_cable["anomalies"]}
