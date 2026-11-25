"""Tests unitaires du cœur pur d'extraction (normalisation, ancrage, confiance, règles)."""

import pytest

from invoicing.domain.extraction import ExtractedField, FieldStatus, TextAnchor
from invoicing.extraction import (
    CatalogHint,
    ExpectedDocument,
    RawFieldCandidate,
    RuleBasedExtractor,
    calibrate_thresholds,
    evaluate_predictions,
    find_text_anchor,
    format_calibration_markdown,
    is_value_grounded_in_raw_text,
    normalize_date,
    normalize_decimal,
    normalize_field_value,
    normalize_int,
    normalize_rate,
    normalize_tax_id,
    normalize_text,
    verify_and_build_field,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Menuiserie   Houénou  ", "Menuiserie Houénou"),
        ("   ", None),
    ],
)
def test_normalize_text_cleans_whitespace(raw: str, expected: str | None) -> None:
    assert normalize_text(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("3999900000011", "3999900000011"),
        ("IFU : 3999 9000 00022", "3999900000022"),
        ("12345", None),
        ("12345678901234", None),
    ],
)
def test_normalize_tax_id_validates_13_digits(raw: str, expected: str | None) -> None:
    assert normalize_tax_id(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2026-11-20", "2026-11-20"),
        ("20/11/2026", "2026-11-20"),
        ("20-11-2026", "2026-11-20"),
        ("20 novembre 2026", "2026-11-20"),
        ("5 février 2026", "2026-02-05"),
        ("31/02/2026", None),
        ("demain matin", None),
    ],
)
def test_normalize_date_handles_iso_dmy_and_french_months(raw: str, expected: str | None) -> None:
    assert normalize_date(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("5500", "5500"),
        ("5 500 FCFA", "5500"),
        ("45.000 F", "45000"),
        ("45,000", "45000"),
        ("12,5 m2", "12.5"),
        ("20.00", "20"),
        ("-10", None),
        ("un peu", None),
    ],
)
def test_normalize_decimal_parses_fcfa_and_quantities(raw: str, expected: str | None) -> None:
    assert normalize_decimal(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("5 %", "0.05"),
        ("5,5%", "0.055"),
        ("0.05", "0.05"),
        ("10", "0.1"),
        ("150%", None),
        ("aucune", None),
    ],
)
def test_normalize_rate_converts_percentages_to_unit_interval(
    raw: str, expected: str | None
) -> None:
    assert normalize_rate(raw) == expected


def test_normalize_int_and_field_dispatcher() -> None:
    assert normalize_int("30 jours") == "30"
    assert normalize_int("comptant") is None
    assert normalize_field_value("customer.tax_id", "3999900000011") == "3999900000011"
    assert normalize_field_value("document.date", "20/11/2026") == "2026-11-20"
    assert normalize_field_value("payment.terms_days", "45 jours") == "45"
    assert normalize_field_value("discount.global_rate", "5%") == "0.05"
    assert normalize_field_value("lines[0].unit_price", "5 500 F") == "5500"
    assert normalize_field_value("customer.name", "  Menuiserie Houénou ") == "Menuiserie Houénou"
    assert normalize_field_value("customer.name", None) is None


def test_find_text_anchor_handles_exact_and_whitespace_tolerant_matches() -> None:
    source = "Commande du 20/11/2026 : 20   sacs de Ciment CPJ 35 à 5 500 FCFA."
    exact = find_text_anchor(source, "20/11/2026")
    assert exact == TextAnchor(start=12, end=22)

    tolerant = find_text_anchor(source, "20 sacs de Ciment", start_from=10)
    assert tolerant is not None
    assert source[tolerant.start : tolerant.end] == "20   sacs de Ciment"

    case_insensitive = find_text_anchor(source, "ciment cpj 35", start_from=30)
    assert case_insensitive is not None
    assert source[case_insensitive.start : case_insensitive.end] == "Ciment CPJ 35"

    assert find_text_anchor(source, "introuvable") is None
    assert find_text_anchor(source, "   ") is None


def test_is_value_grounded_in_raw_text_detects_calculated_or_invented_values() -> None:
    assert is_value_grounded_in_raw_text("lines[0].unit_price", "5500", "5 500 FCFA")
    assert not is_value_grounded_in_raw_text(
        "lines[0].quantity", "12", "2 sacs par classe pour 6 classes"
    )
    assert is_value_grounded_in_raw_text("document.date", "2026-11-20", "le 20 novembre 2026")
    assert is_value_grounded_in_raw_text("discount.global_rate", "0.05", "remise 5%")
    assert is_value_grounded_in_raw_text(
        "customer.name", "Menuiserie Houénou", "Menuiserie Houénou"
    )
    assert not is_value_grounded_in_raw_text("customer.name", None, "Menuiserie")


def test_verify_and_build_field_downgrades_hallucinated_source_to_missing() -> None:
    source = "Bonjour, envoyez 10 sacs de Ciment CPJ 35."
    hallucinated = RawFieldCandidate(
        name="lines[0].unit_price",
        status=FieldStatus.FOUND,
        raw_value="5500",
        raw_text="5 500 FCFA",
        base_confidence=0.95,
    )
    field = verify_and_build_field(hallucinated, source)
    assert field.status is FieldStatus.MISSING
    assert field.value is None
    assert field.confidence is None
    assert field.anchor is None


def test_verify_and_build_field_caps_confidence_on_implicit_calculation() -> None:
    source = "Il nous faut 2 sacs de ciment par chantier pour 6 chantiers."
    calculated = RawFieldCandidate(
        name="lines[0].quantity",
        status=FieldStatus.FOUND,
        raw_value="12",
        raw_text="2 sacs de ciment par chantier pour 6 chantiers",
        base_confidence=0.95,
    )
    field = verify_and_build_field(calculated, source)
    assert field.status is FieldStatus.FOUND
    assert field.value == "12"
    assert field.confidence == 0.40


def test_verify_and_build_field_handles_ambiguous_and_invalid_format() -> None:
    source = "Date : demain matin. Remise : 5% fidélité + 2% cash."
    bad_date = RawFieldCandidate(
        name="document.date",
        status=FieldStatus.FOUND,
        raw_value="demain matin",
        raw_text="demain matin",
        base_confidence=0.90,
    )
    date_field = verify_and_build_field(bad_date, source)
    assert date_field.status is FieldStatus.AMBIGUOUS
    assert date_field.value is None
    assert date_field.confidence == 0.35

    ambiguous_discount = RawFieldCandidate(
        name="discount.global_rate",
        status=FieldStatus.AMBIGUOUS,
        raw_value=None,
        raw_text="5% fidélité + 2% cash",
        base_confidence=0.80,
    )
    disc_field = verify_and_build_field(ambiguous_discount, source)
    assert disc_field.status is FieldStatus.AMBIGUOUS
    assert disc_field.confidence == 0.50


def test_verify_and_build_field_uses_catalog_hint() -> None:
    catalog = CatalogHint(
        customer_names=("Entreprise Kpadonou et Fils", "Menuiserie Houénou"),
        tax_ids=("3999900000011",),
        item_labels=("Ciment CPJ 35 (sac de 50 kg)",),
    )
    source = "Client : Entreprise Kpadonou | IFU : 3999900000099 | Article : Peinture bleue"
    partial_customer = verify_and_build_field(
        RawFieldCandidate(
            "customer.name", FieldStatus.FOUND, "Entreprise Kpadonou", "Entreprise Kpadonou", 0.95
        ),
        source,
        catalog,
    )
    assert partial_customer.confidence == 0.75

    unknown_tax = verify_and_build_field(
        RawFieldCandidate(
            "customer.tax_id", FieldStatus.FOUND, "3999900000099", "3999900000099", 0.95
        ),
        source,
        catalog,
    )
    assert unknown_tax.confidence == 0.70

    unknown_item = verify_and_build_field(
        RawFieldCandidate(
            "lines[0].label", FieldStatus.FOUND, "Peinture bleue", "Peinture bleue", 0.95
        ),
        source,
        catalog,
    )
    assert unknown_item.confidence == 0.70


def test_rule_based_extractor_extracts_structured_message() -> None:
    catalog = CatalogHint(
        customer_names=("Entreprise Kpadonou et Fils",),
        tax_ids=("3999900000011",),
        item_labels=("Ciment CPJ 35 (sac de 50 kg)",),
    )
    extractor = RuleBasedExtractor(catalog=catalog)
    assert extractor.name == "local-rules-v1"

    message = (
        "Commande CMD-2026-001 du 20/11/2026\n"
        "Client : Entreprise Kpadonou et Fils\n"
        "IFU : 3999900000011\n"
        "- 20 sacs de Ciment CPJ 35 (sac de 50 kg) à 5 500 FCFA\n"
        "Remise fidélité 5 %\n"
        "Délai de paiement : 30 jours\n"
        "Total HT : 104 500 FCFA\n"
    )
    fields = {f.name: f for f in extractor.extract(message.encode("utf-8"), "text/plain")}
    assert fields["customer.name"].value == "Entreprise Kpadonou et Fils"
    assert fields["customer.tax_id"].value == "3999900000011"
    assert fields["document.reference"].value == "CMD-2026-001"
    assert fields["document.date"].value == "2026-11-20"
    assert fields["lines[0].quantity"].value == "20"
    assert fields["lines[0].unit"].value == "sacs"
    assert fields["lines[0].label"].value == "Ciment CPJ 35 (sac de 50 kg)"
    assert fields["lines[0].unit_price"].value == "5500"
    assert fields["discount.global_rate"].value == "0.05"
    assert fields["payment.terms_days"].value == "30"
    assert fields["totals.net"].value == "104500"


def test_rule_based_extractor_handles_unsupported_media_and_cumulative_discounts() -> None:
    extractor = RuleBasedExtractor()
    unsupported = extractor.extract(b"%PDF-1.4", "application/pdf")
    assert all(f.status is FieldStatus.MISSING for f in unsupported)

    ambiguous_msg = "Client : Menuiserie Houénou\nRemise 5% et remise cash 2%"
    fields = {f.name: f for f in extractor.extract(ambiguous_msg.encode("utf-8"), "text/plain")}
    assert fields["discount.global_rate"].status is FieldStatus.AMBIGUOUS
    assert fields["lines[0].quantity"].status is FieldStatus.MISSING


def test_evaluation_metrics_and_threshold_calibration() -> None:
    expected = [
        ExpectedDocument(
            doc_id="p001",
            fields={
                "customer.name": "Menuiserie Houénou",
                "customer.tax_id": None,
                "lines[0].quantity": "20",
            },
        )
    ]
    predictions = {
        "p001": [
            ExtractedField(
                "customer.name",
                FieldStatus.FOUND,
                "Menuiserie Houénou",
                "Menuiserie Houénou",
                0.92,
                TextAnchor(0, 18),
            ),
            ExtractedField(
                "customer.tax_id",
                FieldStatus.MISSING,
                None,
                None,
                None,
                None,
            ),
            ExtractedField(
                "lines[0].quantity",
                FieldStatus.FOUND,
                "25",
                "20",
                0.80,
                TextAnchor(20, 22),
            ),
        ]
    }
    m_85 = evaluate_predictions(expected, predictions, review_threshold=0.85)
    assert m_85.field_accuracy == 0.5
    assert m_85.true_missing_rate == 1.0
    assert m_85.high_confidence_errors == 0
    assert m_85.precision_above_threshold == 1.0
    assert m_85.automation_coverage == 0.5

    m_75 = evaluate_predictions(expected, predictions, review_threshold=0.75)
    assert m_75.high_confidence_errors == 1
    assert m_75.false_certainty_rate == 0.5

    table = format_calibration_markdown(calibrate_thresholds(expected, predictions, (0.75, 0.85)))
    assert "| 0.85 | 100.0 % | 0.0 % (0) |" in table
