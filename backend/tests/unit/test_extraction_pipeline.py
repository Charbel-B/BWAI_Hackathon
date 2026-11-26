"""Tests unitaires du cœur pur d'extraction (normalisation, ancrage, confiance, règles)."""

import pytest

from invoicing.domain.errors import InvariantViolationError
from invoicing.domain.extraction import ExtractedField, FieldStatus, TextAnchor
from invoicing.extraction import (
    CalibrationPolicy,
    CatalogHint,
    ExpectedDocument,
    RawFieldCandidate,
    RuleBasedExtractor,
    apply_financial_cross_validation,
    calibrate_thresholds,
    evaluate_predictions,
    finalize_extracted_fields,
    find_text_anchor,
    format_calibration_markdown,
    is_local_extraction_sufficient,
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


def test_apply_financial_cross_validation_caps_deviating_price_and_mismatched_total() -> None:
    catalog = CatalogHint(
        item_labels=("Serrure de porte à cylindre",),
        item_prices=(("Serrure de porte à cylindre", "6500"),),
    )
    fields = [
        ExtractedField(
            "lines[0].label",
            FieldStatus.FOUND,
            "Serrure de porte à cylindre",
            "Serrure de porte à cylindre",
            0.95,
            TextAnchor(0, 27),
        ),
        ExtractedField(
            "lines[0].quantity",
            FieldStatus.FOUND,
            "10",
            "10",
            0.95,
            TextAnchor(28, 30),
        ),
        ExtractedField(
            "lines[0].unit_price",
            FieldStatus.FOUND,
            "4000",
            "4 000 FCFA",
            0.92,
            TextAnchor(31, 41),
        ),
        ExtractedField(
            "totals.net",
            FieldStatus.FOUND,
            "35000",
            "35 000 FCFA",
            0.90,
            TextAnchor(42, 53),
        ),
    ]
    validated = {f.name: f for f in apply_financial_cross_validation(fields, catalog)}
    assert validated["lines[0].unit_price"].confidence == 0.75
    assert validated["totals.net"].confidence == 0.70

    normal_fields = [
        fields[0],
        fields[1],
        ExtractedField(
            "lines[0].unit_price",
            FieldStatus.FOUND,
            "6500",
            "6 500 FCFA",
            0.92,
            TextAnchor(31, 41),
        ),
        ExtractedField(
            "totals.net",
            FieldStatus.FOUND,
            "65000",
            "65 000 FCFA",
            0.90,
            TextAnchor(42, 53),
        ),
    ]
    normal_validated = {f.name: f for f in apply_financial_cross_validation(normal_fields, catalog)}
    assert normal_validated["lines[0].unit_price"].confidence == 0.92
    assert normal_validated["totals.net"].confidence == 0.90


def _extract(text: str) -> dict[str, ExtractedField]:
    return {f.name: f for f in RuleBasedExtractor().extract(text.encode(), "text/plain")}


def test_quantity_anchor_targets_the_line_not_an_earlier_number() -> None:
    text = "Commande CMD-2026-001 du 20/11/2026\nClient : X\n- 20 sacs de Ciment à 5 500 FCFA\n"
    anchor = _extract(text)["lines[0].quantity"].anchor
    assert isinstance(anchor, TextAnchor)
    assert text[anchor.start : anchor.start + 7] == "20 sacs"


def test_unrecognized_second_line_is_flagged_and_forces_escalation() -> None:
    text = (
        "Client : Test\nDate : 20/11/2026\n- 2 sacs de ciment à 5500 F\n"
        "Envoyez aussi 3 barres de fer pour demain"
    )
    fields = _extract(text)
    assert fields["lines[1].quantity"].status is FieldStatus.AMBIGUOUS
    assert fields["lines[1].unit_price"].status is FieldStatus.MISSING
    assert not is_local_extraction_sufficient(list(fields.values()))


def test_cumulated_discounts_without_repeated_keyword_are_ambiguous() -> None:
    fields = _extract("Client : Test\n- 2 sacs de ciment à 5500 F\nRemise 5% fidelite + 2% cash")
    assert fields["discount.global_rate"].status is FieldStatus.AMBIGUOUS
    assert fields["discount.global_rate"].value is None


def test_ambiguous_discount_does_not_trigger_external_escalation() -> None:
    text = (
        "Commande du 20/11/2026\nClient : Test\n- 2 sacs de ciment à 5500 F\n"
        "Remise fidélité 5 % et remise cash 2 %\nDélai de paiement : 30 jours"
    )
    fields = _extract(text)
    assert fields["discount.global_rate"].status is FieldStatus.AMBIGUOUS
    assert is_local_extraction_sufficient(list(fields.values()))


def test_vat_rate_is_not_read_as_a_vat_amount_and_phone_is_not_an_ifu() -> None:
    fields = _extract("Client : Test\nTel 2290199990001\n- 2 sacs de farine à 5000 F\nTVA 18 %")
    assert fields["totals.vat"].status is FieldStatus.MISSING
    assert fields["customer.tax_id"].status is FieldStatus.MISSING
    assert _extract("Client : Test\nTVA : 27 540 FCFA")["totals.vat"].value == "27540"


def test_calibration_policy_rejects_cap_at_or_above_threshold() -> None:
    with pytest.raises(InvariantViolationError):
        CalibrationPolicy(review_threshold=0.70, price_deviation_cap=0.75)


def test_conflicting_duplicate_fields_become_ambiguous() -> None:
    f1 = ExtractedField("customer.name", FieldStatus.FOUND, "A", "A", 0.9, TextAnchor(0, 1))
    f2 = ExtractedField("customer.name", FieldStatus.FOUND, "B", "B", 0.9, TextAnchor(2, 3))
    merged = {f.name: f for f in finalize_extracted_fields([f1, f2])}
    assert merged["customer.name"].status is FieldStatus.AMBIGUOUS
    assert merged["customer.name"].value is None
    assert merged["customer.name"].confidence == 0.50


def test_total_mismatch_check_is_skipped_when_discount_is_present() -> None:
    text = (
        "Commande du 20/11/2026\nClient : Test\n"
        "- 10 sacs de Ciment à 5 000 FCFA\nRemise 10 %\nTotal HT : 45 000 FCFA\n"
    )
    fields = _extract(text)
    assert fields["totals.net"].value == "45000"
    assert fields["totals.net"].confidence == 0.88


def test_delivered_quantity_normalization_and_partial_delivery_extraction() -> None:
    assert normalize_field_value("lines[0].delivered_quantity", "8 rouleaux") == "8"
    assert is_value_grounded_in_raw_text("lines[0].delivered_quantity", "8", "8")

    p008 = (
        "Bonsoir boss, Pharmacie Espoir de Calavi (IFU 3999900000066) le 23/11/2026. "
        "On a bien reçu Fil électrique 2.5 mm2 (rouleau de 100 m), qté livrée 8 rouleaux "
        "sur les 10 commandés, tarif convenu 32000f le rouleau."
    )
    catalog = CatalogHint(
        customer_names=("Pharmacie Espoir de Calavi",),
        tax_ids=("3999900000066",),
        item_labels=("Fil électrique 2.5 mm2 (rouleau de 100 m)",),
        item_prices=(("Fil électrique 2.5 mm2 (rouleau de 100 m)", "32000"),),
    )
    fields = {
        f.name: f
        for f in RuleBasedExtractor(catalog=catalog).extract(p008.encode("utf-8"), "text/plain")
    }
    assert fields["customer.name"].value == "Pharmacie Espoir de Calavi"
    assert fields["lines[0].label"].value == "Fil électrique 2.5 mm2 (rouleau de 100 m)"
    assert fields["lines[0].quantity"].value == "10"
    assert fields["lines[0].delivered_quantity"].value == "8"
    assert fields["lines[0].unit"].value == "rouleaux"
    assert fields["lines[0].unit_price"].value == "32000"
    assert "lines[1].quantity" not in fields


def test_structured_line_reads_trailing_or_separate_delivered_quantity() -> None:
    inline = (
        "Commande du 23/11/2026\nClient : Test\n"
        "- 10 sacs de Ciment CPJ 35 à 5 500 FCFA (qté livrée : 8)\n"
    )
    fields = _extract(inline)
    assert fields["lines[0].quantity"].value == "10"
    assert fields["lines[0].delivered_quantity"].value == "8"

    separate = (
        "Commande du 23/11/2026\nClient : Test\n"
        "- 10 sacs de Ciment CPJ 35 à 5 500 FCFA\n"
        "Livraison partielle : 7 sacs sur les 10 commandés.\n"
    )
    sep_fields = _extract(separate)
    assert sep_fields["lines[0].quantity"].value == "10"
    assert sep_fields["lines[0].delivered_quantity"].value == "7"
    assert "lines[1].quantity" not in sep_fields


def test_multiple_partial_deliveries_keep_bounded_windows_and_zero_delivery() -> None:
    text = (
        "Client : Test\nDate : 24/11/2026\n"
        "On a reçu Ciment CPJ 35, 0 sacs sur les 10 prévus.\n"
        "On a reçu Peinture blanche à 28 000 FCFA, livré 3 seaux sur les 5 commandés.\n"
    )
    fields = _extract(text)
    assert fields["lines[0].label"].value == "Ciment CPJ 35"
    assert fields["lines[0].quantity"].value == "10"
    assert fields["lines[0].delivered_quantity"].value == "0"
    assert fields["lines[0].unit_price"].status is FieldStatus.MISSING
    assert fields["lines[1].label"].value == "Peinture blanche à 28 000 FCFA"
    assert fields["lines[1].quantity"].value == "5"
    assert fields["lines[1].delivered_quantity"].value == "3"
    assert fields["lines[1].unit_price"].value == "28000"
