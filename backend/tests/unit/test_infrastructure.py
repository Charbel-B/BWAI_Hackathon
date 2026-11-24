from datetime import UTC, datetime
from pathlib import Path

import pytest

from invoicing.application.ports import Clock
from invoicing.domain.errors import InvariantViolationError
from invoicing.infrastructure.clock import FixedClock, SystemClock
from invoicing.infrastructure.config_files import config_sha256, load_config


def test_fixed_clock_always_returns_reference_instant() -> None:
    instant = datetime(2026, 11, 24, 9, 0, tzinfo=UTC)
    clock: Clock = FixedClock(instant)
    assert clock.now() == instant
    assert clock.now() == instant


def test_fixed_clock_refuses_naive_instant() -> None:
    with pytest.raises(InvariantViolationError):
        FixedClock(datetime(2026, 11, 24))  # noqa: DTZ001 - cas testé volontairement


def test_system_clock_is_timezone_aware() -> None:
    assert SystemClock().now().tzinfo is UTC


def test_config_hash_is_stable_and_detects_changes(tmp_path: Path) -> None:
    rule_file = tmp_path / "calcul.yaml"
    rule_file.write_text("taux: 18\n", encoding="utf-8")
    first = config_sha256(tmp_path)
    assert config_sha256(tmp_path) == first
    rule_file.write_text("taux: 19\n", encoding="utf-8")
    assert config_sha256(tmp_path) != first


def test_load_config_indexes_files_by_name(tmp_path: Path) -> None:
    (tmp_path / "calcul.yaml").write_text("devise: XOF\n", encoding="utf-8")
    assert load_config(tmp_path) == {"calcul": {"devise": "XOF"}}
