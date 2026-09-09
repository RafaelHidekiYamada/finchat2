from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User, UserType

bearer = HTTPBearer(auto_error=False, description="Faça login e cole somente o access_token retornado.")
Db = Annotated[Session, Depends(get_db)]


def get_current_user(db: Db, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    try:
        if credentials is None:
            raise ValueError("Token ausente")
        user = db.get(User, decode_access_token(credentials.credentials))
    except (jwt.InvalidTokenError, ValueError, TypeError):
        raise AppError(401, "UNAUTHENTICATED", "Token ausente, inválido ou expirado.") from None
    if user is None or not user.is_active:
        raise AppError(401, "UNAUTHENTICATED", "Usuário indisponível ou inativo.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_company(user: User) -> None:
    if user.document_type != UserType.CNPJ:
        raise AppError(403, "FORBIDDEN", "Funcionalidade disponível somente para CNPJ.")
