from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response
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
import qrcode
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm

router = APIRouter(prefix="/api/tenant", tags=["Tenant - Gestão de Alimentos"])


# ==================== SCHEMAS ====================
class MovimentacaoCreate(BaseModel):
    alimento_id: int
    tipo: str  # 'entrada', 'saida', 'ajuste'
    quantidade: float
    observacao: Optional[str] = None
    data_producao: Optional[str] = None  # Data de produção (ISO format)
    data_validade: Optional[str] = None  # Data de validade (ISO format)


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
    import uuid
    from datetime import datetime as dt
    
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
    quantidade_anterior = alimento.quantidade_estoque or 0
    
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
    
    # Gera QR code único se for entrada
    qr_code_gerado = None
    data_producao = None
    data_validade = None
    
    if dados.tipo == 'entrada':
        qr_code_gerado = str(uuid.uuid4())
        
        # Parse datas se fornecidas (apenas a parte da data, ignorando timezone)
        if dados.data_producao:
            try:
                # Extrai apenas YYYY-MM-DD e converte para date
                date_str = dados.data_producao.split('T')[0]
                data_producao = dt.strptime(date_str, '%Y-%m-%d').date()
            except:
                data_producao = dt.now().date()
        else:
            data_producao = dt.now().date()
            
        if dados.data_validade:
            try:
                # Extrai apenas YYYY-MM-DD e converte para date
                date_str = dados.data_validade.split('T')[0]
                data_validade = dt.strptime(date_str, '%Y-%m-%d').date()
            except:
                pass
    
    # Cria a movimentação
    movimentacao = MovimentacaoEstoque(
        tenant_id=tenant_id,
        alimento_id=dados.alimento_id,
        usuario_id=current_user.id,
        tipo=dados.tipo,  # Usa string diretamente do request
        quantidade=dados.quantidade,
        quantidade_anterior=quantidade_anterior,
        quantidade_nova=quantidade_nova,
        motivo=dados.observacao,
        qr_code_gerado=qr_code_gerado,
        data_producao=data_producao,
        data_validade=data_validade,
        etiqueta_impressa=False,
        usado=False
    )
    
    # Atualiza o estoque do alimento
    alimento.quantidade_estoque = quantidade_nova
    
    db.add(movimentacao)
    db.commit()
    db.refresh(movimentacao)
    
    return {
        "message": "Movimentação registrada com sucesso",
        "movimentacao_id": movimentacao.id,
        "qr_code_gerado": qr_code_gerado
    }


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
            "data_hora": mov.created_at,
            "qr_code_gerado": mov.qr_code_gerado,
            "data_producao": mov.data_producao.isoformat() if mov.data_producao else None,
            "data_validade": mov.data_validade.isoformat() if mov.data_validade else None,
            "usado": mov.usado,
            "unidade_medida": mov.alimento.unidade_medida if mov.alimento else None
        })
    
    return movimentacoes


# ==================== ETIQUETAS E QR CODE ====================
@router.get("/{tenant_id}/movimentacoes/{movimentacao_id}/etiqueta")
def gerar_etiqueta_pdf(
    tenant_id: int,
    movimentacao_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Gera PDF com etiqueta e QR code para impressão"""
    # Verifica acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Busca a movimentação
    movimentacao = db.query(MovimentacaoEstoque).join(Alimento).filter(
        MovimentacaoEstoque.id == movimentacao_id,
        MovimentacaoEstoque.tenant_id == tenant_id,
        MovimentacaoEstoque.tipo == 'entrada'
    ).first()
    
    if not movimentacao:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movimentação não encontrada ou não é uma entrada"
        )
    
    if not movimentacao.qr_code_gerado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Movimentação não possui QR code gerado"
        )
    
    alimento = movimentacao.alimento
    
    # Gera QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(movimentacao.qr_code_gerado)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    # Cria PDF otimizado para impressora térmica (apenas preto e branco)
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=(80*mm, 60*mm))  # Etiqueta 80x60mm
    
    # Desenha QR code
    c.drawInlineImage(qr_img, 5*mm, 25*mm, width=25*mm, height=25*mm)
    
    # Adiciona texto - APENAS PRETO (impressora térmica)
    c.setFillColorRGB(0, 0, 0)
    
    # Nome do produto (fonte maior e bold)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(35*mm, 52*mm, alimento.nome[:25])
    
    # Quantidade
    c.setFont("Helvetica", 9)
    c.drawString(35*mm, 46*mm, f"Qtd: {movimentacao.quantidade} {alimento.unidade_medida or 'un'}")
    
    # Data de produção
    if movimentacao.data_producao:
        c.drawString(35*mm, 40*mm, f"Prod: {movimentacao.data_producao.strftime('%d/%m/%Y')}")
    
    # Data de validade (destaque com *** mas ainda preto)
    if movimentacao.data_validade:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(35*mm, 34*mm, f"*** VAL: {movimentacao.data_validade.strftime('%d/%m/%Y')} ***")
    
    # Rodapé - categoria se houver
    c.setFont("Helvetica", 7)
    if alimento.categoria:
        c.drawString(35*mm, 28*mm, f"Cat: {alimento.categoria}")
    
    # UUID simplificado no rodapé (para debug)
    c.setFont("Courier", 5)
    c.drawString(5*mm, 2*mm, movimentacao.qr_code_gerado[:36])
    
    c.save()
    
    # Marca como impressa
    movimentacao.etiqueta_impressa = True
    db.commit()
    
    pdf_buffer.seek(0)
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=etiqueta_{movimentacao_id}.pdf"}
    )


@router.post("/{tenant_id}/qrcode/validar")
def validar_qrcode(
    tenant_id: int,
    qr_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Valida QR code e retorna informações do produto"""
    from pydantic import BaseModel
    
    class QRCodeRequest(BaseModel):
        qr_code: str
    
    # Verifica acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Busca movimentação pelo QR code
    movimentacao = db.query(MovimentacaoEstoque).join(Alimento).filter(
        MovimentacaoEstoque.qr_code_gerado == qr_code,
        MovimentacaoEstoque.tenant_id == tenant_id,
        MovimentacaoEstoque.tipo == 'entrada'
    ).first()
    
    if not movimentacao:
        return {
            "valido": False,
            "mensagem": "QR Code não encontrado ou inválido"
        }
    
    if movimentacao.usado:
        return {
            "valido": False,
            "mensagem": "Este QR Code já foi utilizado"
        }
    
    alimento = movimentacao.alimento
    
    # Verifica validade
    status_validade = "válido"
    if movimentacao.data_validade:
        from datetime import date
        hoje = date.today()
        if movimentacao.data_validade < hoje:
            status_validade = "vencido"
        elif (movimentacao.data_validade - hoje).days <= 3:
            status_validade = "vencendo"
    
    # Log das datas para debug
    print(f"🔍 DEBUG - Data produção no banco: {movimentacao.data_producao}")
    print(f"🔍 DEBUG - Data validade no banco: {movimentacao.data_validade}")
    
    data_prod_str = movimentacao.data_producao.strftime('%Y-%m-%d') if movimentacao.data_producao else None
    data_val_str = movimentacao.data_validade.strftime('%Y-%m-%d') if movimentacao.data_validade else None
    
    print(f"🔍 DEBUG - Data produção formatada: {data_prod_str}")
    print(f"🔍 DEBUG - Data validade formatada: {data_val_str}")
    
    return {
        "valido": True,
        "movimentacao_id": movimentacao.id,
        "alimento_nome": alimento.nome,
        "quantidade": movimentacao.quantidade,
        "unidade_medida": alimento.unidade_medida or "un",
        "data_producao": data_prod_str,
        "data_validade": data_val_str,
        "status_validade": status_validade,
        "categoria": alimento.categoria
    }


@router.post("/{tenant_id}/qrcode/usar")
def usar_qrcode(
    tenant_id: int,
    qr_code: str,
    quantidade_usada: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Dá baixa no estoque usando QR code escaneado"""
    from pydantic import BaseModel
    
    class QRCodeUsarRequest(BaseModel):
        qr_code: str
        quantidade_usada: Optional[float] = None
    
    # Verifica acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Busca movimentação pelo QR code
    movimentacao_entrada = db.query(MovimentacaoEstoque).join(Alimento).filter(
        MovimentacaoEstoque.qr_code_gerado == qr_code,
        MovimentacaoEstoque.tenant_id == tenant_id,
        MovimentacaoEstoque.tipo == 'entrada'
    ).first()
    
    if not movimentacao_entrada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR Code não encontrado"
        )
    
    if movimentacao_entrada.usado:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este QR Code já foi utilizado"
        )
    
    alimento = movimentacao_entrada.alimento
    
    # Quantidade a dar baixa (se não especificada, usa a quantidade total da entrada)
    qtd_baixa = quantidade_usada if quantidade_usada else movimentacao_entrada.quantidade
    
    # Verifica se há estoque suficiente
    estoque_atual = alimento.quantidade_estoque or 0
    if estoque_atual < qtd_baixa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estoque insuficiente. Disponível: {estoque_atual}"
        )
    
    # Registra saída
    quantidade_anterior = estoque_atual
    quantidade_nova = estoque_atual - qtd_baixa
    
    movimentacao_saida = MovimentacaoEstoque(
        tenant_id=tenant_id,
        alimento_id=alimento.id,
        usuario_id=current_user.id,
        tipo='saida',
        quantidade=qtd_baixa,
        quantidade_anterior=quantidade_anterior,
        quantidade_nova=quantidade_nova,
        motivo=f"Baixa via QR Code scanner",
        qr_code_usado=qr_code
    )
    
    # Atualiza estoque
    alimento.quantidade_estoque = quantidade_nova
    
    # Marca entrada como usada
    movimentacao_entrada.usado = True
    
    db.add(movimentacao_saida)
    db.commit()
    
    return {
        "sucesso": True,
        "mensagem": "Baixa realizada com sucesso",
        "produto": alimento.nome,
        "quantidade_baixa": qtd_baixa,
        "estoque_anterior": quantidade_anterior,
        "estoque_novo": quantidade_nova
    }
