from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.auth.jwt import decode_access_token

PUBLIC_PATHS = {"/", "/docs", "/openapi.json", "/redoc", "/auth", "/api/v1/health"}


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.tenant_id = None

        path = request.url.path
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = decode_access_token(token)
                request.state.tenant_id = payload.get("tenant_id")
            except Exception:
                pass

        return await call_next(request)
