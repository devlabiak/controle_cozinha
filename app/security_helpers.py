"""
Helpers de segurança para validação de tenant_id e acesso multi-tenant
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import User, Tenant, user_tenants_association, RoleType
import logging

logger = logging.getLogger(__name__)


def validate_user_tenant_access(
    user: User,
    tenant_id: int,
    db: Session,
    required_role: str = "leitura"
) -> bool:
    """
    Valida se um usuário tem acesso a um tenant específico.
    
    Args:
        user: Usuário autenticado
        tenant_id: ID do tenant a acessar
        db: Sessão do banco de dados
        required_role: Role mínima necessária ('leitura' ou 'admin')
    
    Returns:
        True se tem acesso, False caso contrário
    
    Raises:
        HTTPException com status 403 se não tem acesso
    """
    
    # Admin SaaS tem acesso total
    if user.is_admin:
        logger.debug(f"✅ Admin SaaS (user_id={user.id}) acesso total")
        return True
    
    # Verifica se usuário está ativo
    if not user.ativo:
        logger.warning(f"❌ Usuário inativo (user_id={user.id}) tentou acessar tenant {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )
    
    # Verifica se cliente está ativo
    if user.cliente_id:
        cliente = db.query(None).from_statement(
            select(None).where(None)
        ).scalar()
        # Importar aqui para evitar circular import
        from app.models import Cliente
        cliente = db.query(Cliente).filter(Cliente.id == user.cliente_id).first()
        if cliente and not cliente.ativo:
            logger.warning(f"❌ Cliente inativo (cliente_id={user.cliente_id}) tentou acessar tenant {tenant_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Empresa bloqueada"
            )
    
    # Busca o relacionamento na tabela de associação
    stmt = select(user_tenants_association).where(
        user_tenants_association.c.user_id == user.id,
        user_tenants_association.c.tenant_id == tenant_id
    )
    result = db.execute(stmt).first()
    
    if not result:
        logger.warning(f"❌ Usuário (user_id={user.id}) não vinculado a tenant {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado a este restaurante"
        )
    
    # Verifica role necessária
    user_role = result.role
    
    if required_role == "admin":
        if user_role != RoleType.ADMIN:
            logger.warning(f"❌ Usuário (user_id={user.id}) sem permissão admin em tenant {tenant_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissão negada. Apenas administradores podem realizar esta ação."
            )
    elif required_role == "leitura":
        if user_role not in [RoleType.ADMIN, RoleType.LEITURA]:
            logger.warning(f"❌ Usuário (user_id={user.id}) sem permissão em tenant {tenant_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado"
            )
    
    logger.debug(f"✅ Usuário (user_id={user.id}) autorizado em tenant {tenant_id} com role {user_role}")
    return True


def validate_tenant_exists(tenant_id: int, db: Session) -> Tenant:
    """
    Valida se um tenant existe e está ativo.
    
    Args:
        tenant_id: ID do tenant
        db: Sessão do banco de dados
    
    Returns:
        Objeto Tenant se existe
    
    Raises:
        HTTPException com status 404 se não existe
    """
    tenant = db.query(Tenant).filter(
        Tenant.id == tenant_id,
        Tenant.ativo == True
    ).first()
    
    if not tenant:
        logger.warning(f"❌ Tentativa de acesso a tenant inválido/inativo: {tenant_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurante não encontrado ou inativo"
        )
    
    return tenant


def require_admin_access(user: User, tenant_id: int, db: Session) -> bool:
    """
    Valida que um usuário é admin no tenant específico.
    
    Args:
        user: Usuário autenticado
        tenant_id: ID do tenant
        db: Sessão do banco de dados
    
    Returns:
        True se é admin
    
    Raises:
        HTTPException com status 403 se não é admin
    """
    return validate_user_tenant_access(user, tenant_id, db, required_role="admin")


def get_user_tenants(user: User, db: Session) -> list:
    """
    Obtém lista de IDs de tenants que o usuário tem acesso.
    
    Args:
        user: Usuário autenticado
        db: Sessão do banco de dados
    
    Returns:
        Lista de IDs de tenants
    """
    if user.is_admin:
        # Admin tem acesso a todos os tenants ativos
        return [t.id for t in db.query(Tenant).filter(Tenant.ativo == True).all()]
    
    # Usuário comum tem acesso apenas aos tenants associados
    return [t.id for t in user.tenants if t.ativo]
