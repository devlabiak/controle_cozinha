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

// ==================== PROTEÇÃO DE NAVEGAÇÃO ====================
// Previne que o botão voltar saia da aplicação
window.addEventListener('beforeunload', (e) => {
    // Se a página está sendo realmente fechada/recarregada, permite
    if (performance.navigation.type === 1) return;
});

// Tratamento de erros global - sempre volta para estoque em caso de erro
window.addEventListener('error', (e) => {
    console.error('Erro capturado:', e.error);
    // Se a área principal está ativa e há erro, tenta voltar para estoque
    if (document.getElementById('main-area')?.classList.contains('active')) {
        try {
            showTab('estoque', false);
        } catch (err) {
            console.error('Não foi possível voltar para estoque:', err);
        }
    }
});

// ==================== VARIÁVEIS GLOBAIS ====================
let tenantId = localStorage.getItem('selectedTenantId');
let tenantName = localStorage.getItem('selectedTenantName');
let isAdminRestaurante = false;

console.log('TenantId armazenado:', tenantId);
console.log('TenantName armazenado:', tenantName);

// ==================== INICIALIZAÇÃO ====================
// ==================== DATA DE PRODUÇÃO AUTOMÁTICA ====================
function setDataProducaoHoje() {
    const input = document.getElementById('entrada-data-producao');
    if (input) {
        const hoje = new Date();
        const yyyy = hoje.getFullYear();
        const mm = String(hoje.getMonth() + 1).padStart(2, '0');
        const dd = String(hoje.getDate()).padStart(2, '0');
        input.value = `${yyyy}-${mm}-${dd}`;
    }
}

// Sempre que abrir a aba de entrada, preenche a data
const tabEntrada = document.querySelector('[data-tab="entrada"]');
if (tabEntrada) {
    tabEntrada.addEventListener('click', setDataProducaoHoje);
}
// Também ao carregar a página, se já estiver na aba entrada
if (document.getElementById('entrada-data-producao')) {
    setDataProducaoHoje();
}
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
        
        div.innerHTML = restos.map(r => {
            if (r.ativo) {
                return `<button class="restaurant-btn" onclick="selectRestaurant(${r.id}, '${r.nome.replace(/'/g, "\\'")}', true)">${r.nome}</button>`;
            } else {
                return `<button class="restaurant-btn bloqueado" onclick="selectRestaurant(${r.id}, '${r.nome.replace(/'/g, "\\'")}', false)">
                    ${r.nome}
                    <span class="badge-bloqueado">🔒 Bloqueado</span>
                </button>`;
            }
        }).join('');
    })
    .catch(err => {
        console.error('Erro ao carregar restaurantes:', err);
        showNotification('Erro ao carregar restaurantes: ' + err.message, 'error');
    });
}

function selectRestaurant(id, nome, ativo) {
    // Verifica se o restaurante está bloqueado
    if (!ativo) {
        showNotification('⚠️ Restaurante bloqueado. Entre em contato com o administrador do sistema.', 'error');
        return;
    }
    
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
        
        if (!response.ok) {
            if (response.status === 401) {
                // Token inválido ou expirado
                console.error('Token inválido ou expirado');
                localStorage.clear();
                window.location.href = '/painelfoods/login.html';
                return;
            }
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        const resto = data.restaurantes.find(r => r.id == tenantId);
        isAdminRestaurante = resto?.role === 'admin';
        
        showMainArea();
    } catch (err) {
        console.error('Erro em checkPermissionsAndShowMain:', err);
        showNotification('Erro ao verificar permissões. Faça login novamente.', 'error');
        setTimeout(() => {
            localStorage.clear();
            window.location.href = '/painelfoods/login.html';
        }, 2000);
    }
}

function showMainArea() {
    document.getElementById('selector').classList.remove('active');
    document.getElementById('main-area').classList.add('active');
    document.getElementById('rest-name').textContent = tenantName;
    
    // Detecta aba pela URL hash ou abre estoque por padrão
    const tabFromHash = window.location.hash.replace('#', '') || 'estoque';
    const validTabs = ['estoque', 'entrada', 'utilizar', 'historico', 'gerenciar', 'usuarios'];
    const initialTab = validTabs.includes(tabFromHash) ? tabFromHash : 'estoque';
    
    // Define estado inicial no histórico
    if (!window.location.hash) {
        history.replaceState({ tab: 'estoque', isApp: true }, '', window.location.pathname + '#estoque');
    } else {
        history.replaceState({ tab: initialTab, isApp: true }, '', window.location);
    }
    
    // Aplica permissões de acesso baseadas no role
    aplicarPermissoes();
    
    // Abre a aba inicial
    showTab(initialTab, false);
    iniciarAlertas(); // Inicia verificação automática de estoque baixo
}

// ==================== SISTEMA DE PERMISSÕES ====================
function aplicarPermissoes() {
    console.log('Aplicando permissões. isAdminRestaurante:', isAdminRestaurante);
    
    if (!isAdminRestaurante) {
        // Oculta aba de gerenciamento
        const tabGerenciar = document.querySelector('[data-tab="gerenciar"]');
        if (tabGerenciar) {
            tabGerenciar.style.display = 'none';
        }
        
        // Oculta aba de usuários
        const tabUsuarios = document.querySelector('[data-tab="usuarios"]');
        if (tabUsuarios) {
            tabUsuarios.style.display = 'none';
        }
        
        // Adiciona mensagem informativa no início da aba entrada
        const tabEntrada = document.getElementById('tab-entrada');
        if (tabEntrada && !document.getElementById('aviso-permissao')) {
            const aviso = document.createElement('div');
            aviso.id = 'aviso-permissao';
            aviso.style.cssText = 'background: #fef3c7; border: 2px solid #f59e0b; border-radius: 8px; padding: 15px; margin-bottom: 20px; color: #92400e;';
            aviso.innerHTML = '<i class="fas fa-info-circle"></i> <strong>Modo Leitura:</strong> Você pode visualizar o estoque e utilizar produtos via QR code, mas não pode cadastrar novos produtos ou fazer ajustes manuais.';
            tabEntrada.insertBefore(aviso, tabEntrada.firstChild);
        }
        
        // Exibe badge indicando modo de leitura no header
        const headerInfo = document.querySelector('.header-info');
        if (headerInfo && !document.getElementById('badge-permissao')) {
            const badge = document.createElement('span');
            badge.id = 'badge-permissao';
            badge.className = 'restaurant-badge';
            badge.style.cssText = 'background: #fef3c7; color: #92400e;';
            badge.innerHTML = '<i class="fas fa-eye"></i> Modo Leitura';
            headerInfo.appendChild(badge);
        }
    } else {
        // Remove avisos se usuário é admin
        document.getElementById('aviso-permissao')?.remove();
        document.getElementById('badge-permissao')?.remove();
        
        // Garante que aba gerenciar está visível
        const tabGerenciar = document.querySelector('[data-tab="gerenciar"]');
        if (tabGerenciar) {
            tabGerenciar.style.display = '';
        }
        
        // Garante que aba usuários está visível
        const tabUsuarios = document.querySelector('[data-tab="usuarios"]');
        if (tabUsuarios) {
            tabUsuarios.style.display = '';
        }
    }
}

// ==================== NAVEGAÇÃO POR ABAS ====================
document.addEventListener('click', (e) => {
    if (e.target.closest('.nav-tab')) {
        const tab = e.target.closest('.nav-tab');
        showTab(tab.dataset.tab, true);
    }
});

// Gerencia navegação com botão voltar/avançar
window.addEventListener('popstate', (e) => {
    // Se não há state válido da aplicação, volta para estoque
    if (!e.state || !e.state.isApp) {
        e.preventDefault();
        history.pushState({ tab: 'estoque', isApp: true }, '', window.location.pathname + '#estoque');
        showTab('estoque', false);
        return;
    }
    
    const tabName = e.state.tab || 'estoque';
    showTab(tabName, false);
});

function showTab(tabName, pushState = true) {
    try {
        // Para o scanner se estava rodando e não for a aba utilizar
        if (tabName !== 'utilizar' && typeof html5QrScanner !== 'undefined' && html5QrScanner) {
            pararScanner();
        }
        
        // Remove active de todas as abas e seções
        document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-section').forEach(c => c.classList.remove('active'));
        
        // Ativa a aba clicada
        document.querySelector(`.nav-tab[data-tab="${tabName}"]`)?.classList.add('active');
        document.getElementById(`tab-${tabName}`)?.classList.add('active');
        
        // Atualiza URL sem recarregar a página
        if (pushState) {
            const url = new URL(window.location);
            url.hash = tabName;
            history.pushState({ tab: tabName, isApp: true }, '', url);
        }
        
        // Carrega dados conforme a aba
        if (tabName === 'estoque') loadEstoque();
        if (tabName === 'historico') loadHistorico();
        if (tabName === 'gerenciar') loadProdutosSelects();
        if (tabName === 'usuarios') loadUsuarios();
    } catch (error) {
        console.error('Erro ao trocar aba:', error);
        // Em caso de erro, volta para estoque
        if (tabName !== 'estoque') {
            showTab('estoque', false);
        }
    }
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
            
            // Calcula embalagens se aplicável
            let displayEstoque = `<strong>${estoqueAtual.toFixed(2)}</strong>`;
            if (p.tipo_embalagem && p.unidades_por_embalagem > 0) {
                const pacotesCompletos = Math.floor(estoqueAtual / p.unidades_por_embalagem);
                const avulsos = estoqueAtual % p.unidades_por_embalagem;
                displayEstoque += `<br><small style="color:#718096;">(${pacotesCompletos} ${p.tipo_embalagem}${pacotesCompletos !== 1 ? 's' : ''}${avulsos > 0 ? ` + ${avulsos}` : ''})</small>`;
            }
            
            return `
                <tr>
                    <td><strong>${p.nome}</strong></td>
                    <td>${p.categoria || '-'}</td>
                    <td class="${isLow ? 'stock-low' : 'stock-ok'}">
                        ${displayEstoque}
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
// Ajusta step do input de quantidade baseado na unidade de medida
function ajustarStepQuantidade(selectId, inputId) {
    const select = document.getElementById(selectId);
    const input = document.getElementById(inputId);
    
    if (!select || !input) return;
    
    const option = select.options[select.selectedIndex];
    const unidade = option?.dataset?.unidade || '';
    const isUnidade = unidade.toLowerCase() === 'unidade' || unidade.toLowerCase() === 'un';
    
    if (isUnidade) {
        input.step = '1';
        input.min = '1';
        if (input.value && parseFloat(input.value) < 1) {
            input.value = '1';
        }
    } else {
        input.step = '0.01';
        input.min = '0.01';
    }
}

// Listeners para ajustar step quando produto for selecionado
document.getElementById('entrada-produto')?.addEventListener('change', function() {
    const formato = document.querySelector('input[name="entrada-formato"]:checked')?.value;
    if (formato !== 'embalagens') {
        ajustarStepQuantidade('entrada-produto', 'entrada-quantidade');
    }
});

document.getElementById('ajuste-produto')?.addEventListener('change', function() {
    ajustarStepQuantidade('ajuste-produto', 'ajuste-quantidade');
});

// Preenche todos os selects
        const selects = ['ajuste-produto', 'minimo-produto', 'editar-select', 'entrada-produto', 'excluir-produto'];
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (select) {
                select.innerHTML = '<option value="">Selecione um produto...</option>' +
                    produtos.map(p => {
                        const emb = p.tipo_embalagem ? ` data-embalagem="${p.tipo_embalagem}" data-unidadesemb="${p.unidades_por_embalagem || 0}"` : '';
                        return `<option value="${p.id}" data-estoque="${p.quantidade_estoque || 0}" data-unidade="${p.unidade_medida}" data-nome="${p.nome}" data-categoria="${p.categoria}" data-minimo="${p.quantidade_minima || 0}"${emb}>${p.nome} (${(p.quantidade_estoque || 0).toFixed(2)} ${p.unidade_medida})</option>`;
                    }).join('');
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
    const tipoEmbalagem = document.getElementById('produto-embalagem').value || null;
    const unidadesPorEmb = document.getElementById('produto-unidades-emb').value;
    
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
                quantidade_estoque: 0,
                quantidade_minima: 0,
                tipo_embalagem: tipoEmbalagem,
                unidades_por_embalagem: unidadesPorEmb ? parseInt(unidadesPorEmb) : null
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
                quantidade_minima: parseFloat(quantidade)
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

// 3. ENTRADA DE PRODUTO NO ESTOQUE
// Funções auxiliares para controle de formato
function updateEntradaFormat() {
    const select = document.getElementById('entrada-produto');
    const option = select.options[select.selectedIndex];
    const tipoEmb = option.dataset.embalagem;
    const unidadesPorEmb = parseInt(option.dataset.unidadesemb || 0);
    
    const formatContainer = document.getElementById('entrada-formato-container');
    const infoEmbalagem = document.getElementById('entrada-info-embalagem');
    const embText = document.getElementById('entrada-emb-text');
    const formatoEmbLabel = document.getElementById('entrada-formato-emb-label');
    
    if (tipoEmb && unidadesPorEmb > 0) {
        infoEmbalagem.style.display = 'block';
        embText.textContent = `Embalagem: ${unidadesPorEmb} unidades por ${tipoEmb}`;
        formatContainer.style.display = 'block';
        formatoEmbLabel.innerHTML = `<i class="fas fa-box"></i> ${tipoEmb}s (${unidadesPorEmb} un/${tipoEmb})`;
    } else {
        infoEmbalagem.style.display = 'none';
        formatContainer.style.display = 'none';
        document.querySelector('input[name="entrada-formato"][value="unidades"]').checked = true;
    }
    
    updateEntradaPlaceholder();
}

function updateEntradaPlaceholder() {
    const select = document.getElementById('entrada-produto');
    const option = select.options[select.selectedIndex];
    const tipoEmb = option.dataset.embalagem;
    const unidadesPorEmb = parseInt(option.dataset.unidadesemb || 0);
    const formato = document.querySelector('input[name="entrada-formato"]:checked')?.value;
    const input = document.getElementById('entrada-quantidade');
    const calcInfo = document.getElementById('entrada-calc-info');
    
    // Remove qualquer listener anterior
    const oldListener = input._updateCalcInfoListener;
    if (oldListener) {
        input.removeEventListener('input', oldListener);
        delete input._updateCalcInfoListener;
    }
    
    if (formato === 'embalagens' && tipoEmb) {
        input.placeholder = `Ex: 5`;
        input.step = '1';
        input.min = '1';
        input.value = ''; // Limpa o valor anterior
        
        function updateCalcInfo() {
            const qtd = parseInt(input.value);
            if (qtd && unidadesPorEmb) {
                calcInfo.style.display = 'block';
                calcInfo.textContent = `= ${qtd * unidadesPorEmb} unidades`;
            } else {
                calcInfo.style.display = 'none';
            }
        }
        
        // Armazena referência ao listener para poder remover depois
        input._updateCalcInfoListener = updateCalcInfo;
        input.addEventListener('input', updateCalcInfo);
    } else {
        input.placeholder = 'Ex: 50';
        input.step = '0.01';
        input.min = '0.01';
        input.value = ''; // Limpa o valor anterior
        calcInfo.style.display = 'none'; // Esconde o cálculo
    }
}

document.getElementById('form-entrada')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const alimentoId = parseInt(document.getElementById('entrada-produto').value);
    const inputQtd = document.getElementById('entrada-quantidade').value;
    const observacao = document.getElementById('entrada-obs').value;
    const formato = document.querySelector('input[name="entrada-formato"]:checked')?.value;
    const dataProducao = document.getElementById('entrada-data-producao').value;
    const dataValidade = document.getElementById('entrada-data-validade').value;
    
    // Se for embalagens, multiplica pela quantidade de unidades
    const select = document.getElementById('entrada-produto');
    const option = select.options[select.selectedIndex];
    const unidadesPorEmb = parseInt(option.dataset.unidadesemb || 0);
    
    let quantidade;
    if (formato === 'embalagens' && unidadesPorEmb > 0) {
        quantidade = parseInt(inputQtd) * unidadesPorEmb; // Usa parseInt para embalagens
    } else {
        quantidade = parseFloat(inputQtd); // Usa parseFloat para unidades avulsas
    }
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/movimentacoes`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({
                alimento_id: alimentoId,
                tipo: 'entrada',
                quantidade: quantidade,
                observacao: observacao || null,
                data_producao: dataProducao || null,
                data_validade: dataValidade || null
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao registrar entrada');
        }
        
        const result = await response.json();
        showNotification('Entrada registrada com sucesso!', 'success');
        
        // Se gerou QR code, mostra botão para imprimir etiqueta
        if (result.qr_code_gerado && result.movimentacao_id) {
            // Exibe modal para selecionar quantidade de etiquetas
            window._movimentacaoIdEtiqueta = result.movimentacao_id;
            document.getElementById('qtd-etiquetas').value = 1;
            document.getElementById('modal-etiquetas').style.display = 'block';
        }
        // Funções para modal de etiquetas
        function fecharModalEtiquetas() {
            document.getElementById('modal-etiquetas').style.display = 'none';
            window._movimentacaoIdEtiqueta = null;
        }

        function confirmarImpressaoEtiquetas() {
            const qtd = parseInt(document.getElementById('qtd-etiquetas').value) || 1;
            const movimentacaoId = window._movimentacaoIdEtiqueta;
            fecharModalEtiquetas();
            for (let i = 0; i < qtd; i++) {
                imprimirEtiqueta(movimentacaoId);
            }
        }
        
        document.getElementById('form-entrada').reset();
        loadEstoque();
        loadProdutosSelects();
    } catch (err) {
        showNotification(err.message, 'error');
    }
});

function imprimirEtiqueta(movimentacaoId) {
    showNotification('Gerando etiqueta...', 'success');
    
    fetch(`/api/tenant/${tenantId}/movimentacoes/${movimentacaoId}/etiqueta`, {
        method: 'GET',
        headers: {
            'Authorization': 'Bearer ' + token
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Erro ao gerar etiqueta');
        }
        return response.blob();
    })
    .then(blob => {
        // Cria URL temporária e faz download
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `etiqueta_${movimentacaoId}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        showNotification('Etiqueta baixada com sucesso!', 'success');
    })
    .catch(err => {
        showNotification('Erro ao baixar etiqueta: ' + err.message, 'error');
    });
}

// 4. EDITAR PRODUTO
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

// 5. AJUSTAR ESTOQUE MANUALMENTE
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

// 6. EXCLUIR PRODUTO
async function confirmarExclusaoProduto() {
    const select = document.getElementById('excluir-produto');
    const produtoId = select.value;
    
    if (!produtoId) {
        showNotification('Selecione um produto para excluir', 'error');
        return;
    }
    
    const option = select.options[select.selectedIndex];
    const nomeProduto = option.dataset.nome;
    
    const confirmacao = confirm(
        `⚠️ ATENÇÃO: AÇÃO IRREVERSÍVEL!\n\n` +
        `Você está prestes a excluir permanentemente:\n\n` +
        `Produto: ${nomeProduto}\n\n` +
        `Esta ação irá:\n` +
        `• Remover o produto do sistema\n` +
        `• Apagar todo o histórico de movimentações\n` +
        `• Perder todas as etiquetas geradas\n\n` +
        `Deseja realmente continuar?`
    );
    
    if (!confirmacao) {
        return;
    }
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/alimentos/${produtoId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': 'Bearer ' + token
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erro ao excluir produto');
        }
        
        showNotification(`Produto "${nomeProduto}" excluído com sucesso!`, 'success');
        document.getElementById('excluir-produto').value = '';
        loadEstoque();
        loadProdutosSelects();
    } catch (err) {
        showNotification(err.message, 'error');
    }
}

// ==================== UTILITÁRIOS ====================
function showNotification(message, type = 'success', duration = 3000) {
    const notif = document.getElementById('notification');
    notif.innerHTML = message; // Mudado para innerHTML para suportar HTML
    notif.className = `notification ${type}`;
    notif.style.display = 'block';
    
    if (duration > 0) {
        setTimeout(() => {
            notif.style.display = 'none';
        }, duration);
    }
}

// ==================== ALERTAS AUTOMÁTICOS ====================
async function verificarEstoqueBaixo() {
    if (!tenantId) return;
    
    try {
        console.log('🔍 Verificando estoque baixo...');
        const response = await fetch(`/api/tenant/${tenantId}/alimentos`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        const produtos = await response.json();
        
        const produtosBaixos = produtos.filter(p => 
            p.quantidade_minima > 0 && 
            p.quantidade_estoque <= p.quantidade_minima &&
            p.ativo
        );
        
        console.log(`✅ Encontrados ${produtosBaixos.length} produtos com estoque baixo:`, produtosBaixos);
        
        if (produtosBaixos.length > 0) {
            const lista = produtosBaixos.map(p => 
                `<div style="margin:5px 0;padding:5px;background:rgba(255,255,255,0.1);border-radius:4px;">
                    <strong>${p.nome}</strong>: ${p.quantidade_estoque.toFixed(1)} ${p.unidade_medida} 
                    <small>(mín: ${p.quantidade_minima})</small>
                </div>`
            ).join('');
            
            const mensagem = `
                <div style="text-align:left;">
                    <strong style="font-size:16px;">⚠️ ALERTA DE ESTOQUE BAIXO</strong>
                    <div style="margin-top:10px;">${lista}</div>
                </div>
            `;
            
            console.log('📢 Mostrando alerta de estoque baixo');
            showNotification(mensagem, 'warning', 10000); // 10 segundos
        }
    } catch (err) {
        console.error('❌ Erro ao verificar estoque baixo:', err);
    }
}

async function verificarProdutosVencendo() {
    if (!tenantId) return;
    
    try {
        console.log('🔍 Verificando produtos próximos ao vencimento...');
        const response = await fetch(`/api/tenant/${tenantId}/lotes/vencendo?dias=4`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        if (!response.ok) {
            console.error('❌ Erro ao buscar lotes vencendo:', response.status, response.statusText);
            throw new Error('Erro ao buscar lotes vencendo');
        }
        
        const lotes = await response.json();
        console.log(`✅ Encontrados ${lotes.length} lotes próximos ao vencimento:`, lotes);
        
        if (lotes.length === 0) {
            console.log('✅ Nenhum lote próximo ao vencimento (0-4 dias)');
            return;
        }
        
        const lista = lotes.map(lote => {
            const urgenciaIcon = lote.urgencia === 'critico' ? '🔴' : 
                                 lote.urgencia === 'alto' ? '🟠' : '🟡';
            const diasTexto = lote.dias_restantes === 0 ? 'HOJE' : 
                             lote.dias_restantes === 1 ? 'AMANHÃ' : 
                             `${lote.dias_restantes} dias`;
            
            const dataValidade = new Date(lote.data_validade);
            
            return `<div style="margin:5px 0;padding:8px;background:rgba(255,255,255,0.1);border-radius:4px;border-left:3px solid ${lote.urgencia === 'critico' ? '#ef4444' : lote.urgencia === 'alto' ? '#f59e0b' : '#eab308'}">
                <strong>${lote.alimento_nome}</strong> ${urgenciaIcon} ${diasTexto}
                <br><small>Lote: ${lote.lote_numero} | Qtd: ${lote.quantidade_disponivel} ${lote.unidade_medida} | Validade: ${dataValidade.toLocaleDateString('pt-BR')}</small>
            </div>`;
        }).join('');
        
        const mensagem = `
            <div style="text-align:left;">
                <strong style="font-size:16px;">📅 PRODUTOS PRÓXIMOS DO VENCIMENTO</strong>
                <div style="margin-top:10px;max-height:300px;overflow-y:auto;">${lista}</div>
            </div>
        `;
        
        console.log('📢 Mostrando alerta de validade');
        showNotification(mensagem, 'error', 12000); // 12 segundos
    } catch (err) {
        console.error('❌ Erro ao verificar produtos vencendo:', err);
    }
}

async function verificarTodosAlertas() {
    await verificarEstoqueBaixo();
    // Aguarda 11 segundos antes de mostrar o próximo alerta (tempo do alerta anterior + 1s)
    await new Promise(resolve => setTimeout(resolve, 11000));
    await verificarProdutosVencendo();
}

// Inicia verificação automática a cada 60 minutos (3600000ms)
let alertInterval;
function iniciarAlertas() {
    if (alertInterval) clearInterval(alertInterval);
    
    // Verifica imediatamente ao carregar
    setTimeout(() => verificarTodosAlertas(), 3000); // Aguarda 3s após login
    
    // Depois verifica a cada 60 minutos
    alertInterval = setInterval(() => {
        verificarTodosAlertas();
    }, 3600000); // 60 minutos
}

// Para os alertas quando trocar de restaurante ou fazer logout
function pararAlertas() {
    if (alertInterval) {
        clearInterval(alertInterval);
        alertInterval = null;
    }
}

// Trocar restaurante
document.getElementById('trocar-rest')?.addEventListener('click', () => {
    pararAlertas(); // Para verificações automáticas
    localStorage.removeItem('selectedTenantId');
    localStorage.removeItem('selectedTenantName');
    showSelector();
});

// Logout
document.getElementById('logout')?.addEventListener('click', () => {
    pararAlertas(); // Para verificações automáticas
    localStorage.clear();
    window.location.href = '/painelfoods/login.html';
});

// ==================== SCANNER QR CODE (ABA UTILIZAR PRODUTO) - VERSÃO MOBILE OTIMIZADA ====================
let html5QrScannerUtilizar = null;
let currentQRDataUtilizar = null;
let currentLoteUtilizar = null;

// Função para tocar bipe de sucesso
function playBeep() {
    try {
        // Cria um contexto de áudio
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Primeiro bipe
        const oscillator1 = audioContext.createOscillator();
        const gainNode1 = audioContext.createGain();
        oscillator1.connect(gainNode1);
        gainNode1.connect(audioContext.destination);
        oscillator1.frequency.value = 800;
        oscillator1.type = 'sine';
        gainNode1.gain.setValueAtTime(0.5, audioContext.currentTime);
        gainNode1.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);
        oscillator1.start(audioContext.currentTime);
        oscillator1.stop(audioContext.currentTime + 0.1);
        
        // Segundo bipe (após 150ms)
        const oscillator2 = audioContext.createOscillator();
        const gainNode2 = audioContext.createGain();
        oscillator2.connect(gainNode2);
        gainNode2.connect(audioContext.destination);
        oscillator2.frequency.value = 800;
        oscillator2.type = 'sine';
        gainNode2.gain.setValueAtTime(0.5, audioContext.currentTime + 0.15);
        gainNode2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.25);
        oscillator2.start(audioContext.currentTime + 0.15);
        oscillator2.stop(audioContext.currentTime + 0.25);
    } catch (err) {
        console.error('Erro ao tocar bipe:', err);
    }
}

// Auto-start scanner quando a aba é ativada
document.querySelector('[data-tab="utilizar"]')?.addEventListener('click', () => {
    setTimeout(() => {
        if (!html5QrScannerUtilizar) {
            initScannerUtilizar();
        }
    }, 100);
});

function initScannerUtilizar() {
    try {
        html5QrScannerUtilizar = new Html5Qrcode("qr-reader-utilizar");
        
        const config = {
            fps: 10,
            qrbox: { width: 250, height: 250 },
            aspectRatio: 1.0
        };
        
        html5QrScannerUtilizar.start(
            { facingMode: "environment" },
            config,
            onScanSuccessUtilizar,
            (error) => {} // Silent error
        ).then(() => {
            updateScannerStatusUtilizar('ready', '📷 Aponte a câmera para o QR Code');
        }).catch(err => {
            updateScannerStatusUtilizar('error', '❌ Erro ao acessar câmera');
            console.error(err);
        });
    } catch (err) {
        showNotification('Erro ao iniciar scanner: ' + err.message, 'error');
    }
}

async function onScanSuccessUtilizar(decodedText) {
    if (html5QrScannerUtilizar) {
        html5QrScannerUtilizar.pause();
    }
    
    updateScannerStatusUtilizar('scanning', '🔍 Validando QR Code...');
    currentQRDataUtilizar = decodedText;
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/qrcode/validar?qr_code=${encodeURIComponent(decodedText)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({ qr_code: decodedText })
        });
        
        const data = await response.json();
        
        if (response.ok && data.valido) {
            playBeep(); // Toca bipe de sucesso
            showNotification('✅ QR Code lido com sucesso!', 'success');
            currentLoteUtilizar = data;
            displayProductInfoUtilizar(data);
            updateScannerStatusUtilizar('ready', '✅ QR Code válido!');
        } else {
            showNotification(data.mensagem || 'QR Code inválido', 'error');
            updateScannerStatusUtilizar('ready', '📷 Aponte a câmera para o QR Code');
            if (html5QrScannerUtilizar) {
                html5QrScannerUtilizar.resume();
            }
        }
    } catch (err) {
        showNotification('Erro ao validar QR Code: ' + err.message, 'error');
        updateScannerStatusUtilizar('ready', '📷 Aponte a câmera para o QR Code');
        if (html5QrScannerUtilizar) {
            html5QrScannerUtilizar.resume();
        }
    }
}

function updateScannerStatusUtilizar(type, message) {
    const status = document.getElementById('scanner-status-utilizar');
    if (status) {
        status.className = `scanner-status ${type}`;
        status.textContent = message;
    }
}

function displayProductInfoUtilizar(data) {
    document.getElementById('product-name-utilizar').textContent = data.alimento_nome;
    document.getElementById('lote-numero-utilizar').textContent = data.movimentacao_id || '-';
    
    if (data.data_producao) {
        const dateOnly = data.data_producao.split('T')[0];
        const [year, month, day] = dateOnly.split('-');
        const dataProducao = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
        document.getElementById('data-fabricacao-utilizar').textContent = dataProducao.toLocaleDateString('pt-BR');
    } else {
        document.getElementById('data-fabricacao-utilizar').textContent = '-';
    }
    
    if (data.data_validade) {
        const dateOnly = data.data_validade.split('T')[0];
        const [year, month, day] = dateOnly.split('-');
        const dataValidade = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
        document.getElementById('data-validade-utilizar').textContent = dataValidade.toLocaleDateString('pt-BR');
    } else {
        document.getElementById('data-validade-utilizar').textContent = '-';
    }
    
    document.getElementById('quantidade-disponivel-utilizar').textContent = `${data.quantidade} ${data.unidade_medida}`;
    
    // Se foi usado parcialmente, mostra informação adicional
    if (data.quantidade_usada && data.quantidade_usada > 0) {
        const infoExtra = document.createElement('div');
        infoExtra.style.fontSize = '12px';
        infoExtra.style.color = '#666';
        infoExtra.style.marginTop = '5px';
        infoExtra.textContent = `Original: ${data.quantidade_original} ${data.unidade_medida} • Usado: ${data.quantidade_usada}`;
        document.getElementById('quantidade-disponivel-utilizar').appendChild(infoExtra);
    }
    
    const badge = document.getElementById('status-badge-utilizar');
    const daysToExpire = getDaysToExpireUtilizar(data.data_validade);
    
    if (daysToExpire < 0) {
        badge.className = 'badge expired';
        badge.textContent = '⚠️ Vencido';
    } else if (daysToExpire <= 3) {
        badge.className = 'badge expiring';
        badge.textContent = '⏰ Vencendo';
    } else {
        badge.className = 'badge valid';
        badge.textContent = '✓ Válido';
    }
    
    const quantityInput = document.getElementById('quantity-input-utilizar');
    const isUnidade = data.unidade_medida && (data.unidade_medida.toLowerCase() === 'unidade' || data.unidade_medida.toLowerCase() === 'un');
    
    if (isUnidade) {
        quantityInput.step = '1';
        quantityInput.value = 1;
    } else {
        quantityInput.step = '0.1';
        quantityInput.value = 1;
    }
    quantityInput.max = data.quantidade;
    
    // Armazena a unidade para uso nas funções de incremento/decremento
    quantityInput.dataset.isUnidade = isUnidade;
    
    const productCard = document.getElementById('product-card-utilizar');
    productCard.classList.add('show');
    
    // Aguarda um momento para o card aparecer, então rola suavemente até ele
    setTimeout(() => {
        productCard.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'start'
        });
    }, 100);
}

async function confirmUsageUtilizar() {
    const quantidade = parseFloat(document.getElementById('quantity-input-utilizar').value);
    
    if (!quantidade || quantidade <= 0) {
        showNotification('Informe uma quantidade válida', 'error');
        return;
    }
    
    if (quantidade > currentLoteUtilizar.quantidade) {
        showNotification('Quantidade indisponível', 'error');
        return;
    }
    
    console.log('🔵 Iniciando confirmação de uso...');
    console.log('QR Code:', currentQRDataUtilizar);
    console.log('Quantidade:', quantidade);
    console.log('Tenant ID:', tenantId);
    
    try {
        const url = `/api/tenant/${tenantId}/qrcode/usar?qr_code=${encodeURIComponent(currentQRDataUtilizar)}&quantidade_usada=${quantidade}`;
        console.log('🔵 URL:', url);
        
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            }
        });
        
        console.log('🔵 Response status:', response.status);
        console.log('🔵 Response ok:', response.ok);
        
        const responseText = await response.text();
        console.log('🔵 Response text:', responseText);
        
        if (!response.ok) {
            let errorData;
            try {
                errorData = JSON.parse(responseText);
            } catch {
                errorData = { detail: 'Erro desconhecido' };
            }
            console.error('❌ Erro na resposta:', errorData);
            showNotification(errorData.detail || errorData.mensagem || 'Erro ao dar baixa', 'error');
            return;
        }
        
        const data = JSON.parse(responseText);
        console.log('🔵 Dados recebidos:', data);
        
        if (data.sucesso) {
            const unidadeMedida = currentLoteUtilizar?.unidade_medida || '';
            showNotification(`✓ Baixa realizada com sucesso!\nProduto: ${data.produto}\nQuantidade: ${data.quantidade_baixa} ${unidadeMedida}`, 'success');
            cancelScanUtilizar();
            await loadEstoque();
        } else {
            showNotification(data.mensagem || 'Erro ao processar', 'error');
        }
    } catch (error) {
        console.error('❌ Erro ao confirmar uso:', error);
        showNotification('Erro ao conectar ao servidor: ' + error.message, 'error');
    }
}

function cancelScanUtilizar() {
    document.getElementById('product-card-utilizar').classList.remove('show');
    currentQRDataUtilizar = null;
    currentLoteUtilizar = null;
    
    if (html5QrScannerUtilizar) {
        html5QrScannerUtilizar.resume();
    }
    updateScannerStatusUtilizar('ready', '📷 Aponte a câmera para o QR Code');
}

// Torna as funções globais acessíveis no HTML
window.incrementQuantityUtilizar = function() {
    const input = document.getElementById('quantity-input-utilizar');
    const isUnidade = input.dataset.isUnidade === 'true';
    const incremento = isUnidade ? 1 : 0.5;
    const newValue = parseFloat(input.value) + incremento;
    
    if (newValue <= parseFloat(input.max)) {
        input.value = isUnidade ? Math.round(newValue) : newValue.toFixed(1);
    }
}

window.decrementQuantityUtilizar = function() {
    const input = document.getElementById('quantity-input-utilizar');
    const isUnidade = input.dataset.isUnidade === 'true';
    const decremento = isUnidade ? 1 : 0.5;
    const minimo = isUnidade ? 1 : 0.1;
    const newValue = parseFloat(input.value) - decremento;
    
    if (newValue >= minimo) {
        input.value = isUnidade ? Math.round(newValue) : newValue.toFixed(1);
    }
}

window.cancelScanUtilizar = cancelScanUtilizar;
window.confirmUsageUtilizar = confirmUsageUtilizar;

function getDaysToExpireUtilizar(dateString) {
    if (!dateString) return 0;
    
    const dateOnly = dateString.split('T')[0];
    const [year, month, day] = dateOnly.split('-');
    
    const expireDate = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const diffTime = expireDate - today;
    return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
}

// ==================== ABA: USUÁRIOS ====================
async function loadUsuarios() {
    if (!isAdminRestaurante) {
        // Se não é admin, não mostra a aba
        return;
    }
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/usuarios`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const usuarios = await response.json();
        
        const tbody = document.getElementById('tbody-usuarios');
        const empty = document.getElementById('empty-usuarios');
        
        if (usuarios.length === 0) {
            tbody.innerHTML = '';
            empty.style.display = 'block';
            return;
        }
        
        empty.style.display = 'none';
        tbody.innerHTML = usuarios.map(u => `
            <tr>
                <td>${u.nome}</td>
                <td>${u.email}</td>
                <td>
                    ${u.is_admin_restaurante ? 
                        '<span style="color:#10b981;font-weight:600;"><i class="fas fa-crown"></i> Administrador</span>' : 
                        '<span style="color:#6366f1;"><i class="fas fa-eye"></i> Leitura</span>'}
                </td>
                <td>
                    ${u.ativo ? 
                        '<span style="color:#10b981;">● Ativo</span>' : 
                        '<span style="color:#ef4444;">● Inativo</span>'}
                </td>
                <td>
                    <button class="btn-sm btn-primary" onclick="editarUsuario(${u.id})">
                        <i class="fas fa-edit"></i> Editar
                    </button>
                    <button class="btn-sm btn-danger" onclick="removerUsuario(${u.id}, '${u.nome}')">
                        <i class="fas fa-user-minus"></i> Remover
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        showNotification('Erro ao carregar usuários: ' + err.message, 'error');
    }
}

// Formulário de novo usuário
document.getElementById('form-usuario')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const dados = {
        nome: document.getElementById('usuario-nome').value,
        email: document.getElementById('usuario-email').value,
        senha: document.getElementById('usuario-senha').value,
        is_admin_restaurante: document.getElementById('usuario-permissao').value === 'true'
    };
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/usuarios`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify(dados)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Usuário adicionado com sucesso!', 'success');
            document.getElementById('form-usuario').reset();
            loadUsuarios();
        } else {
            showNotification(data.detail || 'Erro ao adicionar usuário', 'error');
        }
    } catch (err) {
        showNotification('Erro ao conectar: ' + err.message, 'error');
    }
});

async function editarUsuario(usuarioId) {
    try {
        const response = await fetch(`/api/tenant/${tenantId}/usuarios`, {
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        const usuarios = await response.json();
        const usuario = usuarios.find(u => u.id === usuarioId);
        
        if (!usuario) {
            showNotification('Usuário não encontrado', 'error');
            return;
        }
        
        document.getElementById('edit-usuario-id').value = usuario.id;
        document.getElementById('edit-usuario-nome').value = usuario.nome;
        document.getElementById('edit-usuario-email').value = usuario.email;
        document.getElementById('edit-usuario-senha').value = '';
        document.getElementById('edit-usuario-permissao').value = usuario.is_admin_restaurante ? 'true' : 'false';
        
        document.getElementById('modal-usuario').style.display = 'flex';
    } catch (err) {
        showNotification('Erro ao carregar dados do usuário: ' + err.message, 'error');
    }
}

async function submitEditarUsuario(e) {
    e.preventDefault();
    
    const usuarioId = document.getElementById('edit-usuario-id').value;
    const dados = {
        nome: document.getElementById('edit-usuario-nome').value,
        email: document.getElementById('edit-usuario-email').value,
        is_admin_restaurante: document.getElementById('edit-usuario-permissao').value === 'true'
    };
    
    const senha = document.getElementById('edit-usuario-senha').value;
    if (senha) {
        dados.senha = senha;
    }
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/usuarios/${usuarioId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify(dados)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showNotification('Usuário atualizado com sucesso!', 'success');
            closeModalUsuario();
            loadUsuarios();
        } else {
            showNotification(data.detail || 'Erro ao atualizar usuário', 'error');
        }
    } catch (err) {
        showNotification('Erro ao conectar: ' + err.message, 'error');
    }
}

async function removerUsuario(usuarioId, nome) {
    if (!confirm(`Tem certeza que deseja remover o acesso de "${nome}" a este restaurante?\n\nEsta ação não pode ser desfeita.`)) {
        return;
    }
    
    try {
        const response = await fetch(`/api/tenant/${tenantId}/usuarios/${usuarioId}`, {
            method: 'DELETE',
            headers: { 'Authorization': 'Bearer ' + token }
        });
        
        if (response.ok) {
            showNotification('Usuário removido com sucesso!', 'success');
            loadUsuarios();
        } else {
            const data = await response.json();
            showNotification(data.detail || 'Erro ao remover usuário', 'error');
        }
    } catch (err) {
        showNotification('Erro ao conectar: ' + err.message, 'error');
    }
}

function closeModalUsuario() {
    document.getElementById('modal-usuario').style.display = 'none';
    document.getElementById('form-editar-usuario').reset();
}

window.editarUsuario = editarUsuario;
window.submitEditarUsuario = submitEditarUsuario;
window.removerUsuario = removerUsuario;
window.closeModalUsuario = closeModalUsuario;
window.updateEntradaFormat = updateEntradaFormat;
window.updateEntradaPlaceholder = updateEntradaPlaceholder;
