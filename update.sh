#!/bin/bash

# ==================== SCRIPT DE ATUALIZAÇÃO - CONTROLE COZINHA ====================
# Execute este script na VPS para atualizar a aplicação
# Uso: ./update.sh
# ==================================================================================

set -e  # Parar se algum comando falhar

APP_DIR="/var/www/controle_cozinha"

echo "🚀 Iniciando atualização da aplicação Controle Cozinha (Docker)..."
echo "📁 Diretório: $APP_DIR"
echo "📅 Data: $(date)"
echo ""

# 1. Verificar se diretório existe
if [ ! -d "$APP_DIR" ]; then
    echo "❌ Erro: Diretório $APP_DIR não encontrado"
    exit 1
fi

# 2. Mudar para diretório da aplicação
cd "$APP_DIR"
echo "✅ Entrando em $APP_DIR"

# 3. Fazer backup do .env (por segurança)
if [ -f ".env" ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "✅ Backup de .env criado"
fi

# 4. Fazer pull do repositório
echo "📥 Fazendo pull do repositório..."
git pull origin main
echo "✅ Pull concluído"

# 5. Verificar se docker-compose.yml existe
if [ ! -f "docker-compose.yml" ]; then
    echo "❌ Erro: docker-compose.yml não encontrado"
    exit 1
fi

# 6. Parar containers antigos
echo "⏹️  Parando containers antigos..."
docker-compose down
echo "✅ Containers parados"

# 7. Rebuild da imagem
echo "🔨 Fazendo rebuild da imagem Docker..."
docker-compose build
echo "✅ Image buildada"

# 8. Iniciar containers
echo "🚀 Iniciando containers..."
docker-compose up -d
echo "✅ Containers iniciados"

# 9. Executar migrações
echo "🗄️  Executando migrações do banco de dados..."
docker-compose exec -T app alembic upgrade head
echo "✅ Migrações concluídas"

# 10. Health check
echo "🏥 Realizando health check..."
sleep 3

if docker-compose ps app | grep -q "Up"; then
    echo "✅ Container app está rodando"
else
    echo "❌ Erro: Container app não está respondendo"
    echo "   Verifique com: docker-compose logs app"
    exit 1
fi

# 11. Verificar aplicação
echo "🔗 Testando conexão com aplicação..."
if docker-compose exec -T app curl -s http://localhost:8000/docs > /dev/null 2>&1; then
    echo "✅ Aplicação respondendo corretamente"
else
    echo "⚠️  Aviso: Não foi possível conectar à aplicação via curl interno"
    echo "   Verifique com: docker-compose logs app"
fi

echo ""
echo "🎉 ======================== ATUALIZAÇÃO CONCLUÍDA ========================"
echo "✅ Data: $(date)"
echo "✅ Versão: $(git log -1 --pretty=%h)"
echo "✅ Mensagem: $(git log -1 --pretty=%B | head -1)"
echo "✅ Containers rodando:"
echo ""
docker-compose ps
echo ""
echo "📊 Próximos passos:"
echo "   1. Verificar logs: docker-compose logs -f app"
echo "   2. Testar em: https://app.wlsolucoes.eti.br"
echo "   3. Em caso de erro, reverter com: git reset --hard HEAD~1 && docker-compose down && docker-compose up -d"
echo "=========================================================================="
