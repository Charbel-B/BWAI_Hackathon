"""Entités immuables des référentiels clients et articles (cœur métier pur)."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from invoicing.domain.errors import InvariantViolationError


class Channel(StrEnum):
    """Canaux d'émission simulés."""

    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"


@dataclass(frozen=True, slots=True)
class Customer:
    """Client issu du référentiel ``clients.csv``."""

    id: str
    legal_name: str
    tax_id: str
    phone: str
    email: str
    preferred_channel: Channel
    payment_terms_days: int
    vat_liable: bool

    def __post_init__(self) -> None:
        if not self.id or not self.legal_name:
            raise InvariantViolationError("un client a un identifiant et une raison sociale")
        if self.payment_terms_days < 0:
            raise InvariantViolationError("le délai de paiement est positif ou nul")


@dataclass(frozen=True, slots=True)
class Item:
    """Article issu du référentiel ``articles.csv``."""

    id: str
    label: str
    unit: str
    unit_price_net: Decimal
    vat_rate: Decimal

    def __post_init__(self) -> None:
        if not self.id or not self.label or not self.unit:
            raise InvariantViolationError("un article a un identifiant, un libellé et une unité")
        if self.unit_price_net < 0:
            raise InvariantViolationError("le prix unitaire HT est positif ou nul")
        if not (Decimal(0) <= self.vat_rate <= Decimal(100)):
            raise InvariantViolationError("le taux de TVA en pourcentage est dans [0, 100]")


@dataclass(frozen=True, slots=True)
class Catalog:
    """Référentiels clients et articles en lecture seule."""

    customers: tuple[Customer, ...]
    items: tuple[Item, ...]

    def find_customer_by_id(self, customer_id: str) -> Customer | None:
        """Recherche un client par identifiant exact."""
        return next((c for c in self.customers if c.id == customer_id), None)

    def find_customer_by_name(self, name: str) -> Customer | None:
        """Recherche un client par raison sociale (insensible à la casse)."""
        target = name.strip().lower()
        return next((c for c in self.customers if c.legal_name.strip().lower() == target), None)

    def find_item_by_id(self, item_id: str) -> Item | None:
        """Recherche un article par identifiant exact."""
        return next((it for it in self.items if it.id == item_id), None)

    def find_item_by_label(self, label: str) -> Item | None:
        """Recherche un article par désignation (insensible à la casse)."""
        target = label.strip().lower()
        return next((it for it in self.items if it.label.strip().lower() == target), None)
