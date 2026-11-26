"""Routes transverses : authentification, journal d'audit, réinitialisation de la démo."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

from invoicing.api.deps import Ctx
from invoicing.api.errors import ApiError
from invoicing.api.schemas import (
    AuditOut,
    AuditVerifyOut,
    LoginIn,
    TokenOut,
    UserOut,
    audit_out,
    user_out,
)
from invoicing.api.security import Admin, Operator, Validator, directory
from invoicing.domain.audit import verify_chain

router = APIRouter(tags=["système"])


@router.post("/auth/login")
def login(request: Request, body: LoginIn) -> TokenOut:
    """Échange des identifiants contre un jeton porteur."""
    users = directory(request)
    user = users.authenticate(body.username, body.password)
    if user is None:
        raise ApiError(401, "UNAUTHENTICATED", "identifiants invalides")
    return TokenOut(access_token=users.issue_token(user), user=user_out(user))


@router.get("/auth/me")
def me(user: Operator) -> UserOut:
    """Utilisateur courant."""
    return user_out(user)


class IssuerOut(BaseModel):
    """Identité de l'émetteur, pour l'en-tête des factures."""

    name: str
    address: str
    tax_id: str
    phone: str
    email: str


@router.get("/issuer")
def issuer(ctx: Ctx, _: Operator) -> IssuerOut:
    """Émetteur des factures (config/emetteur.yaml)."""
    i = ctx.issuer
    return IssuerOut(name=i.name, address=i.address, tax_id=i.tax_id, phone=i.phone, email=i.email)


@router.get("/audit-log")
def audit_log(ctx: Ctx, _: Validator, entity_id: str | None = None) -> list[AuditOut]:
    """Journal, filtrable par entité."""
    with ctx.store.transaction() as tx:
        return [audit_out(e) for e in tx.audit_entries(entity_id)]


@router.get("/audit-log/verify")
def verify_audit_log(ctx: Ctx, _: Validator) -> AuditVerifyOut:
    """Recalcule toute la chaîne d'empreintes."""
    with ctx.store.transaction() as tx:
        entries = tx.audit_entries()
    broken = verify_chain(entries)
    return AuditVerifyOut(intact=broken is None, entries=len(entries), first_broken_seq=broken)


@router.post("/admin/reset", status_code=204)
def reset(ctx: Ctx, _: Admin) -> None:
    """Vide les données de démonstration. Refusé hors mode démonstration."""
    if not ctx.demo_mode:
        raise ApiError(403, "FORBIDDEN", "réinitialisation désactivée hors mode démonstration")
    with ctx.store.transaction() as tx:
        tx.reset()
