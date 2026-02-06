# 🔧 Guia de Restart e Troubleshooting em Produção

## ⚠️ Quando Usar Este Guia

- Aplicação não responde
- Erros 502/503/504
- Containers parados
- Banco de dados inacessível
- Alto consumo de recursos
- Após mudanças de configuração

## 🚨 Restart Rápido (Problema Comum)

### Opção 1: Restart Completo (Recomendado)
acessar via SSH
```bash
cd /root/controle_cozinha
docker compose restart
```

### Opção 2: Restart Individual
```bash
# Apenas aplicação
docker compose restart app

# Apenas nginx
docker compose restart nginx

# Apenas banco de dados
docker compose restart db
```

## 🔍 Diagnóstico de Problemas

### 1. Verificar Status dos Containers
```bash
docker compose ps
```

**Estados esperados:**
- `Up` - Container rodando
- `healthy` - Healthcheck passou
- `unhealthy` - Healthcheck falhou
- `Exit` - Container parou (PROBLEMA!)

### 2. Ver Últimos Logs
```bash
# Últimas 100 linhas de todos os containers
docker compose logs --tail=100

# Últimas 50 linhas apenas do app
docker compose logs --tail=50 app

# Erros apenas
docker compose logs | grep -i error
```

### 3. Verificar Uso de Recursos
```bash
# Memória e CPU
docker stats --no-stream

# Espaço em disco
df -h
docker system df
```

## 🛠️ Soluções por Tipo de Problema

### Problema: Aplicação não responde (502/503)

**Diagnóstico:**
```bash
# Ver se app está rodando
docker compose ps app

# Ver logs do app
docker compose logs app --tail=50

# Ver logs do nginx
docker compose logs nginx --tail=50
```

**Solução:**
```bash
# Restart do app
docker compose restart app

# Se não resolver, restart completo
docker compose down
docker compose up -d

# Verificar
docker compose ps
docker compose logs app
```

### Problema: Banco de dados inacessível

**Diagnóstico:**
```bash
# Ver status do db
docker compose ps db

# Testar conexão
docker compose exec db psql -U postgres -c "SELECT 1;"

# Ver logs
docker compose logs db --tail=50
```

**Solução:**
```bash
# Restart do banco
docker compose restart db

# Aguardar 10 segundos
sleep 10

# Restart do app (reconectar)
docker compose restart app

# Verificar
docker compose exec db psql -U postgres -d controle_cozinha -c "SELECT COUNT(*) FROM tenants;"
```

### Problema: Alto consumo de memória

**Diagnóstico:**
```bash
docker stats --no-stream
free -h
```

**Solução:**
```bash
# Limpar containers parados
docker system prune -a

# Limpar volumes não usados
docker volume prune

# Restart dos containers
docker compose restart

# Em caso extremo, rebuild
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Problema: Logs muito grandes

**Diagnóstico:**
```bash
# Ver tamanho dos logs
du -sh /var/lib/docker/containers/*/*-json.log
```

**Solução:**
```bash
# Rotacionar logs
docker compose down
truncate -s 0 /var/lib/docker/containers/*/*-json.log
docker compose up -d

# Ou limpar tudo
docker system prune -a --volumes
```

### Problema: Porta em uso

**Diagnóstico:**
```bash
# Ver quem está usando as portas
netstat -tuln | grep -E ':(80|443|8000|5432)'
```

**Solução:**
```bash
# Parar processo específico
kill -9 $(lsof -t -i:8000)

# Ou restart docker
systemctl restart docker
docker compose up -d
```

## 🔄 Procedimentos de Emergência

### 1. Restart Completo (Sem Perda de Dados)
```bash
cd /root/controle_cozinha

# 1. Parar tudo
docker compose down

# 2. Verificar se parou
docker ps -a

# 3. Iniciar novamente
docker compose up -d

# 4. Aguardar inicialização (30s)
sleep 30

# 5. Verificar status
docker compose ps
docker compose logs app --tail=20
```

### 2. Rebuild Completo (Problema Persistente)
```bash
cd /root/controle_cozinha

# 1. Backup do banco
docker compose exec db pg_dump -U postgres controle_cozinha > backup_emergency.sql

# 2. Backup do .env
cp .env .env.emergency

# 3. Parar e remover tudo
docker compose down -v

# 4. Rebuild
docker compose build --no-cache

# 5. Iniciar
docker compose up -d

# 6. Restaurar banco (se necessário)
# cat backup_emergency.sql | docker compose exec -T db psql -U postgres controle_cozinha

# 7. Verificar
docker compose ps
docker compose logs -f app
```

### 3. Rollback de Emergência
```bash
cd /root/controle_cozinha

# 1. Ver últimos commits
git log --oneline -10

# 2. Reverter para versão estável anterior
git reset --hard <hash_commit_anterior>

# 3. Rebuild
docker compose down
docker compose build
docker compose up -d

# 4. Verificar
docker compose ps
```

## 📊 Comandos de Monitoramento

### Logs em Tempo Real
```bash
# Todos os containers
docker compose logs -f

# Apenas app (recomendado)
docker compose logs -f app

# Apenas erros
docker compose logs -f | grep -i error
```

### Health Checks
```bash
# Interno
docker compose exec app curl http://localhost:8000/docs

# Externo
curl https://painelfood.wlsolucoes.eti.br/docs

# Status HTTP
curl -I https://painelfood.wlsolucoes.eti.br
```

### Performance
```bash
# CPU e Memória
docker stats

# Processos no container
docker compose exec app ps aux

# Conexões no banco
docker compose exec db psql -U postgres -c "SELECT count(*) FROM pg_stat_activity;"
```

## 🔐 Comandos de Manutenção

### Limpeza
```bash
# Remover containers parados
docker container prune -f

# Remover imagens não usadas
docker image prune -a -f

# Remover volumes não usados (CUIDADO!)
docker volume prune -f

# Limpar tudo (CUIDADO!)
docker system prune -a --volumes -f
```

### Backup Rápido
```bash
# Banco de dados
docker compose exec db pg_dump -U postgres controle_cozinha | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Arquivos de configuração
tar -czf config_backup_$(date +%Y%m%d_%H%M%S).tar.gz .env docker-compose.yml nginx/
```

## 🆘 Situações Críticas

### Sistema Travado / Não Responde
```bash
# 1. Conectar via SSH em outra janela
# 2. Forçar parada
pkill -9 docker
systemctl restart docker

# 3. Aguardar 30s
sleep 30

# 4. Subir novamente
cd /root/controle_cozinha
docker compose up -d
```

### Disco Cheio
```bash
# Ver uso
df -h

# Limpar Docker
docker system prune -a --volumes

# Limpar logs do sistema
journalctl --vacuum-time=2d

# Limpar APT cache
apt-get clean
```

### Migrações Falharam
```bash
# Ver status das migrações
docker compose exec app alembic current

# Ver histórico
docker compose exec app alembic history

# Reverter 1 migração
docker compose exec app alembic downgrade -1

# Aplicar novamente
docker compose exec app alembic upgrade head
```

## 📞 Checklist de Emergência

- [ ] Verificar status dos containers (`docker compose ps`)
- [ ] Verificar logs (`docker compose logs app --tail=100`)
- [ ] Verificar recursos (`docker stats`, `df -h`)
- [ ] Tentar restart simples (`docker compose restart`)
- [ ] Se não resolver, rebuild (`docker compose down && docker compose up -d`)
- [ ] Verificar conexão com banco de dados
- [ ] Testar endpoints (`curl`)
- [ ] Verificar SSL/DNS (Cloudflare)
- [ ] Fazer backup antes de mudanças drásticas
- [ ] Documentar o que foi feito

## 📝 Registro de Incidentes

Sempre registre:
```bash
# Data/hora
date

# Status antes
docker compose ps > incident_before.log
docker compose logs > incident_logs.log

# Ação tomada
echo "Restart completo executado" >> incident_actions.log

# Status depois
docker compose ps > incident_after.log
```

## 🔗 Links Úteis

- Dashboard Admin: https://painelfood.wlsolucoes.eti.br
- API Docs: https://wlsolucoes.eti.br/docs
- Cloudflare Dashboard: [seu_dashboard]
- Repositório: https://github.com/devlabiak/controle_cozinha

## ⚡ Comandos Rápidos de Referência

```bash
# Status
docker compose ps

# Logs
docker compose logs -f app

# Restart
docker compose restart

# Rebuild
docker compose down && docker compose up -d

# Stats
docker stats --no-stream

# Health
curl -I https://painelfood.wlsolucoes.eti.br
```
