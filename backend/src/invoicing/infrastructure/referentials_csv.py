"""Chargement des référentiels CSV de data/referentiels/ (format : formats-de-donnees.md)."""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from invoicing.domain.referentials import Customer, Item, Referentials

CUSTOMER_COLUMNS = (
    "id",
    "raison_sociale",
    "ifu",
    "telephone",
    "email",
    "canal_prefere",
    "delai_paiement_jours",
    "assujetti_tva",
)
ITEM_COLUMNS = ("id", "designation", "unite", "prix_unitaire_ht", "taux_tva")


class ReferentialError(ValueError):
    """Fichier de référentiel mal formé : l'application refuse de démarrer avec."""


def _rows(path: Path, columns: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = set(columns) - set(reader.fieldnames or ())
        if missing:
            raise ReferentialError(f"{path.name} : colonnes manquantes {sorted(missing)}")
        rows = [{k: (v or "").strip() for k, v in row.items()} for row in reader]
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ReferentialError(f"{path.name} : identifiant en double")
    return rows


def _decimal(value: str, where: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise ReferentialError(f"{where} : nombre illisible « {value} »") from error


def load_referentials(directory: Path) -> Referentials:
    """Lit clients.csv et articles.csv ; un fichier absent donne un référentiel vide."""
    customers = tuple(
        Customer(
            id=r["id"],
            legal_name=r["raison_sociale"],
            tax_id=r["ifu"] or None,
            phone=r["telephone"] or None,
            email=r["email"] or None,
            preferred_channel=r["canal_prefere"],
            payment_terms_days=int(_decimal(r["delai_paiement_jours"], r["id"])),
            vat_liable=r["assujetti_tva"].lower() == "oui",
        )
        for r in _rows(directory / "clients.csv", CUSTOMER_COLUMNS)
    )
    items = tuple(
        Item(
            id=r["id"],
            label=r["designation"],
            unit=r["unite"] or None,
            unit_price_net=_decimal(r["prix_unitaire_ht"], r["id"]),
            vat_rate=_decimal(r["taux_tva"], r["id"]),
        )
        for r in _rows(directory / "articles.csv", ITEM_COLUMNS)
    )
    return Referentials(customers, items)
