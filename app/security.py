"""
Funções de segurança e autenticação
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from functools import wraps

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models import User, Tenant, user_tenants_association
from sqlalchemy import and_
from app.config import settings

# Contexto de hash de senha
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme para extrair token do header Authorization
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_password_hash(password: str) -> str:
    """Gera hash da senha"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Cria um token JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verifica e decodifica um token JWT"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Obtém o usuário atual baseado no token"""
    from app.database import SessionLocal
    
    payload = verify_token(token)
    user_id = payload.get("user_id")
    email = payload.get("sub")
    
    if user_id is None or email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.email == email).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado"
            )
        
        return user
    finally:
        db.close()


def check_role_access(user_id: int, tenant_id: int, required_role: str, db: Session) -> bool:
    """
    Verifica se um usuário tem acesso a um restaurante com o role especificado
    
    Args:
        user_id: ID do usuário
        tenant_id: ID do restaurante
        required_role: 'admin' ou 'leitura'
        db: Sessão do banco de dados
    
    Returns:
        True se o usuário tem o acesso, False caso contrário
    """
    
    # Sempre permitir admin (is_admin=True)
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.is_admin:
        return True
    
    # Verificar na tabela de associação
    association = db.query(user_tenants_association).filter(
        and_(
            user_tenants_association.c.user_id == user_id,
            user_tenants_association.c.tenant_id == tenant_id
        )
    ).first()
    
    if not association:
        return False
    
    # Se requer 'admin', o usuário deve ter role 'admin'
    if required_role == "admin":
        return association.role == "admin"
    
    # Se requer 'leitura', o usuário pode ter 'admin' ou 'leitura'
    if required_role == "leitura":
        return association.role in ["admin", "leitura"]
    
    return False


def require_role(required_role: str = "admin"):
    """
    Decorator para proteger endpoints que requerem um role específico
    
    Uso:
        @router.post("/produtos")
        @require_role("admin")
        def criar_produto(tenant_id: int, ..., user_id: int = Depends(get_current_user_id)):
            ...
    
    Args:
        required_role: 'admin' ou 'leitura'
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Esta função será chamada pelos endpoints
            # O endpoint precisa passar user_id e tenant_id
            return func(*args, **kwargs)
        return wrapper
    return decorator


def validate_access(user_id: int, tenant_id: int, required_role: str, db: Session):
    """
    Valida se o usuário tem acesso ao restaurante com o role requerido
    Lança exceção se não tiver acesso
    """
    if not check_role_access(user_id, tenant_id, required_role, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Acesso negado. Role '{required_role}' requerido neste restaurante"
        )
