"""Pipeline d'extraction : normalisation, ancrage, confiance, règles et évaluation."""

from invoicing.extraction.anchoring import find_text_anchor, is_value_grounded_in_raw_text
from invoicing.extraction.confidence import (
    CatalogHint,
    RawFieldCandidate,
    verify_and_build_field,
)
from invoicing.extraction.evaluation import (
    EvaluationMetrics,
    ExpectedDocument,
    calibrate_thresholds,
    evaluate_predictions,
    format_calibration_markdown,
)
from invoicing.extraction.normalization import (
    normalize_date,
    normalize_decimal,
    normalize_field_value,
    normalize_int,
    normalize_rate,
    normalize_tax_id,
    normalize_text,
)
from invoicing.extraction.rules_extractor import RuleBasedExtractor

__all__ = [
    "CatalogHint",
    "EvaluationMetrics",
    "ExpectedDocument",
    "RawFieldCandidate",
    "RuleBasedExtractor",
    "calibrate_thresholds",
    "evaluate_predictions",
    "find_text_anchor",
    "format_calibration_markdown",
    "is_value_grounded_in_raw_text",
    "normalize_date",
    "normalize_decimal",
    "normalize_field_value",
    "normalize_int",
    "normalize_rate",
    "normalize_tax_id",
    "normalize_text",
    "verify_and_build_field",
]
