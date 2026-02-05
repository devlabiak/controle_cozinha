#!/bin/bash

# ==================== SCRIPT DE ATUALIZAÇÃO - CONTROLE COZINHA ====================
# Execute este script na VPS para atualizar a aplicação
# Uso: ./update.sh
# ==================================================================================

set -e  # Parar se algum comando falhar

APP_DIR="/var/www/controle_cozinha"
SERVICE_NAME="controle_cozinha"

echo "🚀 Iniciando atualização da aplicação Controle Cozinha..."
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

# 4. Parar a aplicação
echo "⏹️  Parando serviço $SERVICE_NAME..."
sudo systemctl stop $SERVICE_NAME
echo "✅ Serviço parado"

# 5. Fazer pull do repositório
echo "📥 Fazendo pull do repositório..."
git pull origin main
echo "✅ Pull concluído"

# 6. Ativar virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Criando virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "✅ Virtual environment ativado"

# 7. Instalar/atualizar dependências
echo "📚 Instalando dependências..."
pip install -r requirements.txt --upgrade
echo "✅ Dependências instaladas"

# 8. Executar migrações
echo "🗄️  Executando migrações do banco de dados..."
alembic upgrade head
echo "✅ Migrações concluídas"

# 9. Limpar cache Python
echo "🧹 Limpando cache Python..."
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
echo "✅ Cache limpo"

# 10. Reiniciar aplicação
echo "🔄 Reiniciando serviço $SERVICE_NAME..."
sudo systemctl start $SERVICE_NAME
sleep 2

# 11. Verificar status do serviço
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo "✅ Serviço iniciado com sucesso"
else
    echo "❌ Erro ao iniciar serviço"
    echo "   Verifique com: sudo systemctl status $SERVICE_NAME"
    exit 1
fi

# 12. Health check
echo "🏥 Realizando health check..."
sleep 2

if curl -s https://app.wlsolucoes.eti.br/docs > /dev/null; then
    echo "✅ Aplicação respondendo corretamente"
else
    echo "⚠️  Aviso: Não foi possível conectar à aplicação"
    echo "   Verifique com: curl -s https://app.wlsolucoes.eti.br/docs"
fi

echo ""
echo "🎉 ======================== ATUALIZAÇÃO CONCLUÍDA ========================"
echo "✅ Data: $(date)"
echo "✅ Versão: $(git log -1 --pretty=%h)"
echo "✅ Mensagem: $(git log -1 --pretty=%B | head -1)"
echo "✅ Serviço $SERVICE_NAME está rodando"
echo ""
echo "📊 Próximos passos:"
echo "   1. Verificar logs: sudo journalctl -u $SERVICE_NAME -f"
echo "   2. Testar em: https://app.wlsolucoes.eti.br"
echo "   3. Em caso de erro, reverter com: git reset --hard HEAD~1"
echo "=========================================================================="
