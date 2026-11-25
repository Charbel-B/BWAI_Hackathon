"""Tests unitaires des référentiels CSV (clients.csv, articles.csv) et de leur lecteur."""

from pathlib import Path

import pytest

from invoicing.domain.catalog import Channel
from invoicing.infrastructure.catalog_reader import (
    CatalogLoadError,
    load_catalog,
    load_customers,
    load_items,
)
from invoicing.infrastructure.dataset_eval import load_dataset_split
from invoicing.settings import REPO_ROOT


def test_real_referentiels_load_cleanly_and_cover_all_required_constraints() -> None:
    catalog = load_catalog(REPO_ROOT / "data" / "referentiels")
    assert 8 <= len(catalog.customers) <= 10
    assert 15 <= len(catalog.items) <= 20

    channels = {c.preferred_channel for c in catalog.customers}
    assert channels == {Channel.WHATSAPP, Channel.SMS, Channel.EMAIL}
    assert any(not c.vat_liable for c in catalog.customers)
    assert catalog.find_customer_by_id("CLI-001") is not None
    assert catalog.find_item_by_id("ART-001") is not None


def test_real_referentiels_match_all_known_customers_and_items_in_pieces() -> None:
    catalog = load_catalog(REPO_ROOT / "data" / "referentiels")
    for split in ("mise-au-point", "test"):
        docs, _ = load_dataset_split(REPO_ROOT / "data" / "pieces" / split)
        for doc in docs:
            customer_name = doc.fields.get("customer.name")
            if customer_name and "UNKNOWN_CUSTOMER" not in doc.expected_anomalies:
                assert catalog.find_customer_by_name(customer_name) is not None, (
                    f"{doc.doc_id} : client {customer_name!r} absent de clients.csv"
                )
            if "UNKNOWN_ITEM" not in doc.expected_anomalies:
                for key, label in doc.fields.items():
                    if key.endswith(".label") and label is not None:
                        assert catalog.find_item_by_label(label) is not None, (
                            f"{doc.doc_id} : article {label!r} absent de articles.csv"
                        )


def test_missing_column_raises_clear_error(tmp_path: Path) -> None:
    bad_clients = tmp_path / "clients.csv"
    bad_clients.write_text("id,raison_sociale\nCLI-001,Test\n", encoding="utf-8")
    with pytest.raises(CatalogLoadError, match="colonne\\(s\\) manquante\\(s\\)"):
        load_customers(bad_clients)


def test_duplicate_ids_raise_clear_error(tmp_path: Path) -> None:
    dup_clients = tmp_path / "clients.csv"
    dup_clients.write_text(
        "id,raison_sociale,ifu,telephone,email,canal_prefere,delai_paiement_jours,assujetti_tva\n"
        "CLI-001,A,3999900000011,+2290199990001,a@a.example,whatsapp,30,oui\n"
        "CLI-001,B,3999900000022,+2290199990002,b@b.example,sms,15,non\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogLoadError, match="en double"):
        load_customers(dup_clients)

    dup_items = tmp_path / "articles.csv"
    dup_items.write_text(
        "id,designation,unite,prix_unitaire_ht,taux_tva\n"
        "ART-001,Ciment,sac,5500,18\n"
        "ART-001,Sable,m3,14000,18\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogLoadError, match="en double"):
        load_items(dup_items)


@pytest.mark.parametrize(
    ("row", "match"),
    [
        ("BAD-001,A,3999900000011,+2290199990001,a@a.example,whatsapp,30,oui", "id invalide"),
        ("CLI-001,A,12345,+2290199990001,a@a.example,whatsapp,30,oui", "IFU invalide"),
        ("CLI-001,A,3999900000011,99990001,a@a.example,whatsapp,30,oui", "téléphone invalide"),
        ("CLI-001,A,3999900000011,+2290199990001,a@gmail.com,whatsapp,30,oui", "email invalide"),
        ("CLI-001,A,3999900000011,+2290199990001,a@a.example,pigeon,30,oui", "canal_prefere"),
        ("CLI-001,A,3999900000011,+2290199990001,a@a.example,whatsapp,30,peut-etre", "oui"),
    ],
)
def test_invalid_customer_fields_are_rejected(tmp_path: Path, row: str, match: str) -> None:
    path = tmp_path / "clients.csv"
    path.write_text(
        "id,raison_sociale,ifu,telephone,email,canal_prefere,delai_paiement_jours,assujetti_tva\n"
        f"{row}\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogLoadError, match=match):
        load_customers(path)


def test_invalid_item_and_missing_file_are_rejected(tmp_path: Path) -> None:
    with pytest.raises(CatalogLoadError, match="introuvable"):
        load_items(tmp_path / "inexistant.csv")

    bad_item = tmp_path / "articles.csv"
    bad_item.write_text(
        "id,designation,unite,prix_unitaire_ht,taux_tva\nART-001,Ciment,sac,-100,18\n",
        encoding="utf-8",
    )
    with pytest.raises(CatalogLoadError, match="entier positif"):
        load_items(bad_item)
