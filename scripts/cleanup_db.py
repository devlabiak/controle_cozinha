#!/usr/bin/env python3
"""
Script para limpar banco de dados completamente
Executa limpeza respeitando foreign keys e constraints
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal, engine
from app.models import User, Cliente, Tenant, Alimento, MovimentacaoEstoque, user_tenants_association
from sqlalchemy import text, inspect
from sqlalchemy.orm import Session

def limpar_banco_dados():
    """Limpa todas as tabelas mantendo apenas admin principal"""
    db: Session = SessionLocal()
    
    try:
        print("🧹 Iniciando limpeza do banco de dados...")
        print("-" * 50)
        
        # 1. Desabilitar constraints durante limpeza
        db.execute(text("SET session_replication_role = 'replica'"))
        
        # 2. Limpar em ordem inversa de criação (respeitar dependências)
        print("📊 Status antes da limpeza:")
        print(f"  • Users: {db.query(User).count()}")
        print(f"  • Clientes: {db.query(Cliente).count()}")
        print(f"  • Tenants: {db.query(Tenant).count()}")
        print(f"  • Alimentos: {db.query(Alimento).count()}")
        
        # Limpar tabelas
        print("\n🗑️  Limpando...")
        
        # user_tenants_association (relação muitos-para-muitos)
        db.execute(text("DELETE FROM user_tenants_association"))
        print("  ✓ Removidos user_tenants_association")
        
        # MovimentacaoEstoque
        db.execute(text("DELETE FROM movimentacao_estoque"))
        print("  ✓ Removidas movimentações de estoque")
        
        # Alimentos
        db.execute(text("DELETE FROM alimentos"))
        print("  ✓ Removidos alimentos")
        
        # Tenants
        db.execute(text("DELETE FROM tenants"))
        print("  ✓ Removidos tenants")
        
        # Users (exceto admin id=1)
        db.execute(text("DELETE FROM users WHERE id != 1"))
        print("  ✓ Removidos users (exceto admin)")
        
        # Clientes
        db.execute(text("DELETE FROM clientes"))
        print("  ✓ Removidos clientes")
        
        # Reabilitar constraints
        db.execute(text("SET session_replication_role = 'origin'"))
        db.commit()
        
        # 3. Verificar estado final
        print("\n✅ Status após limpeza:")
        print(f"  • Users: {db.query(User).count()} (apenas admin)")
        print(f"  • Clientes: {db.query(Cliente).count()}")
        print(f"  • Tenants: {db.query(Tenant).count()}")
        print(f"  • Alimentos: {db.query(Alimento).count()}")
        
        # 4. Mostrar usuário admin restante
        admin = db.query(User).filter(User.id == 1).first()
        if admin:
            print(f"\n👤 Usuário admin restante:")
            print(f"  • ID: {admin.id}")
            print(f"  • Email: {admin.email}")
            print(f"  • Nome: {admin.nome}")
            print(f"  • Admin: {admin.is_admin}")
        
        print("\n" + "=" * 50)
        print("✨ Limpeza concluída com sucesso!")
        print("=" * 50)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Erro durante limpeza: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    sucesso = limpar_banco_dados()
    sys.exit(0 if sucesso else 1)
