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
    
    // Mostra/oculta aba de gerenciamento conforme permissão
    if (isAdminRestaurante) {
        document.getElementById('tab-gerenciar').style.display = 'block';
    }
    
    loadProdutos();
}

// ==================== NAVEGAÇÃO POR ABAS ====================
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('tab')) {
        showTab(e.target.dataset.tab);
    }
});

function showTab(tabName) {
    // Remove active de todas as abas
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    // Ativa a aba clicada
    document.querySelector(`[data-tab="${tabName}"]`)?.classList.add('active');
    document.getElementById(`tab-${tabName}`)?.classList.add('active');
    
    // Carrega dados conforme a aba
    if (tabName === 'estoque') loadProdutos();
    if (tabName === 'historico') loadHistorico();
    if (tabName === 'gerenciar') loadGerenciar();
}

// ==================== ABA: ESTOQUE ====================
async function loadProdutos() {
    try {
        const search = document.getElementById('search-produto')?.value || '';
        const categoria = document.getElementById('filter-categoria')?.value || '';
        
        let url = `/api/tenant/${tenantId}/alimentos?`;
        if (search) url += `search=${search}&`;
        if (categoria) url += `categoria=${categoria}`;
        
        const response = await fetch(url, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const produtos = await response.json();
        
        const container = document.getElementById('lista-produtos');
        const empty = document.getElementById('empty-estoque');
        
        if (produtos.length === 0) {
            container.innerHTML = '';
            empty.style.display = 'block';
            return;
        }
        
        empty.style.display = 'none';
        container.innerHTML = produtos.map(p => `
            <div class="product-card">
                <div class="product-info">
                    <h3>${p.nome}</h3>
                    <span class="badge">${p.categoria || 'Sem categoria'}</span>
                </div>
                <div class="product-stock ${p.estoque_atual < p.estoque_minimo ? 'low' : ''}">
                    <strong>${p.estoque_atual} ${p.unidade_medida}</strong>
                    ${p.estoque_atual < p.estoque_minimo ? '<span class="badge" style="background:#f56565;">Estoque baixo!</span>' : ''}
                    ${p.estoque_minimo > 0 ? `<small>Mínimo: ${p.estoque_minimo}</small>` : ''}
                </div>
            </div>
        `).join('');
    } catch (err) {
        showNotification('Erro ao carregar produtos', 'error');
    }
}

document.getElementById('search-produto')?.addEventListener('input', loadProdutos);
document.getElementById('filter-categoria')?.addEventListener('change', loadProdutos);
document.getElementById('btn-refresh')?.addEventListener('click', loadProdutos);

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
        tbody.innerHTML = movimentacoes.map(m => `
            <tr>
                <td>${new Date(m.data_hora).toLocaleString('pt-BR')}</td>
                <td>${m.alimento_nome || 'N/A'}</td>
                <td><span class="badge">${m.tipo}</span></td>
                <td>${m.quantidade} ${m.unidade || ''}</td>
                <td>${m.usuario_nome || 'Sistema'}</td>
                <td>${m.observacao || '-'}</td>
            </tr>
        `).join('');
    } catch (err) {
        showNotification('Erro ao carregar histórico', 'error');
    }
}

document.getElementById('btn-filter-historico')?.addEventListener('click', loadHistorico);

// ==================== ABA: GERENCIAR ====================
async function loadGerenciar() {
    await loadProdutosGerenciar();
    await loadProdutosSelect();
}

async function loadProdutosGerenciar() {
    try {
        const response = await fetch(`/api/tenant/${tenantId}/alimentos`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const produtos = await response.json();
        
        const tbody = document.getElementById('tbody-gerenciar');
        tbody.innerHTML = produtos.map(p => `
            <tr>
                <td>${p.nome}</td>
                <td>${p.categoria || '-'}</td>
                <td>${p.estoque_atual}</td>
                <td>${p.unidade_medida}</td>
                <td>
                    <button class="btn-sm" onclick="editarProduto(${p.id})"><i class="fas fa-edit"></i></button>
                    <button class="btn-sm btn-danger" onclick="deletarProduto(${p.id})"><i class="fas fa-trash"></i></button>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        showNotification('Erro ao carregar produtos', 'error');
    }
}

async function loadProdutosSelect() {
    try {
        const response = await fetch(`/api/tenant/${tenantId}/alimentos`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const produtos = await response.json();
        
        const select = document.getElementById('ajuste-produto');
        select.innerHTML = '<option value="">Selecione um produto...</option>' +
            produtos.map(p => `<option value="${p.id}">${p.nome} (${p.estoque_atual} ${p.unidade_medida})</option>`).join('');
    } catch (err) {
        showNotification('Erro ao carregar produtos', 'error');
    }
}

// CRUD de Produtos
document.getElementById('form-produto')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const id = document.getElementById('produto-id').value;
    const dados = {
        nome: document.getElementById('produto-nome').value,
        categoria: document.getElementById('produto-categoria').value,
        unidade_medida: document.getElementById('produto-unidade').value,
        estoque_minimo: parseFloat(document.getElementById('produto-estoque-min').value) || 0,
        qrcode: document.getElementById('produto-qrcode').value || null,
        descricao: document.getElementById('produto-descricao').value || null
    };
    
    try {
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/tenant/${tenantId}/alimentos/${id}` : `/api/tenant/${tenantId}/alimentos`;
        
        const response = await fetch(url, {
            method,
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(dados)
        });
        
        if (response.ok) {
            showNotification(`Produto ${id ? 'atualizado' : 'cadastrado'} com sucesso!`, 'success');
            document.getElementById('form-produto').reset();
            document.getElementById('produto-id').value = '';
            loadProdutosGerenciar();
            loadProdutosSelect();
            loadProdutos();
        } else {
            showNotification('Erro ao salvar produto', 'error');
        }
    } catch (err) {
        showNotification('Erro ao salvar produto', 'error');
    }
});

async function editarProduto(id) {
    try {
        const response = await fetch(`/api/tenant/${tenantId}/alimentos/${id}`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const produto = await response.json();
        
        document.getElementById('produto-id').value = produto.id;
        document.getElementById('produto-nome').value = produto.nome;
        document.getElementById('produto-categoria').value = produto.categoria || '';
        document.getElementById('produto-unidade').value = produto.unidade_medida;
        document.getElementById('produto-estoque-min').value = produto.estoque_minimo || 0;
        document.getElementById('produto-qrcode').value = produto.qrcode || '';
        document.getElementById('produto-descricao').value = produto.descricao || '';
        
        document.querySelector('#form-produto h3').innerHTML = '<i class="fas fa-edit"></i> Editar Produto';
    } catch (err) {
        showNotification('Erro ao carregar produto', 'error');
    }
}

async function deletarProduto(id) {
    if (!confirm('Deseja realmente excluir este produto?')) return;
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/alimentos/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        if (response.ok) {
            showNotification('Produto excluído com sucesso!', 'success');
            loadProdutosGerenciar();
            loadProdutosSelect();
            loadProdutos();
        } else {
            showNotification('Erro ao excluir produto', 'error');
        }
    } catch (err) {
        showNotification('Erro ao excluir produto', 'error');
    }
}

document.getElementById('btn-cancelar-produto')?.addEventListener('click', () => {
    document.getElementById('form-produto').reset();
    document.getElementById('produto-id').value = '';
    document.querySelector('#form-produto h3').innerHTML = '<i class="fas fa-plus-circle"></i> Cadastrar Produto';
});

// Ajuste de Estoque
document.getElementById('form-ajuste')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const dados = {
        alimento_id: parseInt(document.getElementById('ajuste-produto').value),
        tipo: document.getElementById('ajuste-tipo').value,
        quantidade: parseFloat(document.getElementById('ajuste-quantidade').value),
        observacao: document.getElementById('ajuste-obs').value || null
    };
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/movimentacoes`, {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + token,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(dados)
        });
        
        if (response.ok) {
            showNotification('Movimentação registrada com sucesso!', 'success');
            document.getElementById('form-ajuste').reset();
            loadProdutos();
            loadProdutosGerenciar();
            loadProdutosSelect();
        } else {
            showNotification('Erro ao registrar movimentação', 'error');
        }
    } catch (err) {
        showNotification('Erro ao registrar movimentação', 'error');
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
