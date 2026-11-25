"""Tests unitaires des adaptateurs d'extraction (RecordedExtractor et GeminiExtractor)."""

import json
from pathlib import Path

import pytest

from invoicing.domain.extraction import (
    ExtractedField,
    FieldStatus,
    RegionAnchor,
    TextAnchor,
)
from invoicing.infrastructure.extraction_config import load_extraction_config
from invoicing.infrastructure.gemini_extractor import (
    GeminiConfig,
    GeminiExtractor,
    _extract_candidate_json,
    _NonRetryableApiError,
)
from invoicing.infrastructure.recorded_extractor import (
    RecordedExtractor,
    content_sha256,
    serialize_extracted_fields,
)
from invoicing.settings import REPO_ROOT


def test_recorded_extractor_replays_by_sha256_and_serializes(tmp_path: Path) -> None:
    content = b"Commande du 20/11/2026 pour Menuiserie Houenou"
    digest = content_sha256(content)
    fields = [
        ExtractedField(
            "customer.name",
            FieldStatus.FOUND,
            "Menuiserie Houénou",
            "Menuiserie Houenou",
            0.94,
            TextAnchor(28, 46),
        ),
        ExtractedField(
            "lines[0].quantity",
            FieldStatus.FOUND,
            "10",
            "10",
            0.90,
            RegionAnchor(page=1, box=(0.1, 0.2, 0.3, 0.4)),
        ),
    ]
    serialized = serialize_extracted_fields(fields)
    store_file = tmp_path / "recorded.json"
    store_file.write_text(
        json.dumps(
            {
                "source_model": "gemini-2.5-flash",
                "records": {digest: serialized},
            }
        ),
        encoding="utf-8",
    )

    fallback = RecordedExtractor(
        records={
            content_sha256(b"autre"): [
                ExtractedField("customer.name", FieldStatus.MISSING, None, None, None, None)
            ]
        }
    )
    extractor = RecordedExtractor.from_json_file(store_file, fallback=fallback)
    assert extractor.name == "recorded:gemini-2.5-flash"

    replayed = extractor.extract(content, "text/plain")
    assert len(replayed) == 2
    assert replayed[0].value == "Menuiserie Houénou"
    assert replayed[1].anchor == RegionAnchor(page=1, box=(0.1, 0.2, 0.3, 0.4))

    from_fallback = extractor.extract(b"autre", "text/plain")
    assert len(from_fallback) == 1
    assert from_fallback[0].status is FieldStatus.MISSING

    no_fallback = RecordedExtractor(records={})
    missing_fields = no_fallback.extract(b"inconnu", "text/plain")
    assert len(missing_fields) == 5
    assert all(f.status is FieldStatus.MISSING for f in missing_fields)


def test_gemini_extractor_validates_and_anchors_response() -> None:
    text = "Bonjour, commande du 20/11/2026 pour Menuiserie Houénou : 10 sacs à 5 500 FCFA."
    fake_llm_json = (
        "```json\n"
        + json.dumps(
            {
                "fields": [
                    {
                        "name": "customer.name",
                        "status": "FOUND",
                        "value": "Menuiserie Houénou",
                        "raw_text": "Menuiserie Houénou",
                        "confidence": 0.95,
                    },
                    {
                        "name": "customer.unknown_extra",
                        "status": "FOUND",
                        "value": "hors-contrat",
                        "raw_text": "Bonjour",
                        "confidence": 0.99,
                    },
                    {
                        "name": "document.date",
                        "status": "FOUND",
                        "value": "20/11/2026",
                        "raw_text": "20/11/2026",
                        "confidence": 0.96,
                    },
                    {
                        "name": "customer.tax_id",
                        "status": "MISSING",
                        "value": None,
                        "raw_text": None,
                        "confidence": None,
                    },
                ]
            }
        )
        + "\n```"
    )
    extractor = GeminiExtractor(
        config=GeminiConfig(api_key="fake-key", model="gemini-2.5-flash"),
        transport=lambda _prompt: fake_llm_json,
        sleep_fn=lambda _sec: None,
    )
    assert extractor.name == "cascade:local-rules-v1+gemini:gemini-2.5-flash"

    fields = {f.name: f for f in extractor.extract(text.encode("utf-8"), "text/plain")}
    assert extractor.name == "gemini:gemini-2.5-flash"
    assert "customer.unknown_extra" not in fields
    assert fields["customer.name"].value == "Menuiserie Houénou"
    assert isinstance(fields["customer.name"].anchor, TextAnchor)
    assert fields["document.date"].value == "2026-11-20"
    assert fields["customer.tax_id"].status is FieldStatus.MISSING
    assert fields["lines[0].quantity"].status is FieldStatus.MISSING


def test_gemini_extractor_retries_once_on_invalid_json_then_succeeds() -> None:
    calls = 0

    def flaky_transport(_prompt: str) -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            return "{not-valid-json"
        return json.dumps(
            {
                "fields": [
                    {
                        "name": "customer.name",
                        "status": "FOUND",
                        "value": "Menuiserie Houénou",
                        "raw_text": "Menuiserie Houénou",
                        "confidence": 0.91,
                    }
                ]
            }
        )

    extractor = GeminiExtractor(
        config=GeminiConfig(api_key="fake-key"),
        transport=flaky_transport,
        sleep_fn=lambda _sec: None,
    )
    result = extractor.extract(b"Client : Menuiserie Hou\xc3\xa9nou", "text/plain")
    assert calls == 2
    assert result[0].value == "Menuiserie Houénou"


def test_gemini_extractor_does_not_retry_non_retryable_errors() -> None:
    calls = 0

    def auth_error_transport(_prompt: str) -> str:
        nonlocal calls
        calls += 1
        msg = "HTTP 401"
        raise _NonRetryableApiError(msg)

    extractor = GeminiExtractor(
        config=GeminiConfig(api_key="bad-key"),
        transport=auth_error_transport,
        sleep_fn=lambda _sec: None,
    )
    extractor.extract(b"Client : Menuiserie Hou\xc3\xa9nou", "text/plain")
    assert calls == 1
    assert extractor.name == "fallback:local-rules-v1"


def test_gemini_extractor_falls_back_to_rules_after_two_failures_or_missing_key() -> None:
    def failing_transport(_prompt: str) -> str:
        msg = "network timeout"
        raise OSError(msg)

    extractor = GeminiExtractor(
        config=GeminiConfig(api_key="fake-key"),
        transport=failing_transport,
        sleep_fn=lambda _sec: None,
    )
    msg = "Client : Menuiserie Houénou\nDate : 20/11/2026"
    fallback_fields = {f.name: f for f in extractor.extract(msg.encode("utf-8"), "text/plain")}
    assert extractor.name == "fallback:local-rules-v1"
    assert fallback_fields["customer.name"].value == "Menuiserie Houénou"
    assert fallback_fields["document.date"].value == "2026-11-20"

    no_key_extractor = GeminiExtractor(config=GeminiConfig(api_key=""))
    no_key_fields = {f.name: f for f in no_key_extractor.extract(msg.encode("utf-8"), "text/plain")}
    assert no_key_extractor.name == "fallback:local-rules-v1"
    assert no_key_fields["document.date"].value == "2026-11-20"

    unsupported = no_key_extractor.extract(b"binary", "application/octet-stream")
    assert all(f.status is FieldStatus.MISSING for f in unsupported)


def test_gemini_extractor_local_first_skips_api_when_local_is_complete() -> None:
    calls = 0

    def counting_transport(_prompt: str) -> str:
        nonlocal calls
        calls += 1
        return '{"fields": []}'

    extractor = GeminiExtractor(
        config=GeminiConfig(api_key="fake-key", local_first=True),
        transport=counting_transport,
        sleep_fn=lambda _sec: None,
    )
    complete_doc = (
        "Commande CMD-2026-001 du 20/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "- 20 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
    )
    fields = {f.name: f for f in extractor.extract(complete_doc.encode("utf-8"), "text/plain")}
    assert calls == 0
    assert extractor.name == "cascade:local-rules-v1"
    assert fields["customer.name"].value == "Entreprise Kpadonou et Fils"
    assert fields["lines[0].unit_price"].value == "5500"


def test_load_extraction_config_reads_yaml_and_builds_policy() -> None:
    cfg, policy = load_extraction_config(REPO_ROOT / "config")
    assert cfg.seuil_confiance_revue == 0.85
    assert cfg.local_first is True
    assert policy.review_threshold == 0.85
    assert str(policy.price_deviation_limit) == "0.2"


def test_extract_candidate_json_parses_rest_envelope() -> None:
    envelope = json.dumps({"candidates": [{"content": {"parts": [{"text": '{"fields": []}'}]}}]})
    assert _extract_candidate_json(envelope) == '{"fields": []}'

    with pytest.raises(ValueError, match="sans contenu candidat"):
        _extract_candidate_json(json.dumps({"candidates": []}))

    with pytest.raises(ValueError, match="pas une chaîne JSON"):
        _extract_candidate_json(
            json.dumps({"candidates": [{"content": {"parts": [{"text": 123}]}}]})
        )
