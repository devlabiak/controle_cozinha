import asyncio
import contextlib
import logging
import traceback

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.middleware import TenantMiddleware
from app.rate_limit import limiter
from app.services.history_cleanup import cleanup_history, RETENTION_DAYS

logger = logging.getLogger("app.history_cleanup")

# Importar routers com error handling
try:
    from app.routers import auth, admin_clientes, admin_usuarios, tenant_alimentos, tenant_usuarios
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
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=3600,
)

# Middleware de Tenant
app.add_middleware(TenantMiddleware)

# Routers
app.include_router(auth.router)
app.include_router(admin_clientes.router)
app.include_router(admin_usuarios.router)
app.include_router(tenant_alimentos.router)
app.include_router(tenant_usuarios.router)


async def history_cleanup_worker():
    """Executa a limpeza do histórico uma vez por dia."""
    while True:
        try:
            removed = cleanup_history()
            if removed:
                logger.info("🧹 %s movimentações antigas removidas (>%s dias)", removed, RETENTION_DAYS)
        except Exception:  # pragma: no cover
            logger.exception("Erro ao executar limpeza de histórico")
        await asyncio.sleep(24 * 60 * 60)


@app.on_event("startup")
async def startup_event():
    app.state.history_cleanup_task = asyncio.create_task(history_cleanup_worker())


@app.on_event("shutdown")
async def shutdown_event():
    task = getattr(app.state, "history_cleanup_task", None)
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task


@app.get("/")
def root():
    return {
        "message": "Controle de Cozinha - API Multi-Tenant",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
