"""ZitadelUserAuth - Custom OIDC authentication for Spider-Builder.

Integrates OpenHands OSS with Zitadel OIDC via kgateway OAuth2 filter.
"""

import os
from dataclasses import dataclass, field
from typing import Any

from fastapi import Request
from pydantic import SecretStr

from openhands.server.user_auth.user_auth import UserAuth, AuthType
from openhands.storage.data_models.settings import Settings
from openhands.storage.data_models.user_secrets import UserSecrets
from openhands.storage.settings.settings_store import SettingsStore
from openhands.storage.secrets.secrets_store import SecretsStore
from openhands.integrations.provider import PROVIDER_TOKEN_TYPE

from .kgateway_middleware import get_oidc_user_id, get_oidc_user_email, get_oidc_user


@dataclass
class ZitadelUserAuth(UserAuth):
    """Custom OIDC authentication via Zitadel (through kgateway)."""
    
    _user_id: str | None = None
    _email: str | None = None
    _name: str | None = None
    _settings: Settings | None = None
    _settings_store: SettingsStore | None = None
    _secrets_store: SecretsStore | None = None
    _secrets: UserSecrets | None = None
    
    FILE_STORE_PATH: str = field(default_factory=lambda: os.getenv("FILE_STORE_PATH", "/.openhands"))
    
    async def get_user_id(self) -> str | None:
        return self._user_id
    
    async def get_user_email(self) -> str | None:
        return self._email
    
    async def get_access_token(self) -> SecretStr | None:
        return None
    
    async def get_provider_tokens(self) -> PROVIDER_TOKEN_TYPE | None:
        """Load provider tokens from secrets store."""
        secrets = await self.get_secrets()
        if secrets and secrets.provider_tokens:
            return secrets.provider_tokens
        return None
    
    async def get_user_settings_store(self) -> SettingsStore:
        from openhands.server import shared
        if self._settings_store:
            return self._settings_store
        
        user_id = await self.get_user_id()
        store_path = os.path.join(self.FILE_STORE_PATH, user_id) if user_id else self.FILE_STORE_PATH
        
        self._settings_store = await shared.SettingsStoreImpl.get_instance(
            shared.config, user_id, store_path=store_path
        )
        return self._settings_store
    
    async def get_secrets_store(self) -> SecretsStore:
        from openhands.server import shared
        if self._secrets_store:
            return self._secrets_store
        
        user_id = await self.get_user_id()
        store_path = os.path.join(self.FILE_STORE_PATH, user_id) if user_id else self.FILE_STORE_PATH
        
        self._secrets_store = await shared.SecretsStoreImpl.get_instance(
            shared.config, user_id, store_path=store_path
        )
        return self._secrets_store
    
    async def get_secrets(self) -> UserSecrets | None:
        if self._secrets:
            return self._secrets
        store = await self.get_secrets_store()
        self._secrets = await store.load()
        return self._secrets
    
    async def get_user_secrets(self) -> UserSecrets | None:
        return await self.get_secrets()
    
    async def get_mcp_api_key(self) -> str | None:
        return None
    
    def get_auth_type(self) -> AuthType | None:
        return AuthType.COOKIE
    
    @classmethod
    async def get_instance(cls, request: Request) -> "ZitadelUserAuth":
        instance = cls()
        
        user_id = get_oidc_user_id(request)
        user_email = get_oidc_user_email(request)
        user = get_oidc_user(request)
        
        if user_id:
            instance._user_id = user_id
            instance._email = user_email
            instance._name = user.get("name") if user else None
        
        return instance
    
    @classmethod
    async def get_for_user(cls, user_id: str) -> "ZitadelUserAuth":
        instance = cls()
        instance._user_id = user_id
        return instance
