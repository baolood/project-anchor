"""FastAPI mount for the read-only Anchor control MCP."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import Response

from app.mcp.protocol import dispatch_http


router = APIRouter(tags=["anchor-control-mcp"])


@router.api_route("/mcp", methods=["POST", "GET", "DELETE"])
async def anchor_control_mcp(request: Request) -> Response:
    """Read-only ANCHOR_CONTROL_MCP_V1 Streamable HTTP endpoint."""
    result = dispatch_http(
        method=request.method,
        headers={key.lower(): value for key, value in request.headers.items()},
        body=await request.body(),
        query_string=request.url.query,
    )
    media_type = result.headers.get("content-type")
    extra = {key: value for key, value in result.headers.items() if key.lower() != "content-type"}
    return Response(content=result.body, status_code=result.status, media_type=media_type, headers=extra)
