from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ============= TENANT SCHEMAS =============
class TenantBase(BaseModel):
    nome: str
    slug: str
    email: EmailStr
    telefone: Optional[str] = None


class TenantCreate(TenantBase):
    admin_nome: str
    admin_email: EmailStr
    admin_senha: str


class TenantUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    telefone: Optional[str] = None
    ativo: Optional[bool] = None


class TenantResponse(TenantBase):
    id: int
    ativo: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============= USER SCHEMAS =============
class UserBase(BaseModel):
    nome: str
    email: EmailStr


class UserCreate(UserBase):
    senha: str
    is_tenant_admin: bool = False


class UserUpdate(BaseModel):
    nome: Optional[str] = None
    email: Optional[EmailStr] = None
    senha: Optional[str] = None
    is_tenant_admin: Optional[bool] = None
    ativo: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    tenant_id: Optional[int] = None
    is_admin: bool
    is_tenant_admin: bool
    ativo: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ============= ALIMENTO SCHEMAS =============
class AlimentoBase(BaseModel):
    nome: str
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    tipo_conservacao: Optional[str] = None  # congelado, resfriado
    unidade_medida: Optional[str] = None
    quantidade_estoque: float = 0
    quantidade_minima: float = 0
    preco_unitario: Optional[float] = None
    fornecedor: Optional[str] = None
    observacoes: Optional[str] = None


class AlimentoCreate(AlimentoBase):
    pass


class AlimentoUpdate(BaseModel):
    nome: Optional[str] = None
    categoria: Optional[str] = None
    subcategoria: Optional[str] = None
    tipo_conservacao: Optional[str] = None
    unidade_medida: Optional[str] = None
    quantidade_estoque: Optional[float] = None
    quantidade_minima: Optional[float] = None
    preco_unitario: Optional[float] = None
    fornecedor: Optional[str] = None
    observacoes: Optional[str] = None
    ativo: Optional[bool] = None


class AlimentoResponse(AlimentoBase):
    id: int
    tenant_id: int
    ativo: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============= AUTH SCHEMAS =============
class RestauranteSeletor(BaseModel):
    """Restaurante para seletor no login"""
    id: int
    nome: str
    slug: str
    
    class Config:
        from_attributes = True


class UsuarioLoginResponse(BaseModel):
    """Resposta com dados do usuário após login"""
    id: int
    nome: str
    email: str
    is_admin: bool
    cliente_id: int | None
    restaurantes: list[RestauranteSeletor] = []  # Restaurantes que o usuário pode acessar
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UsuarioLoginResponse | None = None


class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None
    tenant_id: Optional[int] = None
    cliente_id: Optional[int] = None
    is_admin: bool = False


class LoginRequest(BaseModel):
    email: EmailStr
    senha: str


# ============= PRODUTO LOTE SCHEMAS =============
class ProdutoLoteBase(BaseModel):
    alimento_id: int
    lote_numero: Optional[str] = None
    data_fabricacao: datetime
    data_validade: datetime
    quantidade_produzida: float
    unidade_medida: Optional[str] = None
    quantidade_etiquetas: Optional[int] = 1
    fabricante: Optional[str] = None
    sif: Optional[str] = None
    peso_liquido: Optional[str] = None
    ingredientes: Optional[str] = None
    informacao_nutricional: Optional[str] = None
    modo_conservacao: Optional[str] = None
    responsavel_tecnico: Optional[str] = None
    observacoes: Optional[str] = None


class ProdutoLoteCreate(ProdutoLoteBase):
    imprimir_etiqueta: bool = True  # Se True, cria print job automaticamente


class ProdutoLoteResponse(ProdutoLoteBase):
    id: int
    tenant_id: int
    qr_code: str
    quantidade_disponivel: float
    ativo: bool
    usado_completamente: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    lote_numero: str


    class Config:
        from_attributes = True


# ============= MOVIMENTAÇÃO SCHEMAS =============
class MovimentacaoEstoqueBase(BaseModel):
    alimento_id: int
    tipo: str  # entrada, saida, ajuste, uso
    quantidade: float
    motivo: Optional[str] = None


class MovimentacaoEstoqueCreate(MovimentacaoEstoqueBase):
    lote_id: Optional[int] = None


class MovimentacaoEstoqueResponse(MovimentacaoEstoqueBase):
    id: int
    tenant_id: int
    lote_id: Optional[int] = None
    usuario_id: int
    quantidade_anterior: Optional[float] = None
    quantidade_nova: Optional[float] = None
    qr_code_usado: Optional[str] = None
    localizacao: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============= PRINT JOB SCHEMAS =============
class PrintJobResponse(BaseModel):
    id: int
    tenant_id: int
    lote_id: int
    status: str
    tentativas: int
    erro_mensagem: Optional[str] = None
    etiqueta_data: Optional[str] = None
    created_at: datetime
    printed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============= QR CODE SCHEMAS =============
class QRCodeValidateRequest(BaseModel):
    qr_code: str


class QRCodeValidateResponse(BaseModel):
    valido: bool
    lote: Optional[ProdutoLoteResponse] = None
    alimento_nome: Optional[str] = None
    mensagem: Optional[str] = None


class QRCodeUsarRequest(BaseModel):
    qr_code: str
    quantidade: float
    motivo: Optional[str] = None
    localizacao: Optional[str] = None  # GPS coords


# ============= ALERTAS SCHEMAS =============
class AlertasLoteItem(BaseModel):
    id: int
    alimento_id: int
    alimento_nome: str
    lote_numero: str
    data_validade: datetime
    quantidade_disponivel: float
    unidade_medida: Optional[str] = None


class AlertasLotesResponse(BaseModel):
    vencidos: list[AlertasLoteItem]
    vencendo: list[AlertasLoteItem]
    total_vencidos: int
    total_vencendo: int


class QRCodeUsarResponse(BaseModel):
    sucesso: bool
    mensagem: str
    quantidade_restante: float
    movimentacao_id: int
