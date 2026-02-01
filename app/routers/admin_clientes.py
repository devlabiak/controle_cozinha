"""
Rotas de Administração SaaS
Gerencia clientes, restaurantes e usuários
Acesso: painelfood.wlsolucoes.eti.br
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Cliente, Tenant, User, RoleType, user_tenants_association, user_clientes_association
from app.security import get_password_hash, verify_password, create_access_token
from pydantic import BaseModel, EmailStr
from datetime import timedelta
from sqlalchemy import and_

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ==================== SCHEMAS ====================

class ClienteCreate(BaseModel):
    nome_empresa: str
    email: EmailStr
    telefone: str | None = None
    cnpj: str | None = None
    endereco: str | None = None
    cidade: str | None = None
    estado: str | None = None


class ClienteResponse(BaseModel):
    id: int
    nome_empresa: str
    email: str
    telefone: str | None
    cnpj: str | None
    ativo: bool

    class Config:
        from_attributes = True


class RestauranteCreate(BaseModel):
    cliente_id: int
    nome: str
    slug: str  # URL slug único
    email: str
    telefone: str | None = None
    cnpj: str | None = None
    endereco: str | None = None


class RestauranteResponse(BaseModel):
    id: int
    cliente_id: int
    nome: str
    slug: str
    email: str
    ativo: bool

    class Config:
        from_attributes = True


class UsuarioCreate(BaseModel):
    cliente_id: int
    nome: str
    email: EmailStr
    senha: str
    is_admin: bool = False


class UsuarioResponse(BaseModel):
    id: int
    cliente_id: int | None
    nome: str
    email: str
    is_admin: bool
    ativo: bool

    class Config:
        from_attributes = True


class UsuarioClienteResponse(BaseModel):
    """Modelo para retornar usuário com lista de clientes associados"""
    id: int
    cliente_id: int  # Cliente principal (criador)
    nome: str
    email: str
    is_admin: bool
    ativo: bool
    clientes_acesso: List['ClienteResponse'] = []  # Empresas extras que o usuário pode acessar

    class Config:
        from_attributes = True


class RestauranteUsuarioLink(BaseModel):
    user_id: int
    tenant_id: int
    role: str = "leitura"  # "admin" ou "leitura"


class UsuarioRestauranteResponse(BaseModel):
    """Resposta com dados do usuário + restaurantes + roles"""
    id: int
    nome: str
    email: str
    restaurantes: List[dict] = []  # Lista com {id, nome, slug, role}

    class Config:
        from_attributes = True


# ==================== DEPENDENCIES ====================

def get_admin_user(db: Session = Depends(get_db)) -> User:
    """
    Em produção, validar JWT token e verificar is_admin
    Por enquanto, assume que apenas admin pode chamar essas rotas
    """
    # TODO: Implementar validação de token
    return None


# ==================== CLIENTES ====================

@router.post("/clientes", response_model=ClienteResponse)
def criar_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    """Cria novo cliente (proprietário de restaurantes)"""
    
    # Verificar se email já existe
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
    """Lista todos os clientes"""
    clientes = db.query(Cliente).filter(Cliente.ativo == True).all()
    return clientes


@router.get("/clientes/{cliente_id}", response_model=ClienteResponse)
def obter_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Obtém dados de um cliente específico"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    return cliente


@router.put("/clientes/{cliente_id}", response_model=ClienteResponse)
def atualizar_cliente(cliente_id: int, dados: ClienteCreate, db: Session = Depends(get_db)):
    """Atualiza dados do cliente"""
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


# ==================== RESTAURANTES ====================

@router.post("/restaurantes", response_model=RestauranteResponse)
def criar_restaurante(restaurante: RestauranteCreate, db: Session = Depends(get_db)):
    """Cria novo restaurante para um cliente"""
    
    # Verificar se cliente existe
    cliente = db.query(Cliente).filter(Cliente.id == restaurante.cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    # Normalizar campos
    restaurante.slug = restaurante.slug.strip()
    restaurante.email = restaurante.email.strip().lower()
    restaurante.telefone = restaurante.telefone.strip() if restaurante.telefone else None
    restaurante.cnpj = restaurante.cnpj.strip() if restaurante.cnpj else None
    restaurante.endereco = restaurante.endereco.strip() if restaurante.endereco else None

    # Verificar se slug já existe
    slug_existente = db.query(Tenant).filter(Tenant.slug == restaurante.slug).first()
    if slug_existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slug (URL) já cadastrado"
        )

    # Verificar se email já existe
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
def listar_restaurantes(cliente_id: int | None = None, db: Session = Depends(get_db)):
    """Lista restaurantes (opcionalmente filtrados por cliente)"""
    query = db.query(Tenant).filter(Tenant.ativo == True)
    
    if cliente_id:
        query = query.filter(Tenant.cliente_id == cliente_id)
    
    return query.all()


@router.get("/clientes/{cliente_id}/restaurantes", response_model=List[RestauranteResponse])
def listar_restaurantes_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Lista restaurantes de um cliente específico"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    return cliente.tenants


@router.get("/restaurantes/{restaurante_id}", response_model=RestauranteResponse)
def obter_restaurante(restaurante_id: int, db: Session = Depends(get_db)):
    """Obtém dados de um restaurante específico"""
    restaurante = db.query(Tenant).filter(Tenant.id == restaurante_id).first()
    if not restaurante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurante não encontrado"
        )
    
    return restaurante


@router.put("/restaurantes/{restaurante_id}", response_model=RestauranteResponse)
def atualizar_restaurante(restaurante_id: int, dados: RestauranteCreate, db: Session = Depends(get_db)):
    """Atualiza dados de um restaurante"""
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
    """Desativa um restaurante"""
    restaurante = db.query(Tenant).filter(Tenant.id == restaurante_id).first()
    if not restaurante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurante não encontrado"
        )
    
    restaurante.ativo = False
    db.commit()


# ==================== USUÁRIOS ====================

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
    
    # Verificar se email já existe
    existente = db.query(User).filter(User.email == usuario.email).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado"
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
def listar_usuarios(cliente_id: int | None = None, db: Session = Depends(get_db)):
    """Lista usuários com seus clientes associados (opcionalmente filtrados por cliente principal)"""
    query = db.query(User).filter(User.ativo == True)
    
    if cliente_id:
        query = query.filter(User.cliente_id == cliente_id)
    
    usuarios = query.all()
    resultado = []
    
    for usuario in usuarios:
        usuario_data = {
            'id': usuario.id,
            'cliente_id': usuario.cliente_id,
            'nome': usuario.nome,
            'email': usuario.email,
            'is_admin': usuario.is_admin,
            'ativo': usuario.ativo,
            'clientes_acesso': [
                {
                    'id': c.id,
                    'nome_empresa': c.nome_empresa,
                    'email': c.email,
                    'telefone': c.telefone,
                    'cnpj': c.cnpj,
                    'ativo': c.ativo
                }
                for c in usuario.clientes_acesso
            ]
        }
        resultado.append(usuario_data)
    
    return resultado


@router.get("/clientes/{cliente_id}/usuarios", response_model=List[UsuarioResponse])
def listar_usuarios_cliente(cliente_id: int, db: Session = Depends(get_db)):
    """Lista usuários de um cliente específico"""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    return cliente.users


@router.post("/usuarios/{user_id}/restaurantes/{tenant_id}")
def adicionar_usuario_restaurante(
    user_id: int, 
    tenant_id: int,
    role: str = "leitura",  # "admin" ou "leitura"
    db: Session = Depends(get_db)
):
    """Associa um usuário a um restaurante com role específico"""
    
    # Validar role
    if role not in ["admin", "leitura"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role inválido. Deve ser 'admin' ou 'leitura'"
        )
    
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    restaurante = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not restaurante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurante não encontrado"
        )
    
    # Verificar se mesmo cliente
    if usuario.cliente_id != restaurante.cliente_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário e restaurante devem ser do mesmo cliente"
        )
    
    # Verificar se já existe a associação
    existing = db.query(user_tenants_association).filter(
        and_(
            user_tenants_association.c.user_id == user_id,
            user_tenants_association.c.tenant_id == tenant_id
        )
    ).first()
    
    if existing:
        # Atualizar role se já existe
        db.execute(
            user_tenants_association.update()
            .where(and_(
                user_tenants_association.c.user_id == user_id,
                user_tenants_association.c.tenant_id == tenant_id
            ))
            .values(role=role)
        )
        db.commit()
        return {"message": f"Usuário associado ao restaurante com role '{role}' (atualizado)"}
    else:
        # Adicionar nova associação
        stmt = user_tenants_association.insert().values(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role
        )
        db.execute(stmt)
        db.commit()
        return {"message": f"Usuário associado ao restaurante com role '{role}'"}



@router.delete("/usuarios/{user_id}/restaurantes/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_usuario_restaurante(user_id: int, tenant_id: int, db: Session = Depends(get_db)):
    """Remove um usuário de um restaurante"""
    
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    restaurante = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not restaurante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurante não encontrado"
        )
    
    db.execute(
        user_tenants_association.delete().where(
            and_(
                user_tenants_association.c.user_id == user_id,
                user_tenants_association.c.tenant_id == tenant_id
            )
        )
    )
    db.commit()


@router.get("/restaurantes/{tenant_id}/usuarios", response_model=List[dict])
def listar_usuarios_restaurante(tenant_id: int, db: Session = Depends(get_db)):
    """Lista usuários de um restaurante com seus roles"""
    
    restaurante = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not restaurante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurante não encontrado"
        )
    
    # Query para pegar usuários + roles
    resultado = db.query(User, user_tenants_association.c.role).join(
        user_tenants_association,
        User.id == user_tenants_association.c.user_id
    ).filter(
        user_tenants_association.c.tenant_id == tenant_id
    ).all()
    
    usuarios = []
    for user, role in resultado:
        usuarios.append({
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "role": role
        })
    
    return usuarios


@router.put("/usuarios/{user_id}/restaurantes/{tenant_id}/role")
def atualizar_role_usuario(
    user_id: int,
    tenant_id: int,
    role: str,  # Query parameter
    db: Session = Depends(get_db)
):
    """Atualiza o role de um usuário em um restaurante específico"""
    
    # Normalizar para minúsculas
    role = role.lower()
    
    # Validar role
    if role not in ["admin", "leitura"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role inválido. Deve ser 'admin' ou 'leitura'"
        )
    
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    restaurante = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not restaurante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurante não encontrado"
        )
    
    # Verificar se associação existe
    existing = db.query(user_tenants_association).filter(
        and_(
            user_tenants_association.c.user_id == user_id,
            user_tenants_association.c.tenant_id == tenant_id
        )
    ).first()
    
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não tem acesso a este restaurante"
        )
    
    # Atualizar role
    db.execute(
        user_tenants_association.update()
        .where(and_(
            user_tenants_association.c.user_id == user_id,
            user_tenants_association.c.tenant_id == tenant_id
        ))
        .values(role=role)
    )
    db.commit()
    
    return {"message": f"Role do usuário atualizado para '{role}'"}


# ==================== COMPARTILHAMENTO DE USUÁRIOS ===================

@router.post("/usuarios/{user_id}/clientes/{cliente_id}")
def adicionar_usuario_cliente(
    user_id: int,
    cliente_id: int,
    db: Session = Depends(get_db)
):
    """Compartilha um usuário com outra empresa (cliente)
    Permite que o usuário acesse múltiplas empresas"""
    
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    # Evitar adicionar o cliente principal novamente
    if usuario.cliente_id == cliente_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Este é o cliente principal do usuário"
        )
    
    # Verificar se já existe a associação
    existing = db.query(user_clientes_association).filter(
        and_(
            user_clientes_association.c.user_id == user_id,
            user_clientes_association.c.cliente_id == cliente_id
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário já tem acesso a este cliente"
        )
    
    # Adicionar a associação
    stmt = user_clientes_association.insert().values(
        user_id=user_id,
        cliente_id=cliente_id
    )
    db.execute(stmt)
    db.commit()
    
    return {"message": f"Usuário {usuario.nome} agora tem acesso à empresa {cliente.nome_empresa}"}


@router.delete("/usuarios/{user_id}/clientes/{cliente_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_usuario_cliente(
    user_id: int,
    cliente_id: int,
    db: Session = Depends(get_db)
):
    """Remove o acesso de um usuário a uma empresa específica"""
    
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    # Evitar remover o cliente principal
    if usuario.cliente_id == cliente_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível remover o cliente principal do usuário"
        )
    
    # Remover a associação
    db.execute(
        user_clientes_association.delete().where(
            and_(
                user_clientes_association.c.user_id == user_id,
                user_clientes_association.c.cliente_id == cliente_id
            )
        )
    )
    db.commit()


@router.get("/usuarios/{user_id}/clientes-disponiveis")
def listar_clientes_disponiveis(user_id: int, db: Session = Depends(get_db)):
    """Lista clientes disponíveis para compartilhar com um usuário
    (clientes que o usuário ainda não tem acesso)"""
    
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Pegar todos os clientes ativos
    todos_clientes = db.query(Cliente).filter(Cliente.ativo == True).all()
    
    # Pegar clientes que o usuário já tem acesso (principal + compartilhados)
    clientes_usuario = [usuario.cliente_id]
    for c in usuario.clientes_acesso:
        clientes_usuario.append(c.id)
    
    # Filtrar clientes disponíveis
    clientes_disponiveis = [
        {
            'id': c.id,
            'nome_empresa': c.nome_empresa,
            'email': c.email,
            'telefone': c.telefone,
            'cnpj': c.cnpj,
            'ativo': c.ativo
        }
        for c in todos_clientes if c.id not in clientes_usuario
    ]
    
    return clientes_disponiveis


@router.get("/usuarios/{user_id}/todas-empresas")
def listar_todas_empresas_usuario(user_id: int, db: Session = Depends(get_db)):
    """Lista todas as empresas que um usuário pode acessar
    (empresa principal + empresas compartilhadas)"""
    
    usuario = db.query(User).filter(User.id == user_id).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Empresa principal
    empresas = [
        {
            'id': usuario.cliente.id,
            'nome_empresa': usuario.cliente.nome_empresa,
            'email': usuario.cliente.email,
            'telefone': usuario.cliente.telefone,
            'cnpj': usuario.cliente.cnpj,
            'ativo': usuario.cliente.ativo,
            'principal': True
        }
    ]
    
    # Empresas compartilhadas
    for c in usuario.clientes_acesso:
        empresas.append({
            'id': c.id,
            'nome_empresa': c.nome_empresa,
            'email': c.email,
            'telefone': c.telefone,
            'cnpj': c.cnpj,
            'ativo': c.ativo,
            'principal': False
        })
    
    return empresas
