import asyncio
import contextlib
import logging
import sys
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text

from app.config import settings
from app.middleware import TenantMiddleware
from app.rate_limit import limiter
from app.services.history_cleanup import cleanup_history, RETENTION_DAYS

# Configurar logging estruturado para produção
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
cleanup_logger = logging.getLogger("app.history_cleanup")

# Importar routers com error handling
try:
    from app.routers import auth, admin_clientes, admin_usuarios, tenant_alimentos, tenant_usuarios, admin_audit
    print("✓ Routers importados com sucesso")
except Exception as e:
    print(f"✗ Erro ao importar routers: {e}")
    raise

app = FastAPI(
    title="Controle de Cozinha - Multi-Tenant",
    description="Sistema de controle de estoque para restaurantes (SaaS)",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Exception handler para logar erros de autenticação
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if exc.status_code == 401:
        print(f"🔴 401 Unauthorized em {request.url.path}")
        print(f"   Headers: {dict(request.headers)}")
        print(f"   Detail: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=3600,
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Adiciona headers de segurança às respostas"""
    response = await call_next(request)
    
    # Previne clickjacking
    response.headers["X-Frame-Options"] = "DENY"
    
    # Desabilita MIME sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    
    # Ativa proteção contra XSS
    response.headers["X-XSS-Protection"] = "1; mode=block"
    
    # Content Security Policy (CSP)
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "img-src 'self' data: https:; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "connect-src 'self' https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    
    # HSTS (se em HTTPS)
    if settings.ENABLE_HTTPS_REDIRECT or request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    # Referrer Policy
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    return response

# Middleware de Tenant
app.add_middleware(TenantMiddleware)

# Routers
app.include_router(auth.router)
app.include_router(admin_clientes.router)
app.include_router(admin_usuarios.router)
app.include_router(tenant_alimentos.router)
app.include_router(tenant_usuarios.router)
app.include_router(admin_audit.router)


async def history_cleanup_worker():
    """Executa a limpeza do histórico uma vez por dia com retry logic robusto."""
    retry_count = 0
    max_retries = 5
    base_sleep = 60  # 1 minuto
    
    cleanup_logger.info("✅ Worker de limpeza de histórico iniciado")
    
    while True:
        try:
            removed = cleanup_history()
            if removed:
                cleanup_logger.info(
                    "🧹 Limpeza executada com sucesso: %s movimentações removidas (retenção: %s dias)",
                    removed, RETENTION_DAYS
                )
            else:
                cleanup_logger.debug("Limpeza executada: nenhuma movimentação antiga encontrada")
            
            # Reset retry counter em caso de sucesso
            retry_count = 0
            
            # Aguarda 24 horas até próxima execução
            await asyncio.sleep(24 * 60 * 60)
            
        except asyncio.CancelledError:
            cleanup_logger.info("🛑 Worker de limpeza cancelado (shutdown)")
            raise
            
        except Exception as e:
            retry_count += 1
            sleep_time = min(base_sleep * (2 ** retry_count), 3600)  # Máximo 1 hora
            
            cleanup_logger.error(
                "❌ Erro na limpeza de histórico (tentativa %s/%s): %s",
                retry_count, max_retries, str(e), exc_info=True
            )
            
            if retry_count >= max_retries:
                cleanup_logger.critical(
                    "🔥 FALHA CRÍTICA: Worker de limpeza falhou %s vezes consecutivas. "
                    "Requer atenção imediata!",
                    max_retries
                )
                # Notificar administrador (implementar webhook/email aqui)
            
            cleanup_logger.info("⏳ Aguardando %s segundos antes de tentar novamente...", sleep_time)
            await asyncio.sleep(sleep_time)


@app.on_event("startup")
async def startup_event():
    """Inicializa tasks e recursos na inicialização"""
    logger.info("🚀 Iniciando aplicação...")
    
    # Verifica conexão com banco de dados
    from app.database import SessionLocal
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Conexão com banco de dados OK")
    except Exception as e:
        logger.error("❌ Falha na conexão com banco de dados: %s", e)
        raise
    
    # Inicia worker de limpeza de histórico
    app.state.history_cleanup_task = asyncio.create_task(history_cleanup_worker())
    app.state.startup_time = datetime.utcnow()
    
    logger.info("✅ Aplicação inicializada com sucesso")


@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown - finaliza tasks e libera recursos"""
    logger.info("🔴 Iniciando shutdown graceful...")
    
    # Cancela task de limpeza
    task = getattr(app.state, "history_cleanup_task", None)
    if task:
        logger.info("🛑 Cancelando worker de limpeza de histórico...")
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        logger.info("✅ Worker de limpeza finalizado")
    
    # Fecha pool de conexões
    from app.database import engine
    logger.info("🔌 Fechando pool de conexões do banco...")
    engine.dispose()
    
    logger.info("✅ Shutdown completo")


@app.get("/")
def root():
    return {
        "message": "Controle de Cozinha - API Multi-Tenant",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check detalhado para monitoramento e load balancers"""
    from app.database import SessionLocal, get_pool_status
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": {}
    }
    
    # Verifica banco de dados
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        health_status["checks"]["database"] = "ok"
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = f"error: {str(e)}"
    
    # Verifica pool de conexões
    try:
        pool_status = get_pool_status()
        health_status["checks"]["connection_pool"] = {
            "status": "ok" if pool_status["checked_out"] < pool_status["size"] + pool_status["max_overflow"] else "warning",
            **pool_status
        }
    except Exception as e:
        health_status["checks"]["connection_pool"] = f"error: {str(e)}"
    
    # Verifica worker de limpeza
    task = getattr(app.state, "history_cleanup_task", None)
    if task:
        health_status["checks"]["cleanup_worker"] = "ok" if not task.done() else "stopped"
    else:
        health_status["checks"]["cleanup_worker"] = "not_started"
    
    # Uptime
    startup_time = getattr(app.state, "startup_time", None)
    if startup_time:
        uptime = (datetime.utcnow() - startup_time).total_seconds()
        health_status["uptime_seconds"] = uptime
    
    # Define status code baseado na saúde geral
    status_code = 200 if health_status["status"] == "healthy" else 503
    
    return JSONResponse(content=health_status, status_code=status_code)
