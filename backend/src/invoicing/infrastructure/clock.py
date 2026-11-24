"""Implémentations du port Clock."""

from datetime import UTC, datetime

from invoicing.domain.errors import InvariantViolationError


class SystemClock:
    """Heure réelle, en UTC."""

    def now(self) -> datetime:
        """Instant courant."""
        return datetime.now(UTC)


class FixedClock:
    """Heure figée sur la date de référence : calculs et tests reproductibles."""

    def __init__(self, instant: datetime) -> None:
        if instant.tzinfo is None:
            raise InvariantViolationError("l'instant de référence doit porter un fuseau")
        self._instant = instant

    def now(self) -> datetime:
        """Toujours le même instant."""
        return self._instant
