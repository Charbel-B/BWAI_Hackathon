"""Lecture et validation des règles métier de config/*.yaml (source unique de vérité)."""

from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from invoicing.application.context import NumberingFormats
from invoicing.domain.calculation import CalculationRules
from invoicing.domain.collection import CollectionRules, ReminderStep
from invoicing.domain.controls import ControlRules
from invoicing.domain.invoice import Severity
from invoicing.domain.referentials import Issuer


class _Strict(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class _Rounding(_Strict):
    mode: str = "ROUND_HALF_UP"
    unite: Decimal = Decimal(1)


class _Tax(_Strict):
    code: str
    libelle: str
    taux_par_defaut: Decimal


class _Calculation(_Strict):
    devise: str = "XOF"
    arrondi: _Rounding = Field(default_factory=_Rounding)
    ordre_des_remises: list[str] = Field(default_factory=lambda: ["ligne", "globale"])
    taxes: list[_Tax]


class _Controls(_Strict):
    seuil_prix_inhabituel_pourcent: Decimal
    seuil_gros_montant_ttc: Decimal
    gravites: dict[str, Severity]


class _Numbering(_Strict):
    facture: str
    avoir: str


class _Security(_Strict):
    separation_des_taches: bool = True
    duree_jeton_minutes: int = 480


class _Channels(_Strict):
    actifs: list[str]
    modeles: dict[str, str] = Field(default_factory=dict)


class _Account(_Strict):
    identifiant: str
    nom: str
    role: str
    mot_de_passe_scrypt: str


class _Step(_Strict):
    code: str
    libelle: str
    decalage_jours: int
    modele: str


class _Reminders(_Strict):
    bientot_du_jours: int = 3
    etapes: list[_Step]


class _Issuer(_Strict):
    nom: str
    adresse: str
    ifu: str
    telephone: str
    email: str


class _Accounts(_Strict):
    comptes: list[_Account]


class BusinessConfig(_Strict):
    """Toute la configuration métier, validée au démarrage : une erreur arrête l'application."""

    calcul: _Calculation
    controles: _Controls
    numerotation: _Numbering
    securite: _Security
    canaux: _Channels
    utilisateurs: _Accounts
    relances: _Reminders
    emetteur: _Issuer

    def calculation_rules(self) -> CalculationRules:
        """Règles de calcul du domaine."""
        vat = next((t for t in self.calcul.taxes if t.code == "TVA"), None)
        return CalculationRules(
            rounding_mode=self.calcul.arrondi.mode,
            rounding_unit=self.calcul.arrondi.unite,
            default_vat_rate=vat.taux_par_defaut if vat else Decimal(0),
            discount_order=tuple(self.calcul.ordre_des_remises),
        )

    def control_rules(self, review_threshold: float) -> ControlRules:
        """Règles de contrôle du domaine ; le seuil de confiance vient de extraction.yaml."""
        return ControlRules(
            unusual_price_percent=self.controles.seuil_prix_inhabituel_pourcent,
            high_amount_gross=self.controles.seuil_gros_montant_ttc,
            review_threshold=review_threshold,
            severities=dict(self.controles.gravites),
        )

    def collection_rules(self) -> CollectionRules:
        """Étapes de relance du domaine."""
        steps = tuple(
            ReminderStep(s.code, s.libelle, s.decalage_jours, s.modele)
            for s in self.relances.etapes
        )
        return CollectionRules(self.relances.bientot_du_jours, steps)

    def issuer(self) -> Issuer:
        """Identité de l'émetteur."""
        e = self.emetteur
        return Issuer(e.nom, e.adresse, e.ifu, e.telephone, e.email)

    def numbering(self) -> NumberingFormats:
        """Formats de numérotation."""
        return NumberingFormats(self.numerotation.facture, self.numerotation.avoir)


def _read(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_business_config(config_dir: Path) -> BusinessConfig:
    """Lit les six fichiers de règles et les valide ensemble."""
    names = (
        "calcul",
        "controles",
        "numerotation",
        "securite",
        "canaux",
        "utilisateurs",
        "relances",
        "emetteur",
    )
    return BusinessConfig.model_validate({n: _read(config_dir / f"{n}.yaml") for n in names})
