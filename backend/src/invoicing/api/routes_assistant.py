"""Route du copilote."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from invoicing.api.deps import Ctx
from invoicing.api.security import Operator
from invoicing.application import assistant

router = APIRouter(prefix="/assistant", tags=["copilote"])


class AskIn(BaseModel):
    """Question posée, et facture ouverte s'il y en a une."""

    question: str = Field(min_length=1, max_length=500)
    invoice_id: str | None = None


class SourceOut(BaseModel):
    """Source d'une affirmation."""

    label: str
    invoice_id: str | None
    field: str | None


class ActionOut(BaseModel):
    """Action proposée."""

    label: str
    path: str


class AnswerOut(BaseModel):
    """Réponse du copilote."""

    intent: str
    answer: str
    sources: list[SourceOut]
    actions: list[ActionOut]
    engine: str


@router.post("/ask")
def ask(ctx: Ctx, _: Operator, body: AskIn) -> AnswerOut:
    """Répond à partir des données réelles ; `engine` dit quel moteur a répondu."""
    a = assistant.ask(ctx, body.question, body.invoice_id)
    return AnswerOut(
        intent=a.intent,
        answer=a.text,
        sources=[
            SourceOut(label=s.label, invoice_id=s.invoice_id, field=s.field) for s in a.sources
        ],
        actions=[ActionOut(label=x.label, path=x.path) for x in a.actions],
        engine=a.engine,
    )
