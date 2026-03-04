"""OIDC Authentication module for Spider-Builder.

Provides multi-user authentication for OpenHands OSS via Zitadel OIDC.
"""

from .zitadel_auth import ZitadelUserAuth
from .kgateway_middleware import KgatewayOIDCMiddleware, get_oidc_user, get_oidc_user_id, get_oidc_user_email
from .server_patch import patch_server_app, get_user_auth_class
from .session_manager import SessionManager

__all__ = [
    "ZitadelUserAuth",
    "KgatewayOIDCMiddleware",
    "get_oidc_user",
    "get_oidc_user_id", 
    "get_oidc_user_email",
    "patch_server_app",
    "get_user_auth_class",
    "SessionManager",
]
