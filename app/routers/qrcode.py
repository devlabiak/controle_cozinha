from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.models import ProdutoLote, Alimento, MovimentacaoEstoque, TipoMovimentacao, User
from app.schemas import (
    QRCodeValidateRequest, QRCodeValidateResponse,
    QRCodeUsarRequest, QRCodeUsarResponse,
    ProdutoLoteResponse
)
from app.auth import get_current_user
from app.middleware import get_tenant_id

router = APIRouter(prefix="/api/qrcode", tags=["QR Code - Validação e Uso"])


@router.post("/validar", response_model=QRCodeValidateResponse)
def validar_qrcode(
    data: QRCodeValidateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Valida um QR Code e retorna informações do lote.
    Usado pelo app mobile antes de dar baixa.
    """
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    # Busca o lote pelo QR code
    lote = db.query(ProdutoLote).filter(
        ProdutoLote.qr_code == data.qr_code,
        ProdutoLote.tenant_id == tenant_id
    ).first()
    
    if not lote:
        return QRCodeValidateResponse(
            valido=False,
            mensagem="QR Code inválido ou não encontrado"
        )
    
    # Verifica se está ativo
    if not lote.ativo:
        return QRCodeValidateResponse(
            valido=False,
            mensagem="Este lote foi desativado"
        )
    
    # Verifica se ainda tem quantidade disponível
    if lote.usado_completamente or lote.quantidade_disponivel <= 0:
        return QRCodeValidateResponse(
            valido=False,
            mensagem="Este lote já foi totalmente utilizado"
        )
    
    # Verifica validade
    if lote.data_validade < datetime.now():
        return QRCodeValidateResponse(
            valido=False,
            lote=ProdutoLoteResponse.from_orm(lote),
            alimento_nome=lote.alimento.nome,
            mensagem=f"⚠️ ATENÇÃO: Produto VENCIDO desde {lote.data_validade.strftime('%d/%m/%Y')}"
        )
    
    # Tudo OK
    return QRCodeValidateResponse(
        valido=True,
        lote=ProdutoLoteResponse.from_orm(lote),
        alimento_nome=lote.alimento.nome,
        mensagem=f"✓ {lote.alimento.nome} - Lote {lote.lote_numero}\n"
                 f"Validade: {lote.data_validade.strftime('%d/%m/%Y')}\n"
                 f"Disponível: {lote.quantidade_disponivel} {lote.unidade_medida}"
    )


@router.post("/usar", response_model=QRCodeUsarResponse)
def usar_produto_qrcode(
    data: QRCodeUsarRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Dá baixa no produto via QR Code.
    Usado pelo app mobile após confirmação do usuário.
    """
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    # Busca o lote
    lote = db.query(ProdutoLote).filter(
        ProdutoLote.qr_code == data.qr_code,
        ProdutoLote.tenant_id == tenant_id
    ).first()
    
    if not lote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR Code não encontrado"
        )
    
    if not lote.ativo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este lote está desativado"
        )
    
    if lote.usado_completamente or lote.quantidade_disponivel <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este lote já foi totalmente utilizado"
        )
    
    # Verifica se tem quantidade suficiente
    if data.quantidade > lote.quantidade_disponivel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quantidade solicitada ({data.quantidade}) maior que disponível ({lote.quantidade_disponivel})"
        )
    
    # Guarda quantidade anterior
    quantidade_anterior = lote.quantidade_disponivel
    
    # Atualiza quantidade do lote
    lote.quantidade_disponivel -= data.quantidade
    
    # Marca como usado completamente se necessário
    if lote.quantidade_disponivel <= 0:
        lote.usado_completamente = True
        lote.quantidade_disponivel = 0
    
    # Atualiza estoque do alimento
    alimento = lote.alimento
    alimento.quantidade_estoque -= data.quantidade
    
    # Registra movimentação
    movimentacao = MovimentacaoEstoque(
        tenant_id=tenant_id,
        alimento_id=lote.alimento_id,
        lote_id=lote.id,
        usuario_id=current_user.id,
        tipo=TipoMovimentacao.USO,
        quantidade=data.quantidade,
        quantidade_anterior=quantidade_anterior,
        quantidade_nova=lote.quantidade_disponivel,
        qr_code_usado=data.qr_code,
        motivo=data.motivo or f"Uso via QR Code - {lote.alimento.nome}",
        localizacao=data.localizacao
    )
    
    db.add(movimentacao)
    db.commit()
    db.refresh(movimentacao)
    
    mensagem = f"✓ Baixa realizada com sucesso!\n" \
               f"Produto: {alimento.nome}\n" \
               f"Quantidade usada: {data.quantidade} {lote.unidade_medida}\n" \
               f"Restante no lote: {lote.quantidade_disponivel} {lote.unidade_medida}"
    
    if lote.usado_completamente:
        mensagem += "\n⚠️ Lote completamente utilizado!"
    
    return QRCodeUsarResponse(
        sucesso=True,
        mensagem=mensagem,
        quantidade_restante=lote.quantidade_disponivel,
        movimentacao_id=movimentacao.id
    )


@router.get("/lote/{qr_code}", response_model=ProdutoLoteResponse)
def get_lote_by_qrcode(
    qr_code: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém informações completas do lote pelo QR Code (para visualização)"""
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    lote = db.query(ProdutoLote).filter(
        ProdutoLote.qr_code == qr_code,
        ProdutoLote.tenant_id == tenant_id
    ).first()
    
    if not lote:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lote não encontrado"
        )
    
    return lote
