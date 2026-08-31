"""Page/HTMX adapterで共有するresponse helper。"""

import html
import json
from typing import Any, Mapping

from fastapi import status
from fastapi.responses import HTMLResponse, Response


def hx_trigger_response(events: Mapping[str, Any]) -> Response:
    """HX-Trigger eventを返すbodyなし204 response。"""
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"HX-Trigger": json.dumps(events)},
    )


def hx_error_response(detail: str, *, target: str) -> HTMLResponse:
    """HTMX form errorを指定targetへ安全に差し替える。"""
    return HTMLResponse(
        content=html.escape(detail),
        status_code=status.HTTP_200_OK,
        headers={"HX-Retarget": target, "HX-Reswap": "innerHTML"},
    )
