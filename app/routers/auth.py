from fastapi import APIRouter, Depends, HTTPException, Request, status, Response
from sqlalchemy.orm import Session
import logging

from app.database import get_db
from app.models import User, Tenant
from app.schemas import LoginRequest, Token, ConsentRequest
from app.security import verify_password, create_access_token, get_current_user
from app.rate_limit import limiter
from datetime import timedelta
from app.config import settings
from app.services.audit import registrar_auditoria
from app.security_helpers import validate_user_tenant_access, get_user_tenants

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])


def _registrar_login_audit(
    db: Session,
    request: Request,
    action: str,
    detail: str,
    user: User | None = None,
):
    registrar_auditoria(
        db,
        user_id=user.id if user else None,
        tenant_id=None,
        action=action,
        resource="auth",
        resource_id=user.id if user else None,
        details=detail,
        request=request,
    )
    db.commit()


@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(request: Request, credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Endpoint de login.
    Aceita email e senha, retorna token JWT e lista de restaurantes disponíveis.
    """
    from sqlalchemy.orm import joinedload
    
    # Busca usuário pelo email com restaurantes carregados
    user = db.query(User).options(joinedload(User.tenants)).filter(User.email == credentials.email).first()
    
    if not user or not verify_password(credentials.senha, user.senha_hash):
        _registrar_login_audit(
            db,
            request,
            "LOGIN_FAILED",
            f"Credenciais inválidas para {credentials.email}",
            user,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.ativo:
        _registrar_login_audit(
            db,
            request,
            "LOGIN_BLOCKED",
            f"Usuário {user.email} inativo",
            user,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )
    
    # Verificar se o cliente (empresa) está ativo
    if user.cliente_id:
        from app.models import Cliente
        cliente = db.query(Cliente).filter(Cliente.id == user.cliente_id).first()
        if cliente and not cliente.ativo:
            _registrar_login_audit(
                db,
                request,
                "LOGIN_BLOCKED",
                f"Cliente {cliente.id} bloqueado",
                user,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Empresa bloqueada. Entre em contato com o suporte."
            )
    
    # Verificar se usuário não-admin tem pelo menos um restaurante ativo
    if not user.is_admin and user.tenants:
        restaurantes_ativos = [t for t in user.tenants if t.ativo]
        if not restaurantes_ativos:
            _registrar_login_audit(
                db,
                request,
                "LOGIN_BLOCKED",
                f"Usuário {user.email} sem restaurantes ativos",
                user,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Todos os restaurantes estão bloqueados. Entre em contato com o suporte."
            )
    
    # Para usuários admin, não tem tenant_id fixo
    # Para usuários de cliente, retorna os tenants que tem acesso (apenas os ativos no token)
    tenant_ids = [t.id for t in user.tenants if t.ativo] if user.tenants else []
    # Mas retorna todos os restaurantes (incluindo bloqueados) para o frontend exibir
    restaurantes = [
        {
            "id": t.id,
            "nome": t.nome,
            "slug": t.slug,
            "ativo": t.ativo
        }
        for t in user.tenants
    ] if user.tenants else []
    
    # Cria token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "cliente_id": user.cliente_id,
            "tenant_ids": tenant_ids,  # Múltiplos tenants
            "is_admin": user.is_admin,
        },
        expires_delta=access_token_expires
    )
    
    resposta = {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "nome": user.nome,
            "email": user.email,
            "is_admin": user.is_admin,
            "cliente_id": user.cliente_id,
            "restaurantes": restaurantes,
            "lgpd_consent": user.lgpd_consent,
        }
    }
    _registrar_login_audit(
        db,
        request,
        "LOGIN_SUCCESS",
        f"Login bem-sucedido para {user.email}",
        user,
    )
    return resposta


@router.get("/me")
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna informações do usuário logado com seus restaurantes e roles"""
    from app.models import user_tenants_association
    from sqlalchemy import select
    
    # Busca o usuário novamente para garantir que temos os relacionamentos carregados
    user = db.query(User).filter(User.id == current_user.id).first()
    
    if not user:
        logger.error(f"Usuário {current_user.id} não encontrado em /me")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Monta lista de restaurantes com roles (incluindo bloqueados)
    restaurantes = []
    for tenant in user.tenants:
        # Busca o role na tabela de associação
        stmt = select(user_tenants_association).where(
            user_tenants_association.c.user_id == user.id,
            user_tenants_association.c.tenant_id == tenant.id
        )
        result = db.execute(stmt).first()
        
        restaurantes.append({
            "id": tenant.id,
            "nome": tenant.nome,
            "slug": tenant.slug,
            "ativo": tenant.ativo,
            "role": result.role if result else None
        })
    
    return {
        "id": user.id,
        "nome": user.nome,
        "email": user.email,
        "cliente_id": user.cliente_id,
        "restaurantes": restaurantes,
        "is_admin": user.is_admin,
        "lgpd_consent": user.lgpd_consent,
    }


@router.post("/consent")
def registrar_consentimento(
    request: Request,
    payload: ConsentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registra o aceite do termo de consentimento LGPD."""
    if not payload.accepted:
        raise HTTPException(status_code=400, detail="É necessário aceitar o termo de consentimento.")

    if current_user.lgpd_consent:
        return {"message": "Consentimento já registrado."}

    current_user.lgpd_consent = True
    registrar_auditoria(
        db,
        user_id=current_user.id,
        tenant_id=None,
        action="CONSENT_ACCEPTED",
        resource="lgpd",
        resource_id=current_user.id,
        details="Usuário aceitou o termo de consentimento",
        request=request,
    )
    db.commit()

    return {"message": "Consentimento registrado com sucesso."}


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Faz logout do usuário.
    Remove o token dos cookies e registra na auditoria.
    """
    response = Response(
        content='{"message": "Logout realizado com sucesso"}',
        status_code=status.HTTP_200_OK,
        media_type="application/json"
    )
    
    # Remove token do cookie HttpOnly
    response.delete_cookie(
        key="access_token",
        path="/",
        domain=f".{settings.BASE_DOMAIN}" if settings.BASE_DOMAIN else None,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE
    )
    
    # Registra logout na auditoria
    registrar_auditoria(
        db,
        user_id=current_user.id,
        tenant_id=None,
        action="LOGOUT",
        resource="auth",
        resource_id=current_user.id,
        details=f"Logout de {current_user.email}",
        request=request,
    )
    db.commit()
    
    logger.info(f"✅ Logout bem-sucedido para {current_user.email}")
    return response


@router.post("/refresh", response_model=Token)
@limiter.limit("60/minute")
def refresh_token(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Renova o token JWT sem exigir email/senha.
    Valida se o usuário ainda está ativo e tem acesso aos restaurantes.
    """
    # Revalida se usuário ainda está ativo
    if not current_user.ativo:
        logger.warning(f"❌ Tentativa de refresh com usuário inativo: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo"
        )
    
    # Revalida se cliente ainda está ativo
    if current_user.cliente_id:
        from app.models import Cliente
        cliente = db.query(Cliente).filter(Cliente.id == current_user.cliente_id).first()
        if cliente and not cliente.ativo:
            logger.warning(f"❌ Tentativa de refresh com cliente bloqueado: {current_user.cliente_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Empresa bloqueada"
            )
    
    # Regenera lista de tenants (revalida contra BD)
    tenant_ids = get_user_tenants(current_user, db)
    
    if not current_user.is_admin and len(tenant_ids) == 0:
        logger.warning(f"❌ Usuário sem restaurantes ativos no refresh: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nenhum restaurante disponível"
        )
    
    # Cria novo token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": current_user.email,
            "user_id": current_user.id,
            "cliente_id": current_user.cliente_id,
            "tenant_ids": tenant_ids,
            "is_admin": current_user.is_admin,
        },
        expires_delta=access_token_expires
    )
    
    # Prepara resposta com cookie
    response_data = {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": current_user.id,
            "nome": current_user.nome,
            "email": current_user.email,
            "is_admin": current_user.is_admin,
            "cliente_id": current_user.cliente_id,
            "restaurantes": [
                {
                    "id": t.id,
                    "nome": t.nome,
                    "slug": t.slug,
                    "ativo": t.ativo
                }
                for t in current_user.tenants
            ],
            "lgpd_consent": current_user.lgpd_consent,
        }
    }
    
    logger.info(f"✅ Token renovado para {current_user.email}")
    return response_data


@router.get("/verify", response_model=dict)
def verify_token_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Verifica se o token é válido e revalida acesso.
    Útil para verificar sessão no frontend.
    """
    # Revalida se usuário está ativo
    if not current_user.ativo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário inativo"
        )
    
    tenant_ids = get_user_tenants(current_user, db)
    
    return {
        "valid": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "is_admin": current_user.is_admin,
        "tenant_ids": tenant_ids
    }


