from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models import ProdutoLote, Alimento, User, PrintJob, StatusPrintJob
from app.schemas import ProdutoLoteCreate, ProdutoLoteResponse, AlertasLotesResponse
from app.auth import get_current_user
from app.middleware import get_tenant_id
import uuid
import json

router = APIRouter(prefix="/api/tenant/lotes", tags=["Tenant - Gestão de Lotes"])


def gerar_numero_lote(tenant_id: int, alimento_id: int) -> str:
    """Gera número único de lote"""
    data = datetime.now().strftime("%Y%m%d")
    return f"{tenant_id:03d}{alimento_id:04d}{data}{uuid.uuid4().hex[:4].upper()}"


def gerar_qr_code() -> str:
    """Gera código único para QR Code"""
    return f"LOT-{uuid.uuid4()}"


@router.post("/", response_model=ProdutoLoteResponse, status_code=status.HTTP_201_CREATED)
def create_lote(
    lote_data: ProdutoLoteCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria novo lote de produto e opcionalmente agenda impressão"""
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    # Verifica se alimento existe
    alimento = db.query(Alimento).filter(
        Alimento.id == lote_data.alimento_id,
        Alimento.tenant_id == tenant_id
    ).first()
    
    if not alimento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alimento não encontrado"
        )
    
    # Gera número de lote e QR code únicos
    lote_numero = lote_data.lote_numero or gerar_numero_lote(tenant_id, lote_data.alimento_id)
    qr_code = gerar_qr_code()

    quantidade_etiquetas = lote_data.quantidade_etiquetas or 1
    if quantidade_etiquetas < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Quantidade de etiquetas deve ser maior que zero"
        )
    
    # Cria o lote
    new_lote = ProdutoLote(
        tenant_id=tenant_id,
        alimento_id=lote_data.alimento_id,
        lote_numero=lote_numero,
        qr_code=qr_code,
        data_fabricacao=lote_data.data_fabricacao,
        data_validade=lote_data.data_validade,
        quantidade_produzida=lote_data.quantidade_produzida,
        quantidade_disponivel=lote_data.quantidade_produzida,
        unidade_medida=lote_data.unidade_medida,
        quantidade_etiquetas=quantidade_etiquetas,
        fabricante=lote_data.fabricante,
        sif=lote_data.sif,
        peso_liquido=lote_data.peso_liquido,
        ingredientes=lote_data.ingredientes,
        informacao_nutricional=lote_data.informacao_nutricional,
        modo_conservacao=lote_data.modo_conservacao,
        responsavel_tecnico=lote_data.responsavel_tecnico,
        observacoes=lote_data.observacoes,
        created_by=current_user.id
    )
    
    db.add(new_lote)
    db.commit()
    db.refresh(new_lote)
    
    # Atualiza estoque do alimento
    alimento.quantidade_estoque += lote_data.quantidade_produzida
    db.commit()
    
    # Se solicitado, cria job de impressão
    if lote_data.imprimir_etiqueta:
        # Monta dados da etiqueta
        etiqueta_data = {
            "tenant_name": alimento.tenant.nome,
            "tenant_email": alimento.tenant.email,
            "tenant_telefone": alimento.tenant.telefone,
            "produto_nome": alimento.nome,
            "fabricante": lote_data.fabricante or "",
            "sif": lote_data.sif or "",
            "lote_numero": lote_numero,
            "qr_code": qr_code,
            "data_fabricacao": lote_data.data_fabricacao.strftime("%d/%m/%Y"),
            "data_validade": lote_data.data_validade.strftime("%d/%m/%Y"),
            "peso_liquido": lote_data.peso_liquido or f"{lote_data.quantidade_produzida}{lote_data.unidade_medida}",
            "ingredientes": lote_data.ingredientes or "",
            "modo_conservacao": lote_data.modo_conservacao or "Manter refrigerado",
            "responsavel_tecnico": lote_data.responsavel_tecnico or "",
            "informacao_nutricional": lote_data.informacao_nutricional or ""
        }

        for _ in range(quantidade_etiquetas):
            print_job = PrintJob(
                tenant_id=tenant_id,
                lote_id=new_lote.id,
                status=StatusPrintJob.PENDING,
                etiqueta_data=json.dumps(etiqueta_data, ensure_ascii=False)
            )
            db.add(print_job)

        db.commit()
    
    return new_lote


@router.get("/", response_model=List[ProdutoLoteResponse])
def list_lotes(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    alimento_id: int = None,
    ativo: bool = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista todos os lotes do restaurante"""
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    query = db.query(ProdutoLote).filter(ProdutoLote.tenant_id == tenant_id)
    
    if alimento_id:
        query = query.filter(ProdutoLote.alimento_id == alimento_id)
    
    if ativo is not None:
        query = query.filter(ProdutoLote.ativo == ativo)
    
    query = query.order_by(ProdutoLote.created_at.desc())
    
    lotes = query.offset(skip).limit(limit).all()
    return lotes


@router.get("/vencendo", response_model=List[ProdutoLoteResponse])
def list_lotes_vencendo(
    request: Request,
    dias: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista lotes que vencem nos próximos X dias"""
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    from datetime import timedelta
    data_limite = datetime.now() + timedelta(days=dias)
    
    lotes = db.query(ProdutoLote).filter(
        ProdutoLote.tenant_id == tenant_id,
        ProdutoLote.ativo == True,
        ProdutoLote.usado_completamente == False,
        ProdutoLote.data_validade <= data_limite,
        ProdutoLote.data_validade >= datetime.now()
    ).order_by(ProdutoLote.data_validade).all()
    
    return lotes


@router.get("/alertas", response_model=AlertasLotesResponse)
def list_alertas_lotes(
    request: Request,
    dias: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna lotes vencidos e vencendo para alertas em tela"""
    tenant_id = get_tenant_id(request)

    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")

    from datetime import timedelta
    agora = datetime.now()
    data_limite = agora + timedelta(days=dias)

    base_query = db.query(ProdutoLote).filter(
        ProdutoLote.tenant_id == tenant_id,
        ProdutoLote.ativo == True,
        ProdutoLote.usado_completamente == False,
        ProdutoLote.quantidade_disponivel > 0
    )

    vencidos = base_query.filter(
        ProdutoLote.data_validade < agora
    ).order_by(ProdutoLote.data_validade).all()

    vencendo = base_query.filter(
        ProdutoLote.data_validade >= agora,
        ProdutoLote.data_validade <= data_limite
    ).order_by(ProdutoLote.data_validade).all()

    def map_item(lote: ProdutoLote):
        return {
            "id": lote.id,
            "alimento_id": lote.alimento_id,
            "alimento_nome": lote.alimento.nome if lote.alimento else "",
            "lote_numero": lote.lote_numero,
            "data_validade": lote.data_validade,
            "quantidade_disponivel": lote.quantidade_disponivel,
            "unidade_medida": lote.unidade_medida
        }

    return {
        "vencidos": [map_item(l) for l in vencidos],
        "vencendo": [map_item(l) for l in vencendo],
        "total_vencidos": len(vencidos),
        "total_vencendo": len(vencendo)
    }


@router.get("/{lote_id}", response_model=ProdutoLoteResponse)
def get_lote(
    lote_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém detalhes de um lote específico"""
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    lote = db.query(ProdutoLote).filter(
        ProdutoLote.id == lote_id,
        ProdutoLote.tenant_id == tenant_id
    ).first()
    
    if not lote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lote não encontrado"
        )
    
    return lote


@router.post("/{lote_id}/reimprimir")
def reimprimir_etiqueta(
    lote_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria novo job de impressão para o lote"""
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    lote = db.query(ProdutoLote).filter(
        ProdutoLote.id == lote_id,
        ProdutoLote.tenant_id == tenant_id
    ).first()
    
    if not lote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lote não encontrado"
        )
    
    # Busca dados do alimento para montar etiqueta
    alimento = lote.alimento
    
    etiqueta_data = {
        "tenant_name": alimento.tenant.nome,
        "tenant_email": alimento.tenant.email,
        "tenant_telefone": alimento.tenant.telefone,
        "produto_nome": alimento.nome,
        "fabricante": lote.fabricante or "",
        "sif": lote.sif or "",
        "lote_numero": lote.lote_numero,
        "qr_code": lote.qr_code,
        "data_fabricacao": lote.data_fabricacao.strftime("%d/%m/%Y"),
        "data_validade": lote.data_validade.strftime("%d/%m/%Y"),
        "peso_liquido": lote.peso_liquido or f"{lote.quantidade_produzida}{lote.unidade_medida}",
        "ingredientes": lote.ingredientes or "",
        "modo_conservacao": lote.modo_conservacao or "Manter refrigerado",
        "responsavel_tecnico": lote.responsavel_tecnico or "",
        "informacao_nutricional": lote.informacao_nutricional or ""
    }
    
    print_job = PrintJob(
        tenant_id=tenant_id,
        lote_id=lote.id,
        status=StatusPrintJob.PENDING,
        etiqueta_data=json.dumps(etiqueta_data, ensure_ascii=False)
    )
    
    db.add(print_job)
    db.commit()
    
    return {"message": "Etiqueta adicionada à fila de impressão", "print_job_id": print_job.id}
