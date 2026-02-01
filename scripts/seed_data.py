"""
Script para popular o banco com dados de exemplo
Execute: python scripts/seed_data.py
"""
import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.database import SessionLocal
from app.models import Tenant, User, Alimento
from app.auth import get_password_hash


def seed_data():
    db = SessionLocal()
    
    try:
        print("🌱 Populando banco de dados...\n")
        
        # Cria restaurante de exemplo
        restaurante = Tenant(
            nome="Restaurante Exemplo",
            slug="exemplo",
            email="contato@exemplo.com.br",
            telefone="(11) 98765-4321",
            ativo=True
        )
        db.add(restaurante)
        db.commit()
        db.refresh(restaurante)
        print(f"✓ Restaurante criado: {restaurante.nome} (ID: {restaurante.id})")
        
        # Cria usuário admin do restaurante
        admin = User(
            tenant_id=restaurante.id,
            nome="Admin Restaurante",
            email="admin@exemplo.com.br",
            senha_hash=get_password_hash("Admin@123"),
            is_tenant_admin=True,
            ativo=True
        )
        db.add(admin)
        
        # Cria usuário comum
        user = User(
            tenant_id=restaurante.id,
            nome="João Silva",
            email="joao@exemplo.com.br",
            senha_hash=get_password_hash("Senha@123"),
            is_tenant_admin=False,
            ativo=True
        )
        db.add(user)
        db.commit()
        print(f"✓ Usuários criados: {admin.email}, {user.email}")
        
        # Cria alimentos de exemplo
        alimentos = [
            Alimento(
                tenant_id=restaurante.id,
                nome="Arroz Branco",
                categoria="Grãos",
                unidade_medida="kg",
                quantidade_estoque=50.0,
                quantidade_minima=10.0,
                preco_unitario=4.50,
                fornecedor="Distribuidora ABC"
            ),
            Alimento(
                tenant_id=restaurante.id,
                nome="Feijão Preto",
                categoria="Grãos",
                unidade_medida="kg",
                quantidade_estoque=30.0,
                quantidade_minima=8.0,
                preco_unitario=6.80,
                fornecedor="Distribuidora ABC"
            ),
            Alimento(
                tenant_id=restaurante.id,
                nome="Tomate",
                categoria="Hortifruti",
                unidade_medida="kg",
                quantidade_estoque=5.0,
                quantidade_minima=10.0,  # Abaixo do mínimo!
                preco_unitario=3.20,
                fornecedor="Hortifruti XYZ"
            ),
            Alimento(
                tenant_id=restaurante.id,
                nome="Cebola",
                categoria="Hortifruti",
                unidade_medida="kg",
                quantidade_estoque=15.0,
                quantidade_minima=5.0,
                preco_unitario=2.50,
                fornecedor="Hortifruti XYZ"
            ),
            Alimento(
                tenant_id=restaurante.id,
                nome="Azeite",
                categoria="Condimentos",
                unidade_medida="l",
                quantidade_estoque=8.0,
                quantidade_minima=3.0,
                preco_unitario=25.00,
                fornecedor="Importadora Gourmet"
            )
        ]
        
        for alimento in alimentos:
            db.add(alimento)
        
        db.commit()
        print(f"✓ {len(alimentos)} alimentos criados\n")
        
        print("=" * 60)
        print("✅ Dados de exemplo criados com sucesso!")
        print("=" * 60)
        print(f"\n📍 Acesse: http://exemplo.wlsolucoes.eti.br")
        print(f"   Email: {admin.email}")
        print(f"   Senha: Admin@123\n")
        
    except Exception as e:
        print(f"✗ Erro ao popular dados: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
