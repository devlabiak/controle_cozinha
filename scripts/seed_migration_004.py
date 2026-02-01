#!/usr/bin/env python3
"""
Script para popular dados após migração 004
Cria cliente padrão, mapeia usuários existentes e dados antigos
"""

import os
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine
from app.models import Base, Cliente, User, Tenant, user_tenants_association
from app.security import get_password_hash
from sqlalchemy import text

def seed_after_migration():
    """Popula dados após migração 004"""
    db = SessionLocal()
    
    try:
        # Verificar se já temos clientes
        existing_cliente = db.query(Cliente).first()
        if existing_cliente:
            print("✓ Clientes já existem. Pulando seed...")
            return

        # Criar cliente padrão
        cliente = Cliente(
            nome_empresa="WL Soluções",
            email="empresa@wlsolucoes.eti.br",
            telefone="11999999999",
            cnpj="12.345.678/0001-90",
            endereco="Rua Exemplo, 123",
            cidade="São Paulo",
            estado="SP",
            ativo=True
        )
        db.add(cliente)
        db.flush()  # Força ID
        print(f"✓ Cliente 'WL Soluções' criado (ID: {cliente.id})")

        # Atualizar admin existente com cliente_id
        admin = db.query(User).filter_by(email="admin@wlsolucoes.eti.br").first()
        if admin:
            admin.cliente_id = cliente.id
            admin.is_admin = True
            db.add(admin)
            print(f"✓ Admin '{admin.email}' associado ao cliente")

        # Atualizar tenants existentes com cliente_id
        tenants = db.query(Tenant).all()
        for tenant in tenants:
            if not tenant.cliente_id:
                tenant.cliente_id = cliente.id
                # Mapear usuários do tenant ao novo relacionamento
                for user in tenant.users:
                    if user not in cliente.users:
                        cliente.users.append(user)
                    # Adicionar à tabela de associação
                    db.execute(
                        text("""
                            INSERT INTO user_tenants_association (user_id, tenant_id)
                            VALUES (:user_id, :tenant_id)
                            ON CONFLICT DO NOTHING
                        """)
                    )
                db.add(tenant)
                print(f"✓ Restaurante '{tenant.nome}' associado ao cliente")

        db.commit()
        print("\n✅ Seed completo!")
        print(f"   - Cliente padrão criado")
        print(f"   - Admin associado")
        print(f"   - {len(tenants)} restaurantes migrados")

    except Exception as e:
        db.rollback()
        print(f"❌ Erro: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_after_migration()
