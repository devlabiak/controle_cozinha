# 📦 GUIA DE DEPLOY NA VPS (COM DOCKER)

## 🚀 Deploy Rápido (Primeira Vez)

### 1. **Clone o repositório**
```bash
cd /var/www
git clone https://github.com/devlabiak/controle_cozinha.git
cd controle_cozinha
```

### 2. **Verificar arquivo .env**
```bash
# O arquivo .env deve estar presente (incluído no repositório)
cat .env
# Verificar se SECRET_KEY está preenchido
```

### 3. **Atualizar credenciais de produção (IMPORTANTE)**
```bash
# Editar .env com dados reais de produção
nano .env

# Gerar uma NEW SECRET_KEY para produção:
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
# Copiar output e colar em SECRET_KEY=

# Atualizar:
# - DATABASE_URL (com host do BD remoto)
# - COOKIE_SECURE=true
# - COOKIE_SAMESITE=strict
# - LOG_LEVEL=INFO
# - REDIS_URL (se tiver Redis disponível)
```

### 4. **Verificar arquivo docker-compose.yml**
```bash
# Verificar se existe e está configurado corretamente
cat docker-compose.yml
```

### 5. **Build e iniciar containers**
```bash
docker-compose build
docker-compose up -d
```

### 6. **Executar migrações**
```bash
docker-compose exec -T app alembic upgrade head
```

### 7. **Verificar se está rodando**
```bash
docker-compose ps
docker-compose logs -f app
```

---

## ⚙️ Setup com Nginx como Reverse Proxy

### 1. **Criar configuração nginx**
```bash
sudo nano /etc/nginx/sites-available/controle_cozinha
```

### 2. **Colar conteúdo**
```nginx
upstream controle_cozinha {
    server 127.0.0.1:8000;  # Docker expõe na porta 8000
}

# Redirecionar HTTP → HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name *.wlsolucoes.eti.br wlsolucoes.eti.br;
    return 301 https://$host$request_uri;
}

# HTTPS - Subdomínios (Tenants)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ~^(?<tenant>.+)\.wlsolucoes\.eti\.br$ wlsolucoes.eti.br;

    ssl_certificate /etc/letsencrypt/live/wlsolucoes.eti.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/wlsolucoes.eti.br/privkey.pem;
    
    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    client_max_body_size 10M;

    location / {
        proxy_pass http://controle_cozinha;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # WebSocket
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 3. **Habilitar site**
```bash
sudo ln -s /etc/nginx/sites-available/controle_cozinha /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔐 Setup SSL com Let's Encrypt

```bash
# Instalar certbot
sudo apt-get install certbot python3-certbot-nginx

# Gerar certificado
sudo certbot certonly --nginx -d wlsolucoes.eti.br -d "*.wlsolucoes.eti.br"

# Auto-renewal
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

---

## 📊 Setup PostgreSQL

### 1. **Conectar ao servidor**
```bash
sudo -u postgres psql
```

### 2. **Criar banco de dados e usuário**
```sql
CREATE DATABASE controle_cozinha;
CREATE USER postgres_user WITH PASSWORD 'strong_password_here';
ALTER ROLE postgres_user SET client_encoding TO 'utf8';
ALTER ROLE postgres_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE postgres_user SET default_transaction_deferrable TO on;
ALTER ROLE postgres_user SET default_transaction_level TO 'read committed';
ALTER ROLE postgres_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE controle_cozinha TO postgres_user;
\q
```

### 3. **Atualizar .env**
```bash
DATABASE_URL=postgresql://postgres_user:strong_password_here@localhost:5432/controle_cozinha
```

---

## 🔄 Setup Redis (Opcional, para tokens/cache)

```bash
# Instalar
sudo apt-get install redis-server

# Iniciar
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Testar
redis-cli ping
# Esperado: PONG
```

---

## 🔄 Atualizações Futuras

### Comando automático com script
```bash
cd /var/www/controle_cozinha
chmod +x update.sh
./update.sh
```

### Ou comando manual
```bash
cd /var/www/controle_cozinha
git pull origin main
docker-compose down
docker-compose build
docker-compose up -d
docker-compose exec -T app alembic upgrade head
```

---

## 📋 Estrutura Docker

```yaml
# docker-compose.yml deve conter:
# - app: FastAPI rodando em uvicorn
# - db: PostgreSQL
# - redis: (opcional) para cache/tokens

# O Nginx faz proxy para app:8000
```

---

## 🔍 Monitoramento

### Logs de Aplicação
```bash
docker-compose logs -f app
```

### Logs do Nginx
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Health Check
```bash
# Dentro do container
docker-compose exec app curl -s http://localhost:8000/docs

# De fora
curl -s https://app.wlsolucoes.eti.br/docs
```

### Status dos containers
```bash
docker-compose ps
docker stats
```

---

## 🆘 Troubleshooting

### Erro: "Não consegue conectar ao banco"
```bash
# Verificar se BD está rodando
docker-compose ps db

# Verificar logs
docker-compose logs db

# Testar conexão
docker-compose exec app psql $DATABASE_URL -c "SELECT 1;"
```

### Erro: "Porta 8000 já em uso"
```bash
# Verificar processo
sudo lsof -i :8000

# Matar processo
sudo kill -9 <PID>

# Ou mudar porta no docker-compose.yml
```

### Aplicação não responde
```bash
# Ver logs
docker-compose logs app -f

# Reiniciar
docker-compose restart app

# Ou recriar
docker-compose down && docker-compose up -d
```

### Certificado SSL expirado
```bash
sudo certbot renew --dry-run
sudo certbot renew
sudo systemctl restart nginx
```

---

## 📞 Suporte

Para dúvidas de deploy, enviar email:
deploy@wlsolucoes.eti.br

Ver também: [SECURITY.md](SECURITY.md) para detalhes de segurança
