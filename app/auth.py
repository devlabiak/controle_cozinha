from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import TokenData

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha está correta"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Gera hash da senha"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> User:
    """Obtém usuário autenticado pelo token"""
    from app.database import SessionLocal
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais inválidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        
        print(f"🔍 Token decodificado - user_id: {user_id}, email: {email}")
        
        if email is None or user_id is None:
            print(f"❌ user_id ou email é None")
            raise credentials_exception
            
    except JWTError as e:
        print(f"❌ Erro JWT: {e}")
        raise credentials_exception
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.email == email).first()
        
        print(f"🔍 Usuário encontrado no banco: {user is not None}")
        if user:
            print(f"🔍 Usuário ativo: {user.ativo}")
        
        if user is None or not user.ativo:
            print(f"❌ Usuário None ou inativo")
            raise credentials_exception
            
        return user
    finally:
        db.close()


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Verifica se o usuário é admin do SaaS"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: requer privilégios de administrador"
        )
    return current_user


def get_current_tenant_admin(current_user: User = Depends(get_current_user)) -> User:
    """Verifica se o usuário é admin do restaurante"""
    if not current_user.is_tenant_admin and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: requer privilégios de administrador do restaurante"
        )
    return current_user
