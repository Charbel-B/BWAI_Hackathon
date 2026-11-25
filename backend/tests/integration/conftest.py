"""Application complète sur une base temporaire et les référentiels d'essai."""

import itertools
import shutil
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from invoicing.bootstrap import create_app
from invoicing.settings import REPO_ROOT, Settings

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PIECES = REPO_ROOT / "data" / "pieces" / "mise-au-point"
_keys = itertools.count()


@dataclass
class Api:
    """Client HTTP et raccourcis pour les en-têtes du contrat."""

    client: TestClient
    settings: Settings

    def login(self, username: str) -> str:
        body = {"username": username, "password": f"demo-{username}"}
        token: str = self.client.post("/api/v1/auth/login", json=body).json()["access_token"]
        return token

    def get(self, path: str, token: str) -> Response:
        headers = {"Authorization": f"Bearer {token}"}
        response: Response = self.client.get(f"/api/v1{path}", headers=headers)
        return response

    def post(
        self,
        path: str,
        token: str,
        *,
        version: int | None = None,
        key: str | None = None,
        **kw: Any,
    ) -> Response:
        headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": key or f"k{next(_keys)}"}
        if version is not None:
            headers["If-Match"] = str(version)
        response: Response = self.client.post(f"/api/v1{path}", headers=headers, **kw)
        return response

    def import_piece(self, token: str, text: str, name: str = "piece.txt") -> dict[str, Any]:
        files = {"file": (name, text.encode(), "text/plain")}
        response = self.post("/source-documents", token, files=files)
        assert response.status_code == 201, response.text
        body: dict[str, Any] = response.json()
        return body


@pytest.fixture
def api(tmp_path: Path) -> Iterator[Api]:
    data = tmp_path / "data"
    shutil.copytree(FIXTURES / "referentiels", data / "referentiels")
    settings = Settings(data_dir=data, database_path=tmp_path / "db.sqlite3")
    with TestClient(create_app(settings)) as client:
        yield Api(client, settings)


@pytest.fixture
def clean_piece() -> str:
    return (PIECES / "p001.txt").read_text(encoding="utf-8")
