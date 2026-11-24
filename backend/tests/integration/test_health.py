from fastapi.testclient import TestClient

from invoicing.bootstrap import create_app
from invoicing.infrastructure.config_files import config_sha256
from invoicing.settings import Settings


def test_health_reports_status_and_configuration_fingerprint() -> None:
    settings = Settings()
    client = TestClient(create_app(settings))

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["config_sha256"] == config_sha256(settings.config_dir)
