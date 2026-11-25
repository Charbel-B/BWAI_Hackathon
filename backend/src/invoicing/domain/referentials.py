"""Référentiels clients et articles, chargés depuis data/referentiels/ en lecture seule."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Customer:
    """Client du référentiel."""

    id: str
    legal_name: str
    tax_id: str | None
    phone: str | None
    email: str | None
    preferred_channel: str
    payment_terms_days: int
    vat_liable: bool


@dataclass(frozen=True, slots=True)
class Item:
    """Article du référentiel."""

    id: str
    label: str
    unit: str | None
    unit_price_net: Decimal
    vat_rate: Decimal


def _key(text: str) -> str:
    return " ".join(text.lower().split())


@dataclass(frozen=True, slots=True)
class Referentials:
    """Ensemble des référentiels, avec une recherche tolérante à la casse et aux espaces."""

    customers: tuple[Customer, ...] = ()
    items: tuple[Item, ...] = ()

    def find_customer(self, name: str | None, tax_id: str | None = None) -> Customer | None:
        """Client par IFU d'abord (identifiant fiable), puis par raison sociale exacte."""
        if tax_id:
            for c in self.customers:
                if c.tax_id == tax_id:
                    return c
        if name:
            for c in self.customers:
                if _key(c.legal_name) == _key(name):
                    return c
        return None

    def find_item(self, label: str) -> Item | None:
        """Article par désignation exacte, sinon par désignation contenue dans le libellé."""
        wanted = _key(label)
        exact = [i for i in self.items if _key(i.label) == wanted]
        if exact:
            return exact[0]
        contained = [i for i in self.items if _key(i.label) in wanted or wanted in _key(i.label)]
        return contained[0] if len(contained) == 1 else None

    def customer(self, customer_id: str | None) -> Customer | None:
        """Client par identifiant."""
        return next((c for c in self.customers if c.id == customer_id), None)
