"""Session Manager for Spider-Builder OIDC authentication.

Simplified version without itsdangerous dependency.
Uses base64 encoding for session data.
"""

import os
import time
import base64
import json
from dataclasses import dataclass
from typing import Any

from fastapi import Request, Response

# Session cookie configuration
SESSION_COOKIE_NAME = "spider_builder_session"
SESSION_MAX_AGE = 86400 * 7  # 7 days
JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SESSION_SECRET", "change-me-in-production"))


@dataclass
class SessionManager:
    """Manages user sessions via secure cookies."""
    
    cookie_name: str = SESSION_COOKIE_NAME
    max_age: int = SESSION_MAX_AGE
    secret_key: str = JWT_SECRET
    
    def _encode_session(self, data: dict) -> str:
        """Encode session data to base64."""
        json_str = json.dumps(data)
        return base64.urlsafe_b64encode(json_str.encode()).decode()
    
    def _decode_session(self, encoded: str) -> dict | None:
        """Decode session data from base64."""
        try:
            json_str = base64.urlsafe_b64decode(encoded.encode()).decode()
            return json.loads(json_str)
        except Exception:
            return None
    
    async def create_session(
        self,
        response: Response,
        user_id: str,
        email: str | None = None,
        name: str | None = None,
    ) -> None:
        """Create a new session and set cookie."""
        session_data = {
            "user_id": user_id,
            "email": email,
            "name": name,
            "created_at": int(time.time()),
        }
        
        serialized = self._encode_session(session_data)
        
        response.set_cookie(
            key=self.cookie_name,
            value=serialized,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=self.max_age,
        )
    
    async def get_session(self, request: Request) -> dict[str, Any] | None:
        """Get session data from cookie."""
        cookie_value = request.cookies.get(self.cookie_name)
        if not cookie_value:
            return None
        
        session_data = self._decode_session(cookie_value)
        if session_data is None:
            return None
        
        # Check if expired
        created_at = session_data.get("created_at", 0)
        if time.time() - created_at > self.max_age:
            return None
        
        return session_data
    
    async def destroy_session(self, response: Response) -> None:
        """Destroy session by clearing cookie."""
        response.delete_cookie(
            key=self.cookie_name,
            httponly=True,
            secure=True,
            samesite="lax",
        )
