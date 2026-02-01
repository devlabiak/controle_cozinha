"""
Rotas Admin - Gestão de Usuários SaaS
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Cliente, User
from app.security import get_password_hash
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/admin", tags=["Admin - Usuários"])


class UsuarioCreate(BaseModel):
    cliente_id: int
    nome: str
    email: EmailStr
    senha: str
    is_admin: bool = False


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
    """Usuário com lista de clientes associados"""
    id: int
    cliente_id: Optional[int] = None
    nome: str
    email: str
    is_admin: bool
    ativo: bool
    clientes_acesso: List[ClienteResponse] = []

    class Config:
        from_attributes = True


@router.post("/usuarios", response_model=UsuarioResponse)
def criar_usuario(usuario: UsuarioCreate, db: Session = Depends(get_db)):
    """Cria novo usuário (pode ser admin ou funcionário)"""
    
    # Verificar se cliente existe
    cliente = db.query(Cliente).filter(Cliente.id == usuario.cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    # Verificar se email já existe (dentro do mesmo cliente)
    existente = db.query(User).filter(
        User.email == usuario.email,
        User.cliente_id == usuario.cliente_id
    ).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado para este cliente"
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
    db.commit()
    db.refresh(novo_usuario)
    
    return novo_usuario


@router.get("/usuarios", response_model=List[UsuarioClienteResponse])
def listar_usuarios(db: Session = Depends(get_db)):
    """Lista todos os usuários do sistema"""
    usuarios = db.query(User).all()
    return usuarios


@router.get("/usuarios/{user_id}", response_model=UsuarioClienteResponse)
def obter_usuario(user_id: int, db: Session = Depends(get_db)):
    """Obtém usuário específico"""
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    return usuario


@router.put("/usuarios/{user_id}", response_model=UsuarioResponse)
def atualizar_usuario(user_id: int, dados: dict, db: Session = Depends(get_db)):
    """Atualiza dados de usuário"""
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Atualizar campos
    for campo, valor in dados.items():
        if valor is not None and hasattr(usuario, campo):
            setattr(usuario, campo, valor)
    
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
