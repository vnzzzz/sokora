"""Page/HTMX adapterで共有するresponse helper。"""

import html
import json
from typing import Any, Mapping

from fastapi import status
from fastapi.responses import HTMLResponse, Response


def hx_trigger_response(events: Mapping[str, Any]) -> Response:
    """HX-Trigger eventをbodyなし204 responseで返す。

    Args:
        events: event名をkey、event payloadをvalueとするmapping。

    Returns:
        JSON化した`HX-Trigger` headerを持つ204 response。
    """
    return Response(
        status_code=status.HTTP_204_NO_CONTENT,
        headers={"HX-Trigger": json.dumps(events)},
    )


def hx_error_response(detail: str, *, target: str) -> HTMLResponse:
    """HTMX form errorを指定targetへ安全に差し替える。

    Args:
        detail: 利用者へ表示するerror detail。
        target: `HX-Retarget`へ設定するCSS selector。

    Returns:
        HTML escape済みdetailとretarget/reswap headerを持つ200 response。
    """
    return HTMLResponse(
        content=html.escape(detail),
        status_code=status.HTTP_200_OK,
        headers={"HX-Retarget": target, "HX-Reswap": "innerHTML"},
    )
