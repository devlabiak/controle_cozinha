"""
Script para debugar alertas de vencimento indevidos
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from app.models import MovimentacaoEstoque, Alimento, TipoMovimentacao
from app.config import settings

# Conecta ao banco
engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)
db = Session()

print("=" * 80)
print("INVESTIGANDO ALERTAS DE VENCIMENTO INDEVIDOS")
print("=" * 80)

# Data limite (30 dias)
data_limite = datetime.now() + timedelta(days=30)

# Busca movimentações de entrada com validade
movimentacoes = db.query(MovimentacaoEstoque).join(Alimento).filter(
    MovimentacaoEstoque.tipo == TipoMovimentacao.ENTRADA,
    MovimentacaoEstoque.data_validade != None,
    MovimentacaoEstoque.usado == False,
    MovimentacaoEstoque.data_validade <= data_limite.date(),
    MovimentacaoEstoque.data_validade >= datetime.now().date()
).all()

print(f"\n✅ Encontradas {len(movimentacoes)} movimentações de entrada com validade\n")

problemas = []

for mov in movimentacoes:
    # Verifica se alimento existe
    if not mov.alimento:
        print(f"❌ PROBLEMA: Movimentação {mov.id} sem alimento vinculado")
        problemas.append(mov.id)
        continue
    
    # Verifica estoque
    estoque = mov.alimento.quantidade_estoque or 0
    
    # Calcula quantidade usada do lote
    lote_numero = mov.qr_code_usado
    total_usado = db.query(func.sum(MovimentacaoEstoque.quantidade)).filter(
        MovimentacaoEstoque.qr_code_usado == lote_numero,
        MovimentacaoEstoque.tipo == 'saida',
        MovimentacaoEstoque.tenant_id == mov.tenant_id
    ).scalar() or 0
    
    quantidade_disponivel = mov.quantidade - total_usado
    
    # Verifica inconsistências
    tem_problema = False
    motivo = []
    
    if estoque <= 0:
        tem_problema = True
        motivo.append("estoque zerado")
    
    if quantidade_disponivel <= 0:
        tem_problema = True
        motivo.append("lote totalmente usado")
    
    if quantidade_disponivel > estoque:
        tem_problema = True
        motivo.append(f"inconsistência: lote tem {quantidade_disponivel} mas estoque total é {estoque}")
    
    if tem_problema:
        print(f"\n⚠️  MOVIMENTAÇÃO PROBLEMÁTICA:")
        print(f"   ID: {mov.id}")
        print(f"   Produto: {mov.alimento.nome}")
        print(f"   Lote: {lote_numero}")
        print(f"   Validade: {mov.data_validade}")
        print(f"   Qtd Original: {mov.quantidade}")
        print(f"   Qtd Usada: {total_usado}")
        print(f"   Qtd Disponível Lote: {quantidade_disponivel}")
        print(f"   Estoque Total Produto: {estoque}")
        print(f"   ❌ Problemas: {', '.join(motivo)}")
        problemas.append(mov.id)
    else:
        print(f"✅ OK: {mov.alimento.nome} - Lote {lote_numero} - Disponível: {quantidade_disponivel}/{estoque}")

print("\n" + "=" * 80)
print(f"RESUMO: {len(problemas)} movimentações com problemas encontradas")
if problemas:
    print(f"IDs problemáticos: {problemas}")
print("=" * 80)

db.close()
