"""Lecture et validation des référentiels CSV (``clients.csv`` et ``articles.csv``)."""

import csv
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from invoicing.domain.catalog import Catalog, Channel, Customer, Item

_CUSTOMER_COLUMNS = (
    "id",
    "raison_sociale",
    "ifu",
    "telephone",
    "email",
    "canal_prefere",
    "delai_paiement_jours",
    "assujetti_tva",
)
_ITEM_COLUMNS = ("id", "designation", "unite", "prix_unitaire_ht", "taux_tva")

_RE_CUSTOMER_ID = re.compile(r"^CLI-\d{3}$")
_RE_ITEM_ID = re.compile(r"^ART-\d{3}$")
_RE_IFU = re.compile(r"^\d{13}$")
_RE_PHONE = re.compile(r"^\+22901\d{8}$")
_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.example$")


class CatalogLoadError(ValueError):
    """Erreur de format, de colonne manquante ou d'identifiant dupliqué dans un CSV."""


def load_customers(path: Path) -> tuple[Customer, ...]:
    """Charge et valide ``clients.csv``."""
    rows = _read_csv_rows(path, _CUSTOMER_COLUMNS)
    customers: list[Customer] = []
    seen_ids: set[str] = set()
    for line_no, row in enumerate(rows, start=2):
        customer = _parse_customer_row(row, line_no)
        if customer.id in seen_ids:
            msg = f"{path.name} ligne {line_no} : identifiant client en double ({customer.id})"
            raise CatalogLoadError(msg)
        seen_ids.add(customer.id)
        customers.append(customer)
    return tuple(customers)


def load_items(path: Path) -> tuple[Item, ...]:
    """Charge et valide ``articles.csv``."""
    rows = _read_csv_rows(path, _ITEM_COLUMNS)
    items: list[Item] = []
    seen_ids: set[str] = set()
    for line_no, row in enumerate(rows, start=2):
        item = _parse_item_row(row, line_no)
        if item.id in seen_ids:
            msg = f"{path.name} ligne {line_no} : identifiant article en double ({item.id})"
            raise CatalogLoadError(msg)
        seen_ids.add(item.id)
        items.append(item)
    return tuple(items)


def load_catalog(referentiels_dir: Path) -> Catalog:
    """Charge et valide l'ensemble des référentiels depuis ``data/referentiels/``."""
    return Catalog(
        customers=load_customers(referentiels_dir / "clients.csv"),
        items=load_items(referentiels_dir / "articles.csv"),
    )


def _read_csv_rows(path: Path, required_columns: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.is_file():
        msg = f"fichier référentiel introuvable : {path}"
        raise CatalogLoadError(msg)
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        missing = [col for col in required_columns if col not in fieldnames]
        if missing:
            msg = f"{path.name} : colonne(s) manquante(s) : {', '.join(missing)}"
            raise CatalogLoadError(msg)
        return list(reader)


def _parse_customer_row(row: dict[str, str], line_no: int) -> Customer:
    cid = row["id"].strip()
    if not _RE_CUSTOMER_ID.match(cid):
        msg = f"clients.csv ligne {line_no} : id invalide ({cid!r}), attendu CLI-NNN"
        raise CatalogLoadError(msg)
    ifu = row["ifu"].strip()
    if not _RE_IFU.match(ifu):
        msg = f"clients.csv ligne {line_no} : IFU invalide ({ifu!r}), attendu 13 chiffres"
        raise CatalogLoadError(msg)
    phone = row["telephone"].strip()
    if not _RE_PHONE.match(phone):
        msg = (
            f"clients.csv ligne {line_no} : téléphone invalide ({phone!r}), attendu +22901XXXXXXXX"
        )
        raise CatalogLoadError(msg)
    email = row["email"].strip()
    if not _RE_EMAIL.match(email):
        msg = f"clients.csv ligne {line_no} : email invalide ({email!r}), domaine .example requis"
        raise CatalogLoadError(msg)
    return Customer(
        id=cid,
        legal_name=_require_non_empty(row["raison_sociale"], "raison_sociale", line_no),
        tax_id=ifu,
        phone=phone,
        email=email,
        preferred_channel=_parse_channel(row["canal_prefere"], line_no),
        payment_terms_days=_parse_non_negative_int(
            row["delai_paiement_jours"], "delai_paiement_jours", line_no
        ),
        vat_liable=_parse_yes_no(row["assujetti_tva"], line_no),
    )


def _parse_item_row(row: dict[str, str], line_no: int) -> Item:
    item_id = row["id"].strip()
    if not _RE_ITEM_ID.match(item_id):
        msg = f"articles.csv ligne {line_no} : id invalide ({item_id!r}), attendu ART-NNN"
        raise CatalogLoadError(msg)
    price = _parse_non_negative_int(row["prix_unitaire_ht"], "prix_unitaire_ht", line_no)
    vat_rate = _parse_decimal(row["taux_tva"], "taux_tva", line_no)
    if not (Decimal(0) <= vat_rate <= Decimal(100)):
        msg = f"articles.csv ligne {line_no} : taux_tva hors [0, 100] ({vat_rate})"
        raise CatalogLoadError(msg)
    return Item(
        id=item_id,
        label=_require_non_empty(row["designation"], "designation", line_no),
        unit=_require_non_empty(row["unite"], "unite", line_no),
        unit_price_net=Decimal(price),
        vat_rate=vat_rate,
    )


def _require_non_empty(raw: str, col: str, line_no: int) -> str:
    value = raw.strip()
    if not value:
        msg = f"ligne {line_no} : valeur vide pour {col}"
        raise CatalogLoadError(msg)
    return value


def _parse_channel(raw: str, line_no: int) -> Channel:
    try:
        return Channel(raw.strip().lower())
    except ValueError as err:
        msg = f"clients.csv ligne {line_no} : canal_prefere invalide ({raw!r})"
        raise CatalogLoadError(msg) from err


def _parse_non_negative_int(raw: str, col: str, line_no: int) -> int:
    try:
        value = int(raw.strip())
    except ValueError as err:
        msg = f"ligne {line_no} : entier attendu pour {col} ({raw!r})"
        raise CatalogLoadError(msg) from err
    if value < 0:
        msg = f"ligne {line_no} : entier positif attendu pour {col} ({value})"
        raise CatalogLoadError(msg)
    return value


def _parse_decimal(raw: str, col: str, line_no: int) -> Decimal:
    try:
        return Decimal(raw.strip())
    except InvalidOperation as err:
        msg = f"ligne {line_no} : décimal attendu pour {col} ({raw!r})"
        raise CatalogLoadError(msg) from err


def _parse_yes_no(raw: str, line_no: int) -> bool:
    val = raw.strip().lower()
    if val == "oui":
        return True
    if val == "non":
        return False
    msg = f"clients.csv ligne {line_no} : assujetti_tva doit valoir 'oui' ou 'non' ({raw!r})"
    raise CatalogLoadError(msg)
