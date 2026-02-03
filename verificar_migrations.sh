#!/bin/bash
# Script para verificar e corrigir migrations

echo "==================================="
echo "VERIFICANDO MIGRATIONS"
echo "==================================="
echo ""

cd ~/controle_cozinha || exit 1

echo "📋 Verificando heads atuais:"
docker compose exec app alembic heads
echo ""

echo "📋 Histórico de migrations:"
docker compose exec app alembic history
echo ""

echo "📋 Mostrando todas as heads:"
docker compose exec app alembic show heads
echo ""

echo "==================================="
echo "CORRIGINDO MIGRATIONS"
echo "==================================="
echo ""

echo "🔧 Aplicando migration 007 (índices compostos)..."
docker compose exec app alembic upgrade 007 || echo "Migration 007 já aplicada ou com erro"
echo ""

echo "🔧 Aplicando migration 008 (campos restaurante)..."
docker compose exec app alembic upgrade 008 || echo "Migration 008 já aplicada ou com erro"
echo ""

echo "🔧 Tentando sincronizar para o head final..."
docker compose exec app alembic upgrade 008
echo ""

echo "✅ Status final:"
docker compose exec app alembic current
echo ""
