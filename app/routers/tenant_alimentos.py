from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from app.database import get_db
from app.models import Alimento, User, MovimentacaoEstoque, TipoMovimentacao
from app.schemas import AlimentoCreate, AlimentoUpdate, AlimentoResponse
from app.auth import get_current_user
from app.middleware import get_tenant_id
from pydantic import BaseModel

router = APIRouter(prefix="/api/tenant", tags=["Tenant - Gestão de Alimentos"])


# ==================== SCHEMAS ====================
class MovimentacaoCreate(BaseModel):
    alimento_id: int
    tipo: str  # 'entrada', 'saida', 'ajuste'
    quantidade: float
    observacao: Optional[str] = None


class MovimentacaoResponse(BaseModel):
    id: int
    alimento_id: int
    alimento_nome: Optional[str]
    tipo: str
    quantidade: float
    quantidade_anterior: Optional[float]
    quantidade_nova: Optional[float]
    usuario_nome: Optional[str]
    observacao: Optional[str] = None
    data_hora: datetime

    class Config:
        orm_mode = True


@router.post("/{tenant_id}/alimentos", response_model=AlimentoResponse, status_code=status.HTTP_201_CREATED)
def create_alimento(
    tenant_id: int,
    alimento_data: AlimentoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria novo alimento no estoque"""
    # Verifica se o usuário tem acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
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


@router.get("/{tenant_id}/alimentos", response_model=List[AlimentoResponse])
def list_alimentos(
    tenant_id: int,
    skip: int = 0,
    limit: int = 100,
    categoria: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista todos os alimentos do restaurante"""
    # Verifica se o usuário tem acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    query = db.query(Alimento).filter(Alimento.tenant_id == tenant_id)
    
    if categoria:
        query = query.filter(Alimento.categoria == categoria)

    if search:
        query = query.filter(Alimento.nome.ilike(f"%{search}%"))
    
    alimentos = query.offset(skip).limit(limit).all()
    return alimentos


@router.get("/{tenant_id}/alimentos/{alimento_id}", response_model=AlimentoResponse)
def get_alimento(
    tenant_id: int,
    alimento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém detalhes de um alimento específico"""
    # Verifica se o usuário tem acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
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


@router.put("/{tenant_id}/alimentos/{alimento_id}", response_model=AlimentoResponse)
def update_alimento(
    tenant_id: int,
    alimento_id: int,
    alimento_data: AlimentoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualiza dados de um alimento"""
    # Verifica se o usuário tem acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
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


@router.delete("/{tenant_id}/alimentos/{alimento_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alimento(
    tenant_id: int,
    alimento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deleta um alimento"""
    # Verifica se o usuário tem acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
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


# ==================== MOVIMENTAÇÕES ====================
@router.post("/{tenant_id}/movimentacoes", status_code=status.HTTP_201_CREATED)
def criar_movimentacao(
    tenant_id: int,
    dados: MovimentacaoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registra uma movimentação de estoque"""
    # Verifica se o usuário tem acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Busca o alimento
    alimento = db.query(Alimento).filter(
        Alimento.id == dados.alimento_id,
        Alimento.tenant_id == tenant_id
    ).first()
    
    if not alimento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Produto não encontrado"
        )
    
    # Calcula nova quantidade
    quantidade_anterior = alimento.estoque_atual or 0
    
    if dados.tipo == 'entrada':
        quantidade_nova = quantidade_anterior + dados.quantidade
        tipo_enum = TipoMovimentacao.ENTRADA
    elif dados.tipo == 'saida':
        if quantidade_anterior < dados.quantidade:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Estoque insuficiente"
            )
        quantidade_nova = quantidade_anterior - dados.quantidade
        tipo_enum = TipoMovimentacao.SAIDA
    elif dados.tipo == 'ajuste':
        quantidade_nova = dados.quantidade
        tipo_enum = TipoMovimentacao.AJUSTE
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de movimentação inválido"
        )
    
    # Cria a movimentação
    movimentacao = MovimentacaoEstoque(
        tenant_id=tenant_id,
        alimento_id=dados.alimento_id,
        usuario_id=current_user.id,
        tipo=tipo_enum,
        quantidade=dados.quantidade,
        quantidade_anterior=quantidade_anterior,
        quantidade_nova=quantidade_nova,
        motivo=dados.observacao
    )
    
    # Atualiza o estoque do alimento
    alimento.estoque_atual = quantidade_nova
    
    db.add(movimentacao)
    db.commit()
    
    return {"message": "Movimentação registrada com sucesso"}


@router.get("/{tenant_id}/movimentacoes", response_model=List[MovimentacaoResponse])
def listar_movimentacoes(
    tenant_id: int,
    skip: int = 0,
    limit: int = 100,
    tipo: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista movimentações de estoque"""
    # Verifica se o usuário tem acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    query = db.query(
        MovimentacaoEstoque,
        Alimento.nome.label('alimento_nome'),
        User.nome.label('usuario_nome')
    ).join(
        Alimento, MovimentacaoEstoque.alimento_id == Alimento.id
    ).join(
        User, MovimentacaoEstoque.usuario_id == User.id
    ).filter(
        MovimentacaoEstoque.tenant_id == tenant_id
    )
    
    if tipo:
        if tipo == 'entrada':
            query = query.filter(MovimentacaoEstoque.tipo == TipoMovimentacao.ENTRADA)
        elif tipo == 'saida':
            query = query.filter(MovimentacaoEstoque.tipo == TipoMovimentacao.SAIDA)
        elif tipo == 'ajuste':
            query = query.filter(MovimentacaoEstoque.tipo == TipoMovimentacao.AJUSTE)
    
    if data_inicio:
        query = query.filter(MovimentacaoEstoque.created_at >= datetime.fromisoformat(data_inicio))
    
    if data_fim:
        query = query.filter(MovimentacaoEstoque.created_at <= datetime.fromisoformat(data_fim))
    
    query = query.order_by(desc(MovimentacaoEstoque.created_at))
    
    resultados = query.offset(skip).limit(limit).all()
    
    # Formata resposta
    movimentacoes = []
    for mov, alimento_nome, usuario_nome in resultados:
        movimentacoes.append({
            "id": mov.id,
            "alimento_id": mov.alimento_id,
            "alimento_nome": alimento_nome,
            "tipo": mov.tipo.value,
            "quantidade": mov.quantidade,
            "quantidade_anterior": mov.quantidade_anterior,
            "quantidade_nova": mov.quantidade_nova,
            "usuario_nome": usuario_nome,
            "observacao": mov.motivo,
            "data_hora": mov.created_at
        })
    
    return movimentacoes
