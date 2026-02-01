#!/bin/bash
# Script para iniciar a aplicação com migrações automáticas

set -e

echo "🚀 Iniciando aplicação..."
echo "⏳ Aguardando banco de dados..."

# Aguardar PostgreSQL estar pronto
until pg_isready -h ${DB_HOST:-db} -U postgres; do
  echo "⏳ PostgreSQL não está pronto... aguardando..."
  sleep 2
done

echo "✅ PostgreSQL está pronto!"

# Aplicar migrações
echo "🔧 Aplicando migrações..."
alembic upgrade head

# Criar usuário admin se não existir
echo "👤 Verificando usuário admin..."
python scripts/create_admin.py || true

# Iniciar aplicação
echo "🎯 Iniciando Uvicorn..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
