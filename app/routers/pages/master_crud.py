"""Shared SSR/HTMX response helpers for master-management pages."""

import json
from dataclasses import dataclass
from typing import Any, Mapping

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import Response


def _trigger_headers(payload: Mapping[str, Any]) -> dict[str, str]:
    """Encode one HX-Trigger payload using the existing response-header contract."""
    return {"HX-Trigger": json.dumps(dict(payload))}


@dataclass(frozen=True)
class MasterCrudResponder:
    """Render the common modal CRUD interaction used by master-management pages.

    The standard flow is:
    - modal GET appends a dialog to ``body`` and emits ``openModal``;
    - create/update success replaces the dialog and emits ``closeModal`` +
      ``refreshPage``;
    - validation/application errors replace the same dialog with inline errors;
    - delete success removes the dialog body and emits the same refresh contract.
    """

    templates: Jinja2Templates
    form_template: str
    delete_template: str

    @staticmethod
    def _context(
        request: Request,
        modal_id: str,
        context: Mapping[str, Any],
    ) -> dict[str, Any]:
        return {"request": request, "modal_id": modal_id, **dict(context)}

    def open_form(
        self,
        request: Request,
        *,
        modal_id: str,
        context: Mapping[str, Any],
    ) -> Response:
        response_context = self._context(request, modal_id, context)
        response_context.setdefault("errors", {})
        return self.templates.TemplateResponse(
            self.form_template,
            response_context,
            headers=_trigger_headers({"openModal": modal_id}),
        )

    def form_success(
        self,
        request: Request,
        *,
        modal_id: str,
        context: Mapping[str, Any],
        message: str,
    ) -> Response:
        response_context = self._context(request, modal_id, context)
        response_context.setdefault("errors", {})
        return self.templates.TemplateResponse(
            self.form_template,
            response_context,
            headers=_trigger_headers(
                {
                    "closeModal": modal_id,
                    "refreshPage": True,
                    "showMessage": message,
                }
            ),
        )

    def form_error(
        self,
        request: Request,
        *,
        modal_id: str,
        context: Mapping[str, Any],
        errors: Mapping[str, list[str]],
    ) -> Response:
        response_context = self._context(request, modal_id, context)
        response_context["errors"] = dict(errors)
        return self.templates.TemplateResponse(self.form_template, response_context)

    def open_delete(
        self,
        request: Request,
        *,
        modal_id: str,
        context: Mapping[str, Any],
    ) -> Response:
        return self.templates.TemplateResponse(
            self.delete_template,
            self._context(request, modal_id, context),
            headers=_trigger_headers({"openModal": modal_id}),
        )

    @staticmethod
    def delete_success(*, modal_id: str, message: str) -> HTMLResponse:
        return HTMLResponse(
            content="",
            status_code=200,
            headers=_trigger_headers(
                {
                    "closeModal": modal_id,
                    "refreshPage": True,
                    "showMessage": message,
                }
            ),
        )

    def delete_error(
        self,
        request: Request,
        *,
        modal_id: str,
        context: Mapping[str, Any],
        warning_message: str,
    ) -> Response:
        response_context = self._context(request, modal_id, context)
        response_context["warning_message"] = warning_message
        return self.templates.TemplateResponse(self.delete_template, response_context)
