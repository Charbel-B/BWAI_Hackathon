"""Idempotence des POST : même clé et même contenu, même réponse, sans nouvel effet.

La clé est propre à l'utilisateur (le jeton fait partie de l'empreinte), si bien que deux
utilisateurs ne peuvent pas rejouer la réponse l'un de l'autre.
"""

import hashlib

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from invoicing.api.errors import problem
from invoicing.application.ports import IdempotencyStore, StoredResponse

EXEMPT = ("/api/v1/auth/login",)
# Une erreur serveur n'est pas mémorisée : le client doit pouvoir réessayer avec la même clé.
FIRST_SERVER_ERROR = 500


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Exige Idempotency-Key sur les POST et rejoue la réponse mémorisée."""

    def __init__(self, app: object, store: IdempotencyStore) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._store = store

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.method != "POST" or request.url.path in EXEMPT:
            return await call_next(request)
        key = request.headers.get("idempotency-key")
        if not key:
            return problem(422, "INVALID_INPUT", "en-tête Idempotency-Key obligatoire")
        body = await request.body()
        auth = request.headers.get("authorization", "")
        fingerprint = hashlib.sha256(f"{request.url.path}|{auth}|".encode() + body).hexdigest()
        scoped_key = hashlib.sha256(f"{auth}|{key}".encode()).hexdigest()
        stored = self._store.get(scoped_key)
        if stored is not None:
            if stored.fingerprint != fingerprint:
                return problem(409, "IDEMPOTENCY_KEY_REUSED", "même clé, contenu différent")
            return Response(
                stored.body,
                stored.status_code,
                media_type=stored.media_type,
                headers={"Idempotent-Replayed": "true"},
            )
        response = await call_next(request)
        chunks = [chunk async for chunk in response.body_iterator]  # type: ignore[attr-defined]
        content = b"".join(c if isinstance(c, bytes) else c.encode() for c in chunks)
        if response.status_code < FIRST_SERVER_ERROR:
            media = response.media_type or response.headers.get("content-type", "application/json")
            self._store.save(
                scoped_key, StoredResponse(fingerprint, response.status_code, content, media)
            )
        return Response(content, response.status_code, headers=dict(response.headers))
