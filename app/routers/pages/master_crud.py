"""Shared SSR/HTMX response helpers for master-management pages."""

import json
from dataclasses import dataclass
from typing import Any, Mapping

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.responses import Response


def _trigger_headers(payload: Mapping[str, Any]) -> dict[str, str]:
    """HX-Trigger payloadをresponse headerへencodeする。

    Args:
        payload: event名とpayloadを含むmapping。

    Returns:
        JSON化した`HX-Trigger` header mapping。
    """
    return {"HX-Trigger": json.dumps(dict(payload))}


@dataclass(frozen=True)
class MasterCrudResponder:
    """master管理画面で共通するmodal CRUD responseをrenderする。

    standard flow:
    - modal GET appends a dialog to ``body`` and emits ``openModal``;
    - create/update success replaces the dialog and emits ``closeModal`` +
      ``refreshPage``;
    - validation/application errors replace the same dialog with inline errors;
    - delete success removes the dialog body and emits the same refresh contract.

    Args:
        templates: Jinja template renderer。
        form_template: create/update modal template path。
        delete_template: delete confirmation template path。
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
        """共通modal contextを組み立てる。

        Args:
            request: FastAPI request。
            modal_id: client-side modal identifier。
            context: model固有のtemplate context。

        Returns:
            request/modal IDを含むtemplate context。
        """
        return {"request": request, "modal_id": modal_id, **dict(context)}

    def open_form(
        self,
        request: Request,
        *,
        modal_id: str,
        context: Mapping[str, Any],
    ) -> Response:
        """form dialog fragmentを返し、HTMX clientへopen eventだけを通知する。

        callerはmodel固有のcontextだけを渡し、request/modal ID/errors defaultはresponder側で
        統一する。GET時点ではpage refreshやsuccess messageを発火しない。

        Args:
            request: FastAPI request。
            modal_id: 開くmodal ID。
            context: model固有のtemplate context。

        Returns:
            form fragmentと`openModal` eventを持つresponse。
        """
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
        """successful create/update後のdialog fragmentと共通HTMX eventを返す。

        server-side writeがcommit済みであることをcallerの前提とし、clientへ
        ``closeModal`` → page refresh → message表示の契約を1つのHX-Trigger payloadとして
        渡す。ここでDB mutation自体は行わない。

        Args:
            request: FastAPI request。
            modal_id: 閉じるmodal ID。
            context: commit後のmodel固有template context。
            message: 利用者へ表示するsuccess message。

        Returns:
            form fragmentとclose/refresh/message eventを持つresponse。
        """
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
        """validation/application errorを同じdialog fragment内へ再renderする。

        master CRUD UIはfield errorをHTTP 200 fragmentとして扱い、success用HX-Triggerを
        一切付けない。これによりdialogを閉じたりpage refreshしたりせず、利用者が入力を
        修正できる状態を維持する。

        Args:
            request: FastAPI request。
            modal_id: 維持するmodal ID。
            context: 入力値を含むmodel固有context。
            errors: field名をkey、message listをvalueとするvalidation error mapping。

        Returns:
            inline error付きform fragment。
        """
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
        """delete確認dialogを開くfragmentを返す。

        Args:
            request: FastAPI request。
            modal_id: 開くdelete modal ID。
            context: 削除対象を表示するtemplate context。

        Returns:
            delete confirmation fragmentと`openModal` eventを持つresponse。
        """
        return self.templates.TemplateResponse(
            self.delete_template,
            self._context(request, modal_id, context),
            headers=_trigger_headers({"openModal": modal_id}),
        )

    @staticmethod
    def delete_success(*, modal_id: str, message: str) -> HTMLResponse:
        """commit済みdeleteをclose/refresh/message eventで通知する。

        削除対象HTMLをserver側で再構築せず、page全体のread modelをrefreshさせることを
        master画面共通contractとする。

        Args:
            modal_id: 閉じるdelete modal ID。
            message: 利用者へ表示するsuccess message。

        Returns:
            空bodyとclose/refresh/message eventを持つHTML response。
        """
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
        """参照制約等でdeleteできない場合、確認dialogをwarning付きで維持する。

        form errorと同様にsuccess triggerを付けず、clientがclose/refreshを誤実行しない
        response contractを保つ。

        Args:
            request: FastAPI request。
            modal_id: 維持するdelete modal ID。
            context: 削除対象を表示するtemplate context。
            warning_message: 利用者へ表示するwarning。

        Returns:
            warning付きdelete confirmation fragment。
        """
        response_context = self._context(request, modal_id, context)
        response_context["warning_message"] = warning_message
        return self.templates.TemplateResponse(self.delete_template, response_context)
