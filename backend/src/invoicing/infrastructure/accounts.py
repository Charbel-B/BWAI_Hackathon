"""Comptes de démonstration (config/utilisateurs.yaml) et jetons de session en mémoire."""

import hashlib
import hmac
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from invoicing.application.ports import Clock
from invoicing.domain.users import Role, User

_SCRYPT = {"n": 2**14, "r": 8, "p": 1}


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Empreinte scrypt au format scrypt$sel$empreinte, en hexadécimal."""
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, **_SCRYPT)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Comparaison en temps constant."""
    _, salt_hex, _ = stored.split("$")
    return hmac.compare_digest(hash_password(password, bytes.fromhex(salt_hex)), stored)


@dataclass(frozen=True, slots=True)
class Account:
    """Compte et empreinte de son mot de passe."""

    user: User
    password_hash: str


class AccountDirectory:
    """Implémentation du port UserDirectory. Jetons perdus au redémarrage, par choix."""

    def __init__(self, accounts: list[Account], clock: Clock, token_minutes: int) -> None:
        self._accounts = {a.user.username: a for a in accounts}
        self._clock = clock
        self._ttl = timedelta(minutes=token_minutes)
        self._tokens: dict[str, tuple[User, datetime]] = {}

    def authenticate(self, username: str, password: str) -> User | None:
        account = self._accounts.get(username)
        if account is None or not verify_password(password, account.password_hash):
            return None
        return account.user

    def issue_token(self, user: User) -> str:
        token = secrets.token_urlsafe(32)
        self._tokens[token] = (user, self._clock.now() + self._ttl)
        return token

    def resolve_token(self, token: str) -> User | None:
        entry = self._tokens.get(token)
        if entry is None or entry[1] < self._clock.now():
            self._tokens.pop(token, None)
            return None
        return entry[0]


def account(username: str, name: str, role: str, password_hash: str) -> Account:
    """Construit un compte depuis la configuration."""
    return Account(User(f"USR-{username}", username, name, Role(role)), password_hash)
