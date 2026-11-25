from invoicing.infrastructure.config_files import config_sha256
from tests.integration.conftest import Api


def test_health_reports_status_fingerprint_and_what_is_simulated(api: Api) -> None:
    response = api.client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["config_sha256"] == config_sha256(api.settings.config_dir)
    assert body["demo_mode"] is True
    assert body["extractor"] == "local-rules-v1"
    assert body["simulated"]
