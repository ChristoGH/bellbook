"""School context middleware.

Extracts the current school_id from each request and stores it in
request.state.school_id.  The get_db dependency then issues
  SET LOCAL app.current_school_id = <id>
on every database session, enforcing PostgreSQL RLS.

School ID resolution order:
  1. JWT Bearer token  → "school_id" claim  (primary, for all API calls)
  2. X-School-ID header           (admin tooling fallback)
  3. Subdomain parsing            (future: requires a DB/cache lookup)

Implemented as a pure ASGI middleware (not BaseHTTPMiddleware) so it
does not buffer response bodies and is safe for SSE / streaming responses.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from jose import JWTError
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Receive, Scope, Send

from app.services.auth_service import decode_token

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _extract_school_id(headers: Headers) -> str | None:
    """Return the school_id string from the request headers, or None."""

    # 1. Try Bearer token
    auth = headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[len("Bearer "):]
        try:
            payload = decode_token(token)
            school_id = payload.get("school_id")
            if school_id:
                return str(school_id)
        except JWTError:
            pass  # malformed / expired tokens are handled by get_current_user

    # 2. Explicit header (admin CLI / Postman)
    explicit = headers.get("x-school-id")
    if explicit:
        return explicit

    # 3. Subdomain  (e.g. rivonia-primary.bellbook.co.za)
    # Requires a slug→UUID lookup; deferred to Phase 1.5.
    # host = headers.get("host", "")
    # slug = _parse_slug(host)
    # if slug:
    #     return await resolve_slug(slug)  # would need async; skip for now

    return None


class SchoolContextMiddleware:
    """Pure-ASGI middleware — zero overhead on non-HTTP scopes, SSE-safe."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = Headers(scope=scope)
            school_id = _extract_school_id(headers)

            # Starlette lazily initialises scope["state"]; ensure it exists.
            if "state" not in scope:
                scope["state"] = {}
            scope["state"]["school_id"] = school_id

        await self.app(scope, receive, send)
