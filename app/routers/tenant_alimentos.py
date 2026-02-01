from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Alimento, User
from app.schemas import AlimentoCreate, AlimentoUpdate, AlimentoResponse
from app.auth import get_current_user
from app.middleware import get_tenant_id

router = APIRouter(prefix="/api/tenant/alimentos", tags=["Tenant - Gestão de Alimentos"])


@router.post("/", response_model=AlimentoResponse, status_code=status.HTTP_201_CREATED)
def create_alimento(
    alimento_data: AlimentoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria novo alimento no estoque"""
    tenant_id = get_tenant_id(request)
    
    # Verifica se o usuário pertence ao tenant
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    new_alimento = Alimento(
        tenant_id=tenant_id,
        **alimento_data.dict()
    )
    
    db.add(new_alimento)
    db.commit()
    db.refresh(new_alimento)
    
    return new_alimento


@router.get("/", response_model=List[AlimentoResponse])
def list_alimentos(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    categoria: str = None,
    subcategoria: str = None,
    tipo_conservacao: str = None,
    nome: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista todos os alimentos do restaurante"""
    tenant_id = get_tenant_id(request)
    
    # Verifica se o usuário pertence ao tenant
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    query = db.query(Alimento).filter(Alimento.tenant_id == tenant_id)
    
    if categoria:
        query = query.filter(Alimento.categoria == categoria)

    if subcategoria:
        query = query.filter(Alimento.subcategoria == subcategoria)

    if tipo_conservacao:
        query = query.filter(Alimento.tipo_conservacao == tipo_conservacao)

    if nome:
        query = query.filter(Alimento.nome.ilike(f"%{nome}%"))
    
    alimentos = query.offset(skip).limit(limit).all()
    return alimentos


@router.get("/estoque-baixo", response_model=List[AlimentoResponse])
def list_alimentos_estoque_baixo(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista alimentos com estoque abaixo do mínimo"""
    tenant_id = get_tenant_id(request)
    
    # Verifica se o usuário pertence ao tenant
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    alimentos = db.query(Alimento).filter(
        Alimento.tenant_id == tenant_id,
        Alimento.quantidade_estoque <= Alimento.quantidade_minima,
        Alimento.ativo == True
    ).all()
    
    return alimentos


@router.get("/{alimento_id}", response_model=AlimentoResponse)
def get_alimento(
    alimento_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém detalhes de um alimento específico"""
    tenant_id = get_tenant_id(request)
    
    # Verifica se o usuário pertence ao tenant
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    alimento = db.query(Alimento).filter(
        Alimento.id == alimento_id,
        Alimento.tenant_id == tenant_id
    ).first()
    
    if not alimento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alimento não encontrado"
        )
    
    return alimento


@router.put("/{alimento_id}", response_model=AlimentoResponse)
def update_alimento(
    alimento_id: int,
    alimento_data: AlimentoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualiza dados de um alimento"""
    tenant_id = get_tenant_id(request)
    
    # Verifica se o usuário pertence ao tenant
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    alimento = db.query(Alimento).filter(
        Alimento.id == alimento_id,
        Alimento.tenant_id == tenant_id
    ).first()
    
    if not alimento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alimento não encontrado"
        )
    
    # Atualiza apenas os campos fornecidos
    update_data = alimento_data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(alimento, field, value)
    
    db.commit()
    db.refresh(alimento)
    
    return alimento


@router.delete("/{alimento_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alimento(
    alimento_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deleta um alimento"""
    tenant_id = get_tenant_id(request)
    
    # Verifica se o usuário pertence ao tenant
    if current_user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    alimento = db.query(Alimento).filter(
        Alimento.id == alimento_id,
        Alimento.tenant_id == tenant_id
    ).first()
    
    if not alimento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alimento não encontrado"
        )
    
    db.delete(alimento)
    db.commit()
    
    return None
