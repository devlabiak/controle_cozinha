from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserUpdate, UserResponse
from app.auth import get_current_tenant_admin, get_password_hash
from app.middleware import get_tenant_id

router = APIRouter(prefix="/api/tenant/users", tags=["Tenant - Gestão de Usuários"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Cria novo usuário no restaurante"""
    tenant_id = get_tenant_id(request)
    
    # Verifica se o admin pertence ao tenant
    if current_admin.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    # Verifica se email já existe
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{user_data.email}' já está em uso"
        )
    
    new_user = User(
        tenant_id=tenant_id,
        nome=user_data.nome,
        email=user_data.email,
        senha_hash=get_password_hash(user_data.senha),
        is_tenant_admin=user_data.is_tenant_admin,
        ativo=True
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.get("/", response_model=List[UserResponse])
def list_users(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Lista todos os usuários do restaurante"""
    tenant_id = get_tenant_id(request)
    
    # Verifica se o admin pertence ao tenant
    if current_admin.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    users = db.query(User).filter(
        User.tenant_id == tenant_id
    ).offset(skip).limit(limit).all()
    
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Obtém detalhes de um usuário específico"""
    tenant_id = get_tenant_id(request)
    
    # Verifica se o admin pertence ao tenant
    if current_admin.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == tenant_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_data: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Atualiza dados de um usuário"""
    tenant_id = get_tenant_id(request)
    
    # Verifica se o admin pertence ao tenant
    if current_admin.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == tenant_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Atualiza apenas os campos fornecidos
    update_data = user_data.dict(exclude_unset=True)
    
    # Se a senha foi fornecida, gera o hash
    if "senha" in update_data:
        update_data["senha_hash"] = get_password_hash(update_data.pop("senha"))
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_tenant_admin)
):
    """Deleta um usuário"""
    tenant_id = get_tenant_id(request)
    
    # Verifica se o admin pertence ao tenant
    if current_admin.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado"
        )
    
    user = db.query(User).filter(
        User.id == user_id,
        User.tenant_id == tenant_id
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Não permite deletar o próprio usuário
    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível deletar seu próprio usuário"
        )
    
    db.delete(user)
    db.commit()
    
    return None
