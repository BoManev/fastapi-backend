from datetime import datetime, timedelta
from typing import Annotated
import uuid
from fastapi import Depends
from fastapi.security import (
    OAuth2PasswordBearer,
    OAuth2PasswordRequestForm,
    SecurityScopes,
)
from jose import JWTError, jwt
from api.core.db import SessionDB
from api.core.utils import verify_password
from api.config import Config, SessionConfig, get_config
from api.core.error import APIError
from pydantic import BaseModel, validator, ValidationError

from api.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/token",
    scopes={
        "contractor": "Contractor access",
        "homeowner": "Homeowner access",
    },
)
SessionToken = Annotated[str, Depends(oauth2_scheme)]


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: uuid.UUID
    email: str
    scopes: list[str] = []

    @validator("id")
    def validate_id(cls, value):
        if isinstance(value, uuid.UUID):
            return value
        if isinstance(value, str):
            if not value.startswith("urn:uuid:"):
                raise ValueError("ID must start with 'urn:uuid:'")
        return value

    @staticmethod
    def decode(token: str):
        config = get_config()
        payload = jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGO])
        email = payload.get("sub", None)
        id = payload.get("id", None)
        scope = payload.get("scopes", "")
        return TokenData(email=email, id=uuid.UUID(id), scopes=scope.split())


def create_access_token(
    data: dict,
    config: Config,
):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(seconds=config.JWT_TOKEN_EXPIRE_SECONDS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGO)


def validate_token_scopes(
    security_scopes: SecurityScopes,
    token: SessionToken,
    config: SessionConfig,
    db: SessionDB,
) -> User:
    if security_scopes.scopes:
        auth_header = f'Bearer scope="{security_scopes.scope_str}'
    else:
        auth_header = "Bearer"
    try:
        token_data = TokenData.decode(token)
    except (JWTError, ValidationError) as e:
        print(f"JWT error: {e}")
        raise APIError.TokenException(auth_header)

    user = User.by_email(token_data.email, db)
    if user is None:
        raise APIError.TokenException(auth_header)
    if user.id != token_data.id:
        raise APIError.TokenException(auth_header)
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise APIError.TokenException(auth_header)
        elif UserRole(scope) != user.role:
            raise APIError.TokenException(auth_header)
    return user


def validate_user_login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: SessionDB):
    user = User.by_email(form_data.username, db)
    if user is None:
        raise APIError.CredentialsException
    if not verify_password(form_data.password, user.password):
        raise APIError.CredentialsException
    if len(form_data.scopes) != 1:
        raise APIError.PermissionException
    if not UserRole(form_data.scopes[0]) == user.role:
        raise APIError.PermissionException
    return user
