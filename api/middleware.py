from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Enable XSS filtering in browsers that support it
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Prevent MIME-type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Content Security Policy (adjust as needed for your specific frontend/assets)
        # This is a strict starting point; you may need to allow specific domains (e.g., for fonts, scripts)
        # 'self' allows resources from the same origin.
        # 'unsafe-inline' is often needed for some UI frameworks/styles but should be avoided if possible.
        csp_policy = (
            "default-src 'self'; "
            "img-src 'self' data: blob:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # unsafe-eval needed for some dev tools/libraries
            "font-src 'self' data:;"
        )
        response.headers["Content-Security-Policy"] = csp_policy
        
        return response
