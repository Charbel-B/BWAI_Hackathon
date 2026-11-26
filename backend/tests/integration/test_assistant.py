"""Copilote : réponses tirées des données réelles, avec sources et actions."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from invoicing.application.assistant import detect_intent
from invoicing.infrastructure.clock import FixedClock
from tests.integration.conftest import Api, build_api

UNKNOWN_CUSTOMER_PIECE = """Commande CMD-2026-900 du 21/11/2026
Client : Société Inconnue SARL
- 3 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA
"""


def _ask(api: Api, question: str, invoice_id: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"question": question}
    if invoice_id:
        body["invoice_id"] = invoice_id
    result: dict[str, Any] = api.post("/assistant/ask", api.login("operateur"), json=body).json()
    return result


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("Pourquoi je ne peux pas valider ?", "pourquoi_bloquee"),
        ("Explique ce total", "expliquer_total"),
        ("Quelles factures sont en RETARD ?", "factures_en_retard"),
        ("Que faire ensuite ?", "que_faire_ensuite"),
        ("Bonjour", "aide"),
        ("Que sais-tu faire ?", "aide"),
    ],
)
def test_intents_are_detected_without_accents_or_case(question: str, intent: str) -> None:
    assert detect_intent(question) == intent


def test_blocked_draft_lists_its_blocking_points(api: Api) -> None:
    draft = api.import_piece(api.login("operateur"), UNKNOWN_CUSTOMER_PIECE)["invoice"]
    answer = _ask(api, "Pourquoi c'est bloqué ?", draft["id"])
    assert answer["intent"] == "pourquoi_bloquee"
    assert "absent du référentiel" in answer["answer"]
    assert {s["label"] for s in answer["sources"]} >= {"UNKNOWN_CUSTOMER"}
    assert answer["actions"][0]["path"] == f"/factures/{draft['id']}"
    assert answer["engine"] == "local-intents-v1"


def test_total_is_explained_with_the_engine_figures(api: Api, clean_piece: str) -> None:
    draft = api.import_piece(api.login("operateur"), clean_piece)["invoice"]
    answer = _ask(api, "Explique-moi le montant", draft["id"])
    assert "180 540" in answer["answer"]
    assert "110 000 HT" in answer["answer"]


def test_help_without_context(api: Api) -> None:
    assert _ask(api, "salut")["intent"] == "aide"
    assert _ask(api, "Pourquoi ?")["answer"].startswith("Ouvrez une facture")


@pytest.fixture
def late_api(tmp_path: Path) -> Iterator[Api]:
    client, settings = build_api(tmp_path, FixedClock(datetime(2026, 12, 29, 9, tzinfo=UTC)))
    with client:
        yield Api(client, settings)


def test_overdue_invoices_are_listed(late_api: Api, clean_piece: str) -> None:
    draft = late_api.import_piece(late_api.login("operateur"), clean_piece)["invoice"]
    late_api.post(f"/invoices/{draft['id']}/validate", late_api.login("validateur"), version=1)
    answer = _ask(late_api, "Qui est en retard ?")
    assert "1 facture(s) en retard" in answer["answer"]
    assert "9 j de retard" in answer["answer"]
    assert answer["actions"][0]["path"] == "/recouvrement"
    next_move = _ask(late_api, "Que faire maintenant ?", draft["id"])
    assert "émettez-la" in next_move["answer"]
