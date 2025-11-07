from typing import Annotated, Iterable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.api.routes.auth import decode_token
from app.config.config import ConfigDTO
from app.dependecies.stub import AppConfigStub, DatabaseRepositoryStub
from app.models import User
from app.repository.database.base import DatabaseRepository
from app.schemas.enums.user import UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class AuthenticateUser:
    """Dependency for authenticating users via JWT token."""

    required_role: UserRole | Iterable[UserRole] | None = None

    async def get_current_user(
        self,
        db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
        token: str = Depends(oauth2_scheme),
        config: ConfigDTO = Depends(AppConfigStub),
    ) -> User:
        credential_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        username = await decode_token(
            db_repo=db_repo,
            token=token,
            secret_key=config.jwt_token.secret_key,
            algorithm=config.jwt_token.algorithm,
        )

        user = await db_repo.user.get_current_user(username=username)

        if user is None:
            raise credential_exception

        if isinstance(self.required_role, Iterable) and user.role in self.required_role:
            return user

        if self.required_role and user.role != self.required_role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You don't have enough permissions")

        return user

    async def __call__(
        self,
        db_repo: Annotated[DatabaseRepository, Depends(DatabaseRepositoryStub)],
        token: str = Depends(oauth2_scheme),
        config: ConfigDTO = Depends(AppConfigStub),
    ):
        return await self.get_current_user(token=token, config=config, db_repo=db_repo)


class AuthenticateAdmin(AuthenticateUser):
    required_role = UserRole.admin


class AuthenticateLeadWebMaster(AuthenticateUser):
    required_role = (UserRole.admin, UserRole.lead_web_master)


class AuthenticateLeadMediaBuyer(AuthenticateUser):
    required_role = (UserRole.admin, UserRole.lead_media_buyer)


class AuthenticateMediaBuyer(AuthenticateUser):
    required_role = UserRole.media_buyer


class AuthenticateMediaBuyers(AuthenticateUser):
    required_role = (UserRole.media_buyer, UserRole.lead_media_buyer)


class AuthenticateMediaBuyerOrLead(AuthenticateUser):
    required_role = (UserRole.admin, UserRole.media_buyer, UserRole.lead_media_buyer)


class AuthenticateMediaBuyerLeadOrLeadDesigner(AuthenticateUser):
    required_role = (
        UserRole.admin,
        UserRole.media_buyer,
        UserRole.lead_media_buyer,
        UserRole.lead_designer,
    )


class AuthenticateDesignerOrLead(AuthenticateUser):
    required_role = (UserRole.admin, UserRole.lead_designer, UserRole.designer)


class AuthenticateLeadDesigner(AuthenticateUser):
    required_role = (UserRole.admin, UserRole.lead_designer)


class AuthenticatedDesignerTasksRoles(AuthenticateUser):
    required_role = (
        UserRole.media_buyer,
        UserRole.lead_media_buyer,
        UserRole.designer,
        UserRole.lead_designer,
        UserRole.admin,
    )


class AuthenticateWebMasterTasksRoles(AuthenticateUser):
    required_role = (
        UserRole.lead_media_buyer,
        UserRole.media_buyer,
        UserRole.web_master,
        UserRole.lead_web_master,
        UserRole.admin,
    )


class AuthenticateMainRoles(AuthenticateUser):
    required_role = (
        UserRole.lead_media_buyer,
        UserRole.lead_designer,
        UserRole.lead_web_master,
        UserRole.admin,
    )
