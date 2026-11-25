"""Tests unitaires des référentiels CSV (data/referentiels/) et de referentials_csv.py."""

from pathlib import Path

import pytest

from invoicing.infrastructure.dataset_eval import load_dataset_split
from invoicing.infrastructure.referentials_csv import ReferentialError, load_referentials
from invoicing.settings import REPO_ROOT


def test_real_referentiels_load_cleanly_and_cover_required_constraints() -> None:
    refs = load_referentials(REPO_ROOT / "data" / "referentiels")
    assert 8 <= len(refs.customers) <= 10
    assert 15 <= len(refs.items) <= 20

    channels = {c.preferred_channel for c in refs.customers}
    assert channels == {"whatsapp", "sms", "email"}
    assert any(not c.vat_liable for c in refs.customers)
    assert refs.customer("CLI-001") is not None
    assert refs.find_item("Ciment CPJ 35 (sac de 50 kg)") is not None


def test_real_referentiels_match_all_known_customers_and_items_in_pieces() -> None:
    refs = load_referentials(REPO_ROOT / "data" / "referentiels")
    for split in ("mise-au-point", "test"):
        docs, _ = load_dataset_split(REPO_ROOT / "data" / "pieces" / split)
        for doc in docs:
            name = doc.fields.get("customer.name")
            if name and "UNKNOWN_CUSTOMER" not in doc.expected_anomalies:
                assert refs.find_customer(name, doc.fields.get("customer.tax_id")) is not None, (
                    f"{doc.doc_id} : client {name!r} absent de clients.csv"
                )
            if "UNKNOWN_ITEM" not in doc.expected_anomalies:
                for key, label in doc.fields.items():
                    if key.endswith(".label") and label is not None:
                        assert refs.find_item(label) is not None, (
                            f"{doc.doc_id} : article {label!r} absent de articles.csv"
                        )


def test_missing_column_and_duplicate_id_raise_referential_error(tmp_path: Path) -> None:
    (tmp_path / "clients.csv").write_text("id,raison_sociale\nCLI-001,Test\n", encoding="utf-8")
    with pytest.raises(ReferentialError, match="colonnes manquantes"):
        load_referentials(tmp_path)

    (tmp_path / "clients.csv").write_text(
        "id,raison_sociale,ifu,telephone,email,canal_prefere,delai_paiement_jours,assujetti_tva\n"
        "CLI-001,A,3999900000011,+2290199990001,a@a.example,whatsapp,30,oui\n"
        "CLI-001,B,3999900000022,+2290199990002,b@b.example,sms,15,non\n",
        encoding="utf-8",
    )
    with pytest.raises(ReferentialError, match="identifiant en double"):
        load_referentials(tmp_path)


@pytest.mark.parametrize(
    ("row", "match"),
    [
        ("CLI-001,A,12345,+2290199990001,a@a.example,whatsapp,30,oui", "IFU invalide"),
        ("CLI-001,A,3999900000011,99990001,a@a.example,whatsapp,30,oui", "téléphone invalide"),
        ("CLI-001,A,3999900000011,+2290199990001,a@gmail.com,whatsapp,30,oui", "email invalide"),
        ("CLI-001,A,3999900000011,+2290199990001,a@a.example,pigeon,30,oui", "canal_prefere"),
        ("CLI-001,A,3999900000011,+2290199990001,a@a.example,whatsapp,-5,oui", "entier positif"),
        ("CLI-001,A,3999900000011,+2290199990001,a@a.example,whatsapp,30,peut-etre", "oui"),
    ],
)
def test_invalid_customer_row_raises_referential_error(
    tmp_path: Path, row: str, match: str
) -> None:
    (tmp_path / "clients.csv").write_text(
        "id,raison_sociale,ifu,telephone,email,canal_prefere,delai_paiement_jours,assujetti_tva\n"
        f"{row}\n",
        encoding="utf-8",
    )
    with pytest.raises(ReferentialError, match=match):
        load_referentials(tmp_path)


def test_invalid_item_row_raises_referential_error(tmp_path: Path) -> None:
    (tmp_path / "articles.csv").write_text(
        "id,designation,unite,prix_unitaire_ht,taux_tva\nART-001,Ciment,sac,-100,18\n",
        encoding="utf-8",
    )
    with pytest.raises(ReferentialError, match="prix_unitaire_ht"):
        load_referentials(tmp_path)
