"""Serves install.sh with the correct content type for curl | sh."""

from __future__ import annotations

import os
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

_SCRIPT_PATH = Path(__file__).parent.parent / "install.sh"


async def serve_install(request: Request) -> PlainTextResponse:
    if _SCRIPT_PATH.exists():
        content = _SCRIPT_PATH.read_text()
    else:
        content = "#!/bin/sh\necho 'Install script not found.'\n"
    return PlainTextResponse(content, headers={"Content-Type": "text/plain; charset=utf-8"})


app = Starlette(routes=[Route("/{path:path}", serve_install, methods=["GET"])])
