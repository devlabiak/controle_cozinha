# COMANDO RÁPIDO PARA ATUALIZAR NA VPS (COM DOCKER)

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
docker-compose down && \
docker-compose build && \
docker-compose up -d && \
docker-compose exec -T app alembic upgrade head && \
echo "✅ Atualização concluída!"
```

## Opção 3: Verificar status apenas
```bash
docker-compose ps
docker-compose logs -f app
```

## Opção 4: Reverter para versão anterior
```bash
cd /var/www/controle_cozinha
git reset --hard HEAD~1
docker-compose down
docker-compose up -d
```

## Opção 5: Ver logs em tempo real
```bash
docker-compose logs -f app
```

## Opção 6: Parar/Iniciar containers sem atualizar
```bash
# Parar
docker-compose down

# Iniciar
docker-compose up -d
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

## ⚡ Atalhos úteis no .bashrc

```bash
# Criar aliases
echo '
alias cc-update="cd /var/www/controle_cozinha && ./update.sh"
alias cc-status="docker-compose ps"
alias cc-logs="docker-compose logs -f app"
alias cc-down="docker-compose down"
alias cc-up="docker-compose up -d"
alias cc-db="docker-compose exec db psql -U postgres -d controle_cozinha"
' >> ~/.bashrc

source ~/.bashrc
```

Depois:
```bash
cc-update  # Para atualizar
cc-logs    # Para ver logs
cc-status  # Ver status
```

---

## 🚨 Em caso de ERRO

### 1. Ver logs completos:
```bash
docker-compose logs app
docker-compose logs -f app  # Em tempo real
```

### 2. Verificar se container está rodando:
```bash
docker-compose ps
```

### 3. Testar conexão com BD:
```bash
docker-compose exec app psql $DATABASE_URL -c "SELECT 1;"
```

### 4. Verificar .env dentro do container:
```bash
docker-compose exec app cat .env | grep SECRET_KEY
```

### 5. Reverter e reiniciar:
```bash
cd /var/www/controle_cozinha
git log --oneline -n 5
git reset --hard <HASH_ANTERIOR>
docker-compose down
docker-compose up -d
```

### 6. Limpar tudo e recomeçar:
```bash
docker-compose down -v  # Remove volumes também
docker-compose up -d
docker-compose exec -T app alembic upgrade head
```

---

## ℹ️ Diferenças: Com Docker vs Sem Docker

### SEM Docker (Systemd service):
```bash
source venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
sudo systemctl restart controle_cozinha
```

### COM Docker (Recomendado):
```bash
docker-compose down
docker-compose build
docker-compose up -d
docker-compose exec -T app alembic upgrade head
```

✅ **Docker é melhor porque:**
- Não precisa de venv (isolamento já no container)
- Imagem reproducível (funciona em qualquer lugar)
- Fácil rollback (só resetar imagem)
- Sem conflitos de versão
- Mais seguro (isolado completamente)
