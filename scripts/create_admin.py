"""
Script para criar o usuário admin inicial do SaaS
Execute: python scripts/create_admin.py
"""
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models import User
from app.auth import get_password_hash


def create_admin():
    db = SessionLocal()
    
    try:
        # Verifica se já existe um admin
        admin = db.query(User).filter(User.is_admin == True).first()
        
        if admin:
            print(f"✓ Admin já existe: {admin.email}")
            return
        
        # Cria o admin
        admin = User(
            nome="Administrador SaaS",
            email="admin@wlsolucoes.eti.br",
            senha_hash=get_password_hash("Admin@123"),
            is_admin=True,
            ativo=True
        )
        
        db.add(admin)
        db.commit()
        
        print("✓ Admin criado com sucesso!")
        print(f"  Email: {admin.email}")
        print(f"  Senha: Admin@123")
        print("\n⚠️  IMPORTANTE: Altere a senha após o primeiro login!")
        
    except Exception as e:
        print(f"✗ Erro ao criar admin: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
