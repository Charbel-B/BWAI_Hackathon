"""Canal d'émission simulé : compose le vrai message, ne l'envoie pas, et le dit."""

from collections.abc import Mapping

from invoicing.application.ports import SentMessage
from invoicing.domain.invoice import Invoice
from invoicing.domain.referentials import Customer

DEFAULT_TEMPLATE = "Facture {numero} : {montant} FCFA TTC, échéance {echeance}."


class SimulatedChannel:
    """Remplace WhatsApp, SMS et courriel. Le branchement réel se fait ici, derrière le port."""

    def __init__(self, templates: Mapping[str, str]) -> None:
        self._templates = dict(templates)

    def send(self, invoice: Invoice, customer: Customer | None, channel: str) -> SentMessage:
        """Rend le destinataire et le message qui auraient été envoyés."""
        recipient = "destinataire inconnu"
        if customer is not None:
            address = customer.email if channel == "email" else customer.phone
            recipient = address or customer.legal_name
        template = self._templates.get(channel, DEFAULT_TEMPLATE)
        due = invoice.content.due_date
        message = template.format(
            numero=invoice.number,
            montant=f"{invoice.totals.gross_total:,}".replace(",", " "),
            echeance=due.isoformat() if due else "à réception",
            client=invoice.content.customer_name or "",
        )
        return SentMessage(recipient=recipient, message=message)
