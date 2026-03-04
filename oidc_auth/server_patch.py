"""Server patch for Spider-Builder.

This module provides patches to integrate OIDC authentication into OpenHands OSS.
"""

import os


def get_user_auth_class() -> str:
    """Return the custom UserAuth class path."""
    return "oidc_auth.zitadel_auth.ZitadelUserAuth"


def patch_server_app(app):
    """Patch the FastAPI app to add OIDC middleware.
    
    Usage in OpenHands server:
        from oidc_auth.server_patch import patch_server_app
        patch_server_app(app)
    """
    from .kgateway_middleware import KgatewayOIDCMiddleware
    
    # Add middleware to extract user from OIDC headers
    app.add_middleware(KgatewayOIDCMiddleware)
    
    return app


def get_file_store_path(user_id: str | None = None) -> str:
    """Get the file store path for a user.
    
    Per-user storage: FILE_STORE_PATH/{user_id}/
    """
    base_path = os.getenv("FILE_STORE_PATH", "/.openhands")
    
    if user_id:
        return os.path.join(base_path, user_id)
    
    return base_path
