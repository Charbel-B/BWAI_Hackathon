"""Tests unitaires exhaustifs des 10 codes d'anomalies (positif et négatif pour chacun)."""

from datetime import UTC, date, datetime
from decimal import Decimal

from invoicing.domain.calculation import CalculationRules, compute_invoice
from invoicing.domain.controls import (
    ControlRules,
    DraftUnderReview,
    RelatedDocument,
    check_draft,
)
from invoicing.domain.drafting import build_draft
from invoicing.domain.extraction import (
    ExtractedField,
    FieldStatus,
    Review,
    ReviewState,
    TextAnchor,
)
from invoicing.domain.invoice import Severity
from invoicing.domain.referentials import Customer, Item, Referentials
from invoicing.infrastructure.business_config import load_business_config
from invoicing.settings import REPO_ROOT

AT = datetime(2026, 11, 25, tzinfo=UTC)
CALC_RULES = CalculationRules()

REFS = Referentials(
    customers=(
        Customer(
            id="CLI-001",
            legal_name="Entreprise Kpadonou et Fils",
            tax_id="3999900000011",
            phone="+2290199990001",
            email="contact@kpadonou.example",
            preferred_channel="whatsapp",
            payment_terms_days=30,
            vat_liable=True,
        ),
    ),
    items=(
        Item(
            id="ART-001",
            label="Ciment CPJ 35 (sac de 50 kg)",
            unit="sac",
            unit_price_net=Decimal(5500),
            vat_rate=Decimal(18),
        ),
    ),
)

RULES = load_business_config(REPO_ROOT / "config").control_rules(review_threshold=0.85)


def _found(name: str, value: str, confidence: float = 0.95) -> ExtractedField:
    return ExtractedField(name, FieldStatus.FOUND, value, value, confidence, TextAnchor(0, 1))


def _nominal_fields(**overrides: ExtractedField) -> list[ExtractedField]:
    base = {
        "customer.name": _found("customer.name", "Entreprise Kpadonou et Fils"),
        "document.reference": _found("document.reference", "CMD-2026-001"),
        "document.date": _found("document.date", "2026-11-20"),
        "lines[0].label": _found("lines[0].label", "Ciment CPJ 35 (sac de 50 kg)"),
        "lines[0].quantity": _found("lines[0].quantity", "10"),
        "lines[0].unit_price": _found("lines[0].unit_price", "5500"),
        "totals.net": _found("totals.net", "55000"),
    }
    base.update(overrides)
    return list(base.values())


def _run(
    fields: list[ExtractedField],
    *,
    duplicate_of: str | None = None,
    delivered_quantities: dict[int, Decimal] | None = None,
    related_documents: tuple[RelatedDocument, ...] = (),
    rules: ControlRules = RULES,
) -> dict[str, Severity]:
    content = build_draft(fields, REFS, CALC_RULES.default_vat_rate)
    _, totals = compute_invoice(content.lines, content.global_discount_rate, CALC_RULES)
    draft = DraftUnderReview(
        content=content,
        totals=totals,
        fields=fields,
        duplicate_of=duplicate_of,
        delivered_quantities=delivered_quantities or {},
        related_documents=related_documents,
    )
    return {a.code: a.severity for a in check_draft(draft, REFS, rules)}


def test_clean_draft_triggers_no_anomalies() -> None:
    assert _run(_nominal_fields()) == {}


def test_unknown_customer_triggers_and_known_does_not() -> None:
    assert "UNKNOWN_CUSTOMER" not in _run(_nominal_fields())
    anomalies = _run(_nominal_fields(**{"customer.name": _found("customer.name", "Client X")}))
    assert anomalies["UNKNOWN_CUSTOMER"] is Severity.BLOCKING


def test_unknown_item_triggers_and_known_does_not() -> None:
    assert "UNKNOWN_ITEM" not in _run(_nominal_fields())
    anomalies = _run(
        _nominal_fields(**{"lines[0].label": _found("lines[0].label", "Article Inconnu")})
    )
    assert anomalies["UNKNOWN_ITEM"] is Severity.BLOCKING


def test_duplicate_document_triggers_and_unique_does_not() -> None:
    assert "DUPLICATE_DOCUMENT" not in _run(_nominal_fields())
    anomalies = _run(_nominal_fields(), duplicate_of="FA-2026-00001")
    assert anomalies["DUPLICATE_DOCUMENT"] is Severity.BLOCKING


def test_unusual_price_triggers_above_20_percent_and_not_at_exact_20_percent() -> None:
    # 5500 * 1.20 = 6600 -> exactement 20 % : pas d'anomalie
    at_limit = _nominal_fields(
        **{
            "lines[0].unit_price": _found("lines[0].unit_price", "6600"),
            "totals.net": _found("totals.net", "66000"),
        }
    )
    assert "UNUSUAL_PRICE" not in _run(at_limit)

    above_limit = _nominal_fields(
        **{
            "lines[0].unit_price": _found("lines[0].unit_price", "7000"),
            "totals.net": _found("totals.net", "70000"),
        }
    )
    assert _run(above_limit)["UNUSUAL_PRICE"] is Severity.WARNING


def test_amount_mismatch_triggers_and_matching_total_does_not() -> None:
    assert "AMOUNT_MISMATCH" not in _run(_nominal_fields())
    anomalies = _run(_nominal_fields(**{"totals.net": _found("totals.net", "50000")}))
    assert anomalies["AMOUNT_MISMATCH"] is Severity.BLOCKING


def test_quantity_mismatch_triggers_and_matching_delivery_does_not() -> None:
    assert "QUANTITY_MISMATCH" not in _run(_nominal_fields(), delivered_quantities={0: Decimal(10)})
    anomalies = _run(_nominal_fields(), delivered_quantities={0: Decimal(8)})
    assert anomalies["QUANTITY_MISMATCH"] is Severity.BLOCKING
    assert "QUANTITY_MISMATCH" in _run(
        _nominal_fields(), delivered_quantities={0: Decimal(10), 1: Decimal(3)}
    )


def test_document_inconsistency_triggers_on_conflict_and_not_when_coherent() -> None:
    coherent_bl = RelatedDocument(
        kind="bon de livraison",
        customer_name="Entreprise Kpadonou et Fils",
        reference="CMD-2026-001",
        issue_date=date(2026, 11, 21),
    )
    coherent_quote = RelatedDocument(
        kind="devis",
        customer_name="Entreprise Kpadonou et Fils",
        reference="CMD-2026-001",
        issue_date=date(2026, 11, 18),
    )
    assert "DOCUMENT_INCONSISTENCY" not in _run(
        _nominal_fields(), related_documents=(coherent_bl, coherent_quote)
    )

    conflicting_customer = RelatedDocument(kind="devis", customer_name="Autre Client")
    assert (
        _run(_nominal_fields(), related_documents=(conflicting_customer,))["DOCUMENT_INCONSISTENCY"]
        is Severity.BLOCKING
    )

    conflicting_ref = RelatedDocument(kind="bon de livraison", reference="CMD-9999-999")
    assert "DOCUMENT_INCONSISTENCY" in _run(_nominal_fields(), related_documents=(conflicting_ref,))

    earlier_bl = RelatedDocument(kind="bon de livraison", issue_date=date(2026, 11, 18))
    assert "DOCUMENT_INCONSISTENCY" in _run(_nominal_fields(), related_documents=(earlier_bl,))

    later_quote = RelatedDocument(kind="devis", issue_date=date(2026, 11, 25))
    assert "DOCUMENT_INCONSISTENCY" in _run(_nominal_fields(), related_documents=(later_quote,))

    dup_conflicts = (
        RelatedDocument(kind="devis", customer_name="Client A"),
        RelatedDocument(kind="bon de livraison", customer_name="Client B"),
    )
    content = build_draft(_nominal_fields(), REFS, CALC_RULES.default_vat_rate)
    _, totals = compute_invoice(content.lines, content.global_discount_rate, CALC_RULES)
    anomalies = check_draft(
        DraftUnderReview(content, totals, _nominal_fields(), related_documents=dup_conflicts),
        REFS,
        RULES,
    )
    ids = [a.id for a in anomalies]
    assert len(ids) == len(set(ids))


def test_missing_required_field_triggers_and_complete_does_not() -> None:
    assert "MISSING_REQUIRED_FIELD" not in _run(_nominal_fields())
    missing_date = ExtractedField("document.date", FieldStatus.MISSING, None, None, None, None)
    anomalies = _run(_nominal_fields(**{"document.date": missing_date}))
    assert anomalies["MISSING_REQUIRED_FIELD"] is Severity.BLOCKING


def test_low_confidence_triggers_until_human_confirms() -> None:
    uncertain = _found("lines[0].unit_price", "5500", confidence=0.60)
    assert _run(_nominal_fields(**{"lines[0].unit_price": uncertain}))["LOW_CONFIDENCE"] is (
        Severity.BLOCKING
    )

    confirmed = ExtractedField(
        "lines[0].unit_price",
        FieldStatus.FOUND,
        "5500",
        "5500",
        0.60,
        TextAnchor(0, 1),
        review=Review(ReviewState.CONFIRMED, by="op1", at=AT),
    )
    assert "LOW_CONFIDENCE" not in _run(_nominal_fields(**{"lines[0].unit_price": confirmed}))


def test_high_amount_triggers_above_threshold_and_respects_config_severity() -> None:
    assert "HIGH_AMOUNT" not in _run(_nominal_fields())
    big_order = _nominal_fields(
        **{
            "lines[0].quantity": _found("lines[0].quantity", "1000"),
            "totals.net": _found("totals.net", "5500000"),
        }
    )
    assert _run(big_order)["HIGH_AMOUNT"] is Severity.BLOCKING

    custom_rules = ControlRules(
        unusual_price_percent=Decimal(20),
        high_amount_gross=Decimal(5000000),
        review_threshold=0.85,
        severities={"HIGH_AMOUNT": Severity.WARNING},
    )
    assert _run(big_order, rules=custom_rules)["HIGH_AMOUNT"] is Severity.WARNING
