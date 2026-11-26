"""Rejeu bout en bout des trois scénarios de démonstration de data/scenarios/."""

import json
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from invoicing.bootstrap import create_app
from invoicing.settings import REPO_ROOT, Settings
from tests.integration.conftest import Api

SCENARIOS = REPO_ROOT / "data" / "scenarios"


@pytest.fixture
def demo_api(tmp_path: Path) -> Iterator[Api]:
    data = tmp_path / "data"
    shutil.copytree(REPO_ROOT / "data" / "referentiels", data / "referentiels")
    settings = Settings(data_dir=data, database_path=tmp_path / "demo.sqlite3")
    with TestClient(create_app(settings)) as client:
        yield Api(client, settings)


def _load_scenario(name: str) -> tuple[str, dict[str, object]]:
    folder = SCENARIOS / name
    text = (folder / "piece.txt").read_text(encoding="utf-8")
    expected: dict[str, object] = json.loads((folder / "attendu.json").read_text(encoding="utf-8"))
    return text, expected


def test_scenario_01_propre_va_jusqu_a_la_validation(demo_api: Api) -> None:
    text, expected = _load_scenario("01-propre")
    operator = demo_api.login("operateur")
    validator = demo_api.login("validateur")

    draft = demo_api.import_piece(operator, text, "01-propre.txt")["invoice"]
    assert draft["status"] == expected["initial_status"]
    assert draft["blocking_count"] == 0
    assert draft["totals"]["net_total"] == "153000"
    assert draft["totals"]["vat_total"] == "27540"
    assert draft["totals"]["gross_total"] == "180540"

    validated = demo_api.post(
        f"/invoices/{draft['id']}/validate", validator, version=draft["version"]
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == expected["expected_final_status"]
    assert validated.json()["number"] == "FA-2026-00001"


def test_scenario_02_a_corriger_passe_apres_saisie_humaine(demo_api: Api) -> None:
    text, expected = _load_scenario("02-a-corriger")
    operator = demo_api.login("operateur")
    validator = demo_api.login("validateur")

    imported = demo_api.import_piece(operator, text, "02-a-corriger.txt")
    doc_id = imported["document"]["id"]
    draft = imported["invoice"]
    codes = {a["code"] for a in draft["anomalies"] if a["severity"] == "BLOCKING"}
    assert "MISSING_REQUIRED_FIELD" in codes

    blocked = demo_api.post(
        f"/invoices/{draft['id']}/validate", validator, version=draft["version"]
    )
    assert blocked.status_code == 422
    assert blocked.json()["code"] == "VALIDATION_BLOCKED"

    review = demo_api.post(
        f"/source-documents/{doc_id}/fields/document.date/review",
        operator,
        json={"action": "correct", "value": "2026-11-25"},
    )
    assert review.status_code == 200

    refreshed = demo_api.get(f"/invoices/{draft['id']}", operator).json()
    assert refreshed["blocking_count"] == 0
    assert refreshed["totals"]["gross_total"] == "92040"

    validated = demo_api.post(
        f"/invoices/{draft['id']}/validate", validator, version=refreshed["version"]
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == expected["expected_final_status"]


def test_scenario_03_bloque_refuse_la_validation(demo_api: Api) -> None:
    text, expected = _load_scenario("03-bloque")
    operator = demo_api.login("operateur")
    validator = demo_api.login("validateur")

    draft = demo_api.import_piece(operator, text, "03-bloque.txt")["invoice"]
    blocking_codes = {a["code"] for a in draft["anomalies"] if a["severity"] == "BLOCKING"}
    assert {"UNKNOWN_CUSTOMER", "AMOUNT_MISMATCH"}.issubset(blocking_codes)
    assert draft["totals"]["net_total"] == "186000"
    assert draft["totals"]["gross_total"] == "219480"

    blocked = demo_api.post(
        f"/invoices/{draft['id']}/validate", validator, version=draft["version"]
    )
    assert blocked.status_code == expected["expected_validation_http_status"]
    assert blocked.json()["code"] == expected["expected_validation_error_code"]
