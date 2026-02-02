"""
Rotas Admin - Gestão de Usuários SaaS
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import insert
from typing import List, Optional, Dict
from app.database import get_db
from app.models import Cliente, User, RoleType, user_tenants_association
from app.security import get_password_hash
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/admin", tags=["Admin - Usuários"])


class RestauranteComRole(BaseModel):
    tenant_id: int
    is_admin_restaurante: bool = False  # Se True, role=ADMIN; se False, role=LEITURA


class RestauranteVinculoResponse(BaseModel):
    """Restaurante vinculado com role"""
    tenant_id: int
    nome: str
    role: str  # 'admin' ou 'leitura'


class UsuarioCreate(BaseModel):
    cliente_id: Optional[int] = None  # Null para admins do SaaS
    nome: str
    email: EmailStr
    senha: str
    is_admin: bool = False  # Admin do SaaS
    restaurantes: Optional[List[RestauranteComRole]] = None  # Restaurantes com permissões


class ClienteResponse(BaseModel):
    id: int
    nome_empresa: str
    email: str

    class Config:
        from_attributes = True


class UsuarioResponse(BaseModel):
    id: int
    cliente_id: Optional[int] = None
    nome: str
    email: str
    is_admin: bool
    ativo: bool

    class Config:
        from_attributes = True


class UsuarioClienteResponse(BaseModel):
    """Usuário com lista de restaurantes e roles"""
    id: int
    cliente_id: Optional[int] = None
    nome: str
    email: str
    is_admin: bool
    ativo: bool
    restaurantes: List[RestauranteVinculoResponse] = []

    class Config:
        from_attributes = True


@router.post("/usuarios", response_model=UsuarioResponse)
def criar_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    """Cria novo usuário (pode ser admin ou funcionário)"""
    
    # Verificar se cliente existe (apenas se não for admin do SaaS)
    if not usuario.is_admin and not usuario.cliente_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="cliente_id é obrigatório para usuários não-admin"
        )
    
    if usuario.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == usuario.cliente_id).first()
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )
    
    # Verificar se email já existe
    existente = db.query(User).filter(User.email == usuario.email).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )
    
    novo_usuario = User(
        cliente_id=usuario.cliente_id,
        nome=usuario.nome,
        email=usuario.email,
        senha_hash=get_password_hash(usuario.senha),
        is_admin=usuario.is_admin,
        ativo=True
    )
    db.add(novo_usuario)
    db.flush()
    
    # Vincular aos restaurantes com permissões
    if usuario.restaurantes:
        from app.models import Tenant
        
        for resto in usuario.restaurantes:
            # Verificar se restaurante pertence ao cliente
            tenant = db.query(Tenant).filter(
                Tenant.id == resto.tenant_id,
                Tenant.cliente_id == usuario.cliente_id
            ).first()
            
            if not tenant:
                continue
            
            # Determinar role
            role = RoleType.ADMIN if resto.is_admin_restaurante else RoleType.LEITURA
            
            # Inserir associação com role
            db.execute(
                insert(user_tenants_association).values(
                    user_id=novo_usuario.id,
                    tenant_id=resto.tenant_id,
                    role=role
                )
            )
    
    db.commit()
    db.refresh(novo_usuario)
    
    return novo_usuario


@router.get("/usuarios", response_model=List[UsuarioClienteResponse])
def listar_usuarios(db: Session = Depends(get_db)):
    """Lista todos os usuários do sistema"""
    usuarios = db.query(User).all()
    return usuarios


@router.get("/usuarios/{user_id}")
def obter_usuario(user_id: int, db: Session = Depends(get_db)):
    """Obtém usuário específico com restaurantes e roles"""
    from sqlalchemy import select
    from app.models import Tenant
    
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Buscar restaurantes com roles
    query = select(
        user_tenants_association.c.tenant_id,
        user_tenants_association.c.role,
        Tenant.nome
    ).join(
        Tenant, Tenant.id == user_tenants_association.c.tenant_id
    ).where(
        user_tenants_association.c.user_id == user_id
    )
    
    resultados = db.execute(query).all()
    
    restaurantes = [
        {
            "tenant_id": r.tenant_id,
            "nome": r.nome,
            "role": r.role.value if r.role else "leitura"
        }
        for r in resultados
    ]
    
    return {
        "id": usuario.id,
        "cliente_id": usuario.cliente_id,
        "nome": usuario.nome,
        "email": usuario.email,
        "is_admin": usuario.is_admin,
        "ativo": usuario.ativo,
        "restaurantes": restaurantes
    }


@router.get("/usuarios/{user_id}/tenants")
def obter_tenants_usuario(user_id: int, db: Session = Depends(get_db)):
    """Obtém apenas os restaurantes vinculados ao usuário com suas permissões"""
    from sqlalchemy import select
    from app.models import Tenant
    
    # Buscar restaurantes com roles
    query = select(
        user_tenants_association.c.tenant_id,
        user_tenants_association.c.role
    ).where(
        user_tenants_association.c.user_id == user_id
    )
    
    resultados = db.execute(query).all()
    
    tenants = [
        {
            "tenant_id": r.tenant_id,
            "is_admin_restaurante": r.role == RoleType.ADMIN
        }
        for r in resultados
    ]
    
    return tenants


@router.put("/usuarios/{user_id}", response_model=UsuarioResponse)
def atualizar_usuario(user_id: int, dados: dict, db: Session = Depends(get_db)):
    """Atualiza dados de usuário"""
    from sqlalchemy import delete
    from app.models import Tenant
    
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Processar restaurantes separadamente se enviados
    restaurantes_data = dados.pop('restaurantes', None)
    
    # Atualizar senha se fornecida
    if 'senha' in dados and dados['senha']:
        dados['senha_hash'] = get_password_hash(dados.pop('senha'))
    elif 'senha' in dados:
        dados.pop('senha')
    
    # Atualizar campos básicos
    for campo, valor in dados.items():
        if hasattr(usuario, campo):
            setattr(usuario, campo, valor)
    
    # Atualizar vínculos com restaurantes e roles
    if restaurantes_data is not None:
        # Remover todas as associações antigas
        db.execute(
            delete(user_tenants_association).where(
                user_tenants_association.c.user_id == user_id
            )
        )
        
        # Adicionar novas associações
        for resto_data in restaurantes_data:
            # Aceitar tanto dict quanto int (retrocompatibilidade)
            if isinstance(resto_data, dict):
                tenant_id = resto_data.get('tenant_id')
                is_admin_resto = resto_data.get('is_admin_restaurante', False)
            else:
                tenant_id = resto_data
                is_admin_resto = False
            
            # Verificar se restaurante pertence ao cliente
            tenant = db.query(Tenant).filter(
                Tenant.id == tenant_id,
                Tenant.cliente_id == usuario.cliente_id
            ).first()
            
            if not tenant:
                continue
            
            # Determinar role
            role = RoleType.ADMIN if is_admin_resto else RoleType.LEITURA
            
            # Inserir associação
            db.execute(
                insert(user_tenants_association).values(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    role=role
                )
            )
    
    db.commit()
    db.refresh(usuario)
    return usuario


@router.delete("/usuarios/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_usuario(user_id: int, db: Session = Depends(get_db)):
    """Deleta usuário"""
    # Não permitir deletar admin principal (id=1)
    if user_id == 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Não é possível deletar usuário admin principal"
        )
    
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    db.delete(usuario)
    db.commit()
