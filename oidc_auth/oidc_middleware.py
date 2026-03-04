"""OIDC Middleware for Spider-Builder.

Handles OAuth2 authorization code flow with Zitadel:
    - /auth/login - Redirect to Zitadel login
    - /auth/callback - Handle OAuth callback
    - /auth/logout - Logout and redirect
"""

import os
import secrets
import urllib.parse
from typing import Optional

import httpx
from fastapi import FastAPI, Request, Response, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel

from .session_manager import SessionManager


# OIDC configuration from environment
OIDC_ISSUER = os.getenv("OIDC_ISSUER", "https://auth.spideros.dev")
OIDC_CLIENT_ID = os.getenv("OIDC_CLIENT_ID", "")
OIDC_CLIENT_SECRET = os.getenv("OIDC_CLIENT_SECRET", "")
OIDC_REDIRECT_URI = os.getenv("OIDC_REDIRECT_URI", "")


class OIDCConfig(BaseModel):
    """OIDC configuration loaded from Zitadel's well-known endpoint."""
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    end_session_endpoint: str
    jwks_uri: str


class OIDCMiddleware:
    """FastAPI middleware for OIDC authentication.
    
    Adds authentication routes to the OpenHands OSS application:
        GET /auth/login - Start OAuth flow
        GET /auth/callback - Handle OAuth callback
        GET /auth/logout - Logout user
        GET /auth/me - Get current user info
    """
    
    def __init__(
        self,
        issuer: str = OIDC_ISSUER,
        client_id: str = OIDC_CLIENT_ID,
        client_secret: str = OIDC_CLIENT_SECRET,
        redirect_uri: str = OIDC_REDIRECT_URI,
    ):
        self.issuer = issuer.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.session_manager = SessionManager()
        self._config: Optional[OIDCConfig] = None
    
    async def get_oidc_config(self) -> OIDCConfig:
        """Fetch OIDC configuration from Zitadel."""
        if self._config is not None:
            return self._config
        
        well_known_url = f"{self.issuer}/.well-known/openid-configuration"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(well_known_url)
            resp.raise_for_status()
            config_data = resp.json()
        
        self._config = OIDCConfig(**config_data)
        return self._config
    
    def add_routes(self, app: FastAPI) -> None:
        """Add authentication routes to FastAPI app."""
        
        @app.get("/auth/login")
        async def login(request: Request, redirect: Optional[str] = None):
            """Start OAuth2 authorization code flow."""
            config = await self.get_oidc_config()
            
            # Generate state for CSRF protection
            state = secrets.token_urlsafe(32)
            
            # Build authorization URL
            params = {
                "response_type": "code",
                "client_id": self.client_id,
                "redirect_uri": self.redirect_uri,
                "scope": "openid email profile",
                "state": state,
            }
            
            # Store state in session for validation
            request.session["oauth_state"] = state
            request.session["oauth_redirect"] = redirect
            
            auth_url = f"{config.authorization_endpoint}?{urllib.parse.urlencode(params)}"
            return RedirectResponse(url=auth_url)
        
        @app.get("/auth/callback")
        async def callback(request: Request, code: str, state: str):
            """Handle OAuth2 callback from Zitadel."""
            # Validate state
            expected_state = request.session.pop("oauth_state", None)
            redirect = request.session.pop("oauth_redirect", "/")
            
            if state != expected_state:
                raise HTTPException(status_code=400, detail="Invalid state")
            
            config = await self.get_oidc_config()
            
            # Exchange code for tokens
            async with httpx.AsyncClient(timeout=10.0) as client:
                token_resp = await client.post(
                    config.token_endpoint,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": self.redirect_uri,
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )
                token_resp.raise_for_status()
                token_data = token_resp.json()
            
            # Create session
            response = RedirectResponse(url=redirect)
            await self.session_manager.create_session(
                response=response,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                expires_in=token_data.get("expires_in", 3600),
            )
            
            return response
        
        @app.get("/auth/logout")
        async def logout(request: Request):
            """Logout user and redirect to Zitadel logout."""
            config = await self.get_oidc_config()
            
            # Destroy local session
            response = RedirectResponse(url="/")
            await self.session_manager.destroy_session(response)
            
            # Build Zitadel logout URL
            logout_url = f"{config.end_session_endpoint}?post_logout_redirect_uri={urllib.parse.quote('/')}"
            return RedirectResponse(url=logout_url)
        
        @app.get("/auth/me")
        async def get_me(request: Request):
            """Get current user info."""
            session = await self.session_manager.get_session(request)
            
            if session is None:
                return JSONResponse(
                    status_code=401,
                    content={"error": "Not authenticated"}
                )
            
            return JSONResponse(content={
                "user_id": session.get("user_id"),
                "email": session.get("email"),
            })
