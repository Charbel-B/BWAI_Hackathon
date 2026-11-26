"""Chargement des pièces sources (``data/pieces/``) et exécution de l'évaluation IA.

Ce module lit les paires ``<id>.txt`` et ``<id>.attendu.json``, exécute un
extracteur conforme au port ``Extractor``, et génère le rapport Markdown
prêt à être inséré dans la fiche IA.
"""

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from invoicing.application.ports import Extractor
from invoicing.domain.extraction import ExtractedField
from invoicing.extraction.confidence import CatalogHint
from invoicing.extraction.evaluation import (
    EvaluationMetrics,
    ExpectedDocument,
    calibrate_thresholds,
    evaluate_predictions,
    format_calibration_markdown,
)
from invoicing.extraction.rules_extractor import RuleBasedExtractor
from invoicing.infrastructure.extraction_config import load_extraction_config
from invoicing.settings import REPO_ROOT


class _ExpectedJsonModel(BaseModel):
    """Schéma Pydantic d'un fichier ``<id>.attendu.json``."""

    model_config = ConfigDict(extra="forbid")

    fields: dict[str, str | None]
    expected_anomalies: list[str] = []


def load_catalog_hint(referentiels_dir: Path) -> CatalogHint:
    """Charge les noms de clients, IFU et désignations depuis les CSV s'ils existent."""
    customers: list[str] = []
    tax_ids: list[str] = []
    items: list[str] = []

    clients_csv = referentiels_dir / "clients.csv"
    if clients_csv.is_file():
        with clients_csv.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("raison_sociale"):
                    customers.append(row["raison_sociale"].strip())
                if row.get("ifu"):
                    tax_ids.append(row["ifu"].strip())

    articles_csv = referentiels_dir / "articles.csv"
    item_prices: list[tuple[str, str]] = []
    if articles_csv.is_file():
        with articles_csv.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                designation = (row.get("designation") or "").strip()
                price = (row.get("prix_unitaire_ht") or "").strip()
                if designation:
                    items.append(designation)
                    if price:
                        item_prices.append((designation, price))

    return CatalogHint(
        customer_names=tuple(customers),
        tax_ids=tuple(tax_ids),
        item_labels=tuple(items),
        item_prices=tuple(item_prices),
    )


def load_dataset_split(split_dir: Path) -> tuple[list[ExpectedDocument], dict[str, bytes]]:
    """Charge toutes les paires ``<id>.txt`` et ``<id>.attendu.json`` d'un dossier."""
    expected_docs: list[ExpectedDocument] = []
    contents: dict[str, bytes] = {}

    for expected_path in sorted(split_dir.glob("*.attendu.json")):
        doc_id = expected_path.name.removesuffix(".attendu.json")
        source_path = split_dir / f"{doc_id}.txt"
        if not source_path.is_file():
            continue
        parsed = _ExpectedJsonModel.model_validate_json(expected_path.read_text(encoding="utf-8"))
        expected_docs.append(
            ExpectedDocument(
                doc_id=doc_id,
                fields=parsed.fields,
                expected_anomalies=tuple(parsed.expected_anomalies),
            )
        )
        contents[doc_id] = source_path.read_bytes()

    return expected_docs, contents


def run_extractor_on_split(
    extractor: Extractor,
    split_dir: Path,
    review_threshold: float = 0.85,
) -> tuple[EvaluationMetrics, list[EvaluationMetrics]]:
    """Exécute ``extractor`` sur un jeu de pièces et calcule les métriques et la grille."""
    expected_docs, contents = load_dataset_split(split_dir)
    predictions: dict[str, Sequence[ExtractedField]] = {
        doc_id: extractor.extract(raw_bytes, "text/plain") for doc_id, raw_bytes in contents.items()
    }
    summary = evaluate_predictions(expected_docs, predictions, review_threshold)
    calibration = calibrate_thresholds(expected_docs, predictions)
    return summary, calibration


def build_markdown_report(
    extractor_name: str,
    split_name: str,
    metrics: EvaluationMetrics,
    calibration: Sequence[EvaluationMetrics],
) -> str:
    """Produit une section Markdown complète résumant l'évaluation sur un jeu."""
    title = (
        f"### Extracteur `{extractor_name}` — Jeu `{split_name}` ({metrics.total_documents} pièces)"
    )
    lines = [
        title,
        "",
        "| Métrique | Valeur |",
        "| --- | --- |",
        f"| Sorties valides | {metrics.valid_outputs} / {metrics.total_documents} |",
        f"| Exactitude par champ (Accuracy) | {metrics.field_accuracy * 100:.1f} % "
        f"({metrics.exact_matches}/{metrics.total_present_fields}) |",
        f"| Champs vides à raison (True Missing) | {metrics.true_missing_rate * 100:.1f} % "
        f"({metrics.true_missing_matches}/{metrics.total_missing_fields}) |",
        f"| Précision >= seuil ({metrics.review_threshold:.2f}) | "
        f"{metrics.precision_above_threshold * 100:.1f} % |",
        f"| Taux de fausses certitudes | {metrics.false_certainty_rate * 100:.1f} % "
        f"({metrics.high_confidence_errors}) |",
        f"| Couverture d'automatisation (Rappel) | {metrics.automation_coverage * 100:.1f} % |",
        f"| Score F0.5 | {metrics.f05_score:.3f} |",
        "",
        format_calibration_markdown(calibration),
        "",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> None:
    """Point d'entrée CLI : évalue par défaut uniquement ``mise-au-point``."""
    parser = argparse.ArgumentParser(description="Évaluation chiffrée de l'extracteur.")
    parser.add_argument(
        "--split",
        choices=("mise-au-point", "test", "controle", "all"),
        default="mise-au-point",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    data_dir = REPO_ROOT / "data"
    cfg, policy = load_extraction_config(REPO_ROOT / "config")
    catalog = load_catalog_hint(data_dir / "referentiels")
    extractor = RuleBasedExtractor(catalog=catalog, policy=policy)

    splits = ("mise-au-point", "test", "controle") if args.split == "all" else (args.split,)
    for split in splits:
        split_dir = data_dir / "pieces" / split
        metrics, calibration = run_extractor_on_split(
            extractor, split_dir, review_threshold=cfg.seuil_confiance_revue
        )
        report = build_markdown_report(extractor.name, split, metrics, calibration)
        sys.stdout.write(report + "\n")


if __name__ == "__main__":
    main()
