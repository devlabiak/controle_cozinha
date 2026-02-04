from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, select
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.database import get_db
from app.models import Alimento, User, MovimentacaoEstoque, TipoMovimentacao, user_tenants_association, RoleType, ProdutoLote
from app.schemas import AlimentoCreate, AlimentoUpdate, AlimentoResponse
from app.auth import get_current_user
from app.middleware import get_tenant_id
from app.services.audit import registrar_auditoria
from app.rate_limit import limiter
from pydantic import BaseModel
import qrcode
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import mm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tenant", tags=["Tenant - Gestão de Alimentos"])


# ==================== HELPER DE PERMISSÕES ====================
def verificar_admin_restaurante(tenant_id: int, user: User, db: Session):
    """Verifica se o usuário tem permissão de admin no restaurante"""
    # Admin SaaS tem acesso total
    if user.is_admin:
        return True
    
    # Busca o role na tabela de associação
    stmt = select(user_tenants_association).where(
        user_tenants_association.c.user_id == user.id,
        user_tenants_association.c.tenant_id == tenant_id
    )
    result = db.execute(stmt).first()
    
    if not result or result.role != RoleType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permissão negada. Apenas administradores do restaurante podem realizar esta ação."
        )
    
    return True


# ==================== SCHEMAS ====================
class MovimentacaoCreate(BaseModel):
    alimento_id: int
    tipo: str  # 'entrada', 'saida', 'ajuste'
    quantidade: float
    observacao: Optional[str] = None
    data_producao: Optional[str] = None  # Data de produção (ISO format)
    data_validade: Optional[str] = None  # Data de validade (ISO format)
    # Campos para entrada por embalagem/pacote
    modo_embalagem: Optional[str] = None  # 'embalagens' ou None
    qtd_pacotes: Optional[int] = None  # Quantidade de pacotes
    unidades_por_embalagem: Optional[int] = None  # Unidades por pacote


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
@limiter.limit("100/minute")
def create_alimento(
    tenant_id: int,
    alimento_data: AlimentoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cria novo alimento no estoque (apenas admins)"""
    # Verifica se o usuário tem acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Verifica se é admin do restaurante
    verificar_admin_restaurante(tenant_id, current_user, db)
    
    new_alimento = Alimento(
        tenant_id=tenant_id,
        **alimento_data.dict()
    )
    
    db.add(new_alimento)
    db.flush()

    registrar_auditoria(
        db,
        user_id=current_user.id,
        tenant_id=tenant_id,
        action="CREATE",
        resource="alimentos",
        resource_id=new_alimento.id,
        details=f"Alimento '{new_alimento.nome}' criado",
        request=request,
    )
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
    
    query = db.query(Alimento).filter(
        Alimento.tenant_id == tenant_id,
        Alimento.ativo == True
    )
    
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
        Alimento.tenant_id == tenant_id,
        Alimento.ativo == True
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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Atualiza dados de um alimento (apenas admins)"""
    # Verifica se o usuário tem acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Verifica se é admin do restaurante
    verificar_admin_restaurante(tenant_id, current_user, db)
    
    alimento = db.query(Alimento).filter(
        Alimento.id == alimento_id,
        Alimento.tenant_id == tenant_id,
        Alimento.ativo == True
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

    registrar_auditoria(
        db,
        user_id=current_user.id,
        tenant_id=tenant_id,
        action="UPDATE",
        resource="alimentos",
        resource_id=alimento.id,
        details=f"Alimento '{alimento.nome}' atualizado: {update_data or 'sem alterações explícitas'}",
        request=request,
    )
    db.commit()
    db.refresh(alimento)
    
    return alimento


@router.delete("/{tenant_id}/alimentos/{alimento_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alimento(
    tenant_id: int,
    alimento_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deleta um alimento (apenas admins)"""
    # Verifica se o usuário tem acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Verifica se é admin do restaurante
    verificar_admin_restaurante(tenant_id, current_user, db)
    
    alimento = db.query(Alimento).filter(
        Alimento.id == alimento_id,
        Alimento.tenant_id == tenant_id,
        Alimento.ativo == True
    ).first()
    
    if not alimento:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alimento não encontrado"
        )
    
    alimento.ativo = False
    alimento.deleted_at = datetime.utcnow()

    registrar_auditoria(
        db,
        user_id=current_user.id,
        tenant_id=tenant_id,
        action="DELETE",
        resource="alimentos",
        resource_id=alimento.id,
        details=f"Alimento '{alimento.nome}' desativado (soft delete)",
        request=request,
    )
    db.commit()
    
    return {
        "message": "Alimento desativado. Histórico permanecerá disponível por 90 dias."
    }


# ==================== MOVIMENTAÇÕES ====================
@router.post("/{tenant_id}/movimentacoes", status_code=status.HTTP_201_CREATED)
def criar_movimentacao(
    tenant_id: int,
    dados: MovimentacaoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registra uma movimentação de estoque (entrada requer permissão admin)"""
    import uuid
    from datetime import datetime as dt
    
    # Verifica se o usuário tem acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Apenas entrada e ajuste requerem permissão de admin
    if dados.tipo in ['entrada', 'ajuste']:
        verificar_admin_restaurante(tenant_id, current_user, db)
    
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
    
    # Detecta se é entrada por embalagem
    if dados.tipo == 'entrada' and dados.modo_embalagem == 'embalagens' and dados.qtd_pacotes and dados.unidades_por_embalagem:
        # Cria uma movimentação/lote para cada pacote
        quantidade_total = dados.qtd_pacotes * dados.unidades_por_embalagem
        quantidade_anterior = alimento.quantidade_estoque or 0
        results = []
        
        for i in range(dados.qtd_pacotes):
            qr_code_gerado = str(uuid.uuid4())
            # Gera lote_numero: letra + 6 dígitos (ex: A123456)
            import random
            import string
            letra = random.choice(string.ascii_uppercase)
            numeros = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            lote_numero = f"{letra}{numeros}"
            data_producao = None
            data_validade = None
            if dados.data_producao:
                try:
                    date_str = dados.data_producao.split('T')[0]
                    data_producao = dt.strptime(date_str, '%Y-%m-%d').date()
                except:
                    data_producao = dt.now().date()
            else:
                data_producao = dt.now().date()
            if dados.data_validade:
                try:
                    date_str = dados.data_validade.split('T')[0]
                    data_validade = dt.strptime(date_str, '%Y-%m-%d').date()
                except:
                    pass
            
            quantidade_nova = quantidade_anterior + dados.unidades_por_embalagem
            movimentacao = MovimentacaoEstoque(
                tenant_id=tenant_id,
                alimento_id=dados.alimento_id,
                usuario_id=current_user.id,
                tipo=dados.tipo,
                quantidade=dados.unidades_por_embalagem,
                quantidade_anterior=quantidade_anterior,
                quantidade_nova=quantidade_nova,
                motivo=dados.observacao,
                qr_code_gerado=qr_code_gerado,
                qr_code_usado=lote_numero,
                data_producao=data_producao,
                data_validade=data_validade,
                etiqueta_impressa=False,
                usado=False
            )
            alimento.quantidade_estoque = quantidade_nova
            quantidade_anterior = quantidade_nova
            db.add(movimentacao)
            db.commit()
            db.refresh(movimentacao)
            results.append({
                "movimentacao_id": movimentacao.id,
                "qr_code_gerado": qr_code_gerado,
                "lote_numero": lote_numero
            })
        
        return {
            "message": "Movimentações registradas com sucesso",
            "pacotes": results
        }
    
    # Caso normal (avulso ou sem modo_embalagem)
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
    qr_code_gerado = None
    lote_numero = None
    data_producao = None
    data_validade = None
    if dados.tipo == 'entrada':
        qr_code_gerado = str(uuid.uuid4())
        # Gera lote_numero também para entradas avulsas
        import random
        import string
        letra = random.choice(string.ascii_uppercase)
        numeros = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        lote_numero = f"{letra}{numeros}"
        
        if dados.data_producao:
            try:
                date_str = dados.data_producao.split('T')[0]
                data_producao = dt.strptime(date_str, '%Y-%m-%d').date()
            except:
                data_producao = dt.now().date()
        else:
            data_producao = dt.now().date()
        if dados.data_validade:
            try:
                date_str = dados.data_validade.split('T')[0]
                data_validade = dt.strptime(date_str, '%Y-%m-%d').date()
            except:
                pass
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
        qr_code_usado=lote_numero,
        data_producao=data_producao,
        data_validade=data_validade,
        etiqueta_impressa=False,
        usado=False
    )
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


@router.get("/{tenant_id}/movimentacoes/historico", response_model=List[MovimentacaoResponse])
def historico_movimentacoes(
    tenant_id: int,
    dias: int = 90,
    tipo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retorna movimentações dos últimos N dias (máximo 90)."""
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )

    dias = max(1, min(dias, 90))
    cutoff = datetime.utcnow() - timedelta(days=dias)

    query = db.query(
        MovimentacaoEstoque,
        Alimento.nome.label('alimento_nome'),
        User.nome.label('usuario_nome')
    ).outerjoin(
        Alimento, MovimentacaoEstoque.alimento_id == Alimento.id
    ).join(
        User, MovimentacaoEstoque.usuario_id == User.id
    ).filter(
        MovimentacaoEstoque.tenant_id == tenant_id,
        MovimentacaoEstoque.created_at >= cutoff
    ).order_by(desc(MovimentacaoEstoque.created_at))

    if tipo:
        if tipo == 'entrada':
            query = query.filter(MovimentacaoEstoque.tipo == TipoMovimentacao.ENTRADA)
        elif tipo == 'saida':
            query = query.filter(MovimentacaoEstoque.tipo == TipoMovimentacao.SAIDA)
        elif tipo == 'ajuste':
            query = query.filter(MovimentacaoEstoque.tipo == TipoMovimentacao.AJUSTE)

    resultados = query.all()

    historico = []
    for mov, alimento_nome, usuario_nome in resultados:
        historico.append({
            "id": mov.id,
            "alimento_id": mov.alimento_id,
            "alimento_nome": alimento_nome,
            "tipo": mov.tipo.value if hasattr(mov.tipo, 'value') else mov.tipo,
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

    return historico


# ==================== ETIQUETAS E QR CODE ====================
@router.get("/{tenant_id}/movimentacoes/{movimentacao_id}/etiqueta")
def gerar_etiqueta_pdf(
    tenant_id: int,
    movimentacao_id: int,
    qtd: int = None,
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
    
    # Lote manual (letra + 6 dígitos) - logo abaixo do nome
    c.setFont("Helvetica-Bold", 10)
    lote_numero = movimentacao.qr_code_usado or "N/A"
    c.drawString(35*mm, 47*mm, f"Lote: {lote_numero}")
    
    # Quantidade
    c.setFont("Helvetica", 9)
    quantidade_etiqueta = movimentacao.quantidade
    if qtd is not None:
        try:
            quantidade_etiqueta = int(qtd)
        except Exception:
            pass
    c.drawString(35*mm, 41*mm, f"Qtd: {quantidade_etiqueta} {alimento.unidade_medida or 'un'}")
    
    # Data de produção
    if movimentacao.data_producao:
        c.drawString(35*mm, 35*mm, f"Prod: {movimentacao.data_producao.strftime('%d/%m/%Y')}")
    
    # Data de validade (destaque com *** mas ainda preto)
    if movimentacao.data_validade:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(35*mm, 29*mm, f"*** VAL: {movimentacao.data_validade.strftime('%d/%m/%Y')} ***")
    
    # Rodapé - categoria se houver
    c.setFont("Helvetica", 7)
    if alimento.categoria:
        c.drawString(35*mm, 23*mm, f"Cat: {alimento.categoria}")
    
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
    
    # Calcula quantidade já usada deste lote (busca pelo lote_numero)
    lote_numero_entrada = movimentacao.qr_code_usado
    total_usado = db.query(func.sum(MovimentacaoEstoque.quantidade)).filter(
        MovimentacaoEstoque.qr_code_usado == lote_numero_entrada,
        MovimentacaoEstoque.tipo == 'saida',
        MovimentacaoEstoque.tenant_id == tenant_id
    ).scalar() or 0
    
    # Quantidade disponível neste lote
    quantidade_disponivel = movimentacao.quantidade - total_usado
    
    if quantidade_disponivel <= 0:
        return {
            "valido": False,
            "mensagem": "Este lote já foi completamente utilizado"
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
    logger.debug(
        "Validando QR code - Datas",
        extra={
            "qr_code": qr_code[:8] + "...",
            "data_producao": movimentacao.data_producao,
            "data_validade": movimentacao.data_validade
        }
    )
    
    data_prod_str = movimentacao.data_producao.strftime('%Y-%m-%d') if movimentacao.data_producao else None
    data_val_str = movimentacao.data_validade.strftime('%Y-%m-%d') if movimentacao.data_validade else None
    
    return {
        "valido": True,
        "movimentacao_id": movimentacao.id,
        "alimento_nome": alimento.nome,
        "quantidade": quantidade_disponivel,
        "quantidade_original": movimentacao.quantidade,
        "quantidade_usada": total_usado,
        "unidade_medida": alimento.unidade_medida or "un",
        "data_producao": data_prod_str,
        "data_validade": data_val_str,
        "status_validade": status_validade,
        "categoria": alimento.categoria
    }


@router.post("/{tenant_id}/qrcode/usar")
@limiter.limit("200/minute")
def usar_qrcode(
    tenant_id: int,
    qr_code: str,
    quantidade_usada: Optional[float] = None,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Dá baixa no estoque usando QR code escaneado"""
    logger.info(
        "Endpoint /qrcode/usar chamado",
        extra={
            "tenant_id": tenant_id,
            "qr_code": qr_code[:8] + "...",
            "quantidade_usada": quantidade_usada,
            "user_email": current_user.email
        }
    )
    
    from pydantic import BaseModel
    
    class QRCodeUsarRequest(BaseModel):
        qr_code: str
        quantidade_usada: Optional[float] = None
    
    # Verifica acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        logger.warning(
            "Acesso negado ao tenant",
            extra={
                "user_id": current_user.id,
                "tenant_id": tenant_id,
                "user_tenants": user_tenants
            }
        )
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
        logger.warning(
            "QR Code não encontrado",
            extra={"qr_code": qr_code[:8] + "...", "tenant_id": tenant_id}
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="QR Code não encontrado"
        )
    
    # Calcula quantidade já usada deste lote (busca pelo lote_numero)
    lote_numero_entrada = movimentacao_entrada.qr_code_usado
    total_usado = db.query(func.sum(MovimentacaoEstoque.quantidade)).filter(
        MovimentacaoEstoque.qr_code_usado == lote_numero_entrada,
        MovimentacaoEstoque.tipo == 'saida',
        MovimentacaoEstoque.tenant_id == tenant_id
    ).scalar() or 0
    
    # Quantidade disponível neste lote específico
    quantidade_disponivel_lote = movimentacao_entrada.quantidade - total_usado
    
    logger.debug(
        "Calculando quantidade disponível do lote",
        extra={
            "quantidade_original": movimentacao_entrada.quantidade,
            "total_usado": total_usado,
            "disponivel_lote": quantidade_disponivel_lote
        }
    )
    
    if quantidade_disponivel_lote <= 0:
        logger.warning("Lote completamente utilizado", extra={"qr_code": qr_code[:8] + "..."})
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este lote já foi completamente utilizado"
        )
    
    alimento = movimentacao_entrada.alimento
    
    # Quantidade a dar baixa (se não especificada, usa a quantidade disponível do lote)
    qtd_baixa = quantidade_usada if quantidade_usada else quantidade_disponivel_lote
    
    # Não pode usar mais do que está disponível no lote
    if qtd_baixa > quantidade_disponivel_lote:
        logger.warning(
            "Quantidade solicitada maior que disponível no lote",
            extra={
                "quantidade_solicitada": qtd_baixa,
                "disponivel_lote": quantidade_disponivel_lote
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quantidade indisponível neste lote. Disponível: {quantidade_disponivel_lote}"
        )
    
    logger.debug(
        "Processando baixa de estoque",
        extra={
            "produto": alimento.nome,
            "quantidade_baixa": qtd_baixa
        }
    )
    
    # Verifica se há estoque suficiente no total
    estoque_atual = alimento.quantidade_estoque or 0
    if estoque_atual < qtd_baixa:
        logger.error(
            "Estoque insuficiente",
            extra={
                "estoque_atual": estoque_atual,
                "quantidade_solicitada": qtd_baixa,
                "alimento": alimento.nome
            }
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estoque insuficiente. Disponível: {estoque_atual}"
        )
    
    # Registra saída
    quantidade_anterior = estoque_atual
    quantidade_nova = estoque_atual - qtd_baixa
    
    logger.debug("Criando movimentação de saída")
    
    # Pega o lote_numero da entrada original para sincronizar
    lote_numero_entrada = movimentacao_entrada.qr_code_usado
    
    movimentacao_saida = MovimentacaoEstoque(
        tenant_id=tenant_id,
        alimento_id=alimento.id,
        usuario_id=current_user.id,
        tipo='saida',
        quantidade=qtd_baixa,
        quantidade_anterior=quantidade_anterior,
        quantidade_nova=quantidade_nova,
        motivo=None,
        qr_code_usado=lote_numero_entrada  # Usa o lote_numero para sincronizar
    )
    
    # Atualiza estoque
    alimento.quantidade_estoque = quantidade_nova
    
    # NÃO marca entrada como usada - permite uso parcial
    # movimentacao_entrada.usado = True  <- REMOVIDO
    
    db.add(movimentacao_saida)
    db.commit()
    
    # Calcula quanto ainda resta disponível neste lote
    quantidade_restante_lote = quantidade_disponivel_lote - qtd_baixa
    
    logger.info(
        "Baixa realizada com sucesso",
        extra={
            "produto": alimento.nome,
            "quantidade_baixa": qtd_baixa,
            "estoque_anterior": quantidade_anterior,
            "estoque_novo": quantidade_nova,
            "lote_restante": quantidade_restante_lote
        }
    )
    
    resultado = {
        "sucesso": True,
        "mensagem": "Baixa realizada com sucesso",
        "produto": alimento.nome,
        "quantidade_baixa": qtd_baixa,
        "estoque_anterior": quantidade_anterior,
        "estoque_novo": quantidade_nova,
        "lote_restante": quantidade_restante_lote,
        "lote_original": movimentacao_entrada.quantidade
    }
    
    return resultado


# ==================== LOTE MANUAL (ALTERNATIVA AO QR CODE) ====================
@router.post("/{tenant_id}/lote/validar")
def validar_lote(
    tenant_id: int,
    lote_numero: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Valida lote manual e retorna informações do produto (alternativa ao QR code)"""
    # Verifica acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Busca movimentação pelo lote_numero (armazenado em qr_code_usado)
    movimentacao = db.query(MovimentacaoEstoque).join(Alimento).filter(
        MovimentacaoEstoque.qr_code_usado == lote_numero.upper(),
        MovimentacaoEstoque.tenant_id == tenant_id,
        MovimentacaoEstoque.tipo == 'entrada'
    ).first()
    
    if not movimentacao:
        return {
            "valido": False,
            "mensagem": "Lote não encontrado ou inválido"
        }
    
    alimento = movimentacao.alimento
    
    # Calcula quantidade já usada deste lote
    total_usado = db.query(func.sum(MovimentacaoEstoque.quantidade)).filter(
        MovimentacaoEstoque.qr_code_usado == lote_numero.upper(),
        MovimentacaoEstoque.tipo == 'saida',
        MovimentacaoEstoque.tenant_id == tenant_id
    ).scalar() or 0
    
    # Quantidade disponível neste lote
    quantidade_disponivel = movimentacao.quantidade - total_usado
    
    if quantidade_disponivel <= 0:
        return {
            "valido": False,
            "mensagem": "Este lote já foi completamente utilizado"
        }
    
    # Determina status de validade
    from datetime import date
    status_validade = "valido"
    if movimentacao.data_validade:
        dias_restantes = (movimentacao.data_validade - date.today()).days
        if dias_restantes < 0:
            status_validade = "vencido"
        elif dias_restantes <= 3:
            status_validade = "vencendo"
    
    data_prod_str = movimentacao.data_producao.strftime('%Y-%m-%d') if movimentacao.data_producao else None
    data_val_str = movimentacao.data_validade.strftime('%Y-%m-%d') if movimentacao.data_validade else None
    
    return {
        "valido": True,
        "movimentacao_id": movimentacao.id,
        "lote_numero": lote_numero.upper(),
        "alimento_nome": alimento.nome,
        "quantidade": quantidade_disponivel,
        "quantidade_original": movimentacao.quantidade,
        "quantidade_usada": total_usado,
        "unidade_medida": alimento.unidade_medida or "un",
        "data_producao": data_prod_str,
        "data_validade": data_val_str,
        "status_validade": status_validade,
        "categoria": alimento.categoria
    }


@router.post("/{tenant_id}/lote/usar")
@limiter.limit("200/minute")
def usar_lote(
    tenant_id: int,
    lote_numero: str,
    quantidade_usada: float = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None
):
    """Dá baixa no estoque usando lote manual (alternativa ao QR code)"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Verifica acesso ao tenant
    user_tenants = [t.id for t in current_user.tenants]
    if tenant_id not in user_tenants:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Busca a movimentação de entrada original
    movimentacao_entrada = db.query(MovimentacaoEstoque).join(Alimento).filter(
        MovimentacaoEstoque.qr_code_usado == lote_numero.upper(),
        MovimentacaoEstoque.tenant_id == tenant_id,
        MovimentacaoEstoque.tipo == 'entrada'
    ).first()
    
    if not movimentacao_entrada:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Lote não encontrado"
        )
    
    # Calcula quantidade já usada deste lote
    total_usado = db.query(func.sum(MovimentacaoEstoque.quantidade)).filter(
        MovimentacaoEstoque.qr_code_usado == lote_numero.upper(),
        MovimentacaoEstoque.tipo == 'saida',
        MovimentacaoEstoque.tenant_id == tenant_id
    ).scalar() or 0
    
    # Quantidade disponível neste lote específico
    quantidade_disponivel_lote = movimentacao_entrada.quantidade - total_usado
    
    if quantidade_disponivel_lote <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este lote já foi completamente utilizado"
        )
    
    alimento = movimentacao_entrada.alimento
    
    # Quantidade a dar baixa (se não especificada, usa a quantidade disponível do lote)
    qtd_baixa = quantidade_usada if quantidade_usada else quantidade_disponivel_lote
    
    # Não pode usar mais do que está disponível no lote
    if qtd_baixa > quantidade_disponivel_lote:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Quantidade indisponível neste lote. Disponível: {quantidade_disponivel_lote}"
        )
    
    # Não pode usar mais do que tem no estoque total
    quantidade_anterior = alimento.quantidade_estoque or 0
    if qtd_baixa > quantidade_anterior:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estoque insuficiente. Disponível: {quantidade_anterior}"
        )
    
    # Registra saída
    quantidade_nova = quantidade_anterior - qtd_baixa
    
    movimentacao_saida = MovimentacaoEstoque(
        tenant_id=tenant_id,
        alimento_id=movimentacao_entrada.alimento_id,
        usuario_id=current_user.id,
        tipo='saida',
        quantidade=qtd_baixa,
        quantidade_anterior=quantidade_anterior,
        quantidade_nova=quantidade_nova,
        motivo=None,
        qr_code_usado=lote_numero.upper()
    )
    
    # Atualiza estoque
    alimento.quantidade_estoque = quantidade_nova
    
    db.add(movimentacao_saida)
    db.commit()
    
    # Calcula quanto ainda resta disponível neste lote
    quantidade_restante_lote = quantidade_disponivel_lote - qtd_baixa
    
    logger.info(
        "Baixa por lote manual realizada com sucesso",
        extra={
            "lote": lote_numero.upper(),
            "produto": alimento.nome,
            "quantidade_baixa": qtd_baixa,
            "estoque_anterior": quantidade_anterior,
            "estoque_novo": quantidade_nova,
            "lote_restante": quantidade_restante_lote
        }
    )
    
    return {
        "sucesso": True,
        "mensagem": "Baixa realizada com sucesso",
        "lote_numero": lote_numero.upper(),
        "produto": alimento.nome,
        "quantidade_baixa": qtd_baixa,
        "estoque_anterior": quantidade_anterior,
        "estoque_novo": quantidade_nova,
        "lote_restante": quantidade_restante_lote,
        "lote_original": movimentacao_entrada.quantidade
    }


# ==================== ALERTAS DE VALIDADE ====================
@router.get("/{tenant_id}/lotes/vencendo")
async def listar_lotes_vencendo(
    tenant_id: int,
    dias: int = 4,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista lotes e entradas que estão próximos do vencimento
    
    - **dias**: número de dias para considerar (padrão: 4)
    """
    # Verifica se usuário tem acesso ao tenant
    if not current_user.is_admin:
        stmt = select(user_tenants_association).where(
            user_tenants_association.c.user_id == current_user.id,
            user_tenants_association.c.tenant_id == tenant_id
        )
        result = db.execute(stmt).first()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Sem acesso a este restaurante"
            )
    
    # Calcula data limite
    data_limite = datetime.now() + timedelta(days=dias)
    
    resultado = []
    
    # 1. Busca lotes ativos que ainda têm quantidade disponível e estão próximos do vencimento
    lotes = db.query(ProdutoLote).join(Alimento).filter(
        ProdutoLote.tenant_id == tenant_id,
        ProdutoLote.ativo == True,
        ProdutoLote.usado_completamente == False,
        ProdutoLote.quantidade_disponivel > 0,
        ProdutoLote.data_validade <= data_limite,
        ProdutoLote.data_validade >= datetime.now()
    ).order_by(ProdutoLote.data_validade.asc()).all()
    
    for lote in lotes:
        dias_restantes = (lote.data_validade.date() - datetime.now().date()).days
        resultado.append({
            "id": lote.id,
            "tipo": "lote",
            "alimento_id": lote.alimento_id,
            "alimento_nome": lote.alimento.nome,
            "lote_numero": lote.lote_numero,
            "quantidade_disponivel": lote.quantidade_disponivel,
            "unidade_medida": lote.unidade_medida,
            "data_validade": lote.data_validade.isoformat(),
            "dias_restantes": dias_restantes,
            "urgencia": "critico" if dias_restantes <= 1 else "alto" if dias_restantes <= 2 else "medio"
        })
    
    # 2. Busca movimentações de entrada com validade que ainda não foram usadas
    movimentacoes = db.query(MovimentacaoEstoque).join(Alimento).filter(
        MovimentacaoEstoque.tenant_id == tenant_id,
        MovimentacaoEstoque.tipo == TipoMovimentacao.ENTRADA,
        MovimentacaoEstoque.data_validade != None,
        MovimentacaoEstoque.usado == False,
        MovimentacaoEstoque.data_validade <= data_limite,
        MovimentacaoEstoque.data_validade >= datetime.now().date()
    ).order_by(MovimentacaoEstoque.data_validade.asc()).all()
    
    for mov in movimentacoes:
        # Calcula dias restantes considerando que data_validade é um Date
        dias_restantes = (mov.data_validade - datetime.now().date()).days
        resultado.append({
            "id": mov.id,
            "tipo": "movimentacao",
            "alimento_id": mov.alimento_id,
            "alimento_nome": mov.alimento.nome,
            "lote_numero": mov.qr_code_gerado or "Entrada simples",
            "quantidade_disponivel": mov.quantidade,
            "unidade_medida": mov.alimento.unidade_medida,
            "data_validade": mov.data_validade.isoformat(),
            "dias_restantes": dias_restantes,
            "urgencia": "critico" if dias_restantes <= 1 else "alto" if dias_restantes <= 2 else "medio"
        })
    
    # Ordena por data de validade
    resultado.sort(key=lambda x: x['data_validade'])
    
    return resultado
