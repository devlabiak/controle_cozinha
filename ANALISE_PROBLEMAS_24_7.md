# Análise de Problemas - Sistema 24/7

**Data:** 03/02/2026  
**Objetivo:** Identificar pontos críticos que podem comprometer a disponibilidade 24/7, código duplicado e código não utilizado.

---

## 🔴 PROBLEMAS CRÍTICOS - Alta Prioridade

### 1. **Conexões de Banco de Dados Não Gerenciadas (CRÍTICO)**

**Localização:** Múltiplos arquivos
- `app/auth.py` (linha 67)
- `app/middleware.py` (linha 37)
- `app/security.py` (linha 73)
- `app/routers/auth.py` (linha 167)

**Problema:**
```python
# Padrão problemático encontrado:
db = SessionLocal()
try:
    # operações
finally:
    db.close()
```

**Impacto:**
- **Vazamento de conexões**: Conexões criadas manualmente sem uso do dependency injection
- **Pool exhaustion**: Em alta carga, o pool de conexões pode se esgotar
- **Timeout de conexões**: Sistema pode parar de responder sob carga

**Solução:**
Usar sempre `Depends(get_db)` do FastAPI em vez de criar sessões manualmente. Isso garante:
- Gerenciamento automático de conexões
- Fechamento garantido mesmo em caso de exceção
- Melhor performance sob carga

---

### 2. **Falta de Configuração de Pool de Conexões (CRÍTICO)**

**Localização:** `app/database.py`

**Problema:**
```python
engine = create_engine(settings.DATABASE_URL)
# Sem parâmetros de pool!
```

**Impacto:**
- Pool com configurações padrão pode ser insuficiente para produção
- Conexões podem ficar presas indefinidamente
- Sistema pode travar sob carga alta

**Solução:**
```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,              # Tamanho do pool
    max_overflow=40,           # Conexões extras permitidas
    pool_pre_ping=True,        # Verifica conexões antes de usar
    pool_recycle=3600,         # Recicla conexões a cada hora
    echo_pool=False,
    connect_args={
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000"
    }
)
```

---

### 3. **Task Assíncrona Sem Tratamento de Erro Robusto (CRÍTICO)**

**Localização:** `app/main.py` (linhas 82-91)

**Problema:**
```python
async def history_cleanup_worker():
    while True:
        try:
            removed = cleanup_history()
            # ...
        except Exception:  # pragma: no cover
            logger.exception("Erro ao executar limpeza de histórico")
        await asyncio.sleep(24 * 60 * 60)
```

**Impactos:**
- Task pode morrer silenciosamente e nunca mais executar
- Sem monitoramento de saúde da task
- Sem backoff exponencial em caso de falhas repetidas

**Solução:**
```python
async def history_cleanup_worker():
    retry_count = 0
    max_retries = 5
    base_sleep = 60  # 1 minuto
    
    while True:
        try:
            removed = cleanup_history()
            if removed:
                logger.info(f"✅ {removed} movimentações removidas")
            retry_count = 0  # Reset em caso de sucesso
            await asyncio.sleep(24 * 60 * 60)
            
        except Exception as e:
            retry_count += 1
            sleep_time = min(base_sleep * (2 ** retry_count), 3600)
            logger.error(f"❌ Erro na limpeza (tentativa {retry_count}): {e}")
            
            if retry_count >= max_retries:
                logger.critical(f"🔥 FALHA CRÍTICA: cleanup worker falhou {max_retries}x")
                # Notificar admin via email/webhook
            
            await asyncio.sleep(sleep_time)
```

---

### 4. **Código Duplicado: Duas Implementações de Autenticação (ALTO RISCO)**

**Localização:**
- `app/auth.py` - Implementação antiga
- `app/security.py` - Implementação nova

**Problema:**
```python
# Em auth.py
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    # implementação...

# EM security.py (DUPLICADO!)
def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    # implementação diferente usando timezone.utc!
```

**Impactos:**
- **Confusão de importações**: Diferentes partes do código importam de lugares diferentes
- **Inconsistência**: Implementações ligeiramente diferentes (timezone.utc vs utcnow())
- **Manutenção difícil**: Mudanças precisam ser feitas em dois lugares
- **Bugs potenciais**: Diferenças sutis podem causar comportamento inesperado

**Usado por:**
- `app/auth.py` é importado em `tenant_alimentos.py`, `admin_usuarios.py`, etc.
- `app/security.py` é importado em `tenant_usuarios.py`, `routers/auth.py`

**Solução:** Consolidar tudo em `app/security.py` e remover de `app/auth.py`

---

### 5. **Router Duplicado e Não Utilizado (MÉDIO RISCO)**

**Localização:**
- `app/routers/tenant_users.py` - **NÃO USADO**
- `app/routers/tenant_usuarios.py` - Usado atualmente

**Problema:**
```python
# tenant_users.py usa função que não existe mais!
from app.auth import get_current_tenant_admin  # ❌ Função inexistente

# Implementa CRUD completo mas nunca é importado em main.py
```

**Impactos:**
- Código morto confunde desenvolvedores
- Testes podem estar testando código não utilizado
- Possível confusão sobre qual router usar

**Verificação:** `tenant_users.py` NÃO está em `app/main.py`:
```python
# main.py só importa tenant_usuarios
from app.routers import auth, admin_clientes, admin_usuarios, tenant_alimentos, tenant_usuarios, admin_audit
```

**Solução:** Remover `app/routers/tenant_users.py` completamente

---

### 6. **Atributo de Modelo Não Existente (BUG)**

**Localização:** `app/auth.py` (linha 104), `tenant_users.py`

**Problema:**
```python
def get_current_tenant_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_tenant_admin and not current_user.is_admin:  # ❌ is_tenant_admin não existe!
        raise HTTPException(...)
```

**Verificação no modelo User (`app/models.py`):**
```python
class User(Base):
    # ...
    is_admin = Column(Boolean, default=False)  # ✅ Existe
    # is_tenant_admin NÃO EXISTE! ❌
```

**Impacto:**
- `AttributeError` em tempo de execução
- Sistema pode crashar ao tentar usar esse endpoint
- Função `get_current_tenant_admin` está quebrada

**Solução:**
Remover essa função (não é usada) ou reimplementar usando a tabela `user_tenants_association` com verificação de `role`

---

## 🟡 PROBLEMAS DE CÓDIGO - Média Prioridade

### 7. **Código de Debug em Produção**

**Localização:** `app/routers/tenant_alimentos.py` (múltiplas linhas)

**Problema:**
```python
print(f"🔍 DEBUG - Data produção no banco: {movimentacao.data_producao}")
print(f"🔍 DEBUG - Data validade no banco: {movimentacao.data_validade}")
print(f"🔵 Endpoint /qrcode/usar chamado")
print(f"🔵 tenant_id: {tenant_id}")
print(f"🔵 qr_code: {qr_code}")
# ... 20+ chamadas print() para debug
```

**Impacto:**
- Logs poluídos em produção
- Informações sensíveis podem vazar (IDs, dados)
- Performance reduzida (I/O síncrono)
- Impossível controlar níveis de log

**Solução:**
Substituir por logging estruturado:
```python
logger.debug("Validando QR code", extra={
    "tenant_id": tenant_id,
    "qr_code": qr_code[:8] + "...",  # Parcial por segurança
    "user_id": current_user.id
})
```

---

### 8. **Falta de Índices Compostos no Banco**

**Localização:** `app/models.py`

**Problema:**
Queries comuns usam múltiplas colunas mas só há índices simples:

```python
# Query comum:
MovimentacaoEstoque.filter(
    MovimentacaoEstoque.tenant_id == tenant_id,
    MovimentacaoEstoque.tipo == 'entrada',
    MovimentacaoEstoque.data_validade <= data_limite
)
# Só tenant_id e tipo têm índice individual!
```

**Solução:**
Adicionar índices compostos em migration:
```python
Index('ix_movimentacoes_tenant_tipo', 'tenant_id', 'tipo')
Index('ix_movimentacoes_tenant_validade', 'tenant_id', 'data_validade')
Index('ix_lotes_tenant_ativo', 'tenant_id', 'ativo', 'usado_completamente')
```

---

### 9. **Falta de Rate Limiting em Endpoints Críticos**

**Localização:** Maioria dos endpoints

**Problema:**
```python
# Apenas /login tem rate limit
@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(...):

# Outros endpoints estão desprotegidos:
@router.post("/{tenant_id}/alimentos")  # ❌ Sem rate limit
@router.post("/{tenant_id}/movimentacoes")  # ❌ Sem rate limit
@router.post("/{tenant_id}/qrcode/usar")  # ❌ Sem rate limit
```

**Impacto:**
- Vulnerável a ataques DoS
- Abuso de API
- Custos elevados de banco de dados

**Solução:**
Adicionar rate limiting:
```python
@router.post("/{tenant_id}/alimentos")
@limiter.limit("100/minute")  # 100 requisições por minuto
def create_alimento(...):
```

---

### 10. **Falta de Timeout em Operações de Banco**

**Localização:** `app/database.py`

**Problema:**
Queries podem rodar indefinidamente e travar workers

**Solução:**
Já mencionado no item #2, adicionar `statement_timeout`

---

## 🟢 MELHORIAS RECOMENDADAS

### 11. **Monitoramento de Saúde (Health Checks)**

**Adicionar:**
```python
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Verifica DB
        db.execute(text("SELECT 1"))
        
        # Verifica task de cleanup
        task = getattr(app.state, "history_cleanup_task", None)
        task_healthy = task and not task.done()
        
        return {
            "status": "healthy",
            "database": "ok",
            "cleanup_task": "ok" if task_healthy else "error"
        }
    except Exception as e:
        raise HTTPException(500, detail=f"Unhealthy: {str(e)}")
```

---

### 12. **Logging Estruturado**

**Adicionar:**
```python
# config.py
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# main.py
import logging.config
logging.config.dictConfig({
    "version": 1,
    "formatters": {
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "level": settings.LOG_LEVEL
        }
    },
    "root": {
        "level": settings.LOG_LEVEL,
        "handlers": ["console"]
    }
})
```

---

### 13. **Graceful Shutdown**

**Adicionar em `main.py`:**
```python
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("🔴 Iniciando shutdown graceful...")
    
    # Cancela tasks
    task = getattr(app.state, "history_cleanup_task", None)
    if task:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    
    # Fecha pool de conexões
    engine.dispose()
    logger.info("✅ Shutdown completo")
```

---

## 📋 RESUMO DE AÇÕES PRIORITÁRIAS

### Urgente (Fazer Agora)
1. ✅ Configurar pool de conexões com timeouts
2. ✅ Remover código duplicado de autenticação
3. ✅ Remover `tenant_users.py` não utilizado
4. ✅ Substituir `print()` por `logging`
5. ✅ Adicionar tratamento robusto na task de cleanup

### Importante (Esta Semana)
6. ⚠️ Adicionar índices compostos no banco
7. ⚠️ Implementar rate limiting em todos endpoints
8. ⚠️ Melhorar health checks
9. ⚠️ Consolidar uso de `Depends(get_db)` em todos lugares

### Desejável (Este Mês)
10. 📝 Implementar logging estruturado (JSON)
11. 📝 Adicionar métricas (Prometheus)
12. 📝 Documentar arquitetura
13. 📝 Adicionar testes de carga

---

## 🔍 CHECKLIST DE VALIDAÇÃO

- [ ] Pool de conexões configurado e testado sob carga
- [ ] Todas sessões DB usando dependency injection
- [ ] Código duplicado removido (auth.py vs security.py)
- [ ] Router não utilizado removido (tenant_users.py)
- [ ] Debug prints substituídos por logger
- [ ] Rate limiting em todos endpoints públicos
- [ ] Índices compostos criados
- [ ] Task de cleanup com retry logic
- [ ] Health checks implementados
- [ ] Graceful shutdown implementado
- [ ] Testes de carga executados (verificar vazamentos)
- [ ] Monitoramento configurado

---

## 📊 ESTIMATIVA DE IMPACTO

**Antes das correções:**
- 🔴 Risco Alto de downtime sob carga
- 🔴 Vazamento de conexões provável
- 🟡 Código confuso e difícil de manter
- 🟡 Vulnerável a DoS

**Depois das correções:**
- 🟢 Sistema robusto e resiliente
- 🟢 Pronto para produção 24/7
- 🟢 Código limpo e manutenível
- 🟢 Protegido contra abusos

**Tempo estimado de correção:** 8-12 horas de desenvolvimento + testes
