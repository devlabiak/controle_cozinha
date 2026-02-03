#!/bin/bash
# Script para remover from __future__ import annotations dos routers

echo "==================================="
echo "CORRIGINDO IMPORTS"
echo "==================================="
echo ""

cd ~/controle_cozinha || exit 1

echo "📋 Verificando arquivos problemáticos..."
echo ""

# Verificar se tem from __future__ nos arquivos
echo "Arquivo: tenant_alimentos.py"
grep -n "from __future__" app/routers/tenant_alimentos.py || echo "  ✅ Já corrigido"

echo "Arquivo: tenant_usuarios.py"
grep -n "from __future__" app/routers/tenant_usuarios.py || echo "  ✅ Já corrigido"

echo "Arquivo: admin_clientes.py"
grep -n "from __future__" app/routers/admin_clientes.py || echo "  ✅ Já corrigido"

echo ""
echo "🔧 Removendo 'from __future__ import annotations'..."
echo ""

# Remover a linha de todos os arquivos
sed -i '/^from __future__ import annotations$/d' app/routers/tenant_alimentos.py
sed -i '/^from __future__ import annotations$/d' app/routers/tenant_usuarios.py
sed -i '/^from __future__ import annotations$/d' app/routers/admin_clientes.py

echo "✅ Linhas removidas"
echo ""

echo "📋 Verificando novamente..."
echo ""

echo "Arquivo: tenant_alimentos.py"
grep -n "from __future__" app/routers/tenant_alimentos.py || echo "  ✅ Corrigido"

echo "Arquivo: tenant_usuarios.py"
grep -n "from __future__" app/routers/tenant_usuarios.py || echo "  ✅ Corrigido"

echo "Arquivo: admin_clientes.py"
grep -n "from __future__" app/routers/admin_clientes.py || echo "  ✅ Corrigido"

echo ""
echo "🔄 Reconstruindo e reiniciando containers..."
docker compose down
docker compose up -d --build

echo ""
echo "⏳ Aguardando inicialização (15 segundos)..."
sleep 15

echo ""
echo "📋 Status dos containers:"
docker compose ps

echo ""
echo "📋 Últimos logs:"
docker compose logs app --tail=20

echo ""
echo "==================================="
echo "✅ CORREÇÃO CONCLUÍDA"
echo "==================================="
