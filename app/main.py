from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.middleware import TenantMiddleware
import traceback

# Importar routers com error handling
try:
    from app.routers import auth, admin_clientes, admin_usuarios, tenant_alimentos
    print("✓ Routers importados com sucesso")
except Exception as e:
    print(f"✗ Erro ao importar routers: {e}")
    raise

app = FastAPI(
    title="Controle de Cozinha - Multi-Tenant",
    description="Sistema de controle de estoque para restaurantes (SaaS)",
    version="1.0.0"
)

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
    allow_origins=["*"],  # Em produção, especifique os domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de Tenant
app.add_middleware(TenantMiddleware)

# Routers
app.include_router(auth.router)
app.include_router(admin_clientes.router)
app.include_router(admin_usuarios.router)
app.include_router(tenant_alimentos.router)


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
