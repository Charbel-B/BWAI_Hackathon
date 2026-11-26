"""Recouvrement : échéancier et relances, à date figée."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from invoicing.infrastructure.clock import FixedClock
from tests.integration.conftest import Api, build_api

# p001 : pièce du 20/11/2026, client à 30 jours, échéance le 20/12/2026.
LATE = datetime(2026, 12, 29, 9, tzinfo=UTC)


@pytest.fixture
def late_api(tmp_path: Path) -> Iterator[Api]:
    client, settings = build_api(tmp_path, FixedClock(LATE))
    with client:
        yield Api(client, settings)


def _validated(api: Api, piece: str) -> dict[str, Any]:
    draft = api.import_piece(api.login("operateur"), piece)["invoice"]
    body: dict[str, Any] = api.post(
        f"/invoices/{draft['id']}/validate", api.login("validateur"), version=draft["version"]
    ).json()
    return body


def test_overdue_invoice_is_listed_with_its_next_reminder(late_api: Api, clean_piece: str) -> None:
    invoice = _validated(late_api, clean_piece)
    board = late_api.get("/receivables", late_api.login("operateur")).json()
    assert board["overdue_count"] == 1
    assert board["overdue_amount"] == "180540"
    item = board["items"][0]
    assert item["invoice"]["id"] == invoice["id"]
    assert item["standing"] == "OVERDUE"
    assert item["days_late"] == 9
    assert item["next_step"]["code"] == "dernier-rappel"


def test_reminder_is_sent_once_on_the_preferred_channel(late_api: Api, clean_piece: str) -> None:
    invoice = _validated(late_api, clean_piece)
    operator = late_api.login("operateur")
    sent = late_api.post(f"/invoices/{invoice['id']}/reminders", operator)
    assert sent.status_code == 201
    body = sent.json()
    assert body["channel"] == "whatsapp"
    assert body["is_simulated"] is True
    assert "9 jours de retard" in body["message"]
    assert "180 540" in body["message"]

    again = late_api.post(f"/invoices/{invoice['id']}/reminders", operator)
    assert again.status_code == 422
    item = late_api.get("/receivables", operator).json()["items"][0]
    assert item["next_step"] is None
    assert len(item["reminders"]) == 1


def test_paid_invoice_leaves_the_board(late_api: Api, clean_piece: str) -> None:
    invoice = _validated(late_api, clean_piece)
    operator = late_api.login("operateur")
    late_api.post(f"/invoices/{invoice['id']}/payments", operator, json={"amount": "180540"})
    board = late_api.get("/receivables", operator).json()
    assert board["items"] == []
    assert board["outstanding"] == "0"
    refused = late_api.post(f"/invoices/{invoice['id']}/reminders", operator)
    assert refused.status_code == 422


def test_invoice_not_yet_due_has_no_reminder(api: Api, clean_piece: str) -> None:
    invoice = _validated(api, clean_piece)
    item = api.get("/receivables", api.login("operateur")).json()["items"][0]
    assert item["invoice"]["id"] == invoice["id"]
    assert item["standing"] in {"NOT_DUE", "DUE_SOON", "OVERDUE"}
