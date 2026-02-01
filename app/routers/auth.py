from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Tenant
from app.schemas import LoginRequest, Token
from app.security import verify_password, create_access_token, get_current_user
from datetime import timedelta
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])


@router.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Endpoint de login.
    Aceita email e senha, retorna token JWT e lista de restaurantes disponíveis.
    """
    # Busca usuário pelo email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.senha, user.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )
    
    # Para usuários admin, não tem tenant_id fixo
    # Para usuários de cliente, retorna os tenants que tem acesso
    tenant_ids = [t.id for t in user.tenants] if user.tenants else []
    restaurantes = [
        {
            "id": t.id,
            "nome": t.nome,
            "slug": t.slug
        }
        for t in user.tenants
    ] if user.tenants else []
    
    # Cria token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "cliente_id": user.cliente_id,
            "tenant_ids": tenant_ids,  # Múltiplos tenants
            "is_admin": user.is_admin,
        },
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "is_admin": user.is_admin,
            "cliente_id": user.cliente_id,
            "restaurantes": restaurantes
        }
    }


@router.get("/me", response_model=None)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> dict:
    """Retorna informações do usuário logado com seus restaurantes e roles"""
    # Busca o usuário novamente para garantir que temos os relacionamentos carregados
    user = db.query(User).filter(User.id == current_user.id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Monta lista de restaurantes com roles
    restaurantes = []
    for tenant in user.tenants:
        # Busca o role na tabela de associação
        from app.models import user_tenants_association
        from sqlalchemy import select
        
        stmt = select(user_tenants_association).where(
            user_tenants_association.c.user_id == user.id,
            user_tenants_association.c.tenant_id == tenant.id
        )
        result = db.execute(stmt).first()
        
        restaurantes.append({
            "id": tenant.id,
            "nome": tenant.nome,
            "slug": tenant.slug,
            "role": result.role if result else None
        })
    
    return {
        "id": user.id,
        "nome": user.nome,
        "email": user.email,
        "cliente_id": user.cliente_id,
        "restaurantes": restaurantes,
        "is_admin": user.is_admin
    }

