from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Float, Enum, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class StatusPrintJob(str, enum.Enum):
    PENDING = "pending"
    PRINTING = "printing"
    COMPLETED = "completed"
    FAILED = "failed"


class TipoMovimentacao(str, enum.Enum):
    ENTRADA = "entrada"
    SAIDA = "saida"
    AJUSTE = "ajuste"
    USO = "uso"  # Uso via QR Code


class RoleType(str, enum.Enum):
    """Tipos de acesso de usuário em um restaurante"""
    ADMIN = "admin"      # Pode criar/editar/deletar produtos e gerenciar estoque
    LEITURA = "leitura"  # Pode apenas ler QR code para dar baixa automática


# Tabela de Relacionamento Muitos-para-Muitos: User -> Clientes
# Permite que um usuário acesse múltiplas empresas
user_clientes_association = Table(
    'user_clientes_association',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('cliente_id', Integer, ForeignKey('clientes.id', ondelete='CASCADE'), primary_key=True),
)

# Tabela de Relacionamento Muitos-para-Muitos: User -> Tenants (com role)
user_tenants_association = Table(
    'user_tenants_association',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('tenant_id', Integer, ForeignKey('tenants.id', ondelete='CASCADE'), primary_key=True),
    Column('role', Enum(RoleType), default=RoleType.LEITURA, nullable=False),  # ✅ NOVO
)


class Cliente(Base):
    """Modelo de Cliente (proprietário de restaurantes)"""
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome_empresa = Column(String(255), nullable=False)  # Nome do negócio/proprietário
    email = Column(String(255), unique=True, nullable=False, index=True)
    telefone = Column(String(20))
    cnpj = Column(String(20), unique=True, nullable=True)
    endereco = Column(String(255))
    cidade = Column(String(100))
    estado = Column(String(2))
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    tenants = relationship("Tenant", back_populates="cliente", cascade="all, delete-orphan")
    users = relationship("User", back_populates="cliente", cascade="all, delete-orphan")
    usuarios_compartilhados = relationship("User", secondary=user_clientes_association, back_populates="clientes_acesso")


class Tenant(Base):
    """Modelo de Restaurante (Tenant)"""
    __tablename__ = "tenants"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)  # subdomínio
    email = Column(String(255), nullable=False)
    telefone = Column(String(20))
    cnpj = Column(String(20))
    endereco = Column(String(255))
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="tenants")
    users = relationship("User", secondary=user_tenants_association, back_populates="tenants")
    alimentos = relationship("Alimento", back_populates="tenant", cascade="all, delete-orphan")


class User(Base):
    """Modelo de Usuário"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    senha_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)  # Admin SaaS (painelfood)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    cliente = relationship("Cliente", back_populates="users")
    clientes_acesso = relationship("Cliente", secondary=user_clientes_association, back_populates="usuarios_compartilhados")
    tenants = relationship("Tenant", secondary=user_tenants_association, back_populates="users")
    movimentacoes = relationship("MovimentacaoEstoque", back_populates="usuario", cascade="all, delete-orphan")


class Alimento(Base):
    """Modelo de Alimento/Produto"""
    __tablename__ = "alimentos"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = Column(String(255), nullable=False)
    categoria = Column(String(100))
    subcategoria = Column(String(120))
    tipo_conservacao = Column(String(20))  # congelado, resfriado
    unidade_medida = Column(String(20))  # kg, g, l, ml, unidade
    quantidade_estoque = Column(Float, default=0)
    quantidade_minima = Column(Float, default=0)
    preco_unitario = Column(Float)
    fornecedor = Column(String(255))
    observacoes = Column(Text)
    ativo = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Relacionamentos
    tenant = relationship("Tenant", back_populates="alimentos")
    lotes = relationship("ProdutoLote", back_populates="alimento", cascade="all, delete-orphan")
    movimentacoes = relationship("MovimentacaoEstoque", back_populates="alimento", cascade="all, delete-orphan")


class ProdutoLote(Base):
    """Modelo de Lote de Produto (cada etiqueta impressa)"""
    __tablename__ = "produto_lotes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    alimento_id = Column(Integer, ForeignKey("alimentos.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Identificação do lote
    lote_numero = Column(String(50), nullable=False, index=True)  # Ex: 20260201001
    qr_code = Column(String(100), unique=True, nullable=False, index=True)  # UUID único
    
    # Datas
    data_fabricacao = Column(DateTime(timezone=True), nullable=False)
    data_validade = Column(DateTime(timezone=True), nullable=False)
    
    # Quantidades
    quantidade_produzida = Column(Float, nullable=False)  # Quantidade total do lote
    quantidade_disponivel = Column(Float, nullable=False)  # Quantidade ainda disponível
    unidade_medida = Column(String(20))  # kg, g, l, ml, unidade
    quantidade_etiquetas = Column(Integer, default=1)  # Quantas etiquetas imprimir
    
    # Informações adicionais
    fabricante = Column(String(255))
    sif = Column(String(50))
    peso_liquido = Column(String(50))  # Ex: "500g"
    ingredientes = Column(Text)  # Lista de ingredientes
    informacao_nutricional = Column(Text)  # JSON com info nutricional
    modo_conservacao = Column(Text)  # Como conservar
    responsavel_tecnico = Column(String(255))  # Nome + CRN
    observacoes = Column(Text)
    
    # Status
    ativo = Column(Boolean, default=True)
    usado_completamente = Column(Boolean, default=False)  # True quando quantidade_disponivel = 0
    
    # Auditoria
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relacionamentos
    tenant = relationship("Tenant")
    alimento = relationship("Alimento", back_populates="lotes")
    print_jobs = relationship("PrintJob", back_populates="lote", cascade="all, delete-orphan")
    movimentacoes = relationship("MovimentacaoEstoque", back_populates="lote", cascade="all, delete-orphan")


class MovimentacaoEstoque(Base):
    """Modelo de Movimentação de Estoque (histórico)"""
    __tablename__ = "movimentacoes_estoque"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    alimento_id = Column(Integer, ForeignKey("alimentos.id", ondelete="CASCADE"), nullable=False, index=True)
    lote_id = Column(Integer, ForeignKey("produto_lotes.id", ondelete="CASCADE"), nullable=True, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Tipo de movimentação
    tipo = Column(Enum(TipoMovimentacao), nullable=False, index=True)
    
    # Quantidades
    quantidade = Column(Float, nullable=False)
    quantidade_anterior = Column(Float)  # Quantidade antes da movimentação
    quantidade_nova = Column(Float)  # Quantidade após a movimentação
    
    # Informações
    motivo = Column(Text)  # Motivo da movimentação
    qr_code_usado = Column(String(100))  # Se foi via QR code
    localizacao = Column(String(255))  # Localização GPS (opcional)
    
    # Auditoria
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relacionamentos
    tenant = relationship("Tenant")
    alimento = relationship("Alimento", back_populates="movimentacoes")
    lote = relationship("ProdutoLote", back_populates="movimentacoes")
    usuario = relationship("User", back_populates="movimentacoes")


class PrintJob(Base):
    """Modelo de Trabalho de Impressão"""
    __tablename__ = "print_jobs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    lote_id = Column(Integer, ForeignKey("produto_lotes.id", ondelete="CASCADE"), nullable=False)
    
    # Status
    status = Column(Enum(StatusPrintJob), default=StatusPrintJob.PENDING, index=True)
    
    # Tentativas
    tentativas = Column(Integer, default=0)
    erro_mensagem = Column(Text)
    
    # Dados da etiqueta (JSON cache)
    etiqueta_data = Column(Text)  # JSON com todos os dados para impressão
    
    # Auditoria
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    printed_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Relacionamentos
    tenant = relationship("Tenant")
    lote = relationship("ProdutoLote", back_populates="print_jobs")
