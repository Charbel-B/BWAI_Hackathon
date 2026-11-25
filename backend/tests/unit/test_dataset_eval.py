"""Tests unitaires du chargeur de jeu de données et du rapport d'évaluation."""

from pathlib import Path

from invoicing.extraction.rules_extractor import RuleBasedExtractor
from invoicing.infrastructure.dataset_eval import (
    build_markdown_report,
    load_catalog_hint,
    load_dataset_split,
    run_extractor_on_split,
)
from invoicing.settings import REPO_ROOT


def test_load_catalog_hint_reads_csv_files(tmp_path: Path) -> None:
    clients_csv = tmp_path / "clients.csv"
    clients_csv.write_text(
        "id,raison_sociale,ifu,telephone,email,canal_prefere,delai_paiement_jours,assujetti_tva\n"
        "CLI-001,Entreprise Kpadonou et Fils,3999900000011,+22901,a@b.test,whatsapp,30,oui\n",
        encoding="utf-8",
    )
    articles_csv = tmp_path / "articles.csv"
    articles_csv.write_text(
        "id,designation,unite,prix_unitaire_ht,taux_tva\n"
        "ART-001,Ciment CPJ 35 (sac de 50 kg),sac,5500,18\n",
        encoding="utf-8",
    )
    catalog = load_catalog_hint(tmp_path)
    assert catalog.customer_names == ("Entreprise Kpadonou et Fils",)
    assert catalog.tax_ids == ("3999900000011",)
    assert catalog.item_labels == ("Ciment CPJ 35 (sac de 50 kg)",)


def test_run_extractor_on_real_splits_produces_high_accuracy_and_zero_false_certainties() -> None:
    dev_dir = REPO_ROOT / "data" / "pieces" / "mise-au-point"
    test_dir = REPO_ROOT / "data" / "pieces" / "test"

    dev_docs, dev_contents = load_dataset_split(dev_dir)
    assert len(dev_docs) == 10
    assert len(dev_contents) == 10

    test_docs, test_contents = load_dataset_split(test_dir)
    assert len(test_docs) == 6
    assert len(test_contents) == 6

    extractor = RuleBasedExtractor()
    dev_metrics, dev_cal = run_extractor_on_split(extractor, dev_dir, review_threshold=0.85)
    assert dev_metrics.total_documents == 10
    assert dev_metrics.field_accuracy >= 0.85
    assert dev_metrics.true_missing_rate == 1.0
    assert dev_metrics.high_confidence_errors == 0

    report = build_markdown_report(extractor.name, "mise-au-point", dev_metrics, dev_cal)
    assert "local-rules-v1" in report
    assert "Taux de fausses certitudes" in report
