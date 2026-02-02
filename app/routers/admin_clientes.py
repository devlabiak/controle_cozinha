"""
Rotas Admin - Clientes e Restaurantes
"""

from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import Cliente, Tenant
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/api/admin", tags=["Admin - Clientes/Restaurantes"])


# ==================== SCHEMAS ====================

class ClienteCreate(BaseModel):
    nome_empresa: str
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    cnpj: Optional[str] = None
    endereco: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None


class ClienteResponse(BaseModel):
    id: int
    nome_empresa: str
    email: str
    telefone: Optional[str] = None
    cnpj: Optional[str] = None
    ativo: bool

    class Config:
        from_attributes = True


class RestauranteCreate(BaseModel):
    cliente_id: int
    nome: str
    slug: str
    email: Optional[str] = None
    telefone: Optional[str] = None
    cnpj: Optional[str] = None
    endereco: Optional[str] = None


class RestauranteResponse(BaseModel):
    id: int
    cliente_id: int
    nome: str
    slug: str
    email: str
    ativo: bool

    class Config:
        from_attributes = True


# ==================== CLIENTES ====================

@router.post("/clientes", response_model=ClienteResponse)
def criar_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    """Cria novo cliente"""
    
    existente = db.query(Cliente).filter(Cliente.email == cliente.email).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )
    
    novo_cliente = Cliente(**cliente.dict())
    db.add(novo_cliente)
    db.commit()
    db.refresh(novo_cliente)
    
    return novo_cliente


@router.get("/clientes", response_model=List[ClienteResponse])
def listar_clientes(db: Session = Depends(get_db)):
    """Lista todos os clientes (ativos e bloqueados)"""
    clientes = db.query(Cliente).order_by(Cliente.ativo.desc(), Cliente.nome_empresa).all()
    return clientes


@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
def obter_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Obtém cliente específico"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    return cliente


@router.put("/clientes/{cliente_id}", response_model=ClienteResponse)
def atualizar_cliente(cliente_id: int, dados: ClienteCreate, db: Session = Depends(get_db)):
    """Atualiza cliente"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    for key, value in dados.dict().items():
        setattr(cliente, key, value)
    
    db.commit()
    db.refresh(cliente)
    return cliente


@router.delete("/clientes/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Deleta cliente e suas dependências (via CASCADE)"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    db.delete(cliente)
    db.commit()


@router.patch("/clientes/{cliente_id}/toggle-status")
def toggle_status_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Bloqueia ou desbloqueia uma empresa"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    cliente.ativo = not cliente.ativo
    db.commit()
    db.refresh(cliente)
    
    return {
        "id": cliente.id,
        "nome_empresa": cliente.nome_empresa,
        "ativo": cliente.ativo,
        "message": "Empresa bloqueada" if not cliente.ativo else "Empresa desbloqueada"
    }


# ==================== RESTAURANTES ====================

@router.post("/restaurantes", response_model=RestauranteResponse)
def criar_restaurante(restaurante: RestauranteCreate, db: Session = Depends(get_db)):
    """Cria novo restaurante"""
    
    cliente = db.query(Cliente).filter(Cliente.id == restaurante.cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    # Validar slug
    restaurante.slug = restaurante.slug.strip().lower()
    slug_existente = db.query(Tenant).filter(Tenant.slug == restaurante.slug).first()
    if slug_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slug (URL) já cadastrado"
        )

    # Validar email
    restaurante.email = restaurante.email.strip().lower()
    email_existente = db.query(Tenant).filter(Tenant.email == restaurante.email).first()
    if email_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
        )
    
    novo_restaurante = Tenant(**restaurante.dict())
    db.add(novo_restaurante)
    db.commit()
    db.refresh(novo_restaurante)
    
    return novo_restaurante


@router.get("/restaurantes", response_model=List[RestauranteResponse])
def listar_restaurantes(cliente_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Lista restaurantes (opcionalmente por cliente)"""
    query = db.query(Tenant).filter(Tenant.ativo == True)
    
    if cliente_id:
        query = query.filter(Tenant.cliente_id == cliente_id)
    
    return query.all()


@router.get("/clientes/{cliente_id}/restaurantes", response_model=List[RestauranteResponse])
def listar_restaurantes_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Lista restaurantes de um cliente"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    return cliente.tenants


@router.get("/restaurantes/{restaurante_id}", response_model=RestauranteResponse)
def obter_restaurante(restaurante_id: int, db: Session = Depends(get_db)):
    """Obtém restaurante específico"""
    restaurante = db.query(Tenant).filter(Tenant.id == restaurante_id).first()
    if not restaurante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurante não encontrado"
        )
    
    return restaurante


@router.put("/restaurantes/{restaurante_id}", response_model=RestauranteResponse)
def atualizar_restaurante(restaurante_id: int, dados: RestauranteCreate, db: Session = Depends(get_db)):
    """Atualiza restaurante"""
    restaurante = db.query(Tenant).filter(Tenant.id == restaurante_id).first()
    if not restaurante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurante não encontrado"
        )
    
    # Não permitir mudança de cliente
    dados_dict = dados.dict()
    dados_dict.pop("cliente_id", None)
    
    for key, value in dados_dict.items():
        setattr(restaurante, key, value)
    
    db.commit()
    db.refresh(restaurante)
    return restaurante


@router.delete("/restaurantes/{restaurante_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_restaurante(restaurante_id: int, db: Session = Depends(get_db)):
    """Deleta restaurante e suas dependências (via CASCADE)"""
    restaurante = db.query(Tenant).filter(Tenant.id == restaurante_id).first()
    if not restaurante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurante não encontrado"
        )
    
    db.delete(restaurante)
    db.commit()
