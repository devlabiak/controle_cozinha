"""
Script para limpar todos os produtos e movimentações do banco de dados
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Alimento, MovimentacaoEstoque, ProdutoLote
from app.config import settings

# Conecta ao banco
engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)
db = Session()

print("=" * 80)
print("LIMPEZA DE PRODUTOS E MOVIMENTAÇÕES")
print("=" * 80)

# Solicita confirmação
tenant_id = input("\nDigite o ID do restaurante (tenant_id) para limpar [1]: ").strip()
if not tenant_id:
    tenant_id = "1"

try:
    tenant_id = int(tenant_id)
except:
    print("❌ ID inválido!")
    sys.exit(1)

print(f"\n⚠️  ATENÇÃO: Você vai DELETAR TODOS os dados do tenant {tenant_id}:")
print("   - Todas as movimentações de estoque (entradas e saídas)")
print("   - Todos os lotes")
print("   - Todos os produtos/alimentos")

confirmacao = input("\n❌ Digite 'SIM' para confirmar a exclusão PERMANENTE: ").strip().upper()

if confirmacao != "SIM":
    print("\n✅ Operação cancelada. Nenhum dado foi deletado.")
    sys.exit(0)

print("\n🗑️  Iniciando limpeza...")

try:
    # 1. Deleta todas as movimentações
    movimentacoes_deletadas = db.query(MovimentacaoEstoque).filter(
        MovimentacaoEstoque.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    print(f"✅ Deletadas {movimentacoes_deletadas} movimentações")
    
    # 2. Deleta todos os lotes
    lotes_deletados = db.query(ProdutoLote).filter(
        ProdutoLote.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    print(f"✅ Deletados {lotes_deletados} lotes")
    
    # 3. Deleta todos os alimentos
    alimentos_deletados = db.query(Alimento).filter(
        Alimento.tenant_id == tenant_id
    ).delete(synchronize_session=False)
    print(f"✅ Deletados {alimentos_deletados} produtos")
    
    # Commit das alterações
    db.commit()
    
    print("\n" + "=" * 80)
    print("✅ LIMPEZA CONCLUÍDA COM SUCESSO!")
    print("=" * 80)
    print(f"\nResumo:")
    print(f"  - {movimentacoes_deletadas} movimentações deletadas")
    print(f"  - {lotes_deletados} lotes deletados")
    print(f"  - {alimentos_deletados} produtos deletados")
    print("\n✅ O banco está limpo. Você pode cadastrar novos produtos agora.")
    
except Exception as e:
    db.rollback()
    print(f"\n❌ ERRO durante a limpeza: {e}")
    print("❌ Operação revertida. Nenhum dado foi deletado.")
finally:
    db.close()
