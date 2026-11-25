"""Chargement et validation Pydantic de ``config/extraction.yaml``."""

from decimal import Decimal
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field

from invoicing.extraction.confidence import CalibrationPolicy


class _CapsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ambigu: float = Field(default=0.50, ge=0.0, lt=1.0)
    non_ancre: float = Field(default=0.40, ge=0.0, lt=1.0)
    format_invalide: float = Field(default=0.35, ge=0.0, lt=1.0)
    referentiel_partiel: float = Field(default=0.75, ge=0.0, lt=1.0)
    referentiel_inconnu: float = Field(default=0.70, ge=0.0, lt=1.0)
    ecart_prix: float = Field(default=0.75, ge=0.0, lt=1.0)
    ecart_total: float = Field(default=0.70, ge=0.0, lt=1.0)
    confiance_modele_defaut: float = Field(default=0.70, ge=0.0, lt=1.0)


class ExtractionConfig(BaseModel):
    """Configuration validée de l'extraction (source unique : ``config/extraction.yaml``)."""

    model_config = ConfigDict(extra="forbid")

    extracteur_actif: Literal["local", "gemini", "recorded"] = "recorded"
    modele_en_ligne: str = "gemini-2.5-flash"
    extracteur_repli: str = "local-rules-v1"
    local_first: bool = True
    seuil_confiance_revue: float = Field(default=0.85, gt=0.0, le=1.0)
    plafonds: _CapsModel = Field(default_factory=_CapsModel)

    def to_calibration_policy(self, price_deviation_percent: int = 20) -> CalibrationPolicy:
        """Construit la ``CalibrationPolicy`` du domaine à partir du YAML."""
        return CalibrationPolicy(
            review_threshold=self.seuil_confiance_revue,
            ambiguous_cap=self.plafonds.ambigu,
            ungrounded_cap=self.plafonds.non_ancre,
            invalid_format_cap=self.plafonds.format_invalide,
            catalog_partial_cap=self.plafonds.referentiel_partiel,
            catalog_unknown_cap=self.plafonds.referentiel_inconnu,
            price_deviation_cap=self.plafonds.ecart_prix,
            total_mismatch_cap=self.plafonds.ecart_total,
            default_model_confidence=self.plafonds.confiance_modele_defaut,
            price_deviation_limit=Decimal(price_deviation_percent) / Decimal(100),
        )


def load_extraction_config(config_dir: Path) -> tuple[ExtractionConfig, CalibrationPolicy]:
    """Lit ``extraction.yaml`` et le seuil de prix de ``controles.yaml``."""
    ext_path = config_dir / "extraction.yaml"
    raw_ext = yaml.safe_load(ext_path.read_text(encoding="utf-8")) or {}
    cfg = ExtractionConfig.model_validate(raw_ext)

    price_pct = 20
    ctrl_path = config_dir / "controles.yaml"
    if ctrl_path.is_file():
        raw_ctrl = yaml.safe_load(ctrl_path.read_text(encoding="utf-8")) or {}
        if isinstance(raw_ctrl, dict) and isinstance(
            raw_ctrl.get("seuil_prix_inhabituel_pourcent"), int
        ):
            price_pct = raw_ctrl["seuil_prix_inhabituel_pourcent"]

    return cfg, cfg.to_calibration_policy(price_deviation_percent=price_pct)
