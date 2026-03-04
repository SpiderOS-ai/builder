#!/usr/bin/env python3
"""Custom entrypoint for Spider-Builder OpenHands server.

Patches OpenHands OSS to use OIDC authentication via kgateway.
"""

import os


def patch_openhands():
    """Apply OIDC patches to OpenHands before server starts."""
    
    print("[Spider-Builder] Applying OIDC patches...")
    
    # 1. Patch server config for custom UserAuth
    import openhands.server.shared as shared
    from openhands.server.config.server_config import ServerConfig
    
    class PatchedServerConfig(ServerConfig):
        user_auth_class: str = 'oidc_auth.zitadel_auth.ZitadelUserAuth'
    
    shared.server_config = PatchedServerConfig()
    print(f"[Spider-Builder] Set user_auth_class = {shared.server_config.user_auth_class}")
    
    # 2. Patch SettingsStore to use per-user paths
    import openhands.storage.settings.file_settings_store as settings_store
    from openhands.storage import get_file_store
    from pathlib import Path
    
    @classmethod
    async def patched_settings_get_instance(cls, config, user_id, store_path=None):
        if store_path is None:
            store_path = config.file_store_path
        
        Path(store_path).mkdir(parents=True, exist_ok=True)
        
        # Use the proper get_file_store function
        file_store = get_file_store(
            file_store_type='local',
            file_store_path=store_path,
        )
        return cls(file_store=file_store)
    
    settings_store.FileSettingsStore.get_instance = patched_settings_get_instance
    print("[Spider-Builder] Patched SettingsStore")
    
    # 3. Patch SecretsStore
    import openhands.storage.secrets.file_secrets_store as secrets_store
    
    @classmethod
    async def patched_secrets_get_instance(cls, config, user_id, store_path=None):
        if store_path is None:
            store_path = config.file_store_path
        
        Path(store_path).mkdir(parents=True, exist_ok=True)
        
        file_store = get_file_store(
            file_store_type='local',
            file_store_path=store_path,
        )
        return cls(file_store=file_store)
    
    secrets_store.FileSecretsStore.get_instance = patched_secrets_get_instance
    print("[Spider-Builder] Patched SecretsStore")
    
    # 4. Wrap app with OIDC middleware
    import openhands.server.listen as listen_module
    from oidc_auth.kgateway_middleware import KgatewayOIDCMiddleware
    
    listen_module.app = KgatewayOIDCMiddleware(listen_module.app)
    print("[Spider-Builder] Wrapped app with OIDC middleware")
    
    print("[Spider-Builder] All patches applied!")


if __name__ == "__main__":
    patch_openhands()
    print("[Spider-Builder] Starting server...")
    from openhands.server.__main__ import main
    main()
