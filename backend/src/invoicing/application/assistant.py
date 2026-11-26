"""Copilote : répond aux questions à partir des données réelles, sans jamais inventer un chiffre.

Moteur local par intentions (mots-clés). Chaque réponse cite ses sources et propose des actions ;
un modèle de langage pourra reformuler plus tard, jamais produire les valeurs.
"""

import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import Decimal

from invoicing.application.collection import receivables
from invoicing.application.context import Context, NotFoundError
from invoicing.application.invoices import InvoiceView, load, view
from invoicing.domain.collection import Standing
from invoicing.domain.invoice import InvoiceStatus

ENGINE = "local-intents-v1"


@dataclass(frozen=True, slots=True)
class Source:
    """D'où vient une affirmation de la réponse."""

    label: str
    invoice_id: str | None = None
    field: str | None = None


@dataclass(frozen=True, slots=True)
class Action:
    """Geste proposé à l'utilisateur."""

    label: str
    path: str


@dataclass(frozen=True, slots=True)
class Answer:
    """Réponse du copilote."""

    intent: str
    text: str
    sources: tuple[Source, ...] = ()
    actions: tuple[Action, ...] = field(default_factory=tuple)
    engine: str = ENGINE


_INTENTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("aide", ("sais-tu", "sais tu", "aide", "peux-tu", "peux tu", "comment ca marche")),
    ("factures_en_retard", ("retard", "relance", "impaye", "recouvr", "echu", "doit")),
    ("pourquoi_bloquee", ("pourquoi", "bloqu", "peux pas", "impossible", "empeche")),
    ("expliquer_total", ("total", "montant", "calcul", "tva", "explique", "combien")),
    ("que_faire_ensuite", ("faire", "ensuite", "prochaine", "etape", "maintenant", "quoi")),
)


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in folded if not unicodedata.combining(c))


def detect_intent(question: str) -> str:
    """Première intention dont un mot-clé apparaît ; sinon l'aide."""
    plain = _plain(question)
    for intent, keywords in _INTENTS:
        if any(k in plain for k in keywords):
            return intent
    return "aide"


def _fmt(amount: Decimal) -> str:
    return f"{amount:,.0f}".replace(",", " ")


def _invoice_path(invoice_id: str) -> str:
    return f"/factures/{invoice_id}"


def _label(v: InvoiceView) -> str:
    return (
        v.invoice.number or f"le brouillon de {v.invoice.content.customer_name or 'client inconnu'}"
    )


def _why_blocked(v: InvoiceView | None) -> Answer:
    if v is None:
        return Answer(
            "pourquoi_bloquee", "Ouvrez une facture : je vous dirai ce qui bloque sa validation."
        )
    inv = v.invoice
    if inv.status is not InvoiceStatus.DRAFT:
        return Answer("pourquoi_bloquee", f"{_label(v)} est déjà validée : plus rien ne la bloque.")
    blocking = inv.open_blocking_anomalies
    if not blocking:
        return Answer(
            "pourquoi_bloquee",
            "Rien ne bloque ce brouillon : un validateur qui n'en est pas l'auteur "
            "peut le valider.",
            actions=(Action("Ouvrir le brouillon", _invoice_path(inv.id)),),
        )
    lines = "\n".join(f"- {a.message}" for a in blocking)
    return Answer(
        "pourquoi_bloquee",
        f"{len(blocking)} point(s) bloquent la validation :\n{lines}",
        sources=tuple(Source(a.code, inv.id, a.field) for a in blocking),
        actions=(Action("Traiter les points", _invoice_path(inv.id)),),
    )


def _explain_total(v: InvoiceView | None) -> Answer:
    if v is None:
        return Answer(
            "expliquer_total", "Ouvrez une facture : je détaillerai la construction de son total."
        )
    inv, t = v.invoice, v.invoice.totals
    if not inv.lines:
        return Answer(
            "expliquer_total",
            "Aucune ligne n'a encore été lue dans la pièce : "
            "il n'y a rien à calculer pour l'instant.",
            actions=(Action("Compléter les lignes", _invoice_path(inv.id)),),
        )
    parts = [
        f"- {line.source.label} : {line.source.quantity} x {_fmt(line.source.unit_price_net)}"
        f" = {_fmt(line.line_net)} HT"
        for line in inv.lines
    ]
    if t.global_discount_amount:
        parts.append(f"- Remise globale : -{_fmt(t.global_discount_amount)}")
    parts += [
        f"- TVA {vat.rate} % sur {_fmt(vat.base)} : {_fmt(vat.amount)}" for vat in t.vat_breakdown
    ]
    parts.append(f"- Total TTC : {_fmt(t.gross_total)} FCFA")
    return Answer(
        "expliquer_total",
        "Construction du montant, telle que calculée par le moteur :\n" + "\n".join(parts),
        sources=(Source("Moteur de calcul et règles de config/calcul.yaml", inv.id),),
        actions=(Action("Voir la facture", _invoice_path(inv.id)),),
    )


def _overdue(ctx: Context) -> Answer:
    items, summary = receivables(ctx)
    late = [r for r in items if r.standing is Standing.OVERDUE]
    if not late:
        return Answer(
            "factures_en_retard",
            "Aucune facture en retard. "
            f"Reste à encaisser au total : {_fmt(summary.outstanding)} FCFA.",
            actions=(Action("Voir l'échéancier", "/recouvrement"),),
        )
    lines = "\n".join(
        f"- {_label(r.view)} ({r.view.invoice.content.customer_name}) : "
        f"{_fmt(r.view.balance.amount_due)} FCFA, {r.days_late} j de retard"
        + (f", relance du jour : {r.next_step.label}" if r.next_step else "")
        for r in late
    )
    return Answer(
        "factures_en_retard",
        f"{summary.overdue_count} facture(s) en retard, "
        f"{_fmt(summary.overdue_amount)} FCFA au total :\n{lines}",
        sources=tuple(Source(_label(r.view), r.view.invoice.id) for r in late),
        actions=(Action("Ouvrir le recouvrement", "/recouvrement"),),
    )


def _next_move(ctx: Context, v: InvoiceView | None) -> Answer:
    if v is None:
        return Answer(
            "que_faire_ensuite",
            "Importez une pièce pour créer un brouillon, "
            "ou consultez l'échéancier pour relancer les retards.",
            actions=(
                Action("Importer une pièce", "/importer"),
                Action("Recouvrement", "/recouvrement"),
            ),
        )
    inv = v.invoice
    open_path = _invoice_path(inv.id)
    if inv.status is InvoiceStatus.DRAFT:
        if inv.open_blocking_anomalies:
            return _why_blocked(v)
        text = (
            "Le brouillon est propre : faites-le valider par un validateur "
            "qui n'en est pas l'auteur."
        )
        return Answer(
            "que_faire_ensuite", text, actions=(Action("Ouvrir le brouillon", open_path),)
        )
    if inv.status is InvoiceStatus.VALIDATED and not v.dispatches:
        text = f"{_label(v)} est validée : émettez-la au client (WhatsApp, SMS ou courriel)."
        return Answer("que_faire_ensuite", text, actions=(Action("Émettre", open_path),))
    if v.balance.amount_due > 0 and inv.status in (InvoiceStatus.VALIDATED, InvoiceStatus.ISSUED):
        text = (
            f"Il reste {_fmt(v.balance.amount_due)} FCFA à encaisser : enregistrez le règlement "
            "dès réception, ou relancez si l'échéance est dépassée."
        )
        actions = (
            Action("Enregistrer un règlement", open_path),
            Action("Recouvrement", "/recouvrement"),
        )
        return Answer("que_faire_ensuite", text, actions=actions)
    return Answer("que_faire_ensuite", f"{_label(v)} est soldée ou annulée : rien à faire.")


_HELP = (
    "Je réponds à partir des données de l'application, sans rien inventer. Demandez par exemple :\n"
    "- Pourquoi je ne peux pas valider ?\n- Explique ce total\n"
    "- Quelles factures sont en retard ?\n- Que faire ensuite ?"
)


def ask(ctx: Context, question: str, invoice_id: str | None = None) -> Answer:
    """Répond à la question, dans le contexte de la facture ouverte s'il y en a une."""
    current: InvoiceView | None = None
    if invoice_id:
        with ctx.store.transaction() as tx:
            try:
                current = view(tx, load(tx, invoice_id))
            except NotFoundError:
                current = None
    intent = detect_intent(question)
    handlers: dict[str, Callable[[], Answer]] = {
        "pourquoi_bloquee": lambda: _why_blocked(current),
        "expliquer_total": lambda: _explain_total(current),
        "factures_en_retard": lambda: _overdue(ctx),
        "que_faire_ensuite": lambda: _next_move(ctx, current),
    }
    return handlers.get(intent, lambda: Answer("aide", _HELP))()
