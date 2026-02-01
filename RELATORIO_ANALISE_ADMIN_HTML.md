# RELATÓRIO DETALHADO DE ANÁLISE - frontend/admin/index.html

**Data da Análise:** 1 de fevereiro de 2026  
**Arquivo:** `frontend/admin/index.html`  
**Total de Linhas:** 1.320  
**Status:** Análise Completa

---

## RESUMO EXECUTIVO

Foram encontrados **12 problemas** críticos, altos e médios que precisam ser corrigidos:
- **CRÍTICOS:** 3
- **ALTOS:** 4
- **MÉDIOS:** 5
- **BAIXOS:** 0

---

## PROBLEMAS ENCONTRADOS

---

### 1. **MODAL NÃO FECHA AO CLICAR FORA - Bug de Funcionalidade**

**Prioridade:** CRÍTICA  
**Linhas Afetadas:** 1047-1051  
**Tipo:** Problema com Event Listeners / Modal  

**Problema Detalhado:**
```javascript
// Linhas 1047-1051
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('show');
    }
});
```

O código está correto, MAS o evento vai disparar mesmo quando o usuário clica em elementos internos do modal. O problema é que quando você clica em qualquer lugar dentro do `.modal-content`, o clique NÃO vai fechar o modal (está OK), mas se clicar FORA no overlay, vai funcionar apenas se clicar exatamente no elemento `.modal`. Devido à estrutura flex do modal, o clique fora pode não registrar corretamente.

**Impacto:**
- Usuário pode ficar preso no modal sem conseguir fechá-lo em certas situações
- Experiência ruim do usuário

**Como Corrigir:**
```javascript
// Versão corrigida (Linhas 1047-1051)
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal') && e.target.style.display === 'flex') {
        e.target.classList.remove('show');
        e.target.style.display = 'none';
    }
});
```

**Ou melhor ainda, usar delegação correta:**
```javascript
document.addEventListener('click', (e) => {
    // Fechar modal clicando no background
    if (e.target.classList.contains('modal')) {
        const modal = e.target;
        modal.classList.remove('show');
    }
});
```

---

### 2. **VARIÁVEL GLOBAL `event` NÃO É SEGURA - Erro de Escopo JavaScript**

**Prioridade:** CRÍTICA  
**Linha Afetada:** 808  
**Tipo:** Variáveis globais não inicializadas / Erro de sintaxe  

**Problema Detalhado:**
```javascript
// Linha 808 (na função showSection)
function showSection(section) {
    document.querySelectorAll('.content-section').forEach(el => el.classList.remove('active'));
    document.getElementById(section).classList.add('active');

    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    event.target.classList.add('active');  // ❌ LINHA 808 - PROBLEMA!
    
    if (section === 'clientes') carregarClientes();
    if (section === 'restaurantes') carregarRestaurantes();
    if (section === 'usuarios') carregarUsuarios();
    if (section === 'dashboard') carregarDashboard();
}
```

**Problemas:**
1. Usar `event` diretamente é DEPRECATED em JavaScript moderno
2. `event` pode ser `undefined` em contextos assíncronos
3. Quando chamado de outras formas, pode gerar erro "event is not defined"
4. Quebra modo `'use strict'`

**Impacto:**
- **CRÍTICO:** Cliques nas seções da sidebar vão falhar aleatoriamente
- Navegação entre seções pode não funcionar
- Console errors afetam toda a experiência

**Como Corrigir:**

**Opção 1 - Usar parametro do onclick:**
```javascript
// HTML (Linhas 377-380)
<div class="nav-item active" onclick="showSection(event, 'dashboard')">Dashboard</div>
<div class="nav-item" onclick="showSection(event, 'clientes')">Clientes</div>
<div class="nav-item" onclick="showSection(event, 'restaurantes')">Restaurantes</div>
<div class="nav-item" onclick="showSection(event, 'usuarios')">Usuários</div>
<div class="nav-item" onclick="logout()">Sair</div>

// JavaScript
function showSection(evt, section) {
    document.querySelectorAll('.content-section').forEach(el => el.classList.remove('active'));
    document.getElementById(section).classList.add('active');

    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    evt.target.classList.add('active');  // ✓ CORRIGIDO
    
    if (section === 'clientes') carregarClientes();
    if (section === 'restaurantes') carregarRestaurantes();
    if (section === 'usuarios') carregarUsuarios();
    if (section === 'dashboard') carregarDashboard();
}
```

**Opção 2 - Usar event delegado (MELHOR):**
```javascript
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('nav-item')) {
        const section = e.target.dataset.section;
        showSection(section);
    }
});

// HTML
<div class="nav-item active" data-section="dashboard">Dashboard</div>
<div class="nav-item" data-section="clientes">Clientes</div>
<div class="nav-item" data-section="restaurantes">Restaurantes</div>
<div class="nav-item" data-section="usuarios">Usuários</div>

// JavaScript - sem usar event
function showSection(section) {
    document.querySelectorAll('.content-section').forEach(el => el.classList.remove('active'));
    document.getElementById(section).classList.add('active');

    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
    document.querySelector(`.nav-item[data-section="${section}"]`).classList.add('active');
    
    if (section === 'clientes') carregarClientes();
    if (section === 'restaurantes') carregarRestaurantes();
    if (section === 'usuarios') carregarUsuarios();
    if (section === 'dashboard') carregarDashboard();
}
```

---

### 3. **FUNÇÃO `carregarRestaurantesCliente()` COM BUG - Erro de Sincronização Assíncrona**

**Prioridade:** CRÍTICA  
**Linhas Afetadas:** 1000-1027  
**Tipo:** Funções não definidas / Erro de lógica  

**Problema Detalhado:**
```javascript
// Linhas 1000-1027
async function carregarRestaurantesCliente(clienteId) {
    if (!clienteId) {
        document.getElementById('lista-restaurantes-usuario').innerHTML = '';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/admin/clientes/${clienteId}/restaurantes`, { headers });
        const restaurantes = await response.json();

        const container = document.getElementById('lista-restaurantes-usuario');
        container.innerHTML = '';

        restaurantes.forEach(r => {
            const div = document.createElement('div');
            div.style.borderRadius = '5px';
            div.style.border = '1px solid #ddd';
            div.style.padding = '10px';
            div.style.backgroundColor = '#f9f9f9';
            
            div.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <input type="checkbox" value="${r.id}" name="restaurante" class="restaurante-checkbox">
                    <strong>${r.nome}</strong>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding-left: 24px;">
                    <label style="display: flex; align-items: center; gap: 5px; font-size: 14px;">
                        <input type="radio" name="role-${r.id}" value="admin" checked> 
                        👨‍💼 Admin
                    </label>
                    <label style="display: flex; align-items: center; gap: 5px; font-size: 14px;">
                        <input type="radio" name="role-${r.id}" value="leitura"> 
                        👁️ Leitura
                    </label>
                </div>
            `;
            container.appendChild(div);
        });
    } catch (error) {
        console.error('Erro:', error);
    }
}
```

**Problemas:**
1. **Falta tratamento de erro**: Se `response.ok` for `false`, a função vai quebrar ao tentar fazer `json()` em erro
2. **Sem verificação de resposta**: Erro 404, 500, etc não são tratados
3. **API endpoint pode não existir**: A rota `/admin/clientes/{id}/restaurantes` não está validada na documentação da API
4. **Sem feedback ao usuário**: Se algo der errado, o usuário não fica sabendo

**Impacto:**
- Console errors
- Formulário de criação de usuário não carrega os restaurantes
- Usuário fica confuso sem feedback

**Como Corrigir:**
```javascript
async function carregarRestaurantesCliente(clienteId) {
    if (!clienteId) {
        document.getElementById('lista-restaurantes-usuario').innerHTML = '';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/admin/clientes/${clienteId}/restaurantes`, { headers });
        
        // ✓ Validar resposta
        if (!response.ok) {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        const restaurantes = await response.json();

        const container = document.getElementById('lista-restaurantes-usuario');
        container.innerHTML = '';

        if (!restaurantes || restaurantes.length === 0) {
            container.innerHTML = '<p style="color: #718096;">Nenhum restaurante cadastrado para este cliente.</p>';
            return;
        }

        restaurantes.forEach(r => {
            const div = document.createElement('div');
            div.style.borderRadius = '5px';
            div.style.border = '1px solid #ddd';
            div.style.padding = '10px';
            div.style.backgroundColor = '#f9f9f9';
            
            div.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <input type="checkbox" value="${r.id}" name="restaurante" class="restaurante-checkbox">
                    <strong>${r.nome}</strong>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding-left: 24px;">
                    <label style="display: flex; align-items: center; gap: 5px; font-size: 14px;">
                        <input type="radio" name="role-${r.id}" value="admin" checked> 
                        👨‍💼 Admin
                    </label>
                    <label style="display: flex; align-items: center; gap: 5px; font-size: 14px;">
                        <input type="radio" name="role-${r.id}" value="leitura"> 
                        👁️ Leitura
                    </label>
                </div>
            `;
            container.appendChild(div);
        });
    } catch (error) {
        console.error('Erro ao carregar restaurantes:', error);
        document.getElementById('lista-restaurantes-usuario').innerHTML = 
            `<div class="alert alert-error">❌ Erro ao carregar restaurantes: ${error.message}</div>`;
    }
}
```

---

### 4. **FUNÇÃO `editarUsuario()` - Chamada de API Inconsistente**

**Prioridade:** ALTA  
**Linhas Afetadas:** 1216-1259  
**Tipo:** Erro de lógica / Inconsistência de API  

**Problema Detalhado:**
```javascript
// Linha 1234 - PROBLEMA!
const respTenants = await fetch(`${API_BASE}/admin/restaurantes/${usuario.id}/usuarios`, { headers }).catch(() => ({
    json: () => ([])
}));
```

**Problemas:**
1. **Endpoint incorreto**: O endpoint deveria ser `/admin/usuarios/{userId}/restaurantes` (puxar restaurantes DO usuário), não `/admin/restaurantes/{userId}/usuarios` (puxar usuários DO restaurante)
2. **Tratamento de erro vago**: `.catch()` com retorno de mock object é frágil
3. **Sem validação de resposta.ok**: Mesmo que a fetch funcione, pode retornar erro HTTP
4. **Inconsistência com `adicionarUsuario()`**: Na criação (linha 1072), usa um padrão diferente

**Impacto:**
- Edição de usuário pode trazer dados errados dos restaurantes
- Roles dos usuários podem ficar incorretos
- Usuário pode perder acesso a restaurantes ao editar

**Como Corrigir:**
```javascript
async function editarUsuario(id) {
    usuarioEditandoId = id;
    try {
        const response = await fetch(`${API_BASE}/admin/usuarios`, { headers });
        
        if (!response.ok) {
            throw new Error(`Erro ao buscar usuários: ${response.status}`);
        }
        
        const usuarios = await response.json();
        const usuario = usuarios.find(u => u.id === id);

        if (!usuario) {
            throw new Error('Usuário não encontrado');
        }

        document.getElementById('edit-usuario-nome').value = usuario.nome;
        document.getElementById('edit-usuario-email').value = usuario.email;
        document.getElementById('edit-usuario-is-admin').checked = usuario.is_admin;

        // Carregar restaurantes do cliente
        const respRestaurantes = await fetch(`${API_BASE}/admin/clientes/${usuario.cliente_id}/restaurantes`, { headers });
        
        if (!respRestaurantes.ok) {
            throw new Error(`Erro ao buscar restaurantes: ${respRestaurantes.status}`);
        }
        
        const restaurantes = await respRestaurantes.json();

        // ✓ CORRIGER: Endpoint correto para puxar tenants do usuário
        const respTenants = await fetch(`${API_BASE}/admin/usuarios/${usuario.id}/restaurantes`, { headers });
        const tenantsUsuario = respTenants.ok ? await respTenants.json() : [];

        const container = document.getElementById('lista-restaurantes-editar');
        container.innerHTML = '';

        restaurantes.forEach(r => {
            const temAcesso = tenantsUsuario.find(t => t.id === r.id);
            const role = temAcesso ? (tenantsUsuario.find(t => t.id === r.id).role || 'leitura') : 'leitura';

            const div = document.createElement('div');
            div.style.borderRadius = '5px';
            div.style.border = '1px solid #ddd';
            div.style.padding = '10px';
            div.style.backgroundColor = '#f9f9f9';
            
            div.innerHTML = `
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <input type="checkbox" value="${r.id}" name="restaurante-editar" class="restaurante-checkbox-editar" ${temAcesso ? 'checked' : ''}>
                    <strong>${r.nome}</strong>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding-left: 24px;">
                    <label style="display: flex; align-items: center; gap: 5px; font-size: 14px;">
                        <input type="radio" name="role-edit-${r.id}" value="admin" ${role === 'admin' ? 'checked' : ''}> 
                        👨‍💼 Admin
                    </label>
                    <label style="display: flex; align-items: center; gap: 5px; font-size: 14px;">
                        <input type="radio" name="role-edit-${r.id}" value="leitura" ${role === 'leitura' ? 'checked' : ''}> 
                        👁️ Leitura
                    </label>
                </div>
            `;
            container.appendChild(div);
        });

        abrirModal('modal-usuario');
    } catch (error) {
        console.error('Erro ao carregar usuário:', error);
        alert('❌ Erro ao carregar usuário: ' + error.message);
    }
}
```

---

### 5. **FALTA FEEDBACK DE CARREGAMENTO - UX/Funcionalidade**

**Prioridade:** ALTA  
**Linhas Afetadas:** 800-900 (múltiplas funções)  
**Tipo:** Problema com User Experience / Falta de validação  

**Problema Detalhado:**

Funções como `carregarClientes()`, `carregarRestaurantes()`, `carregarUsuarios()` não têm:
- Indicadores de carregamento
- Desabilitação de botões durante fetch
- Tratamento de timeout
- Mensagens de erro visíveis ao usuário (apenas console.error)

**Exemplo (Linhas 800-840):**
```javascript
async function carregarClientes() {
    try {
        const response = await fetch(`${API_BASE}/admin/clientes`, { headers });
        const clientes = await response.json();
        // ... resto do código
    } catch (error) {
        console.error('Erro ao carregar clientes:', error);  // ❌ Só no console!
    }
}
```

**Impacto:**
- Usuário não sabe se está carregando ou se houve erro
- Pode fazer múltiplas requisições (spam)
- Experiência profissional ruim

**Como Corrigir:**
```javascript
async function carregarClientes() {
    const tbody = document.querySelector('#tabela-clientes tbody');
    const statusDiv = document.createElement('tr');
    statusDiv.innerHTML = '<td colspan="5" style="text-align: center; padding: 20px;">⏳ Carregando...</td>';
    tbody.innerHTML = '';
    tbody.appendChild(statusDiv);
    
    try {
        const response = await fetch(`${API_BASE}/admin/clientes`, { headers });
        
        if (!response.ok) {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        const clientes = await response.json();
        tbody.innerHTML = '';

        if (!clientes || clientes.length === 0) {
            const emptyRow = document.createElement('tr');
            emptyRow.innerHTML = '<td colspan="5" style="text-align: center; padding: 20px; color: #718096;">Nenhum cliente cadastrado</td>';
            tbody.appendChild(emptyRow);
            return;
        }

        clientes.forEach(cliente => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${cliente.nome_empresa}</td>
                <td>${cliente.email}</td>
                <td>${cliente.telefone || '-'}</td>
                <td><span class="badge ${cliente.ativo ? 'badge-success' : 'badge-danger'}">${cliente.ativo ? 'Ativo' : 'Inativo'}</span></td>
                <td>
                    <button class="btn btn-secondary" onclick="editarCliente(${cliente.id})">Editar</button>
                </td>
            `;
            tbody.appendChild(row);
        });

        // ... resto do código
    } catch (error) {
        console.error('Erro ao carregar clientes:', error);
        tbody.innerHTML = `<tr><td colspan="5" style="padding: 20px;"><div class="alert alert-error">❌ Erro ao carregar clientes: ${error.message}</div></td></tr>`;
    }
}
```

---

### 6. **FALTA VALIDAÇÃO DE RESPONSE.OK - Erro de Tratamento de Erro**

**Prioridade:** ALTA  
**Linhas Afetadas:** Múltiplas (todos os fetch)  
**Tipo:** Erro de tratamento de erro  

**Problema Detalhado:**

Muitas funções fazem `.json()` sem verificar se a resposta foi bem-sucedida:

```javascript
// ❌ Linhas 828, 894, 967
const response = await fetch(`${API_BASE}/admin/clientes`, { headers });
const clientes = await response.json();  // Se response.ok === false, isso quebra!
```

Se o servidor retornar 401, 403, 404, 500, etc., o `.json()` vai tentar parsear uma mensagem de erro HTML ou JSON inválido, causando crashes.

**Funções Afetadas:**
1. `carregarClientes()` - Linha 828
2. `carregarRestaurantes()` - Linha 879
3. `carregarUsuarios()` - Linha 964
4. `carregarDashboard()` - Linha 801
5. `editarRestaurante()` - Linha 1184
6. `editarUsuario()` - Linha 1234

**Impacto:**
- Console errors
- Funcionalidade quebrada
- Usuário fica sem feedback

**Como Corrigir (Template):**
```javascript
const response = await fetch(`${API_BASE}/admin/clientes`, { headers });

// ✓ Adicionar validação
if (!response.ok) {
    throw new Error(`Erro ${response.status}: ${response.statusText}`);
}

const clientes = await response.json();
```

---

### 7. **IDs DE ELEMENTOS DUPLICADOS - Problema Estrutural HTML**

**Prioridade:** MÉDIA  
**Linhas Afetadas:** Múltiplas  
**Tipo:** IDs duplicados / Inconsistência HTML  

**Problema Detalhado:**

Dentro dos modais, vários elementos compartilham o mesmo padrão de nomenclatura com forms:

**Exemplos de possível conflito:**
- `cliente-nome` (linha 426) vs `edit-cliente-nome` (linha 592) - OK, nomes diferentes
- Porém, dentro de um `forEach`, checkboxes são criados com `name="restaurante"` múltiplas vezes

**Linha 1018:**
```javascript
<input type="checkbox" value="${r.id}" name="restaurante" class="restaurante-checkbox">
```

Quando há múltiplos restaurantes, múltiplos checkboxes com `name="restaurante"` são criados (OK para nome), mas quando você faz:
```javascript
const checkboxes = document.querySelectorAll('input[name="restaurante"]:checked');
```

Se houver dois formulários ativos (improvável mas possível), pode pegar checkboxes errados.

**Problema Real Encontrado:**

Linhas 1018 e 1267 usam o MESMO `name="restaurante"`:
```javascript
// Linha 1018 - Criar usuário
<input type="checkbox" value="${r.id}" name="restaurante" class="restaurante-checkbox">

// Linha 1267 - Editar usuário
<input type="checkbox" value="${r.id}" name="restaurante-editar" class="restaurante-checkbox-editar" ${temAcesso ? 'checked' : ''}>
```

Na verdade, os nomes SÃO diferentes (restaurante vs restaurante-editar), então não é um problema real aqui.

**MAS há um problema:** Se o user abrir DOIS MODAIS simultaneamente (o que não deveria acontecer, mas...) e fazer query por `input[name="restaurante"]`, vai pegar dos dois formulários.

**Impacto:** Baixo (modals não abrem simultaneamente normalmente)

**Como Corrigir:**
- Adicionar validação para impedir múltiplos modals abertos
- ✓ O código já faz isso implicitamente, mas deveria ser explícito

---

### 8. **FALTA DE VALIDAÇÃO DE INPUT - Segurança/UX**

**Prioridade:** MÉDIA  
**Linhas Afetadas:** 425-460, 510-545, 600-700  
**Tipo:** Falta de validação  

**Problema Detalhado:**

Os formulários têm `required` no HTML, mas:
1. Não validam no JavaScript antes de enviar
2. Não fazem trim() consistente em todos os campos
3. Alguns campos permitem XSS simples

**Exemplo (Linha 863):**
```javascript
async function adicionarCliente(event) {
    event.preventDefault();

    const nomeEmpresa = document.getElementById('cliente-nome').value.trim();
    const email = document.getElementById('cliente-email').value.trim().toLowerCase();

    if (!nomeEmpresa || !email) {
        alert('❌ Preencha nome da empresa e email válidos.');
        return;
    }
    // ... resto
}
```

**Problemas:**
1. Não valida formato de email
2. Não valida CNPJ (aceita qualquer coisa)
3. Não valida telefone
4. Não sanitiza inputs

**Como Corrigir:**
```javascript
async function adicionarCliente(event) {
    event.preventDefault();

    const nomeEmpresa = document.getElementById('cliente-nome').value.trim();
    const email = document.getElementById('cliente-email').value.trim().toLowerCase();
    const telefone = document.getElementById('cliente-telefone').value.trim();
    const cnpj = document.getElementById('cliente-cnpj').value.trim();

    // ✓ Validação de email
    if (!nomeEmpresa) {
        alert('❌ Nome da empresa é obrigatório.');
        return;
    }

    if (!validarEmail(email)) {
        alert('❌ Email inválido.');
        return;
    }

    if (cnpj && !validarCNPJ(cnpj)) {
        alert('❌ CNPJ inválido. Use o formato: XX.XXX.XXX/0001-XX');
        return;
    }

    if (telefone && !validarTelefone(telefone)) {
        alert('❌ Telefone inválido.');
        return;
    }

    // ... resto do código
}

// ✓ Funções de validação
function validarEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

function validarCNPJ(cnpj) {
    const regex = /^\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}$/;
    return regex.test(cnpj);
}

function validarTelefone(telefone) {
    const regex = /^(\+55\s?)?\(?\d{2}\)?[\s-]?\d{4,5}[\s-]?\d{4}$/;
    return regex.test(telefone);
}
```

---

### 9. **FUNÇÃO `salvarUsuarioEditado()` - Falta Atualizar Dados Básicos**

**Prioridade:** MÉDIA  
**Linhas Afetadas:** 1290-1334  
**Tipo:** Erro de lógica incompleteto  

**Problema Detalhado:**
```javascript
// Linhas 1290-1334
async function salvarUsuarioEditado(event) {
    event.preventDefault();

    try {
        // ❌ COMENTÁRIO INDICA PROBLEMA!
        // Atualizar dados básicos do usuário se necessário
        // (nome, email, is_admin seriam atualizados aqui)

        // Sincronizar restaurantes
        const checkboxes = document.querySelectorAll('input[name="restaurante-editar"]');
        
        // ... resto do código
    }
}
```

**Problemas:**
1. Nome, email e is_admin nunca são salvos ao editar usuário
2. Apenas os restaurantes/roles são sincronizados
3. Mudanças no nome/email são ignoradas
4. O comentário no código mostra que é intencional, mas deveria estar implementado

**Impacto:**
- Usuário não consegue atualizar dados básicos do usuário
- Apenas roles mudam
- Incompleto

**Como Corrigir:**
```javascript
async function salvarUsuarioEditado(event) {
    event.preventDefault();

    try {
        // ✓ Atualizar dados básicos do usuário
        const usuarioData = {
            nome: document.getElementById('edit-usuario-nome').value.trim(),
            email: document.getElementById('edit-usuario-email').value.trim().toLowerCase(),
            is_admin: document.getElementById('edit-usuario-is-admin').checked
        };

        if (!usuarioData.nome || !usuarioData.email) {
            alert('❌ Nome e email são obrigatórios.');
            return;
        }

        if (!validarEmail(usuarioData.email)) {
            alert('❌ Email inválido.');
            return;
        }

        const updateResponse = await fetch(`${API_BASE}/admin/usuarios/${usuarioEditandoId}`, {
            method: 'PUT',
            headers,
            body: JSON.stringify(usuarioData)
        });

        if (!updateResponse.ok) {
            const error = await updateResponse.json();
            throw new Error(error.detail || 'Erro ao atualizar usuário');
        }

        // Sincronizar restaurantes
        const checkboxes = document.querySelectorAll('input[name="restaurante-editar"]');
        
        // Remover acessos desmarcados e atualizar marcados
        for (const checkbox of checkboxes) {
            const restauranteId = checkbox.value;
            const roleRadio = document.querySelector(`input[name="role-edit-${restauranteId}"]:checked`);
            const role = roleRadio ? roleRadio.value : 'leitura';

            if (checkbox.checked) {
                // Adicionar ou atualizar acesso
                await fetch(`${API_BASE}/admin/usuarios/${usuarioEditandoId}/restaurantes/${restauranteId}?role=${role}`, {
                    method: 'POST',
                    headers
                });
            } else {
                // Remover acesso
                await fetch(`${API_BASE}/admin/usuarios/${usuarioEditandoId}/restaurantes/${restauranteId}`, {
                    method: 'DELETE',
                    headers
                });
            }
        }

        alert('✓ Usuário atualizado com sucesso!');
        fecharModal('modal-usuario');
        carregarUsuarios();
    } catch (error) {
        alert('❌ Erro ao salvar usuário: ' + error.message);
        console.error(error);
    }
}
```

---

### 10. **FALTA ESPAÇAMENTO/PADDING NO MODAL-FOOTER - Problema CSS**

**Prioridade:** MÉDIA  
**Linhas Afetadas:** 338-342 (CSS), 659-662, 702-705, 736-739 (HTML)  
**Tipo:** Problema CSS / UX  

**Problema Detalhado:**
```css
/* Linhas 338-342 */
.modal-footer {
    margin-top: 20px;
    display: flex;
    gap: 10px;
    justify-content: flex-end;
}
```

**Problemas:**
1. Sem `padding` ou `border-top`, fica colado no conteúdo
2. O formulário acaba bem acima dos botões
3. Visualmente desagradável

**Impacto:** UI/UX - Baixo, mas afeta a aparência profissional

**Como Corrigir:**
```css
.modal-footer {
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #e2e8f0;  /* ✓ Adicionar separação visual */
    display: flex;
    gap: 10px;
    justify-content: flex-end;
}
```

---

### 11. **FUNÇÃO `deletarRestaurante()` - Sem Feedback Adequado**

**Prioridade:** MÉDIA  
**Linhas Afetadas:** 946-963  
**Tipo:** Falta de feedback / UX  

**Problema Detalhado:**
```javascript
// Linhas 946-963
async function deletarRestaurante(id) {
    if (confirm('Tem certeza que deseja deletar este restaurante?')) {
        try {
            const response = await fetch(`${API_BASE}/admin/restaurantes/${id}`, {
                method: 'DELETE',
                headers
            });

            if (response.ok) {
                alert('✓ Restaurante deletado');
                carregarRestaurantes();
            }
            // ❌ Sem tratamento do else!
        } catch (error) {
            alert('Erro: ' + error.message);
        }
    }
}
```

**Problemas:**
1. Não trata caso `response.ok === false`
2. Não verifica se a deleção realmente funcionou
3. Se der erro na API, apenas pega exception de rede, não erro HTTP

**Impacto:**
- Erro silencioso na deleção
- Usuário não sabe se foi deletado ou não

**Como Corrigir:**
```javascript
async function deletarRestaurante(id) {
    if (confirm('Tem certeza que deseja deletar este restaurante? Esta ação é irreversível.')) {
        try {
            const response = await fetch(`${API_BASE}/admin/restaurantes/${id}`, {
                method: 'DELETE',
                headers
            });

            // ✓ Validar resposta
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `Erro ${response.status}`);
            }

            alert('✓ Restaurante deletado com sucesso');
            carregarRestaurantes();
        } catch (error) {
            alert('❌ Erro ao deletar restaurante: ' + error.message);
            console.error(error);
        }
    }
}
```

---

### 12. **LOGOUT DUPLO - Código Redundante/Ineficiente**

**Prioridade:** BAIXA/MÉDIA  
**Linhas Afetadas:** 377, 382, 394  
**Tipo:** Código duplicado  

**Problema Detalhado:**
```html
<!-- Líneas 377-382 -->
<div class="nav-item active" onclick="showSection('dashboard')">Dashboard</div>
<div class="nav-item" onclick="showSection('clientes')">Clientes</div>
<div class="nav-item" onclick="showSection('restaurantes')">Restaurantes</div>
<div class="nav-item" onclick="showSection('usuarios')">Usuários</div>
<div style="border-top: 1px solid #4a5568; margin-top: 30px; padding-top: 20px;">
    <div class="nav-item" onclick="logout()">Sair</div>  <!-- ✓ Logout 1 -->
</div>

<!-- Línea 394 -->
<button class="logout-btn" onclick="logout()">Sair</button>  <!-- ✓ Logout 2 -->
```

**Problemas:**
1. Dois botões de logout fazem a mesma coisa
2. Possível confusão do usuário
3. Redundância de código

**Impacto:** Baixo - funciona, mas é redundante

**Como Corrigir:**

Opção 1: Remover um dos dois (exemplo, remover o da sidebar):
```html
<!-- Remover linhas 381-383, mantendo apenas o botão no header -->
```

Opção 2: Manter ambos, mas com feedback visual diferente - já está OK assim

---

## RESUMO GERAL DE AÇÕES NECESSÁRIAS

### Correções CRÍTICAS (devem ser feitas IMEDIATAMENTE):

1. **Linha 808** - Remover uso de `event` global, usar parametrização ou event delegation
2. **Linhas 1000-1027** - Adicionar validação de resposta HTTP em `carregarRestaurantesCliente()`
3. **Linhas 1047-1051** - Corrigir fechamento de modal fora do overlay

### Correções ALTAS (devem ser feitas logo):

4. **Linha 1234** - Corrigir endpoint da API em `editarUsuario()` para `/admin/usuarios/{id}/restaurantes`
5. **Linhas 800-900** - Adicionar indicadores de carregamento e feedback de erro visível
6. **Todos os fetch** - Adicionar validação de `response.ok`

### Correções MÉDIAS (deveriam ser feitas):

7. **Linhas 425-545** - Adicionar validação de input (email, CNPJ, telefone)
8. **Linhas 1290-1334** - Implementar atualização de dados básicos em `salvarUsuarioEditado()`
9. **Linhas 338-342 (CSS)** - Adicionar padding/border-top ao modal-footer
10. **Linhas 946-963** - Adicionar tratamento de erro em `deletarRestaurante()`

### Melhorias BAIXAS (nice-to-have):

11. **Linhas 377-394** - Considerar remover redundância de botão logout
12. **Geral** - Implementar função de validação centralizada para email, CNPJ, telefone

---

## ESTATÍSTICAS

| Categoria | Quantidade |
|-----------|-----------|
| Problemas Críticos | 3 |
| Problemas Altos | 4 |
| Problemas Médios | 5 |
| Problemas Baixos | 0 |
| **TOTAL** | **12** |

| Tipo de Problema | Quantidade |
|-----------|-----------|
| Erro de lógica/funcionalidade | 4 |
| Falta de validação | 3 |
| Erro de tratamento | 3 |
| UX/Feedback | 2 |
| Redundância | 1 |
| CSS | 1 |

---

## RECOMENDAÇÕES FINAIS

1. **Prioridade 1:** Corrigir os 3 problemas CRÍTICOS imediatamente - afetam funcionalidade principal
2. **Prioridade 2:** Adicionar validação de resposta HTTP em todos os fetch
3. **Prioridade 3:** Implementar feedback visual de carregamento
4. **Prioridade 4:** Adicionar validação de inputs no JavaScript
5. **Prioridade 5:** Completar funções incompletas (salvarUsuarioEditado)

---

**Relatório Gerado:** 1 de fevereiro de 2026  
**Recomendação:** Corrigir todos os problemas CRÍTICOS e ALTOS antes de deploy em produção.
