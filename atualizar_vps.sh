#!/bin/bash
# Script para atualizar o sistema na VPS
# Execute este script na VPS com: bash atualizar_vps.sh

echo "==================================="
echo "ATUALIZANDO CONTROLE COZINHA"
echo "==================================="
echo ""

# 1. Ir para o diretório do projeto
cd ~/controle_cozinha || { echo "Erro: Diretório não encontrado"; exit 1; }
echo "✓ Diretório: $(pwd)"
echo ""

# 2. Mostrar branch e último commit atual
echo "📍 Estado atual:"
git log --oneline -1
echo ""

# 3. Puxar atualizações
echo "📥 Puxando atualizações do GitHub..."
git pull
echo ""

# 4. Mostrar novo commit
echo "📍 Novo estado:"
git log --oneline -1
echo ""

# 5. Aplicar migrations do Alembic
echo "🗃️  Aplicando migrations..."
docker compose exec app alembic upgrade head
echo ""

# 6. Reiniciar o app
echo "🔄 Reiniciando aplicação..."
docker compose restart app
echo ""

# 7. Verificar se está rodando
echo "✅ Status dos containers:"
docker compose ps
echo ""

echo "==================================="
echo "✅ ATUALIZAÇÃO CONCLUÍDA!"
echo "==================================="
echo ""
echo "📋 Próximos passos no NAVEGADOR:"
echo "   1. Pressione Ctrl + Shift + Delete"
echo "   2. Marque 'Imagens e arquivos em cache'"
echo "   3. Clique em 'Limpar dados'"
echo "   4. Ou simplesmente: Ctrl + F5 várias vezes"
echo ""
echo "🔍 Para verificar:"
echo "   - Abra o Console (F12)"
echo "   - Deve aparecer: version: 'v2026.02.01.02'"
echo "   - No rodapé da sidebar deve ter: v2026.02.01.02"
echo ""
