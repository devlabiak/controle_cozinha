"""
Rotas de Gestão de Usuários do Restaurante (apenas para admins do restaurante)
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import Response as FastAPIResponse
from sqlalchemy.orm import Session
from sqlalchemy import select, insert, update, delete
from typing import List, Optional
from app.database import get_db
from app.models import User, Tenant, RoleType, user_tenants_association
from app.security import get_password_hash, get_current_user
from app.services.audit import registrar_auditoria
from app.rate_limit import limiter
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/tenant", tags=["Tenant - Usuários"])


# ==================== SCHEMAS ====================
class UsuarioTenantCreate(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    is_admin_restaurante: bool = False  # Se True, role=ADMIN; se False, role=LEITURA


class UsuarioTenantUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    senha: Optional[str] = None
    is_admin_restaurante: Optional[bool] = None


class UsuarioTenantResponse(BaseModel):
    id: int
    nome: str
    email: str
    ativo: bool
    is_admin_restaurante: bool
    
    class Config:
        from_attributes = True


# ==================== HELPER ====================
def verificar_admin_restaurante(tenant_id: int, user: User, db: Session):
    """Verifica se o usuário tem permissão de admin no restaurante"""
    if user.is_admin:
        return True
    
    stmt = select(user_tenants_association).where(
        user_tenants_association.c.user_id == user.id,
        user_tenants_association.c.tenant_id == tenant_id
    )
    result = db.execute(stmt).first()
    
    if not result or result.role != RoleType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem gerenciar usuários"
        )
    return True


# ==================== ROTAS ====================
@router.get("/{tenant_id}/usuarios", response_model=List[UsuarioTenantResponse])
def listar_usuarios(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista todos os usuários do restaurante (apenas admins)"""
    verificar_admin_restaurante(tenant_id, current_user, db)
    
    # Busca o tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    
    # Lista usuários vinculados ao tenant
    usuarios = []
    for user in tenant.users:
        # Busca o role
        stmt = select(user_tenants_association).where(
            user_tenants_association.c.user_id == user.id,
            user_tenants_association.c.tenant_id == tenant_id
        )
        result = db.execute(stmt).first()
        
        usuarios.append({
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "ativo": user.ativo,
            "is_admin_restaurante": result.role == RoleType.ADMIN if result else False
        })
    
    return usuarios


@router.post("/{tenant_id}/usuarios", response_model=UsuarioTenantResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("50/minute")
def criar_usuario(
    tenant_id: int,
    dados: UsuarioTenantCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria novo usuário vinculado ao restaurante (apenas admins)"""
    verificar_admin_restaurante(tenant_id, current_user, db)
    
    # Busca o tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Restaurante não encontrado")
    
    # Verifica se email já existe
    user_existente = db.query(User).filter(User.email == dados.email).first()
    if user_existente:
        raise HTTPException(
            status_code=400,
            detail="Email já cadastrado no sistema"
        )
    
    # Cria o usuário
    novo_user = User(
        cliente_id=tenant.cliente_id,
        nome=dados.nome,
        email=dados.email,
        senha_hash=get_password_hash(dados.senha),
        is_admin=False,
        ativo=True
    )
    
    db.add(novo_user)
    db.flush()  # Para obter o ID
    
    # Vincula ao tenant com role apropriado
    role = RoleType.ADMIN if dados.is_admin_restaurante else RoleType.LEITURA
    stmt = insert(user_tenants_association).values(
        user_id=novo_user.id,
        tenant_id=tenant_id,
        role=role
    )
    db.execute(stmt)
    registrar_auditoria(
        db,
        user_id=current_user.id,
        tenant_id=tenant_id,
        action="CREATE",
        resource="tenant_users",
        resource_id=novo_user.id,
        details=f"Usuário {novo_user.email} criado com role {role.value}",
        request=request,
    )
    db.commit()
    db.refresh(novo_user)
    
    return {
        "id": novo_user.id,
        "nome": novo_user.nome,
        "email": novo_user.email,
        "ativo": novo_user.ativo,
        "is_admin_restaurante": dados.is_admin_restaurante
    }


@router.put("/{tenant_id}/usuarios/{usuario_id}", response_model=UsuarioTenantResponse)
def atualizar_usuario(
    tenant_id: int,
    usuario_id: int,
    dados: UsuarioTenantUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualiza usuário do restaurante (apenas admins)"""
    verificar_admin_restaurante(tenant_id, current_user, db)
    
    # Busca o usuário
    user = db.query(User).filter(User.id == usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    
    # Verifica se usuário está vinculado ao tenant
    stmt = select(user_tenants_association).where(
        user_tenants_association.c.user_id == usuario_id,
        user_tenants_association.c.tenant_id == tenant_id
    )
    vinculo = db.execute(stmt).first()
    
    if not vinculo:
        raise HTTPException(
            status_code=404,
            detail="Usuário não vinculado a este restaurante"
        )
    
    # Atualiza campos
    if dados.nome is not None:
        user.nome = dados.nome
    
    if dados.email is not None:
        # Verifica se novo email já existe
        if dados.email != user.email:
            existente = db.query(User).filter(User.email == dados.email).first()
            if existente:
                raise HTTPException(status_code=400, detail="Email já cadastrado")
        user.email = dados.email
    
    if dados.senha is not None:
        user.senha_hash = get_password_hash(dados.senha)
    
    # Atualiza role se fornecido
    detalhes_alteracao = {}
    if dados.is_admin_restaurante is not None:
        novo_role = RoleType.ADMIN if dados.is_admin_restaurante else RoleType.LEITURA
        stmt = update(user_tenants_association).where(
            user_tenants_association.c.user_id == usuario_id,
            user_tenants_association.c.tenant_id == tenant_id
        ).values(role=novo_role)
        db.execute(stmt)
        detalhes_alteracao["novo_role"] = novo_role.value
    if dados.nome is not None:
        detalhes_alteracao["nome"] = dados.nome
    if dados.email is not None:
        detalhes_alteracao["email"] = dados.email
    if dados.senha is not None:
        detalhes_alteracao["senha_atualizada"] = True

    registrar_auditoria(
        db,
        user_id=current_user.id,
        tenant_id=tenant_id,
        action="UPDATE",
        resource="tenant_users",
        resource_id=usuario_id,
        details=f"Usuário {usuario_id} atualizado: {detalhes_alteracao or 'sem alterações'}",
        request=request,
    )
    db.commit()
    db.refresh(user)
    
    # Busca role atualizado
    stmt = select(user_tenants_association).where(
        user_tenants_association.c.user_id == usuario_id,
        user_tenants_association.c.tenant_id == tenant_id
    )
    result = db.execute(stmt).first()
    
    return {
        "id": user.id,
        "nome": user.nome,
        "email": user.email,
        "ativo": user.ativo,
        "is_admin_restaurante": result.role == RoleType.ADMIN if result else False
    }


@router.delete("/{tenant_id}/usuarios/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_usuario(
    tenant_id: int,
    usuario_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Remove vinculo do usuário com o restaurante (apenas admins)"""
    verificar_admin_restaurante(tenant_id, current_user, db)
    
    # Não permite remover a si mesmo
    if usuario_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Você não pode remover seu próprio acesso"
        )
    
    # Remove o vínculo
    stmt = delete(user_tenants_association).where(
        user_tenants_association.c.user_id == usuario_id,
        user_tenants_association.c.tenant_id == tenant_id
    )
    result = db.execute(stmt)
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Usuário não vinculado a este restaurante"
        )

    registrar_auditoria(
        db,
        user_id=current_user.id,
        tenant_id=tenant_id,
        action="DELETE",
        resource="tenant_users",
        resource_id=usuario_id,
        details=f"Usuário {usuario_id} desvinculado do restaurante",
        request=request,
    )
    db.commit()
    
    return FastAPIResponse(status_code=status.HTTP_204_NO_CONTENT)
