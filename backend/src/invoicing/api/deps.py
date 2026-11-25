"""Accès au contexte applicatif branché par le bootstrap."""

from typing import Annotated

from fastapi import Depends, Request

from invoicing.application.context import Context


def context(request: Request) -> Context:
    """Contexte des cas d'usage."""
    found: Context = request.app.state.context
    return found


Ctx = Annotated[Context, Depends(context)]
