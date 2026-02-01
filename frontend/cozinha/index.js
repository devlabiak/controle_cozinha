// ==================== AUTENTICAÇÃO ====================
console.log('Iniciando verificação de autenticação...');
const token = localStorage.getItem('token');
console.log('Token encontrado:', token ? 'Sim' : 'Não');

if (!token) {
    console.log('Sem token, redirecionando para login...');
    window.location.href = '/painelfoods/login.html';
    throw new Error('Redirecionando para login'); // Para a execução
}

const user = JSON.parse(localStorage.getItem('user') || '{}');
console.log('Usuário:', user);

if (user.is_admin) {
    console.log('Usuário é admin, redirecionando...');
    window.location.href = '/painelfoods/dashboard.html';
    throw new Error('Redirecionando para dashboard'); // Para a execução
}

// ==================== VARIÁVEIS GLOBAIS ====================
let tenantId = localStorage.getItem('selectedTenantId');
let tenantName = localStorage.getItem('selectedTenantName');
let isAdminRestaurante = false;

console.log('TenantId armazenado:', tenantId);
console.log('TenantName armazenado:', tenantName);

// ==================== INICIALIZAÇÃO ====================
if (tenantId) {
    console.log('Já tem tenant selecionado, carregando área principal...');
    checkPermissionsAndShowMain();
} else {
    console.log('Sem tenant, mostrando seletor...');
    showSelector();
}

// ==================== SELETOR DE RESTAURANTE ====================
function showSelector() {
    document.getElementById('selector').classList.add('active');
    document.getElementById('main-area').classList.remove('active');
    
    fetch('/api/auth/me', { 
        headers: { 'Authorization': 'Bearer ' + token } 
    })
    .then(r => {
        if (!r.ok) {
            throw new Error(`HTTP ${r.status}: ${r.statusText}`);
        }
        return r.json();
    })
    .then(data => {
        console.log('Dados recebidos:', data);
        const restos = data.restaurantes || [];
        console.log('Restaurantes:', restos);
        
        const div = document.getElementById('rest-options');
        
        if (restos.length === 0) {
            div.innerHTML = '<p style="text-align:center;padding:20px;color:#666;">Nenhum restaurante disponível para este usuário.</p>';
            return;
        }
        
        div.innerHTML = restos.map(r =>
            `<button class="restaurant-btn" onclick="selectRestaurant(${r.id}, '${r.nome.replace(/'/g, "\\'")}')">${r.nome}</button>`
        ).join('');
    })
    .catch(err => {
        console.error('Erro ao carregar restaurantes:', err);
        showNotification('Erro ao carregar restaurantes: ' + err.message, 'error');
    });
}

function selectRestaurant(id, nome) {
    localStorage.setItem('selectedTenantId', id);
    localStorage.setItem('selectedTenantName', nome);
    tenantId = id;
    tenantName = nome;
    checkPermissionsAndShowMain();
}

async function checkPermissionsAndShowMain() {
    try {
        const response = await fetch('/api/auth/me', {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const data = await response.json();
        
        const resto = data.restaurantes.find(r => r.id == tenantId);
        isAdminRestaurante = resto?.role === 'admin';
        
        showMainArea();
    } catch (err) {
        showNotification('Erro ao verificar permissões', 'error');
    }
}

function showMainArea() {
    document.getElementById('selector').classList.remove('active');
    document.getElementById('main-area').classList.add('active');
    document.getElementById('rest-name').textContent = tenantName;
    
    loadEstoque();
}

// ==================== NAVEGAÇÃO POR ABAS ====================
document.addEventListener('click', (e) => {
    if (e.target.closest('.nav-tab')) {
        const tab = e.target.closest('.nav-tab');
        showTab(tab.dataset.tab);
    }
});

function showTab(tabName) {
    // Remove active de todas as abas e seções
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.section').forEach(c => c.classList.remove('active'));
    
    // Ativa a aba clicada
    document.querySelector(`.nav-tab[data-tab="${tabName}"]`)?.classList.add('active');
    document.getElementById(`tab-${tabName}`)?.classList.add('active');
    
    // Carrega dados conforme a aba
    if (tabName === 'estoque') loadEstoque();
    if (tabName === 'historico') loadHistorico();
    if (tabName === 'gerenciar') loadProdutosSelects();
}

// ==================== ABA: ESTOQUE ====================
async function loadEstoque() {
    try {
        const search = document.getElementById('search-estoque')?.value.toLowerCase() || '';
        const categoria = document.getElementById('filter-estoque-categoria')?.value || '';
        
        let url = `/api/tenant/${tenantId}/alimentos?`;
        if (categoria) url += `categoria=${categoria}`;
        
        const response = await fetch(url, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        let produtos = await response.json();
        
        // Filtro de busca local
        if (search) {
            produtos = produtos.filter(p => 
                p.nome.toLowerCase().includes(search) ||
                (p.categoria || '').toLowerCase().includes(search)
            );
        }
        
        const tbody = document.getElementById('tbody-estoque');
        const empty = document.getElementById('empty-estoque');
        
        if (produtos.length === 0) {
            tbody.innerHTML = '';
            empty.style.display = 'block';
            return;
        }
        
        empty.style.display = 'none';
        tbody.innerHTML = produtos.map(p => {
            const estoqueAtual = p.quantidade_estoque || 0;
            const estoqueMinimo = p.quantidade_minima || 0;
            const isLow = estoqueMinimo > 0 && estoqueAtual <= estoqueMinimo;
            
            return `
                <tr>
                    <td><strong>${p.nome}</strong></td>
                    <td>${p.categoria || '-'}</td>
                    <td class="${isLow ? 'stock-low' : 'stock-ok'}">
                        <strong>${estoqueAtual.toFixed(2)}</strong>
                    </td>
                    <td>${p.unidade_medida || 'un'}</td>
                    <td>${estoqueMinimo > 0 ? estoqueMinimo.toFixed(2) : '-'}</td>
                    <td>
                        ${isLow ? '<span class="badge badge-danger">⚠️ Baixo</span>' : '<span class="badge badge-success">✅ OK</span>'}
                    </td>
                </tr>
            `;
        }).join('');
    } catch (err) {
        console.error('Erro em loadEstoque:', err);
        showNotification('Erro ao carregar estoque: ' + err.message, 'error');
    }
}

document.getElementById('search-estoque')?.addEventListener('input', loadEstoque);
document.getElementById('filter-estoque-categoria')?.addEventListener('change', loadEstoque);
document.getElementById('btn-refresh-estoque')?.addEventListener('click', loadEstoque);

// ==================== ABA: HISTÓRICO ====================
async function loadHistorico() {
    try {
        const tipo = document.getElementById('filter-tipo')?.value || '';
        const dataInicio = document.getElementById('filter-data-inicio')?.value || '';
        const dataFim = document.getElementById('filter-data-fim')?.value || '';
        
        let url = `/api/tenant/${tenantId}/movimentacoes?`;
        if (tipo) url += `tipo=${tipo}&`;
        if (dataInicio) url += `data_inicio=${dataInicio}&`;
        if (dataFim) url += `data_fim=${dataFim}`;
        
        const response = await fetch(url, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const movimentacoes = await response.json();
        
        const tbody = document.getElementById('tbody-historico');
        const empty = document.getElementById('empty-historico');
        
        if (movimentacoes.length === 0) {
            tbody.innerHTML = '';
            empty.style.display = 'block';
            return;
        }
        
        empty.style.display = 'none';
        tbody.innerHTML = movimentacoes.map(m => {
            const tipoIcon = m.tipo === 'entrada' ? '➕' : m.tipo === 'saida' ? '➖' : '🔄';
            const tipoColor = m.tipo === 'entrada' ? '#48bb78' : m.tipo === 'saida' ? '#f56565' : '#ed8936';
            
            return `
            <tr>
                <td>${new Date(m.data_hora).toLocaleString('pt-BR')}</td>
                <td><strong>${m.alimento_nome || 'N/A'}</strong></td>
                <td><span class="badge" style="background:${tipoColor};color:white;">${tipoIcon} ${m.tipo.toUpperCase()}</span></td>
                <td style="text-align:center;">
                    <div>${m.quantidade_anterior || 0}</div>
                    <small style="color:#a0aec0;">anterior</small>
                </td>
                <td style="text-align:center;font-weight:bold;color:${tipoColor};">
                    ${m.tipo === 'entrada' ? '+' : m.tipo === 'saida' ? '-' : ''}${m.quantidade}
                </td>
                <td style="text-align:center;">
                    <div><strong>${m.quantidade_nova || 0}</strong></div>
                    <small style="color:#a0aec0;">final</small>
                </td>
                <td>${m.usuario_nome || 'Sistema'}</td>
                <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;">${m.observacao || '-'}</td>
            </tr>
        `}).join('');
    } catch (err) {
        console.error('Erro em loadHistorico:', err);
        showNotification('Erro ao carregar histórico: ' + err.message, 'error');
    }
}

document.getElementById('btn-filter-historico')?.addEventListener('click', loadHistorico);

// ==================== ABA: GERENCIAR ====================
async function loadGerenciar() {
    await loadProdutosSelects();
}

async function loadProdutosSelects() {
    try {
        const response = await fetch(`/api/tenant/${tenantId}/alimentos`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const produtos = await response.json();
        
        // Preenche todos os selects
        const selects = ['ajuste-produto', 'minimo-produto', 'editar-select'];
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                select.innerHTML = '<option value="">Selecione um produto...</option>' +
                    produtos.map(p => `<option value="${p.id}" data-estoque="${p.quantidade_estoque || 0}" data-unidade="${p.unidade_medida}" data-nome="${p.nome}" data-categoria="${p.categoria}" data-minimo="${p.quantidade_minima || 0}">${p.nome} (${(p.quantidade_estoque || 0).toFixed(2)} ${p.unidade_medida})</option>`).join('');
            }
        });
    } catch (err) {
        console.error('Erro ao carregar produtos:', err);
        showNotification('Erro ao carregar produtos', 'error');
    }
}

// 1. CADASTRAR NOVO PRODUTO
document.getElementById('form-produto')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const nome = document.getElementById('produto-nome').value;
    const categoria = document.getElementById('produto-categoria').value;
    const unidade = document.getElementById('produto-unidade').value;
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/alimentos`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({
                nome: nome,
                categoria: categoria,
                unidade_medida: unidade,
                estoque_atual: 0,
                estoque_minimo: 0
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao cadastrar produto');
        }
        
        showNotification('Produto cadastrado com sucesso!', 'success');
        document.getElementById('form-produto').reset();
        loadEstoque();
        loadProdutosSelects();
    } catch (err) {
        showNotification(err.message, 'error');
    }
});

// 2. DEFINIR ESTOQUE MÍNIMO
document.getElementById('form-estoque-minimo')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const produtoId = document.getElementById('minimo-produto').value;
    const quantidade = document.getElementById('minimo-quantidade').value;
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/alimentos/${produtoId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({
                estoque_minimo: parseFloat(quantidade)
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao atualizar estoque mínimo');
        }
        
        showNotification('Estoque mínimo definido com sucesso!', 'success');
        document.getElementById('form-estoque-minimo').reset();
        loadEstoque();
        loadProdutosSelects();
    } catch (err) {
        showNotification(err.message, 'error');
    }
});

// 3. EDITAR PRODUTO
function carregarProdutoEdicao() {
    const select = document.getElementById('editar-select');
    const option = select.options[select.selectedIndex];
    
    if (!option.value) {
        document.getElementById('form-editar-campos').style.display = 'none';
        return;
    }
    
    document.getElementById('editar-id').value = option.value;
    document.getElementById('editar-nome').value = option.dataset.nome;
    document.getElementById('editar-categoria').value = option.dataset.categoria;
    document.getElementById('editar-unidade').value = option.dataset.unidade;
    document.getElementById('form-editar-campos').style.display = 'block';
}

function limparFormEdicao() {
    document.getElementById('editar-select').value = '';
    document.getElementById('form-editar-campos').style.display = 'none';
    document.getElementById('form-editar').reset();
}

document.getElementById('form-editar')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const id = document.getElementById('editar-id').value;
    const nome = document.getElementById('editar-nome').value;
    const categoria = document.getElementById('editar-categoria').value;
    const unidade = document.getElementById('editar-unidade').value;
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/alimentos/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({
                nome: nome,
                categoria: categoria,
                unidade_medida: unidade
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao atualizar produto');
        }
        
        showNotification('Produto atualizado com sucesso!', 'success');
        limparFormEdicao();
        loadEstoque();
        loadProdutosSelects();
    } catch (err) {
        showNotification(err.message, 'error');
    }
});

async function deletarProduto() {
    const id = document.getElementById('editar-id').value;
    
    if (!confirm('Tem certeza que deseja excluir este produto? Esta ação não pode ser desfeita.')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/alimentos/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        if (!response.ok) {
            throw new Error('Erro ao excluir produto');
        }
        
        showNotification('Produto excluído com sucesso!', 'success');
        limparFormEdicao();
        loadEstoque();
        loadProdutosSelects();
    } catch (err) {
        showNotification(err.message, 'error');
    }
}

// 4. AJUSTAR ESTOQUE
document.getElementById('form-ajuste')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const alimentoId = parseInt(document.getElementById('ajuste-produto').value);
    const tipo = document.getElementById('ajuste-tipo').value;
    const quantidade = parseFloat(document.getElementById('ajuste-quantidade').value);
    const observacao = document.getElementById('ajuste-obs').value;
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/movimentacoes`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({
                alimento_id: alimentoId,
                tipo: tipo,
                quantidade: quantidade,
                observacao: observacao || null
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao registrar movimentação');
        }
        
        const tipoNome = tipo === 'entrada' ? 'Entrada' : tipo === 'saida' ? 'Saída' : 'Ajuste';
        showNotification(`${tipoNome} registrado com sucesso!`, 'success');
        document.getElementById('form-ajuste').reset();
        loadEstoque();
        loadProdutosSelects();
    } catch (err) {
        showNotification(err.message, 'error');
    }
});

// ==================== UTILITÁRIOS ====================
function showNotification(message, type = 'success') {
    const notif = document.getElementById('notification');
    notif.textContent = message;
    notif.className = `notification ${type}`;
    notif.style.display = 'block';
    
    setTimeout(() => {
        notif.style.display = 'none';
    }, 3000);
}

// Trocar restaurante
document.getElementById('trocar-rest')?.addEventListener('click', () => {
    localStorage.removeItem('selectedTenantId');
    localStorage.removeItem('selectedTenantName');
    showSelector();
});

// Logout
document.getElementById('logout')?.addEventListener('click', () => {
    localStorage.clear();
    window.location.href = '/painelfoods/login.html';
});
