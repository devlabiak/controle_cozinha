# 🔒 GUIA DE SEGURANÇA - Controle de Cozinha

## ✅ Correções de Segurança Implementadas

### 1. **SECRET_KEY Obrigatória e Validada** ✅
- **Arquivo:** `app/config.py`
- **Mudança:** SECRET_KEY agora é OBRIGATÓRIA e não pode ser a padrão
- **Validação:** Erro fatal se SECRET_KEY está hardcoded ou vazia
- **Geração:** `python -c "import secrets; print(secrets.token_urlsafe(64))"`

### 2. **Isolamento Multi-Tenant Reforçado** ✅
- **Arquivo:** `app/middleware.py`
- **Mudança:** Validação CRÍTICA do tenant_id contra o usuário do JWT
- **Proteção:** Impossível acessar restaurante sem ter permissão (mesmo com URL manipulada)
- **Log:** Tentativas não autorizadas são registradas com erro CRÍTICO

### 3. **Helpers de Validação Centralizados** ✅
- **Arquivo:** `app/security_helpers.py`
- **Funções:** 
  - `validate_user_tenant_access()` - Valida acesso a um tenant
  - `validate_tenant_exists()` - Verifica se tenant existe
  - `require_admin_access()` - Exige permissão admin
  - `get_user_tenants()` - Lista tenants autorizado do usuário

### 4. **Security Headers Adicionados** ✅
- **Arquivo:** `app/main.py`
- **Headers:**
  - `X-Frame-Options: DENY` - Previne clickjacking
  - `X-Content-Type-Options: nosniff` - Desabilita MIME sniffing
  - `X-XSS-Protection: 1; mode=block` - Proteção XSS
  - `Content-Security-Policy` - Política de origem de conteúdo
  - `Strict-Transport-Security` - Força HTTPS
  - `Referrer-Policy` - Controla compartilhamento de referrer

### 5. **Cookies HttpOnly (Em Produção)** ✅
- **Arquivo:** `.env`
- **Config:** 
  - `COOKIE_SECURE=true` (força HTTPS em produção)
  - `COOKIE_SAMESITE=strict` (máxima proteção contra CSRF)
- **Benefício:** Token não acessível via JavaScript (proteção contra XSS)

### 6. **Refresh Tokens e Logout** ✅
- **Arquivo:** `app/routers/auth.py`
- **Endpoints:**
  - `POST /api/auth/refresh` - Renova token sem email/senha
  - `POST /api/auth/logout` - Faz logout e remove cookie
  - `GET /api/auth/verify` - Verifica se sessão é válida
- **Validação:** Revalida status do usuário e empresa em cada refresh

### 7. **CORS Configurado Corretamente** ✅
- **Arquivo:** `app/config.py` e `app/main.py`
- **Mudança:** Apenas domínios específicos permitidos
- **Variável:** `ALLOWED_ORIGINS` (ajustável por .env)

### 8. **Configurações em .env Obrigatório** ✅
- **Arquivo:** `.env` (gerado automaticamente)
- **Não committado:** `.gitignore` bloqueia arquivo .env real
- **Template:** `.env.example` com todos os campos
- **Validação:** Erro fatal se .env está faltando

---

## 📋 Configuração Inicial

### 1. **Primeiro Setup**

```bash
# 1. Copiar template
cp .env.example .env

# 2. Gerar uma SECRET_KEY forte DIFERENTE
python -c "import secrets; print(secrets.token_urlsafe(64))"

# 3. Editar .env e colocar a SECRET_KEY gerada
nano .env

# 4. Verificar se as configurações estão OK
python -c "from app.config import settings; print('✅ Config OK')"
```

### 2. **Para Produção**

```bash
# Alterar em .env:
COOKIE_SECURE=true
COOKIE_SAMESITE=strict
LOG_LEVEL=WARNING
```

---

## 🔐 Variáveis de Ambiente Críticas

| Variável | Obrigatória | Padrão | Descrição |
|----------|-------------|--------|-----------|
| `DATABASE_URL` | ✅ SIM | - | URL PostgreSQL |
| `SECRET_KEY` | ✅ SIM | - | Chave JWT (64+ chars) |
| `BASE_DOMAIN` | ✅ SIM | - | Domínio principal |
| `ALLOWED_ORIGINS` | ✅ SIM | - | Domínios CORS (vírgula) |
| `COOKIE_SECURE` | Não | false | HTTPS only (true em prod) |
| `COOKIE_SAMESITE` | Não | strict | SameSite policy |
| `REDIS_URL` | Não | localhost | Para blacklist tokens |

---

## 🚀 Deploy em Produção

### 1. **Gerar Nova SECRET_KEY**
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
# Copiar output para SECRET_KEY no .env de produção
```

### 2. **Verificar Configurações**
```bash
python -c "from app.config import settings; settings.validate_settings()"
# Deve retornar: ✅ Todas as configurações de segurança validadas
```

### 3. **Habilitar HTTPS**
- Colocar certificado SSL no nginx/proxy reverso
- Em .env: `COOKIE_SECURE=true`
- Em .env: `ENABLE_HTTPS_REDIRECT=true`

### 4. **Testar Isolamento Multi-Tenant**
```bash
# Tentar acessar outro restaurante deve resultar em 403:
curl -H "Authorization: Bearer TOKEN_USER_A" \
     "https://restaurante-b.wlsolucoes.eti.br/api/tenant/999/alimentos"
# Esperado: 403 Forbidden
```

---

## 📊 Vulnerabilidades Corrigidas

| # | Problema | Status | Detalhes |
|----|----------|--------|----------|
| 1 | SECRET_KEY hardcoded | ✅ FIXO | Agora obrigatória do .env |
| 2 | CORS aberto | ✅ FIXO | Apenas domínios autorizados |
| 3 | Tenant_id manipulável | ✅ FIXO | Validado no middleware |
| 4 | JWT sem revalidação | ✅ FIXO | Endpoints de refresh/verify |
| 5 | Sem proteção CSRF | ✅ FIXO | Cookies SameSite=strict |
| 6 | Token em localStorage | ✅ FIXO | HttpOnly cookies (prod) |
| 7 | Sem security headers | ✅ FIXO | CSP, HSTS, X-Frame, etc |
| 8 | DB credentials expostas | ✅ FIXO | Via .env obrigatório |

---

## 🔍 Testes de Segurança

### Teste 1: Validação de SECRET_KEY
```bash
# Deve falhar se SECRET_KEY é padrão
export SECRET_KEY="change-me"
python app/main.py
# Esperado: ValueError com msg de erro
```

### Teste 2: Isolamento Multi-Tenant
```bash
# Usuário A tenta acessar restaurante de Usuário B
curl -H "Authorization: Bearer TOKEN_A" \
  "https://restaurante-b.wlsolucoes.eti.br/api/tenant/2/alimentos"
# Esperado: 403 Forbidden - "Acesso negado a este restaurante"
```

### Teste 3: Token Expirado
```bash
# Usar token expirado
curl -H "Authorization: Bearer EXPIRED_TOKEN" \
  "https://app.wlsolucoes.eti.br/api/auth/me"
# Esperado: 401 Unauthorized
```

### Teste 4: CORS Inválido
```bash
# Fazer requisição de origem não autorizada
curl -H "Origin: https://attacker.com" \
  -H "Authorization: Bearer TOKEN" \
  "https://app.wlsolucoes.eti.br/api/auth/me"
# Esperado: CORS bloqueado ou erro 401
```

---

## 📝 Notas Importantes

1. **Nunca commitar .env real**: `.gitignore` protege, mas sempre double-check
2. **Regenerar SECRET_KEY regularmente**: Em produção, a cada 6 meses
3. **Backup de .env**: Guardar em local seguro (AWS Secrets Manager, HashiCorp Vault)
4. **Monitorar logs**: Procurar por "❌" ou "🚨" para violações de segurança
5. **Testar em staging**: Antes de colocar em produção

---

## 🆘 Troubleshooting

### Erro: "SECRET_KEY não está definida"
```
Solução: Verificar se .env existe e SECRET_KEY está preenchido
```

### Erro: "Acesso negado a este restaurante" (inesperado)
```
Solução: Verificar se token contém tenant_id_correto
         curl -H "Authorization: Bearer TOKEN" https://app.../api/auth/verify
```

### Erro: "Token inválido ou expirado"
```
Solução: Fazer refresh do token
         POST /api/auth/refresh
```

---

## 📞 Suporte

Para dúvidas de segurança, enviar email com detalhes em:
security@wlsolucoes.eti.br
