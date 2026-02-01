# 🍽️ Controle Cozinha - Documentação de Estrutura

## 📁 Estrutura de Pastas

```
controle_cozinha/
├── app/                          # Backend FastAPI
│   ├── __init__.py
│   ├── main.py                  # Ponto de entrada (ASGI)
│   ├── config.py                # Configurações globais
│   ├── database.py              # Conexão com banco
│   ├── models.py                # Modelos SQLAlchemy
│   ├── schemas.py               # Schemas Pydantic
│   ├── security.py              # JWT e autenticação
│   ├── middleware.py            # CORS, logging, etc
│   │
│   ├── routers/                 # Endpoints agrupados por domínio
│   │   ├── __init__.py
│   │   ├── auth.py              # POST /auth/login
│   │   ├── admin_clientes.py    # CRUD clientes, restaurantes, usuários
│   │   ├── admin_tenants.py     # CRUD tenants (restaurantes) - FUTURO
│   │   ├── tenant_users.py      # Usuários dentro de tenant
│   │   └── foods.py             # CRUD alimentos - FUTURO
│   │
│   └── services/                # Lógica de negócios (FUTURO)
│       ├── __init__.py
│       ├── client_service.py
│       ├── user_service.py
│       └── restaurant_service.py
│
├── frontend/                     # React/Vue/HTML+JS frontend
│   ├── admin/                   # Admin dashboard (SaaS)
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── dashboard.js
│   │   └── styles.css
│   │
│   ├── app/                     # App principal (restaurante)
│   │   ├── index.html
│   │   ├── index.js
│   │   └── styles.css
│   │
│   ├── mobile/                  # Mobile responsivo
│   │   └── ...
│   │
│   └── shared/                  # Componentes/estilos compartilhados (FUTURO)
│       ├── components/
│       ├── utils.js
│       └── styles/
│
├── scripts/                      # Utilitários de desenvolvimento
│   ├── create_admin.py          # Criar usuário admin
│   ├── cleanup_db.py            # Limpar banco
│   └── seed_data.py             # Popular dados teste (FUTURO)
│
├── alembic/                     # Migrações banco de dados
│   ├── versions/
│   └── env.py
│
├── nginx/                       # Configuração reverse proxy
│   └── nginx.conf
│
├── tests/                       # Testes (FUTURO)
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_clients.py
│   └── test_restaurants.py
│
├── .env.example                 # Exemplo variáveis ambiente
├── .gitignore
├── docker-compose.yml           # Orquestração containers
├── Dockerfile                   # Build imagem app
├── entrypoint.sh               # Script inicialização
├── requirements.txt            # Dependências Python
├── README.md                   # Documentação principal
└── alembic.ini                 # Configuração migrações
```

## 🎯 Convenções de Código

### Backend (Python/FastAPI)

**Routers:**
```python
# ✅ BOM - Agrupado por domínio
@router.post("/clientes")          # CRUD Cliente
@router.get("/clientes/{id}")
@router.put("/clientes/{id}")
@router.delete("/clientes/{id}")

# ❌ RUIM - Espalhado
/api/create_cliente
/api/get_cliente
/api/update_cliente_name
```

**Models (SQLAlchemy):**
- CamelCase: `class Cliente`, `class Tenant`, `class User`
- Atributos snake_case: `nome_empresa`, `created_at`
- Sempre incluir: `id`, `ativo`, `created_at`, `updated_at`

**Schemas (Pydantic):**
- Create: `ClienteCreate` (sem id, timestamps)
- Response: `ClienteResponse` (com id, timestamps)
- Update: `ClienteUpdate` (todos campos opcionais)

### Frontend (HTML/JavaScript)

**IDs HTML:**
- snake_case com prefixo: `#cliente-nome`, `#form-cliente`, `#btn-salvar`
- Classes: kebab-case: `.form-card`, `.btn-primary`, `.empty-state`

**Funções JavaScript:**
- CRUD: `adicionarCliente()`, `carregarClientes()`, `editarCliente()`, `deletarCliente()`
- Validation: `validarEmail()`, `validarCPF()`
- UI: `showNotification()`, `navigateTo()`, `clearErrors()`

**Organização:**
```javascript
// 1. Configuração global
const API_BASE = ...
const TOKEN = ...

// 2. Funções de notificação
function showNotification() { }

// 3. Funções de validação
function validarEmail() { }

// 4. Funções de autenticação
function logout() { }

// 5. CRUD por seção
// ===== CLIENTES =====
async function adicionarCliente() { }
async function carregarClientes() { }

// 6. Inicialização
document.addEventListener('DOMContentLoaded', () => { })
```

## 🚀 Deploy

### Local Development
```bash
# Terminal 1: Backend
docker-compose up db app

# Terminal 2: Acessar
http://localhost:8000/api/docs
http://localhost/admin/login.html
```

### Production (VPS)
```bash
git pull origin main
docker compose down
docker compose up -d --build
docker compose logs -f app
```

## 📝 Checklist para Novo Endpoint

- [ ] Model criado em `app/models.py`
- [ ] Schema criado em `app/schemas.py`
- [ ] Router criado/atualizado em `app/routers/`
- [ ] Documentação com docstring
- [ ] Validação de entrada
- [ ] Tratamento de erro
- [ ] CORS configurado se necessário
- [ ] Teste manual com Swagger `/api/docs`

## 🔐 Segurança

- [x] JWT tokens com expiração
- [x] Hash bcrypt para senhas
- [x] CORS restrito a domínios
- [x] Validação de email (EmailStr)
- [x] Proteção contra SQL injection (SQLAlchemy)
- [ ] Rate limiting
- [ ] HTTPS (em production)

## 📊 Status da Implementação

### ✅ Concluído
- Login multi-tenant
- CRUD Clientes
- CRUD Restaurantes
- CRUD Usuários
- Delete com cascade
- Email validation

### 🔄 Em Progresso
- Email constraint (remover UNIQUE global)
- Novo entrypoint com migrações

### ❌ Não Iniciado
- Services layer (separar lógica)
- Testes unitários
- Testes de integração
- Documentação de API
- Mobile app
- Rate limiting
- Cache/Redis

## 🐛 Problema Atual

**Erro:** "Email já cadastrado" ao criar usuário mesmo com lista vazia

**Causa:** Constraint UNIQUE global no campo `email` da tabela `users`

**Solução:** Migração 005 para permitir emails duplicados entre clientes
- Remove: `UNIQUE(email)`
- Adiciona: `UNIQUE(email, cliente_id)` para emails locais por cliente
- Admins com `cliente_id=NULL` têm email único globalmente

**Como aplicar:**
1. `git pull` no VPS
2. `docker compose down && docker compose up -d --build`
3. Migration 005 será aplicada automaticamente
4. Tentar cadastrar usuário novamente
