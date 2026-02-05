# COMANDO RÁPIDO PARA ATUALIZAR NA VPS

## Opção 1: Executar script (RECOMENDADO)
```bash
cd /var/www/controle_cozinha
chmod +x update.sh
./update.sh
```

## Opção 2: Comando único (one-liner)
```bash
cd /var/www/controle_cozinha && \
git pull origin main && \
source venv/bin/activate && \
pip install -r requirements.txt && \
alembic upgrade head && \
sudo systemctl restart controle_cozinha && \
echo "✅ Atualização concluída!"
```

## Opção 3: Verificar status apenas
```bash
sudo systemctl status controle_cozinha
sudo journalctl -u controle_cozinha -n 50
```

## Opção 4: Reverter para versão anterior
```bash
cd /var/www/controle_cozinha
git reset --hard HEAD~1
sudo systemctl restart controle_cozinha
```

## Opção 5: Ver logs em tempo real
```bash
sudo journalctl -u controle_cozinha -f
```

## Opção 6: Fazer rollback automático em caso de erro
```bash
#!/bin/bash
set -e
cd /var/www/controle_cozinha
CURRENT=$(git rev-parse HEAD)

git pull origin main || {
    echo "❌ Falha no pull"
    git reset --hard $CURRENT
    exit 1
}

source venv/bin/activate
pip install -r requirements.txt || {
    echo "❌ Falha ao instalar dependências"
    git reset --hard $CURRENT
    exit 1
}

alembic upgrade head || {
    echo "❌ Falha nas migrações"
    git reset --hard $CURRENT
    exit 1
}

sudo systemctl restart controle_cozinha
echo "✅ Atualização com rollback automático concluída"
```

---

## 📝 Adicionar ao crontab (atualização automática diária)

```bash
# Editar crontab
sudo crontab -e

# Adicionar linha (2:00 AM todos os dias):
0 2 * * * cd /var/www/controle_cozinha && ./update.sh >> /var/log/controle_cozinha_update.log 2>&1
```

---

## ⚡ Atalhos úteis

### Criar aliases no .bashrc
```bash
alias cc-update='cd /var/www/controle_cozinha && ./update.sh'
alias cc-status='sudo systemctl status controle_cozinha'
alias cc-logs='sudo journalctl -u controle_cozinha -f'
alias cc-restart='sudo systemctl restart controle_cozinha'
alias cc-stop='sudo systemctl stop controle_cozinha'
alias cc-start='sudo systemctl start controle_cozinha'
```

Depois:
```bash
source ~/.bashrc
cc-update  # Para atualizar
cc-logs    # Para ver logs
```

---

## 🚨 Em caso de ERRO

1. **Ver logs:**
   ```bash
   sudo journalctl -u controle_cozinha -n 100
   ```

2. **Verificar .env:**
   ```bash
   cat /var/www/controle_cozinha/.env | grep SECRET_KEY
   ```

3. **Testar conexão BD:**
   ```bash
   psql $DATABASE_URL -c "SELECT 1;"
   ```

4. **Reverter:**
   ```bash
   cd /var/www/controle_cozinha
   git log --oneline -n 5
   git reset --hard <HASH_ANTERIOR>
   sudo systemctl restart controle_cozinha
   ```
