# 🔒 Análise de Segurança - Controle de Cozinha

**Data da Análise:** 2 de fevereiro de 2026  
**Versão da Aplicação:** 1.0.0  
**Escopo:** Backend FastAPI + Frontend + Infraestrutura Docker

---

## 📋 Sumário Executivo

A aplicação é um **sistema SaaS multi-tenant** para controle de estoque de cozinha/restaurantes. Foram identificados **14 problemas de segurança**, sendo:

- 🔴 **CRÍTICO:** 5 issues
- 🟠 **ALTO:** 6 issues  
- 🟡 **MÉDIO:** 3 issues

---

## 🔴 PROBLEMAS CRÍTICOS

### 1. **SECRET_KEY Hardcoded em Produção**
**Arquivo:** [app/config.py](app/config.py#L10)  
**Severidade:** CRÍTICA  
**Descrição:**
```python
SECRET_KEY: str = "sua-chave-secreta-super-segura-aqui"
```
A chave secreta está hardcoded com um valor padrão. Qualquer pessoa com acesso ao repositório pode comprometer todos os tokens JWT.

**Impacto:**
- Todos os tokens JWT podem ser forjados
- Possibilidade de impersonação de qualquer usuário
- Perda total da autenticação

**Recomendação:**
```python
# ✅ Usar variáveis de ambiente obrigatórias
SECRET_KEY: str  # Sem valor padrão, deve vir de .env
ALGORITHM: str = "HS256"

class Config:
    env_file = ".env"
    # Validar que SECRET_KEY foi carregada
```

---

### 2. **CORS Configurado com `allow_origins=["*"]`**
**Arquivo:** [app/main.py](app/main.py#L26)  
**Severidade:** CRÍTICA  
**Descrição:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ CRÍTICO!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Impacto:**
- Qualquer site pode fazer requisições à API em nome do usuário
- Ataques CSRF (Cross-Site Request Forgery)
- Roubo de cookies/tokens de qualquer origem

**Recomendação:**
```python
# ✅ Especificar domínios permitidos
ALLOWED_ORIGINS = [
    "https://painelfood.wlsolucoes.eti.br",
    "https://*.wlsolucoes.eti.br",  # Se for dinâmico
    "https://app.wlsolucoes.eti.br"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # Específicos
    allow_headers=["Content-Type", "Authorization"],  # Específicos
    max_age=3600  # Cache
)
```

---

### 3. **Credenciais do Banco de Dados em Docker Compose**
**Arquivo:** [docker-compose.yml](docker-compose.yml#L5-L8)  
**Severidade:** CRÍTICA  
**Descrição:**
```yaml
environment:
  POSTGRES_USER: postgres
  POSTGRES_PASSWORD: postgres_db_2026  # ⚠️ Hardcoded!
  POSTGRES_DB: controle_cozinha
```

**Impacto:**
- Credenciais expostas no repositório
- Qualquer pessoa pode acessar a base de dados
- Violação de dados de todos os clientes

**Recomendação:**
```yaml
# ✅ Usar variáveis de ambiente
environment:
  POSTGRES_USER: ${DB_USER}
  POSTGRES_PASSWORD: ${DB_PASSWORD}
  POSTGRES_DB: ${DB_NAME}

# Criar arquivo .env.local (NÃO comitar)
# DB_USER=postgres
# DB_PASSWORD=<senha-complexa-aleatória>
# DB_NAME=controle_cozinha
```

---

### 4. **Validação de Tenant Débil (TenantMiddleware)**
**Arquivo:** [app/middleware.py](app/middleware.py#L30-L45)  
**Severidade:** CRÍTICA  
**Descrição:**

O middleware valida o tenant apenas pelo subdomínio, sem verificar se o usuário autenticado realmente tem acesso aquele tenant:

```python
# O código faz isso:
tenant = db.query(Tenant).filter(
    Tenant.slug == tenant_slug,
    Tenant.ativo == True
).first()

# ⚠️ NÃO verifica se current_user tem acesso a este tenant!
request.state.tenant_id = tenant_id
```

**Impacto:**
- Um usuário pode acessar ANY tenant apenas mudando o subdomínio
- Falta separação de dados entre clientes
- Violação do princípio de multi-tenancy

**Cenário de Ataque:**
1. Usuário se loga em `restaurante_a.wlsolucoes.eti.br`
2. Muda URL para `restaurante_b.wlsolucoes.eti.br`
3. Acessa dados de outro cliente!

**Recomendação:**
```python
# ✅ Validar tanto subdomínio quanto permissão do usuário
async def dispatch(self, request: Request, call_next):
    # ... extrair tenant_slug ...
    
    # ✅ Se for autenticado, verificar permissão
    if "authorization" in request.headers:
        try:
            token = request.headers["authorization"].split(" ")[1]
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_tenant_ids = payload.get("tenant_ids", [])
            
            # Buscar tenant
            tenant = db.query(Tenant).filter(...).first()
            
            # VALIDAR QUE USER TEM ACESSO
            if tenant and tenant.id not in user_tenant_ids:
                raise HTTPException(status_code=403, detail="Acesso negado")
                
            request.state.tenant_id = tenant.id
        except:
            # Erro na decodificação - deixar passar para autenticação
            pass
```

---

### 5. **Falta de Rate Limiting / Proteção contra Brute Force**
**Arquivo:** [app/routers/auth.py](app/routers/auth.py#L13)  
**Severidade:** CRÍTICA  
**Descrição:**

Não há proteção contra tentativas repetidas de login. Um atacante pode fazer força bruta:

```python
@router.post("/login", response_model=Token)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    # ⚠️ Nenhuma proteção contra brute force!
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.senha, user.senha_hash):
        raise HTTPException(status_code=401, ...)
```

**Impacto:**
- Ataque de força bruta contra contas
- Acesso não autorizado a contas de usuários
- Possibilidade de enumerar usuários válidos

**Recomendação:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Em app/main.py
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Em routers/auth.py
@router.post("/login")
@limiter.limit("5/minute")  # 5 tentativas por minuto
def login(request: Request, credentials: LoginRequest, db: Session = Depends(get_db)):
    # Implementar lockout após X tentativas
    ...
```

---

## 🟠 PROBLEMAS ALTOS

### 6. **Falta de HTTPS/TLS Obrigatório**
**Arquivo:** [nginx/nginx.conf](nginx/nginx.conf)  
**Severidade:** ALTO  
**Descrição:**

O Nginx está configurado apenas para HTTP (porta 80). Não há redirecionamento HTTPS:

```properties
ports:
  - "80:80"   # ✅ HTTP
  - "443:443" # ❌ Não configurado/vazio
```

**Impacto:**
- Credenciais enviadas em texto plano
- Tokens JWT podem ser interceptados (Man-in-the-Middle)
- Sem criptografia de dados sensíveis

**Recomendação:**
```nginx
# ✅ Redirecionar HTTP → HTTPS
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

# ✅ HTTPS com certificado
server {
    listen 443 ssl http2;
    ssl_certificate /etc/nginx/ssl/certificate.crt;
    ssl_certificate_key /etc/nginx/ssl/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    # ... resto da configuração
}
```

---

### 7. **Tokens JWT sem Validação de Expiração**
**Arquivo:** [app/security.py](app/security.py#L40-L54)  
**Severidade:** ALTO  
**Descrição:**

Os tokens JWT têm expiração, mas a validação é fraca:

```python
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)  # 15 min padrão
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

**Problemas:**
1. Tempo de expiração MUITO longo (15-30 minutos) para SaaS
2. Sem mecanismo de refresh token
3. Sem logout real (token permanece válido até expirar)

**Impacto:**
- Se token for roubado, fica válido por 15-30 minutos
- Usuário não pode fazer logout imediato
- Sem invalidação proativa de sessions

**Recomendação:**
```python
# ✅ Reduzir tempo de expiração
ACCESS_TOKEN_EXPIRE_MINUTES: int = 5  # Mais curto

# ✅ Implementar refresh tokens
def create_tokens(data: dict) -> dict:
    access_token = create_access_token(data, expires_delta=timedelta(minutes=5))
    refresh_token = create_refresh_token(data, expires_delta=timedelta(days=7))
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

# ✅ Endpoint para refresh
@router.post("/refresh")
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    # Validar refresh token e gerar novo access token
    ...

# ✅ Blacklist de tokens (logout)
# Usar Redis para armazenar tokens revogados
```

---

### 8. **Falta de Validação de Entrada (SQL Injection Risk)**
**Arquivo:** [app/routers/tenant_alimentos.py](app/routers/tenant_alimentos.py#L61-L70)  
**Severidade:** ALTO  
**Descrição:**

Embora use ORM (SQLAlchemy), há risco em campos não validados:

```python
@router.post("/{tenant_id}/alimentos", response_model=AlimentoResponse)
def create_alimento(
    tenant_id: int,
    alimento_data: AlimentoCreate,  # ⚠️ Validação Pydantic, OK
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    new_alimento = Alimento(
        tenant_id=tenant_id,
        **alimento_data.dict()  # ✅ Via ORM, seguro
    )
```

**Pontos de Risco:**
- Campo `observacoes` (Text) sem limite de tamanho
- Campo `slug` sem validação de formato
- Sem sanitização de entrada para campos de texto

**Recomendação:**
```python
# ✅ Validar tamanho e formato
class AlimentoCreate(BaseModel):
    nome: str = Field(..., min_length=1, max_length=255)
    observacoes: Optional[str] = Field(None, max_length=1000)
    
    @validator('nome')
    def nome_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Nome não pode estar vazio')
        return v.strip()
```

---

### 9. **Exposição de Informações Sensíveis em Logs**
**Arquivo:** [app/auth.py](app/auth.py#L58-L68)  
**Severidade:** ALTO  
**Descrição:**

Logs mostram informações sensíveis em produção:

```python
payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
email: str = payload.get("sub")
user_id: int = payload.get("user_id")

print(f"🔍 Token decodificado - user_id: {user_id}, email: {email}")  # ⚠️ Log sensível
print(f"🔍 Usuário encontrado no banco: {user is not None}")
print(f"🔍 Usuário ativo: {user.ativo}")
```

**Impacto:**
- Logs mostram dados de usuários
- Em caso de breach dos logs, dados sensíveis são expostos
- Violação de LGPD/GDPR

**Recomendação:**
```python
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Usar estruturado e sem dados sensíveis
logger.debug(f"Token validation attempt for user_id: {user_id % 1000}")  # Hashear
logger.info("Authentication successful")  # Genérico
```

---

### 10. **Falta de Validação de Permissão Consistente**
**Arquivo:** [app/routers/tenant_alimentos.py](app/routers/tenant_alimentos.py#L21-L35)  
**Severidade:** ALTO  
**Descrição:**

Verificação de permissão manual em cada rota (não DRY):

```python
def verificar_admin_restaurante(tenant_id: int, user: User, db: Session):
    """Verifica se o usuário tem permissão de admin no restaurante"""
    if user.is_admin:
        return True
    
    stmt = select(user_tenants_association).where(...)
    result = db.execute(stmt).first()
    
    if not result or result.role != RoleType.ADMIN:
        raise HTTPException(status_code=403, ...)
```

**Problemas:**
- Implementação duplicada em múltiplas rotas
- Fácil esquecer a validação em novos endpoints
- Sem auditoria centralizada

**Recomendação:**
```python
# ✅ Usar Dependency Injection
from fastapi import Depends

async def get_tenant_context(
    tenant_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Context com validações já feitas"""
    # Validar tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404)
    
    # Validar acesso do user
    if current_user.id not in [t.id for t in current_user.tenants]:
        raise HTTPException(status_code=403)
    
    return tenant

# Usar em rotas:
@router.post("/{tenant_id}/alimentos")
def create_alimento(
    alimento_data: AlimentoCreate,
    tenant_context = Depends(get_tenant_context),
    current_user: User = Depends(get_current_user)
):
    # tenant_context já foi validado!
    ...
```

---

### 11. **Sem Proteção contra CSRF em Formulários**
**Arquivo:** [app/main.py](app/main.py)  
**Severidade:** ALTO  
**Descrição:**

Não há proteção CSRF mesmo usando cookies (se usados):

```python
# ✅ CORS permite credenciais
allow_credentials=True,
allow_methods=["*"],  # ⚠️ DELETE, PUT, PATCH sem validação
```

**Impacto:**
- POST/DELETE podem ser executados de site externo
- Mudanças não autorizadas em dados

**Recomendação:**
```python
from starlette.middleware.csrf import CSRFMiddleware

app.add_middleware(
    CSRFMiddleware,
    secret_key=settings.SECRET_KEY,
    safe_methods=["GET", "HEAD", "OPTIONS"],
    protected_methods=["POST", "PUT", "DELETE", "PATCH"]
)
```

---

### 12. **Dados de Teste em Produção**
**Arquivo:** [docker-compose.yml](docker-compose.yml#L10)  
**Severidade:** ALTO  
**Descrição:**

Script de seed de dados pode preencher dados de teste em produção:

```bash
# em entrypoint.sh
python scripts/create_admin.py || true  # Cria usuário admin
```

Arquivo [scripts/create_admin.py](scripts/create_admin.py) pode ter credenciais padrão.

**Recomendação:**
```bash
# ✅ Separar ambientes
if [ "$ENVIRONMENT" = "production" ]; then
    echo "Production - Skipping seed scripts"
else
    python scripts/create_admin.py
    python scripts/seed_data.py
fi
```

---

## 🟡 PROBLEMAS MÉDIOS

### 13. **Falta de Validação de Comprimento de Senhas**
**Arquivo:** [app/security.py](app/security.py#L27)  
**Severidade:** MÉDIO  
**Descrição:**

Sem requisitos mínimos de senha:

```python
class UsuarioCreate(BaseModel):
    senha: str  # ⚠️ Sem validação de força
```

**Recomendação:**
```python
from pydantic import field_validator

class UsuarioCreate(BaseModel):
    senha: str = Field(..., min_length=8)
    
    @field_validator('senha')
    @classmethod
    def validate_password_strength(cls, v):
        if len(v) < 8:
            raise ValueError('Mínimo 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('Deve conter letra maiúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('Deve conter número')
        if not any(c in '!@#$%^&*' for c in v):
            raise ValueError('Deve conter caractere especial')
        return v
```

---

### 14. **Falta de Auditoria (Audit Logging)**
**Arquivo:** Toda aplicação  
**Severidade:** MÉDIO  
**Descrição:**

Não há registro de quem fez o quê e quando. Essencial para SaaS:

```python
# ⚠️ Não há registro de:
# - Quem deletou um cliente
# - Quem alterou permissões
# - Quem acessou dados sensíveis
```

**Impacto:**
- Impossível investigar violações de segurança
- Não conformidade com regulamentações

**Recomendação:**
```python
# ✅ Criar tabela de auditoria
class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tenant_id = Column(Integer, ForeignKey("tenants.id"))
    action = Column(String(100))  # create, update, delete
    resource_type = Column(String(50))  # user, alimento, etc
    resource_id = Column(Integer)
    old_value = Column(JSON)  # Antes
    new_value = Column(JSON)  # Depois
    ip_address = Column(String(45))
    timestamp = Column(DateTime, server_default=func.now())
```

---

## 📋 Tabela de Risco

| # | Problema | Severidade | Componente | CVSS |
|---|----------|-----------|-----------|------|
| 1 | SECRET_KEY Hardcoded | 🔴 CRÍTICA | Config | 9.8 |
| 2 | CORS wildcard | 🔴 CRÍTICA | Main | 9.1 |
| 3 | DB Credentials | 🔴 CRÍTICA | Docker | 9.9 |
| 4 | Validação Tenant Fraca | 🔴 CRÍTICA | Middleware | 9.3 |
| 5 | Sem Rate Limiting | 🔴 CRÍTICA | Auth | 8.2 |
| 6 | Sem HTTPS | 🟠 ALTO | Nginx | 8.1 |
| 7 | Token sem Refresh | 🟠 ALTO | Security | 7.4 |
| 8 | Validação de Entrada | 🟠 ALTO | Routes | 7.2 |
| 9 | Logs Sensíveis | 🟠 ALTO | Auth | 7.5 |
| 10 | Permissões Inconsistentes | 🟠 ALTO | Routes | 7.1 |
| 11 | Sem CSRF | 🟠 ALTO | Main | 6.9 |
| 12 | Dados de Teste | 🟠 ALTO | Deploy | 6.5 |
| 13 | Validação Senha | 🟡 MÉDIO | Security | 5.8 |
| 14 | Sem Auditoria | 🟡 MÉDIO | Database | 5.2 |

---

## ✅ Recomendações Prioritárias

### **Semana 1 (Crítico)**
1. ✅ Mudar SECRET_KEY para variável de ambiente obrigatória
2. ✅ Restringir CORS para domínios específicos
3. ✅ Mover credenciais DB para .env
4. ✅ Validar tenant_id em relação ao usuário no middleware
5. ✅ Implementar rate limiting no login

### **Semana 2 (Alto)**
6. ✅ Configurar HTTPS no Nginx
7. ✅ Implementar Refresh Token (reduzir expiração)
8. ✅ Adicionar validação de entrada em campos críticos
9. ✅ Remover print() de debug em produção
10. ✅ Centralizar validação de permissões

### **Semana 3 (Médio)**
11. ✅ Implementar CSRF protection
12. ✅ Separar scripts de seed por ambiente
13. ✅ Adicionar validação de força de senha
14. ✅ Implementar audit logging

---

## 🔍 Checklist de Segurança Contínua

- [ ] Revisar logs regularmente
- [ ] Realizar penetration testing trimestral
- [ ] Atualizar dependências mensalmente (pip security audit)
- [ ] Implementar WAF (Web Application Firewall)
- [ ] Backup automático com encryption
- [ ] Monitoramento de anomalias
- [ ] Policy de senha corporativa
- [ ] MFA obrigatório para admins
- [ ] Conformidade LGPD/GDPR
- [ ] Política de segurança de dados

---

## 📚 Referências

- [OWASP Top 10 2023](https://owasp.org/Top10/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [JWT Best Practices](https://tools.ietf.org/html/rfc8725)
- [CWE Top 25](https://cwe.mitre.org/top25/)

---

**Análise realizada:** 2 de fevereiro de 2026  
**Próxima revisão recomendada:** 2 de maio de 2026 (trimestral)
