from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.middleware import TenantMiddleware
from app.routers import (
    auth, admin_tenants, admin_users, admin_clientes,
    tenant_alimentos, tenant_users, tenant_lotes,
    qrcode, print_jobs
)

app = FastAPI(
    title="Controle de Cozinha - Multi-Tenant",
    description="Sistema de controle de estoque para restaurantes (SaaS)",
    version="1.0.0"
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
app.include_router(admin_tenants.router)
app.include_router(admin_users.router)
app.include_router(tenant_alimentos.router)
app.include_router(tenant_users.router)
app.include_router(tenant_lotes.router)
app.include_router(qrcode.router)
app.include_router(print_jobs.router)


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
