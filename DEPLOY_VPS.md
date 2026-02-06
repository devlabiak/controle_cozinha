# 🚀 Guia de Deploy na VPS

## 📋 Pré-requisitos

- Acesso SSH ao servidor: `root@srv1281403`
- Git instalado
- Docker e Docker Compose instalados
- Repositório GitHub configurado

## 🔧 Instalação Inicial (Primeira vez)

### 1. Conectar ao servidor
```bash
ssh root@srv1281403
```

### 2. Clonar o repositório
```bash
cd /root
git clone https://github.com/devlabiak/controle_cozinha.git
cd controle_cozinha
```

### 3. Configurar variáveis de ambiente
```bash
# Copiar exemplo e editar
cp .env.example .env
nano .env

# Configurações importantes:
# - SECRET_KEY (já configurada)
# - DATABASE_URL
# - COOKIE_SECURE=true
# - COOKIE_SAMESITE=strict
```

### 4. Dar permissão ao script de atualização
```bash
chmod +x update.sh
```

### 5. Build inicial
```bash
docker compose build
docker compose up -d
```

### 6. Executar migrações
```bash
docker compose exec -T app alembic upgrade head
```

### 7. Criar usuário admin (opcional)
```bash
docker compose exec app python scripts/create_admin.py
```

## 🔄 Deploy de Atualizações

### Método Automático (Recomendado)
```bash
cd /root/controle_cozinha
./update.sh
```

O script fará automaticamente:
- ✅ Backup do .env
- ✅ Git pull das mudanças
- ✅ Parar containers antigos
- ✅ Rebuild da imagem
- ✅ Iniciar novos containers
- ✅ Executar migrações
- ✅ Health check

### Método Manual
```bash
cd /root/controle_cozinha

# 1. Backup do .env
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# 2. Atualizar código
git pull origin main

# 3. Rebuild e restart
docker compose down
docker compose build
docker compose up -d

# 4. Migrações
docker compose exec -T app alembic upgrade head

# 5. Verificar status
docker compose ps
docker compose logs app
```

## 🔍 Verificações Pós-Deploy

### 1. Status dos containers
```bash
docker compose ps
```
Todos devem estar **Up** e **healthy**

### 2. Logs da aplicação
```bash
docker compose logs app | tail -50
```
Verificar se não há erros

### 3. Logs do nginx
```bash
docker compose logs nginx | tail -50
```
Verificar se está processando requisições

### 4. Testar endpoints
```bash
# Health check interno
docker compose exec app curl -s http://localhost:8000/docs

# Health check externo
curl https://painelfood.wlsolucoes.eti.br/docs
```

### 5. Verificar banco de dados
```bash
docker compose exec db psql -U postgres -d controle_cozinha -c "SELECT COUNT(*) FROM tenants;"
```

## 🌐 URLs de Acesso

- **Dashboard Admin**: https://painelfood.wlsolucoes.eti.br
- **Cozinha**: https://wlsolucoes.eti.br/cozinha/
- **API Docs**: https://wlsolucoes.eti.br/docs
- **API Redoc**: https://wlsolucoes.eti.br/redoc

## 📊 Monitoramento

### Ver logs em tempo real
```bash
# Todos os containers
docker compose logs -f

# Apenas app
docker compose logs -f app

# Apenas nginx
docker compose logs -f nginx

# Apenas database
docker compose logs -f db
```

### Uso de recursos
```bash
docker stats
```

### Espaço em disco
```bash
df -h
docker system df
```

## 🔐 Segurança

### SSL/TLS
- Certificados gerenciados pelo Cloudflare
- Localização: `/root/controle_cozinha/nginx/ssl/`
- Renovação automática via Cloudflare

### Firewall
Portas expostas:
- 80 (HTTP → redireciona para HTTPS)
- 443 (HTTPS)
- 22 (SSH)

### Backup
```bash
# Backup do banco de dados
docker compose exec db pg_dump -U postgres controle_cozinha > backup_$(date +%Y%m%d).sql

# Backup do .env
cp .env .env.backup.$(date +%Y%m%d)
```

## 🆘 Troubleshooting

Ver arquivo [RESTART_PRODUCAO.md](RESTART_PRODUCAO.md) para solução de problemas.

## 📝 Notas Importantes

1. **Sempre** faça backup antes de deploy
2. **Sempre** teste em ambiente local primeiro
3. **Monitore** logs após deploy por alguns minutos
4. **Comunique** à equipe antes de deploys grandes
5. **Mantenha** documentação atualizada

## 🔄 Rollback (Reverter Deploy)

Se algo der errado:

```bash
# 1. Ver últimos commits
git log --oneline -5

# 2. Reverter para commit anterior
git reset --hard <commit_hash>

# 3. Forçar atualização
docker compose down
docker compose build
docker compose up -d
docker compose exec -T app alembic downgrade -1  # Se necessário
```

## 📞 Contatos de Emergência

- Desenvolvedor: [seu contato]
- Servidor VPS: srv1281403
- Suporte Cloudflare: [dashboard cloudflare]
