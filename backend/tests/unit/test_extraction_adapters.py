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
from invoicing.infrastructure.gemini_extractor import (
    GeminiConfig,
    GeminiExtractor,
    _extract_candidate_json,
)
from invoicing.infrastructure.recorded_extractor import (
    RecordedExtractor,
    content_sha256,
    serialize_extracted_fields,
)


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
    assert no_fallback.extract(b"inconnu", "text/plain") == ()


def test_gemini_extractor_validates_and_anchors_response() -> None:
    text = "Bonjour, commande du 20/11/2026 pour Menuiserie Houénou : 10 sacs à 5 500 FCFA."
    fake_llm_json = json.dumps(
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
    extractor = GeminiExtractor(
        config=GeminiConfig(api_key="fake-key", model="gemini-2.5-flash"),
        transport=lambda _prompt: fake_llm_json,
    )
    assert extractor.name == "gemini:gemini-2.5-flash"

    fields = {f.name: f for f in extractor.extract(text.encode("utf-8"), "text/plain")}
    assert fields["customer.name"].value == "Menuiserie Houénou"
    assert isinstance(fields["customer.name"].anchor, TextAnchor)
    assert fields["document.date"].value == "2026-11-20"
    assert fields["customer.tax_id"].status is FieldStatus.MISSING


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
    )
    result = extractor.extract(b"Client : Menuiserie Hou\xc3\xa9nou", "text/plain")
    assert calls == 2
    assert result[0].value == "Menuiserie Houénou"


def test_gemini_extractor_falls_back_to_rules_after_two_failures_or_missing_key() -> None:
    def failing_transport(_prompt: str) -> str:
        msg = "network timeout"
        raise OSError(msg)

    extractor = GeminiExtractor(
        config=GeminiConfig(api_key="fake-key"),
        transport=failing_transport,
    )
    msg = "Client : Menuiserie Houénou\nDate : 20/11/2026"
    fallback_fields = {f.name: f for f in extractor.extract(msg.encode("utf-8"), "text/plain")}
    assert fallback_fields["customer.name"].value == "Menuiserie Houénou"
    assert fallback_fields["document.date"].value == "2026-11-20"

    no_key_extractor = GeminiExtractor(config=GeminiConfig(api_key=""))
    no_key_fields = {f.name: f for f in no_key_extractor.extract(msg.encode("utf-8"), "text/plain")}
    assert no_key_fields["document.date"].value == "2026-11-20"

    unsupported = no_key_extractor.extract(b"binary", "application/octet-stream")
    assert all(f.status is FieldStatus.MISSING for f in unsupported)


def test_extract_candidate_json_parses_rest_envelope() -> None:
    envelope = json.dumps({"candidates": [{"content": {"parts": [{"text": '{"fields": []}'}]}}]})
    assert _extract_candidate_json(envelope) == '{"fields": []}'

    with pytest.raises(ValueError, match="sans contenu candidat"):
        _extract_candidate_json(json.dumps({"candidates": []}))

    with pytest.raises(TypeError, match="pas une chaîne JSON"):
        _extract_candidate_json(
            json.dumps({"candidates": [{"content": {"parts": [{"text": 123}]}}]})
        )
