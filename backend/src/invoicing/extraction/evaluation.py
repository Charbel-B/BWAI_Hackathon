"""Évaluation chiffrée d'un extracteur et calibrage du seuil de revue humaine.

Conformément à la doctrine métier, la sécurité prime : on cherche d'abord à
minimiser les fausses certitudes (faux positifs avec ``confidence >= seuil``),
puis à maximiser la couverture d'automatisation (score F0.5, où la précision
pèse deux fois plus que le rappel).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from invoicing.domain.extraction import ExtractedField, FieldStatus

DEFAULT_THRESHOLDS: tuple[float, ...] = (0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95)


@dataclass(frozen=True, slots=True)
class ExpectedDocument:
    """Vérité terrain d'une pièce source issue d'un fichier ``<id>.attendu.json``."""

    doc_id: str
    fields: Mapping[str, str | None]
    expected_anomalies: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    """Mesures d'exactitude, de sécurité et d'automatisation pour un seuil donné."""

    review_threshold: float
    total_documents: int
    valid_outputs: int
    total_present_fields: int
    exact_matches: int
    total_missing_fields: int
    true_missing_matches: int
    high_confidence_correct: int
    high_confidence_errors: int

    @property
    def field_accuracy(self) -> float:
        """Part des champs attendus non nuls extraits avec la valeur exacte."""
        if self.total_present_fields == 0:
            return 1.0
        return round(self.exact_matches / self.total_present_fields, 4)

    @property
    def true_missing_rate(self) -> float:
        """Part des champs absents (null) correctement laissés en MISSING sans invention."""
        if self.total_missing_fields == 0:
            return 1.0
        return round(self.true_missing_matches / self.total_missing_fields, 4)

    @property
    def false_certainty_rate(self) -> float:
        """Part des champs présents où l'extracteur se trompe avec confidence >= seuil."""
        if self.total_present_fields == 0:
            return 0.0
        return round(self.high_confidence_errors / self.total_present_fields, 4)

    @property
    def precision_above_threshold(self) -> float:
        """Précision parmi les champs qui franchissent le seuil sans revue humaine."""
        total_high = self.high_confidence_correct + self.high_confidence_errors
        if total_high == 0:
            return 1.0
        return round(self.high_confidence_correct / total_high, 4)

    @property
    def automation_coverage(self) -> float:
        """Rappel sous seuil : part des champs présents extraits juste et >= seuil."""
        if self.total_present_fields == 0:
            return 0.0
        return round(self.high_confidence_correct / self.total_present_fields, 4)

    @property
    def f05_score(self) -> float:
        """Score F0.5 pondérant la précision 2 fois plus que le rappel sous seuil."""
        p = self.precision_above_threshold
        r = self.automation_coverage
        if p + r == 0:
            return 0.0
        beta_sq = 0.25
        return round((1 + beta_sq) * (p * r) / (beta_sq * p + r), 4)


def evaluate_predictions(
    expected_docs: Sequence[ExpectedDocument],
    predictions: Mapping[str, Sequence[ExtractedField]],
    review_threshold: float = 0.85,
) -> EvaluationMetrics:
    """Compare les champs extraits aux valeurs attendues pour un seuil de revue donné."""
    valid_outputs = 0
    present_count = 0
    exact_matches = 0
    missing_count = 0
    true_missing = 0
    high_conf_ok = 0
    high_conf_err = 0

    for doc in expected_docs:
        doc_fields = predictions.get(doc.doc_id)
        if doc_fields is not None:
            valid_outputs += 1
        by_name = {f.name: f for f in (doc_fields or ())}
        for name, expected_val in doc.fields.items():
            pred = by_name.get(name)
            if expected_val is None:
                missing_count += 1
                if pred is None or pred.value is None:
                    true_missing += 1
                elif pred.confidence is not None and pred.confidence >= review_threshold:
                    high_conf_err += 1
            else:
                present_count += 1
                is_exact = (
                    pred is not None
                    and pred.status is FieldStatus.FOUND
                    and pred.value == expected_val
                )
                is_high = (
                    pred is not None
                    and pred.confidence is not None
                    and pred.confidence >= review_threshold
                )
                if is_exact:
                    exact_matches += 1
                    if is_high:
                        high_conf_ok += 1
                elif is_high:
                    high_conf_err += 1

    return EvaluationMetrics(
        review_threshold=review_threshold,
        total_documents=len(expected_docs),
        valid_outputs=valid_outputs,
        total_present_fields=present_count,
        exact_matches=exact_matches,
        total_missing_fields=missing_count,
        true_missing_matches=true_missing,
        high_confidence_correct=high_conf_ok,
        high_confidence_errors=high_conf_err,
    )


def calibrate_thresholds(
    expected_docs: Sequence[ExpectedDocument],
    predictions: Mapping[str, Sequence[ExtractedField]],
    thresholds: Sequence[float] = DEFAULT_THRESHOLDS,
) -> list[EvaluationMetrics]:
    """Calcule les métriques pour une grille de seuils afin de choisir le seuil optimal."""
    return [evaluate_predictions(expected_docs, predictions, t) for t in thresholds]


def format_calibration_markdown(calibration: Sequence[EvaluationMetrics]) -> str:
    """Formate le tableau Markdown de calibrage du seuil pour la fiche IA."""
    header = (
        "| Seuil | Précision >= seuil | Fausses certitudes "
        "| Couverture auto (Rappel) | Score F0.5 |"
    )
    lines = [
        header,
        "| --- | --- | --- | --- | --- |",
    ]
    for m in calibration:
        lines.append(
            f"| {m.review_threshold:.2f} "
            f"| {m.precision_above_threshold * 100:.1f} % "
            f"| {m.false_certainty_rate * 100:.1f} % ({m.high_confidence_errors}) "
            f"| {m.automation_coverage * 100:.1f} % "
            f"| {m.f05_score:.3f} |"
        )
    return "\n".join(lines)
