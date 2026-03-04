"""kgateway OIDC Middleware for Spider-Builder.

Extracts user information from:
1. X-Auth-Request-* headers (if kgateway OAuth2 forwards them)
2. Authorization header with Bearer token (decode JWT)
3. Fallback to shared settings if no user info available
"""

import base64
import json
import logging
from typing import Callable, Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


def decode_jwt_payload(token: str) -> dict:
    """Decode JWT payload without verification (for user info extraction)."""
    try:
        # JWT format: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return {}
        
        # Decode payload
        payload = parts[1]
        # Add padding if needed
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += '=' * padding
        
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        logger.warning(f"[OIDC] Failed to decode JWT: {e}")
        return {}


class KgatewayOIDCMiddleware(BaseHTTPMiddleware):
    """Middleware to extract user info from OAuth2 authentication."""
    
    # Header names
    USER_HEADERS = ["X-Auth-Request-User", "X-Forwarded-User", "X-User"]
    EMAIL_HEADERS = ["X-Auth-Request-Email", "X-Forwarded-Email", "X-Email"]
    NAME_HEADERS = ["X-Auth-Request-Preferred-Username", "X-Forwarded-Preferred-Username", "X-Name"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Extract user info from headers or JWT token."""
        
        user_id = None
        user_email = None
        user_name = None
        
        # Log all relevant headers for debugging
        auth_header = request.headers.get("Authorization", "")
        if auth_header:
            logger.info(f"[OIDC] Authorization header present: {auth_header[:20]}...")
        
        # Method 1: Try X-Auth-Request-* headers
        for header in self.USER_HEADERS:
            user_id = request.headers.get(header)
            if user_id:
                logger.info(f"[OIDC] Found user_id from {header}: {user_id}")
                break
        
        for header in self.EMAIL_HEADERS:
            user_email = request.headers.get(header)
            if user_email:
                break
        
        for header in self.NAME_HEADERS:
            user_name = request.headers.get(header)
            if user_name:
                break
        
        # Method 2: If no user headers, try Authorization Bearer token
        if not user_id:
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                payload = decode_jwt_payload(token)
                user_id = payload.get("sub") or payload.get("user_id")
                user_email = payload.get("email") or payload.get("preferred_username")
                user_name = payload.get("name") or payload.get("preferred_username")
                if user_id:
                    logger.info(f"[OIDC] Extracted user_id={user_id} from JWT")
                else:
                    logger.info(f"[OIDC] JWT decoded but no user_id found. Payload keys: {list(payload.keys())}")
        
        # Store in request.state
        request.state.oidc_user_id = user_id
        request.state.oidc_user_email = user_email
        request.state.oidc_user_name = user_name
        
        if user_id:
            request.state.user = {
                "id": user_id,
                "email": user_email,
                "name": user_name,
            }
        else:
            request.state.user = None
            # Log for debugging - but don't block the request
            logger.debug(f"[OIDC] No user_id found for path={request.url.path}")
        
        return await call_next(request)


def get_oidc_user(request: Request) -> dict | None:
    return getattr(request.state, "user", None)


def get_oidc_user_id(request: Request) -> str | None:
    return getattr(request.state, "oidc_user_id", None)


def get_oidc_user_email(request: Request) -> str | None:
    return getattr(request.state, "oidc_user_email", None)
