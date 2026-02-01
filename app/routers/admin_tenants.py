from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Tenant, User
from app.schemas import TenantCreate, TenantUpdate, TenantResponse
from app.auth import get_current_admin, get_password_hash
import re

router = APIRouter(prefix="/api/admin/tenants", tags=["Admin - Gestão de Restaurantes"])


def validate_slug(slug: str) -> str:
    """Valida e normaliza o slug do tenant"""
    # Remove caracteres especiais e espaços
    slug = re.sub(r'[^a-z0-9-]', '', slug.lower().strip())
    
    if not slug or len(slug) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Slug deve ter pelo menos 3 caracteres alfanuméricos"
        )
    
    return slug


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """
    Cria novo restaurante (tenant) e seu usuário admin.
    Apenas admin SaaS pode executar.
    """
    # Valida slug
    slug = validate_slug(tenant_data.slug)
    
    # Verifica se slug já existe
    if db.query(Tenant).filter(Tenant.slug == slug).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Slug '{slug}' já está em uso"
        )
    
    # Verifica se email do tenant já existe
    if db.query(Tenant).filter(Tenant.email == tenant_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{tenant_data.email}' já está em uso"
        )
    
    # Verifica se email do admin já existe
    if db.query(User).filter(User.email == tenant_data.admin_email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email do admin '{tenant_data.admin_email}' já está em uso"
        )
    
    # Cria o tenant
    new_tenant = Tenant(
        nome=tenant_data.nome,
        slug=slug,
        email=tenant_data.email,
        telefone=tenant_data.telefone
    )
    
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)
    
    # Cria o usuário admin do tenant
    admin_user = User(
        tenant_id=new_tenant.id,
        nome=tenant_data.admin_nome,
        email=tenant_data.admin_email,
        senha_hash=get_password_hash(tenant_data.admin_senha),
        is_tenant_admin=True,
        ativo=True
    )
    
    db.add(admin_user)
    db.commit()
    
    return new_tenant


@router.get("/", response_model=List[TenantResponse])
def list_tenants(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Lista todos os restaurantes (tenants)"""
    tenants = db.query(Tenant).offset(skip).limit(limit).all()
    return tenants


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Obtém detalhes de um restaurante específico"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurante não encontrado"
        )
    
    return tenant


@router.put("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: int,
    tenant_data: TenantUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Atualiza dados de um restaurante"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurante não encontrado"
        )
    
    # Atualiza apenas os campos fornecidos
    update_data = tenant_data.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(tenant, field, value)
    
    db.commit()
    db.refresh(tenant)
    
    return tenant


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Deleta um restaurante e todos os dados associados"""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurante não encontrado"
        )
    
    db.delete(tenant)
    db.commit()
    
    return None
