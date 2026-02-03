# Alteração: Campos Detalhados para Restaurante

**Data:** 03/02/2026  
**Migration:** 008_add_tenant_address_responsible.py

---

## 📝 RESUMO DA ALTERAÇÃO

Adicionados campos detalhados de **endereço** e **pessoa responsável** no cadastro de restaurantes (Tenants).

---

## ✨ NOVOS CAMPOS ADICIONADOS

### Endereço Detalhado
- `rua` (String 255)
- `numero` (String 20)
- `complemento` (String 100)
- `bairro` (String 100)
- `cidade` (String 100) 
- `estado` (String 2) - Ex: "SP", "RJ"
- `cep` (String 10)

**Nota:** O campo `endereco` original foi mantido para compatibilidade com dados existentes.

### Pessoa Responsável
- `responsavel_nome` (String 255) - Nome completo
- `responsavel_telefone` (String 20) - Telefone de contato
- `responsavel_email` (String 255) - Email do responsável
- `responsavel_cargo` (String 100) - Ex: "Gerente", "Proprietário"

---

## 🔧 ARQUIVOS MODIFICADOS

### 1. `app/models.py`
- Atualizado modelo `Tenant` com novos campos

### 2. `app/routers/admin_clientes.py`
- Atualizado `RestauranteCreate` schema
- Atualizado `RestauranteResponse` schema

### 3. `app/schemas.py`
- Atualizado `TenantBase` schema
- Atualizado `TenantUpdate` schema

### 4. `alembic/versions/008_add_tenant_address_responsible.py`
- **NOVA MIGRATION** criada

---

## 🚀 COMO APLICAR NA VPS

### 1. Fazer commit e push
```bash
git add .
git commit -m "feat: adicionar campos detalhados de endereço e responsável para restaurantes"
git push origin main
```

### 2. Na VPS, atualizar código
```bash
cd /caminho/do/projeto
git pull origin main
```

### 3. Executar migration
```bash
# Ativar ambiente virtual se necessário
source venv/bin/activate  # Linux
# ou
.\venv\Scripts\Activate.ps1  # Windows

# Executar migration
alembic upgrade head
```

### 4. Reiniciar aplicação
```bash
# Docker
docker-compose restart app

# ou systemd
sudo systemctl restart controle_cozinha

# ou PM2
pm2 restart controle_cozinha
```

---

## 📋 EXEMPLO DE USO

### Criar Restaurante com Endereço Completo

**Request:**
```json
POST /api/admin/restaurantes
{
  "cliente_id": 1,
  "nome": "Restaurante Sabor & Arte",
  "slug": "sabor-arte",
  "email": "contato@saborarte.com",
  "telefone": "(11) 98765-4321",
  "cnpj": "12.345.678/0001-90",
  
  "rua": "Rua das Flores",
  "numero": "123",
  "complemento": "Loja 2",
  "bairro": "Centro",
  "cidade": "São Paulo",
  "estado": "SP",
  "cep": "01234-567",
  
  "responsavel_nome": "João Silva Santos",
  "responsavel_telefone": "(11) 91234-5678",
  "responsavel_email": "joao.silva@saborarte.com",
  "responsavel_cargo": "Gerente Geral"
}
```

**Response:**
```json
{
  "id": 5,
  "cliente_id": 1,
  "nome": "Restaurante Sabor & Arte",
  "slug": "sabor-arte",
  "email": "contato@saborarte.com",
  "telefone": "(11) 98765-4321",
  "cnpj": "12.345.678/0001-90",
  
  "rua": "Rua das Flores",
  "numero": "123",
  "complemento": "Loja 2",
  "bairro": "Centro",
  "cidade": "São Paulo",
  "estado": "SP",
  "cep": "01234-567",
  
  "responsavel_nome": "João Silva Santos",
  "responsavel_telefone": "(11) 91234-5678",
  "responsavel_email": "joao.silva@saborarte.com",
  "responsavel_cargo": "Gerente Geral",
  
  "ativo": true
}
```

---

## ✅ VALIDAÇÕES RECOMENDADAS

### Frontend
- Validar formato de CEP: `\d{5}-?\d{3}`
- Validar UF: lista com 27 estados brasileiros
- Validar telefone: formato brasileiro
- Validar email do responsável

### Backend (Futuro)
Adicionar validações em `RestauranteCreate`:
```python
from pydantic import validator

class RestauranteCreate(BaseModel):
    # ... campos ...
    
    @validator('estado')
    def validate_estado(cls, v):
        estados_validos = [
            'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 
            'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 
            'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
        ]
        if v and v not in estados_validos:
            raise ValueError('Estado inválido')
        return v
    
    @validator('cep')
    def validate_cep(cls, v):
        if v:
            import re
            if not re.match(r'^\d{5}-?\d{3}$', v):
                raise ValueError('CEP deve estar no formato 12345-678')
        return v
```

---

## 🗄️ ESTRUTURA DO BANCO APÓS MIGRATION

```sql
-- Tabela tenants (após migration 008)
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255),
    telefone VARCHAR(20),
    cnpj VARCHAR(20),
    
    -- Endereço (campos antigos + novos)
    endereco VARCHAR(255),  -- Mantido para compatibilidade
    rua VARCHAR(255),
    numero VARCHAR(20),
    complemento VARCHAR(100),
    bairro VARCHAR(100),
    cidade VARCHAR(100),
    estado VARCHAR(2),
    cep VARCHAR(10),
    
    -- Pessoa responsável
    responsavel_nome VARCHAR(255),
    responsavel_telefone VARCHAR(20),
    responsavel_email VARCHAR(255),
    responsavel_cargo VARCHAR(100),
    
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);
```

---

## 🔄 COMPATIBILIDADE

### Dados Existentes
- ✅ Restaurantes existentes continuarão funcionando
- ✅ Novos campos são `nullable=True`
- ✅ Campo `endereco` original mantido

### Migração de Dados (Opcional)
Se quiser migrar dados do campo `endereco` para os novos campos:

```python
# Script de migração (executar após migration)
from app.database import SessionLocal
from app.models import Tenant

db = SessionLocal()
tenants = db.query(Tenant).filter(Tenant.endereco != None).all()

for tenant in tenants:
    if tenant.endereco and not tenant.rua:
        # Lógica simples - pode ser melhorada
        parts = tenant.endereco.split(',')
        if len(parts) >= 2:
            tenant.rua = parts[0].strip()
            tenant.cidade = parts[-1].strip()

db.commit()
db.close()
```

---

## 📊 IMPACTO

- **Performance:** Nenhum impacto negativo
- **Storage:** ~150 bytes adicionais por restaurante
- **Queries:** Índices existentes continuam funcionando
- **API:** Retrocompatível - campos opcionais

---

## ✅ CHECKLIST

- [x] Modelo `Tenant` atualizado
- [x] Schemas atualizados (`RestauranteCreate`, `RestauranteResponse`)
- [x] Schemas principais atualizados (`TenantBase`, `TenantUpdate`)
- [x] Migration criada (`008_add_tenant_address_responsible.py`)
- [ ] Migration executada na VPS
- [ ] Frontend atualizado com novos campos
- [ ] Documentação da API atualizada
- [ ] Testes criados para novos campos
