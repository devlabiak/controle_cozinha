from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import TokenData

# Importa funções de security.py para evitar duplicação
from app.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    verify_token
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Obtém usuário autenticado pelo token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = verify_token(token)
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        
        if email is None or user_id is None:
            raise credentials_exception
            
    except HTTPException:
        raise credentials_exception
    
    from sqlalchemy.orm import joinedload
    
    user = db.query(User).options(joinedload(User.tenants)).filter(
        User.id == user_id, 
        User.email == email
    ).first()
    
    if user is None or not user.ativo:
        raise credentials_exception
    
    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Verifica se o usuário é admin do SaaS"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: requer privilégios de administrador"
        )
    return current_user
