from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Tenant
from app.config import settings


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
