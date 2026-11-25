"""Chargement et validation des référentiels CSV de data/referentiels/ (formats-de-donnees.md)."""

import csv
import re
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

_VALID_CHANNELS = frozenset({"whatsapp", "sms", "email"})
_RE_IFU = re.compile(r"^\d{13}$")
_RE_PHONE = re.compile(r"^\+22901\d{8}$")
_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.example$")


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


def _validate_customer_row(row: dict[str, str]) -> Customer:
    cid = row["id"]
    if not cid or not row["raison_sociale"]:
        raise ReferentialError(f"{cid or '?'} : id et raison_sociale requis")
    ifu = row["ifu"] or None
    if ifu is not None and not _RE_IFU.match(ifu):
        raise ReferentialError(f"{cid} : IFU invalide « {ifu} » (13 chiffres attendus)")
    phone = row["telephone"] or None
    if phone is not None and not _RE_PHONE.match(re.sub(r"\s+", "", phone)):
        raise ReferentialError(f"{cid} : téléphone invalide « {phone} » (+22901XXXXXXXX attendu)")
    email = row["email"] or None
    if email is not None and not _RE_EMAIL.match(email):
        raise ReferentialError(f"{cid} : email invalide « {email} » (domaine .example requis)")
    channel = row["canal_prefere"].lower()
    if channel not in _VALID_CHANNELS:
        raise ReferentialError(f"{cid} : canal_prefere invalide « {channel} »")
    terms = _decimal(row["delai_paiement_jours"], cid)
    if terms < 0 or terms != terms.to_integral_value():
        raise ReferentialError(f"{cid} : delai_paiement_jours doit être un entier positif")
    vat_flag = row["assujetti_tva"].lower()
    if vat_flag not in {"oui", "non"}:
        raise ReferentialError(f"{cid} : assujetti_tva doit valoir 'oui' ou 'non'")
    return Customer(
        id=cid,
        legal_name=row["raison_sociale"],
        tax_id=ifu,
        phone=phone,
        email=email,
        preferred_channel=channel,
        payment_terms_days=int(terms),
        vat_liable=vat_flag == "oui",
    )


def _validate_item_row(row: dict[str, str]) -> Item:
    item_id = row["id"]
    if not item_id or not row["designation"]:
        raise ReferentialError(f"{item_id or '?'} : id et designation requis")
    price = _decimal(row["prix_unitaire_ht"], item_id)
    if price < 0 or price != price.to_integral_value():
        raise ReferentialError(f"{item_id} : prix_unitaire_ht doit être un entier FCFA positif")
    vat_rate = _decimal(row["taux_tva"], item_id)
    if not (Decimal(0) <= vat_rate <= Decimal(100)):
        raise ReferentialError(f"{item_id} : taux_tva hors [0, 100]")
    return Item(
        id=item_id,
        label=row["designation"],
        unit=row["unite"] or None,
        unit_price_net=price,
        vat_rate=vat_rate,
    )


def load_referentials(directory: Path) -> Referentials:
    """Lit et valide clients.csv et articles.csv ; un fichier absent donne un référentiel vide."""
    customers = tuple(
        _validate_customer_row(r) for r in _rows(directory / "clients.csv", CUSTOMER_COLUMNS)
    )
    items = tuple(_validate_item_row(r) for r in _rows(directory / "articles.csv", ITEM_COLUMNS))
    return Referentials(customers, items)
