from fastapi import Request, HTTPException, status
from jose import JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import Tenant


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware para extrair o tenant_id do subdomínio e adicionar ao request.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Pega o host do request
        host = request.headers.get("host", "").split(":")[0]
        
        # Inicializa tenant_id como None
        tenant_id = None
        tenant_slug = None
        
        # Verifica se é um subdomínio
        if host.endswith(f".{settings.BASE_DOMAIN}"):
            # Extrai o slug (subdomínio)
            tenant_slug = host.replace(f".{settings.BASE_DOMAIN}", "")

            # Subdomínios que não representam restaurante
            non_tenant_subdomains = {"painelfood", "cozinha", "admin"}
            if tenant_slug in non_tenant_subdomains:
                request.state.tenant_id = None
                request.state.tenant_slug = tenant_slug
                return await call_next(request)
            
            # Busca o tenant no banco
            db = SessionLocal()
            try:
                tenant = db.query(Tenant).filter(
                    Tenant.slug == tenant_slug,
                    Tenant.ativo == True
                ).first()
                
                if tenant:
                    tenant_id = tenant.id
                else:
                    # Subdomínio não encontrado ou inativo
                    if not request.url.path.startswith("/docs") and not request.url.path.startswith("/openapi.json"):
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Restaurante '{tenant_slug}' não encontrado"
                        )
            finally:
                db.close()
        
        # Adiciona tenant_id e tenant_slug ao estado do request
        request.state.tenant_id = tenant_id
        request.state.tenant_slug = tenant_slug
        
        # Verifica se o usuário autenticado pode acessar o tenant
        authorization_header = request.headers.get("authorization")
        has_tenant_context = tenant_id is not None
        if has_tenant_context and authorization_header:
            scheme, _, token = authorization_header.partition(" ")
            if scheme.lower() != "bearer" or not token:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Cabeçalho de autenticação inválido"
                )
            
            try:
                payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            except JWTError:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido"
                )
            
            tenant_ids = payload.get("tenant_ids") or []
            is_admin = payload.get("is_admin", False)
            
            if not is_admin and tenant_id not in tenant_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Acesso negado a este restaurante"
                )
        
        # Continua o processamento
        response = await call_next(request)
        return response


def get_tenant_id(request: Request) -> int:
    """
    Dependency para obter o tenant_id do request.
    Usado em rotas que precisam filtrar por tenant.
    """
    tenant_id = getattr(request.state, "tenant_id", None)
    
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant não identificado. Acesse através do subdomínio do restaurante."
        )
    
    return tenant_id
