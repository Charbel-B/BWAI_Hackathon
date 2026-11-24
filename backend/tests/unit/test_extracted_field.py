from datetime import UTC, datetime

import pytest

from invoicing.domain.errors import InvariantViolationError
from invoicing.domain.extraction import (
    ExtractedField,
    FieldStatus,
    RegionAnchor,
    Review,
    ReviewState,
    TextAnchor,
)

AT = datetime(2026, 11, 24, tzinfo=UTC)


def found(**changes: object) -> ExtractedField:
    values: dict[str, object] = {
        "name": "lines[0].quantity",
        "status": FieldStatus.FOUND,
        "value": "20",
        "raw_text": "20 sacs",
        "confidence": 0.9,
        "anchor": TextAnchor(start=41, end=48),
    }
    values.update(changes)
    return ExtractedField(**values)  # type: ignore[arg-type]


def test_missing_field_cannot_carry_an_invented_value() -> None:
    with pytest.raises(InvariantViolationError):
        ExtractedField("customer.name", FieldStatus.MISSING, "Akpro", None, None, None)


def test_missing_field_is_accepted_when_empty() -> None:
    field = ExtractedField("customer.name", FieldStatus.MISSING, None, None, None, None)
    assert field.effective_value is None


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_confidence_outside_unit_interval_is_rejected(confidence: float) -> None:
    with pytest.raises(InvariantViolationError):
        found(confidence=confidence)


def test_human_correction_replaces_extracted_value() -> None:
    review = Review(ReviewState.CORRECTED, value="25", by="operateur", at=AT)
    assert found(review=review).effective_value == "25"


def test_confirmation_keeps_extracted_value() -> None:
    review = Review(ReviewState.CONFIRMED, by="operateur", at=AT)
    assert found(review=review).effective_value == "20"


def test_correction_without_value_is_rejected() -> None:
    with pytest.raises(InvariantViolationError):
        Review(ReviewState.CORRECTED, value=None, by="operateur", at=AT)


def test_human_decision_without_author_is_rejected() -> None:
    with pytest.raises(InvariantViolationError):
        Review(ReviewState.CONFIRMED)


@pytest.mark.parametrize(("start", "end"), [(-1, 2), (5, 4)])
def test_invalid_text_anchor_is_rejected(start: int, end: int) -> None:
    with pytest.raises(InvariantViolationError):
        TextAnchor(start=start, end=end)


@pytest.mark.parametrize(
    ("page", "box"),
    [(0, (0.1, 0.1, 0.2, 0.2)), (1, (0.5, 0.1, 0.2, 0.2)), (1, (0.1, 0.1, 1.2, 0.2))],
)
def test_invalid_region_anchor_is_rejected(
    page: int, box: tuple[float, float, float, float]
) -> None:
    with pytest.raises(InvariantViolationError):
        RegionAnchor(page=page, box=box)


def test_valid_region_anchor_is_accepted() -> None:
    assert RegionAnchor(page=1, box=(0.1, 0.2, 0.3, 0.4)).page == 1
