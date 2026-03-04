from openhands.agent_server.env_parser import from_env


class UserCreateAuthorization(BaseModel):
    success: bool
    error_detail: str | None = None


class UserCreateAuthorizer(ABC):
    """Class determining whether a user may be created."""

    @abstractmethod
    async def authorize_user_create(
        self, user_info: KeycloakUserInfo
    ) -> UserCreateAuthorization:
        """Determine whether the info given is permitted when creating an account."""


class UserCreateAuthorizerInjector(
    DiscriminatedUnionMixin, Injector[UserCreateAuthorizer], ABC
):
    pass


def depends_user_create_authorizer():
    injector: UserCreateAuthorizerInjector = from_env(
        UserCreateAuthorizerInjector, 'OH_USER_CREATE_AUTHORIZER'
    )
    if injector is None:
        from server.auth.default_user_create_authorizer import (
            DefaultUserCreateAuthorizerInjector,
        )

        injector = DefaultUserCreateAuthorizerInjector()
    return Depends(injector.depends)
