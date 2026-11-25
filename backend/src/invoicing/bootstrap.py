"""Seul endroit qui relie les ports à leurs adaptateurs selon la configuration."""

from importlib.metadata import version

from fastapi import FastAPI

from invoicing.api.app import AppInfo, Services, create_api
from invoicing.application.context import Context
from invoicing.application.ports import Clock, Extractor
from invoicing.domain.referentials import Referentials
from invoicing.extraction import CatalogHint, RuleBasedExtractor
from invoicing.infrastructure.accounts import AccountDirectory, account
from invoicing.infrastructure.business_config import load_business_config
from invoicing.infrastructure.clock import SystemClock
from invoicing.infrastructure.config_files import config_sha256
from invoicing.infrastructure.extraction_config import load_extraction_config
from invoicing.infrastructure.gemini_extractor import GeminiConfig, GeminiExtractor
from invoicing.infrastructure.referentials_csv import load_referentials
from invoicing.infrastructure.simulated_channel import SimulatedChannel
from invoicing.infrastructure.sqlite_store import SqliteStore
from invoicing.settings import Settings


def _catalog(referentials: Referentials) -> CatalogHint:
    return CatalogHint(
        customer_names=tuple(c.legal_name for c in referentials.customers),
        tax_ids=tuple(c.tax_id for c in referentials.customers if c.tax_id),
        item_labels=tuple(i.label for i in referentials.items),
        item_prices=tuple((i.label, str(i.unit_price_net)) for i in referentials.items),
    )


def _extractor(settings: Settings, referentials: Referentials) -> tuple[Extractor, float]:
    """Extracteur local par règles ; Gemini seulement s'il est choisi ET qu'une clé existe."""
    config, policy = load_extraction_config(settings.config_dir)
    catalog = _catalog(referentials)
    local = RuleBasedExtractor(catalog=catalog, policy=policy)
    key = settings.gemini_api_key.get_secret_value()
    if config.extracteur_actif == "gemini" and key:
        gemini = GeminiConfig(
            api_key=key,
            model=config.modele_en_ligne,
            catalog=catalog,
            policy=policy,
            local_first=config.local_first,
        )
        return GeminiExtractor(config=gemini, fallback=local), config.seuil_confiance_revue
    return local, config.seuil_confiance_revue


def create_app(settings: Settings | None = None, clock: Clock | None = None) -> FastAPI:
    """Point d'entrée de uvicorn : `uvicorn --factory invoicing.bootstrap:create_app`."""
    settings = settings or Settings()
    clock = clock or SystemClock()
    business = load_business_config(settings.config_dir)
    referentials = load_referentials(settings.data_dir / "referentiels")
    extractor, threshold = _extractor(settings, referentials)
    store = SqliteStore(settings.database_path)
    fingerprint = config_sha256(settings.config_dir)
    context = Context(
        store=store,
        clock=clock,
        extractor=extractor,
        channel=SimulatedChannel(business.canaux.modeles),
        referentials=referentials,
        calculation=business.calculation_rules(),
        controls=business.control_rules(threshold),
        numbering=business.numbering(),
        separation_of_duties=business.securite.separation_des_taches,
        active_channels=tuple(business.canaux.actifs),
        config_sha256=fingerprint,
        demo_mode=settings.demo_mode,
    )
    accounts = [
        account(a.identifiant, a.nom, a.role, a.mot_de_passe_scrypt)
        for a in business.utilisateurs.comptes
    ]
    users = AccountDirectory(accounts, clock, business.securite.duree_jeton_minutes)
    info = AppInfo(version=version("invoicing"), config_sha256=fingerprint)
    return create_api(info, Services(context, users, store))
