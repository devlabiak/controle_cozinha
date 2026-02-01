# Controle de Cozinha - Sistema Multi-Tenant SaaS

Sistema de controle de estoque para restaurantes com arquitetura multi-tenant, roles de acesso e interface web/mobile.

## ✅ Status - PRONTO PARA PRODUÇÃO

A aplicação está **100% funcional** e pronta para deploy na VPS.

## 🚀 Deploy Rápido

### 1. Clone e configure
```bash
git clone <seu-repo> && cd Controle_cozinha
cp .env.example .env
```

### 2. Edite `.env` com seus dados
```bash
nano .env
# Altere: SECRET_KEY, DB_PASSWORD, BASE_DOMAIN
```

### 3. Suba os containers
```bash
docker-compose up -d --build
```

### 4. Acesse
- **Admin**: https://seu-dominio.com/admin/login.html
- **Cozinha**: https://seu-dominio.com/
- **API**: https://seu-dominio.com:8000/api

## 📋 Funcionalidades Implementadas

✅ **Multi-tenant** - Múltiplos restaurantes segregados  
✅ **Roles** - ADMIN (acesso completo) / LEITURA (apenas QR)  
✅ **JWT Auth** - Autenticação segura  
✅ **API REST** - Endpoints completos  
✅ **Web Interface** - Admin + Cozinha  
✅ **Mobile Ready** - Interface responsiva  
✅ **QR Code** - Controle de estoque  
✅ **Subdomínios** - `restaurante.seu-dominio.com`

## 👤 Credenciais Padrão

| Acesso | Email | Senha |
|--------|-------|-------|
| Admin SaaS | admin@wlsolucoes.eti.br | admin123 |

Resposta:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

### Usar o token
Adicione o header em todas as requisições autenticadas:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

## 🏪 Fluxo de Criação de Restaurante

### 1. Admin cria novo restaurante
```bash
POST /api/admin/tenants/
Authorization: Bearer <token-admin>
Content-Type: application/json

{
  "nome": "Restaurante do João",
  "slug": "joao",
  "email": "contato@joao.com.br",
  "telefone": "(11) 98765-4321",
  "admin_nome": "João Silva",
  "admin_email": "joao@joao.com.br",
  "admin_senha": "SenhaSegura123"
}
```

### 2. Restaurante já está acessível
- URL: `http://joao.wlsolucoes.eti.br`
- Login: `joao@joao.com.br` / `SenhaSegura123`

### 3. Restaurante gerencia seu estoque
```bash
# Acessar via subdomínio do restaurante
POST http://joao.wlsolucoes.eti.br/api/tenant/alimentos/
Authorization: Bearer <token-restaurante>
Content-Type: application/json

{
  "nome": "Arroz Branco",
  "categoria": "Grãos",
  "unidade_medida": "kg",
  "quantidade_estoque": 50.0,
  "quantidade_minima": 10.0,
  "preco_unitario": 4.50,
  "fornecedor": "Distribuidora ABC"
}
```

## 📁 Estrutura do Projeto

```
Controle_cozinha/
├── app/
│   ├── __init__.py
│   ├── main.py              # Aplicação FastAPI principal
│   ├── config.py            # Configurações
│   ├── database.py          # Conexão com banco
│   ├── models.py            # Models SQLAlchemy
│   ├── schemas.py           # Schemas Pydantic
│   ├── auth.py              # Autenticação JWT
│   ├── middleware.py        # Middleware de tenant
│   └── routers/
│       ├── auth.py          # Login
│       ├── admin_tenants.py # CRUD de restaurantes
│       ├── admin_users.py   # CRUD de usuários (admin)
│       ├── tenant_alimentos.py  # CRUD de alimentos
│       └── tenant_users.py  # CRUD de usuários (tenant)
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 001_initial_migration.py
├── nginx/
│   ├── nginx.conf
│   └── conf.d/
│       └── default.conf     # Config wildcard DNS
├── scripts/
│   ├── create_admin.py      # Criar admin inicial
│   └── seed_data.py         # Dados de exemplo
├── .env.example
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🔑 Endpoints Principais

### Autenticação
- `POST /api/auth/login` - Login

### Portal Admin (requer admin SaaS)
- `POST /api/admin/tenants/` - Criar restaurante
- `GET /api/admin/tenants/` - Listar restaurantes
- `GET /api/admin/tenants/{id}` - Detalhes do restaurante
- `PUT /api/admin/tenants/{id}` - Atualizar restaurante
- `DELETE /api/admin/tenants/{id}` - Deletar restaurante
- `GET /api/admin/users/` - Listar todos os usuários
- `PUT /api/admin/users/{id}` - Atualizar usuário
- `DELETE /api/admin/users/{id}` - Deletar usuário

### Portal Restaurante (requer login + acesso via subdomínio)
- `POST /api/tenant/alimentos/` - Criar alimento
- `GET /api/tenant/alimentos/` - Listar alimentos
- `GET /api/tenant/alimentos/estoque-baixo` - Alimentos com estoque baixo
- `GET /api/tenant/alimentos/{id}` - Detalhes do alimento
- `PUT /api/tenant/alimentos/{id}` - Atualizar alimento
- `DELETE /api/tenant/alimentos/{id}` - Deletar alimento
- `POST /api/tenant/users/` - Criar usuário
- `GET /api/tenant/users/` - Listar usuários
- `PUT /api/tenant/users/{id}` - Atualizar usuário
- `DELETE /api/tenant/users/{id}` - Deletar usuário

## 🌐 Configuração DNS

Para produção, configure no seu provedor de DNS:

```
Type    Name                          Value
A       wlsolucoes.eti.br            <IP_DO_SERVIDOR>
A       *.wlsolucoes.eti.br          <IP_DO_SERVIDOR>
```

## 🔧 Comandos Úteis

### Logs
```bash
# Ver logs de todos os containers
docker-compose logs -f

# Ver logs apenas do app
docker-compose logs -f app
```

### Banco de Dados
```bash
# Acessar PostgreSQL
docker-compose exec db psql -U postgres -d controle_cozinha

# Criar nova migração
docker-compose exec app alembic revision --autogenerate -m "descrição"

# Aplicar migrações
docker-compose exec app alembic upgrade head

# Reverter última migração
docker-compose exec app alembic downgrade -1
```

### Desenvolvimento
```bash
# Reiniciar apenas o app (após mudanças)
docker-compose restart app

# Reconstruir containers
docker-compose up -d --build

# Parar tudo
docker-compose down

# Parar e remover volumes (⚠️ deleta dados)
docker-compose down -v
```

## 🔒 Segurança

### Em Produção:
1. ✅ Altere `SECRET_KEY` no `.env`
2. ✅ Use senhas fortes
3. ✅ Configure SSL/TLS (HTTPS) no Nginx
4. ✅ Configure CORS adequadamente
5. ✅ Limite o acesso ao PostgreSQL
6. ✅ Use secrets do Docker para dados sensíveis
7. ✅ Configure backup automático do banco

### SSL/HTTPS com Let's Encrypt
```bash
# Instale certbot
docker-compose exec nginx sh
apk add certbot certbot-nginx

# Obtenha certificado
certbot --nginx -d wlsolucoes.eti.br -d *.wlsolucoes.eti.br
```

## 📊 Models do Banco

### Tenant (Restaurante)
- id, nome, slug, email, telefone, ativo, created_at, updated_at

### User (Usuário)
- id, tenant_id, nome, email, senha_hash, is_admin, is_tenant_admin, ativo, created_at, updated_at

### Alimento (Produto)
- id, tenant_id, nome, categoria, unidade_medida, quantidade_estoque, quantidade_minima, preco_unitario, fornecedor, observacoes, ativo, created_at, updated_at

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -am 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está sob a licença MIT.

## 👨‍💻 Autor

Desenvolvido para WL Soluções

---

**Dúvidas?** Abra uma issue no repositório!
