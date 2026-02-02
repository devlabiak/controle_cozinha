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
    from sqlalchemy.orm import joinedload
    
    # Busca usuário pelo email com restaurantes carregados
    user = db.query(User).options(joinedload(User.tenants)).filter(User.email == credentials.email).first()
    
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
    
    # Verificar se o cliente (empresa) está ativo
    if user.cliente_id:
        from app.models import Cliente
        cliente = db.query(Cliente).filter(Cliente.id == user.cliente_id).first()
        if cliente and not cliente.ativo:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Empresa bloqueada. Entre em contato com o suporte."
            )
    
    # Verificar se usuário não-admin tem pelo menos um restaurante ativo
    if not user.is_admin and user.tenants:
        restaurantes_ativos = [t for t in user.tenants if t.ativo]
        if not restaurantes_ativos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Todos os restaurantes estão bloqueados. Entre em contato com o suporte."
            )
    
    # Para usuários admin, não tem tenant_id fixo
    # Para usuários de cliente, retorna os tenants que tem acesso (somente os ativos)
    tenant_ids = [t.id for t in user.tenants if t.ativo] if user.tenants else []
    restaurantes = [
        {
            "id": t.id,
            "nome": t.nome,
            "slug": t.slug
        }
        for t in user.tenants if t.ativo
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


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Retorna informações do usuário logado com seus restaurantes e roles"""
    from app.database import SessionLocal
    from app.models import user_tenants_association
    from sqlalchemy import select
    
    # Cria sessão própria
    db = SessionLocal()
    try:
        # Busca o usuário novamente para garantir que temos os relacionamentos carregados
        user = db.query(User).filter(User.id == current_user.id).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        # Monta lista de restaurantes com roles (incluindo bloqueados)
        restaurantes = []
        for tenant in user.tenants:
            # Busca o role na tabela de associação
            stmt = select(user_tenants_association).where(
                user_tenants_association.c.user_id == user.id,
                user_tenants_association.c.tenant_id == tenant.id
            )
            result = db.execute(stmt).first()
            
            restaurantes.append({
                "id": tenant.id,
                "nome": tenant.nome,
                "slug": tenant.slug,
                "ativo": tenant.ativo,
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
    finally:
        db.close()

