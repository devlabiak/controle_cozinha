// Dashboard Admin - v2026.02.01.03 (CNPJ + Email Opcional + Editar Usuários)
const API = `${window.location.protocol}//${window.location.hostname.replace('admin.', '')}/api`;
const TOKEN = localStorage.getItem('token');

console.log('Dashboard Init:', { API, TOKEN: TOKEN ? '✓' : '✗ (nulo)', version: 'v2026.02.01.03' });

if (!TOKEN) {
    alert('Sessão expirada! Faça login novamente.');
    window.location.href = '/admin/login.html';
}

// ===== NOTIFICAÇÃO =====
function notify(msg, type = 'success') {
    const div = document.createElement('div');
    div.className = `notification ${type}`;
    div.innerHTML = `<i class="fas fa-${type === 'success' ? 'check' : 'exclamation'}-circle"></i> ${msg}`;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 3000);
}

function api(url, options = {}) {
    return fetch(`${API}${url}`, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${TOKEN}`,
            ...options.headers
        }
    }).then(async r => {
        const text = await r.text();
        const data = text ? JSON.parse(text) : null;
        
        if (!r.ok) {
            const msg = data?.detail || `HTTP ${r.status}`;
            console.error('API Error:', msg, data);
            throw new Error(msg);
        }
        return data;
    }).catch(e => {
        console.error('Request Error:', e);
        throw e;
    });
}

// ===== CLIENTES =====
async function loadClientes() {
    try {
        const clientes = await api('/admin/clientes');
        const html = clientes.map(c => `
            <tr style="${!c.ativo ? 'background: #fee; opacity: 0.7;' : ''}">
                <td>${c.nome_empresa}</td>
                <td>${c.cnpj || '-'}</td>
                <td>${c.email || '-'}</td>
                <td>${c.telefone || '-'}</td>
                <td>
                    <span style="padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; ${c.ativo ? 'background: #c6f6d5; color: #22543d;' : 'background: #fed7d7; color: #742a2a;'}">
                        ${c.ativo ? '✓ Ativa' : '✖ Bloqueada'}
                    </span>
                </td>
                <td>
                    <button class="btn-small" onclick="editCliente(${c.id})"><i class="fas fa-edit"></i> Editar</button>
                    <button class="btn-small ${c.ativo ? 'danger' : 'success'}" onclick="toggleStatusCliente(${c.id}, ${c.ativo})">
                        <i class="fas fa-${c.ativo ? 'ban' : 'check'}"></i> ${c.ativo ? 'Bloquear' : 'Desbloquear'}
                    </button>
                    <button class="btn-small danger" onclick="delCliente(${c.id})"><i class="fas fa-trash"></i> Deletar</button>
                </td>
            </tr>
        `).join('');
        document.getElementById('clientes-list').innerHTML = `<table><thead><tr><th>Nome</th><th>CNPJ</th><th>Email</th><th>Telefone</th><th>Status</th><th>Ações</th></tr></thead><tbody>${html}</tbody></table>`;
    } catch (e) {
        document.getElementById('clientes-list').innerHTML = `<p style="color:red">Erro: ${e.message}</p>`;
    }
}

async function addCliente(e) {
    e.preventDefault();
    try {
        await api('/admin/clientes', {
            method: 'POST',
            body: JSON.stringify({
                nome_empresa: document.getElementById('cli-nome').value,
                cnpj: document.getElementById('cli-cnpj').value || null,
                email: document.getElementById('cli-email').value || null,
                telefone: document.getElementById('cli-tel').value || null
            })
        });
        notify('Cliente criado!');
        e.target.reset();
        loadClientes();
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function editCliente(id) {
    try {
        const c = await api(`/admin/clientes/${id}`);
        
        // Preencher modal
        document.getElementById('edit-cli-id').value = c.id;
        document.getElementById('edit-cli-nome').value = c.nome_empresa;
        document.getElementById('edit-cli-cnpj').value = c.cnpj || '';
        document.getElementById('edit-cli-email').value = c.email || '';
        document.getElementById('edit-cli-tel').value = c.telefone || '';
        
        // Abrir modal
        document.getElementById('modal-edit-cliente').classList.add('active');
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function salvarClienteEdit(e) {
    e.preventDefault();
    const id = document.getElementById('edit-cli-id').value;
    
    try {
        await api(`/admin/clientes/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                nome_empresa: document.getElementById('edit-cli-nome').value,
                cnpj: document.getElementById('edit-cli-cnpj').value || null,
                email: document.getElementById('edit-cli-email').value || null,
                telefone: document.getElementById('edit-cli-tel').value || null
            })
        });
        
        notify('Empresa atualizada com sucesso!');
        fecharModal('modal-edit-cliente');
        loadClientes();
    } catch (e) {
        notify(e.message, 'error');
    }
}

function fecharModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

async function delCliente(id) {
    if (!confirm('Deletar este cliente?')) return;
    try {
        await api(`/admin/clientes/${id}`, { method: 'DELETE' });
        notify('Deletado!');
        loadClientes();
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function toggleStatusCliente(id, ativoAtual) {
    const acao = ativoAtual ? 'bloquear' : 'desbloquear';
    const confirmMsg = ativoAtual 
        ? '⚠️ Bloquear esta empresa?\n\nTodos os usuários desta empresa perderão acesso ao sistema.'
        : '✅ Desbloquear esta empresa?\n\nOs usuários poderão acessar o sistema novamente.';
    
    if (!confirm(confirmMsg)) return;
    
    try {
        const result = await api(`/admin/clientes/${id}/toggle-status`, { method: 'PATCH' });
        notify(result.message, 'success');
        loadClientes();
    } catch (e) {
        notify(e.message, 'error');
    }
}

// ===== RESTAURANTES =====
async function loadRestaurantes() {
    try {
        const rests = await api('/admin/restaurantes');
        const html = rests.map(r => `
            <tr style="${!r.ativo ? 'background: #fee; opacity: 0.7;' : ''}">
                <td>${r.nome}</td>
                <td><code>${r.slug}</code></td>
                <td>${r.cnpj || '-'}</td>
                <td>${r.email || '-'}</td>
                <td>
                    <span style="padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: bold; ${r.ativo ? 'background: #c6f6d5; color: #22543d;' : 'background: #fed7d7; color: #742a2a;'}">
                        ${r.ativo ? '✓ Ativo' : '✖ Bloqueado'}
                    </span>
                </td>
                <td>
                    <div style="display: flex; gap: 5px; flex-wrap: wrap;">
                        <button class="btn-small" onclick="editRest(${r.id})" title="Editar restaurante">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn-small ${r.ativo ? 'danger' : 'success'}" onclick="toggleStatusRest(${r.id}, ${r.ativo})" title="${r.ativo ? 'Bloquear restaurante' : 'Desbloquear restaurante'}">
                            <i class="fas fa-${r.ativo ? 'ban' : 'check'}"></i>
                        </button>
                        <button class="btn-small danger" onclick="delRest(${r.id})" title="Deletar restaurante">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');
        document.getElementById('rests-list').innerHTML = `<table><thead><tr><th>Nome</th><th>Slug</th><th>CNPJ</th><th>Email</th><th>Status</th><th>Ações</th></tr></thead><tbody>${html}</tbody></table>`;
    } catch (e) {
        document.getElementById('rests-list').innerHTML = `<p style="color:red">Erro: ${e.message}</p>`;
    }
}

async function loadClientesDropdown() {
    try {
        const clientes = await api('/admin/clientes');
        const html = clientes.map(c => `<option value="${c.id}">${c.nome_empresa}</option>`).join('');
        
        // Preencher select de restaurante
        const restSelect = document.getElementById('rest-cliente');
        if (restSelect) {
            restSelect.innerHTML = `<option value="">Selecione</option>${html}`;
        }
        
        // Preencher select de usuário
        const userSelect = document.getElementById('user-cliente');
        if (userSelect) {
            userSelect.innerHTML = `<option value="">Selecione</option>${html}`;
        }
        
        // Preencher select de filtro de usuários
        const filterSelect = document.getElementById('filter-user-cliente');
        if (filterSelect) {
            filterSelect.innerHTML = `<option value="">Todas as Empresas</option>${html}`;
        }
    } catch (e) {}
}

async function addRest(e) {
    e.preventDefault();
    try {
        await api('/admin/restaurantes', {
            method: 'POST',
            body: JSON.stringify({
                cliente_id: parseInt(document.getElementById('rest-cliente').value),
                nome: document.getElementById('rest-nome').value,
                slug: document.getElementById('rest-slug').value,
                cnpj: document.getElementById('rest-cnpj').value || null,
                email: document.getElementById('rest-email').value || null,
                telefone: document.getElementById('rest-tel').value || null
            })
        });
        notify('Restaurante criado!');
        e.target.reset();
        loadRestaurantes();
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function editRest(id) {
    try {
        const r = await api(`/admin/restaurantes/${id}`);
        
        // Preencher modal
        document.getElementById('edit-rest-id').value = r.id;
        document.getElementById('edit-rest-cliente-id').value = r.cliente_id;
        document.getElementById('edit-rest-nome').value = r.nome;
        document.getElementById('edit-rest-slug').value = r.slug;
        document.getElementById('edit-rest-cnpj').value = r.cnpj || '';
        document.getElementById('edit-rest-email').value = r.email || '';
        document.getElementById('edit-rest-tel').value = r.telefone || '';
        
        // Abrir modal
        document.getElementById('modal-edit-rest').classList.add('active');
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function salvarRestEdit(e) {
    e.preventDefault();
    const id = document.getElementById('edit-rest-id').value;
    
    try {
        await api(`/admin/restaurantes/${id}`, {
            method: 'PUT',
            body: JSON.stringify({
                cliente_id: parseInt(document.getElementById('edit-rest-cliente-id').value),
                nome: document.getElementById('edit-rest-nome').value,
                slug: document.getElementById('edit-rest-slug').value,
                cnpj: document.getElementById('edit-rest-cnpj').value || null,
                email: document.getElementById('edit-rest-email').value || null,
                telefone: document.getElementById('edit-rest-tel').value || null
            })
        });
        
        notify('Restaurante atualizado com sucesso!');
        fecharModal('modal-edit-rest');
        loadRestaurantes();
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function delRest(id) {
    if (!confirm('Deletar este restaurante?')) return;
    try {
        await api(`/admin/restaurantes/${id}`, { method: 'DELETE' });
        notify('Deletado!');
        loadRestaurantes();
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function toggleStatusRest(id, ativoAtual) {
    const acao = ativoAtual ? 'bloquear' : 'desbloquear';
    const confirmMsg = ativoAtual 
        ? '⚠️ Bloquear este restaurante?\n\nOs usuários deste restaurante perderão acesso.'
        : '✅ Desbloquear este restaurante?\n\nOs usuários poderão acessar novamente.';
    
    if (!confirm(confirmMsg)) return;
    
    try {
        const result = await api(`/admin/restaurantes/${id}/toggle-status`, { method: 'PATCH' });
        notify(result.message, 'success');
        loadRestaurantes();
    } catch (e) {
        notify(e.message, 'error');
    }
}

// ===== USUÁRIOS =====
function toggleEmpresaField() {
    const checkbox = document.getElementById('user-admin');
    const empresaGroup = document.getElementById('user-empresa-group');
    const restaurantesGroup = document.getElementById('user-restaurantes-group');
    const empresaSelect = document.getElementById('user-cliente');
    
    if (!checkbox || !empresaGroup || !restaurantesGroup || !empresaSelect) {
        console.error('Elementos não encontrados!', {checkbox, empresaGroup, restaurantesGroup, empresaSelect});
        return;
    }
    
    const isAdmin = checkbox.checked;
    console.log('toggleEmpresaField chamado, isAdmin:', isAdmin);
    console.log('restaurantesGroup:', restaurantesGroup);
    
    if (isAdmin) {
        empresaGroup.style.display = 'none';
        empresaSelect.removeAttribute('required');
        restaurantesGroup.style.display = 'none';
    } else {
        empresaGroup.style.display = 'block';
        empresaSelect.setAttribute('required', 'required');
        restaurantesGroup.style.display = 'block';
        console.log('Mostrando campo restaurantes, display:', restaurantesGroup.style.display);
        // Carregar restaurantes da empresa selecionada
        if (empresaSelect.value) {
            carregarRestaurantesUsuario();
        }
    }
}

// Carregar restaurantes ao selecionar empresa
document.getElementById('user-cliente')?.addEventListener('change', carregarRestaurantesUsuario);

async function carregarRestaurantesUsuario() {
    const clienteId = document.getElementById('user-cliente').value;
    const container = document.getElementById('user-restaurantes-list');
    
    if (!clienteId) {
        container.innerHTML = '<p style="color: #999; font-size: 13px;">Selecione uma empresa primeiro</p>';
        return;
    }
    
    try {
        const restaurantes = await api(`/admin/clientes/${clienteId}/restaurantes`);
        
        if (restaurantes.length === 0) {
            container.innerHTML = '<p style="color: #999; font-size: 13px;">Esta empresa não possui restaurantes cadastrados</p>';
            return;
        }
        
        container.innerHTML = restaurantes.map(r => `
            <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #cbd5e0;">
                <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
                    <input type="checkbox" name="restaurante" value="${r.id}" style="width: 18px; height: 18px;" onchange="toggleRestaurantePermissao(${r.id})">
                    <span style="font-weight: 600; color: #2d3748; flex: 1;">${r.nome}</span>
                </label>
                <div id="permissao-${r.id}" style="display: none; margin-top: 10px; margin-left: 28px;">
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                        <input type="radio" name="role-${r.id}" value="leitura" checked style="width: 16px; height: 16px;">
                        <span style="color: #4a5568;">🔍 <strong>Leitura</strong> - Visualiza e usa QR codes</span>
                    </label>
                    <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; margin-top: 5px;">
                        <input type="radio" name="role-${r.id}" value="admin" style="width: 16px; height: 16px;">
                        <span style="color: #4a5568;">👑 <strong>Administrador</strong> - Gerencia tudo</span>
                    </label>
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = `<p style="color: red;">Erro ao carregar restaurantes: ${e.message}</p>`;
    }
}

function toggleRestaurantePermissao(restauranteId) {
    const checkbox = document.querySelector(`input[name="restaurante"][value="${restauranteId}"]`);
    const permissaoDiv = document.getElementById(`permissao-${restauranteId}`);
    
    if (checkbox.checked) {
        permissaoDiv.style.display = 'block';
    } else {
        permissaoDiv.style.display = 'none';
    }
}

window.toggleRestaurantePermissao = toggleRestaurantePermissao;

async function carregarRestaurantesParaEdicao(clienteId, usuarioId) {
    const container = document.getElementById('edit-user-restaurantes-list');
    
    try {
        // Buscar todos os restaurantes da empresa
        const restaurantes = await api(`/admin/clientes/${clienteId}/restaurantes`);
        
        // Buscar permissões atuais do usuário
        const usuarioTenants = await api(`/admin/usuarios/${usuarioId}/tenants`);
        const tenantMap = {};
        usuarioTenants.forEach(t => {
            tenantMap[t.tenant_id] = t.is_admin_restaurante;
        });
        
        if (restaurantes.length === 0) {
            container.innerHTML = '<p style="color: #999; font-size: 13px;">Esta empresa não possui restaurantes cadastrados</p>';
            return;
        }
        
        container.innerHTML = restaurantes.map(r => {
            const isChecked = tenantMap.hasOwnProperty(r.id);
            const isAdmin = tenantMap[r.id] === true;
            
            return `
                <div style="background: white; padding: 12px; border-radius: 6px; border: 1px solid #cbd5e0;">
                    <label style="display: flex; align-items: center; gap: 10px; cursor: pointer;">
                        <input type="checkbox" name="edit-restaurante" value="${r.id}" ${isChecked ? 'checked' : ''} style="width: 18px; height: 18px;" onchange="toggleEditRestaurantePermissao(${r.id})">
                        <span style="font-weight: 600; color: #2d3748; flex: 1;">${r.nome}</span>
                    </label>
                    <div id="edit-permissao-${r.id}" style="display: ${isChecked ? 'block' : 'none'}; margin-top: 10px; margin-left: 28px;">
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer;">
                            <input type="radio" name="edit-role-${r.id}" value="leitura" ${!isAdmin ? 'checked' : ''} style="width: 16px; height: 16px;">
                            <span style="color: #4a5568;">🔍 <strong>Leitura</strong> - Visualiza e usa QR codes</span>
                        </label>
                        <label style="display: flex; align-items: center; gap: 8px; cursor: pointer; margin-top: 5px;">
                            <input type="radio" name="edit-role-${r.id}" value="admin" ${isAdmin ? 'checked' : ''} style="width: 16px; height: 16px;">
                            <span style="color: #4a5568;">👑 <strong>Administrador</strong> - Gerencia tudo</span>
                        </label>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        container.innerHTML = `<p style="color: red;">Erro ao carregar restaurantes: ${e.message}</p>`;
    }
}

function toggleEditRestaurantePermissao(restauranteId) {
    const checkbox = document.querySelector(`input[name="edit-restaurante"][value="${restauranteId}"]`);
    const permissaoDiv = document.getElementById(`edit-permissao-${restauranteId}`);
    
    if (checkbox.checked) {
        permissaoDiv.style.display = 'block';
    } else {
        permissaoDiv.style.display = 'none';
    }
}

window.toggleEditRestaurantePermissao = toggleEditRestaurantePermissao;

async function loadUsuarios() {
    try {
        const users = await api('/admin/usuarios');
        const filterClienteId = document.getElementById('filter-user-cliente').value;
        
        // Filtrar por empresa se selecionado
        const filteredUsers = filterClienteId 
            ? users.filter(u => u.cliente_id == filterClienteId)
            : users;
        
        // Carregar clientes para exibir nome da empresa
        const clientes = await api('/admin/clientes');
        const clientesMap = {};
        clientes.forEach(c => clientesMap[c.id] = c.nome_empresa);
        
        const html = filteredUsers.map(u => `
            <tr>
                <td>${u.nome}</td>
                <td>${u.email}</td>
                <td>${clientesMap[u.cliente_id] || '-'}</td>
                <td>${u.is_admin ? 'Sim' : 'Não'}</td>
                <td>
                    <button class="btn-small" onclick="editUser(${u.id})"><i class="fas fa-edit"></i> Editar</button>
                    <button class="btn-small danger" onclick="delUser(${u.id})"><i class="fas fa-trash"></i> Deletar</button>
                </td>
            </tr>
        `).join('');
        
        const totalMsg = filterClienteId 
            ? `${filteredUsers.length} usuário(s) encontrado(s)`
            : `Total: ${filteredUsers.length} usuário(s)`;
        
        document.getElementById('users-list').innerHTML = `
            <div style="margin-bottom: 10px; color: #666; font-size: 14px;">${totalMsg}</div>
            <table>
                <thead>
                    <tr>
                        <th>Nome</th>
                        <th>Email</th>
                        <th>Empresa</th>
                        <th>Admin</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody>${html}</tbody>
            </table>`;
    } catch (e) {
        document.getElementById('users-list').innerHTML = `<p style="color:red">Erro: ${e.message}</p>`;
    }
}

async function addUser(e) {
    e.preventDefault();
    const isAdmin = document.getElementById('user-admin').checked;
    
    try {
        const dados = {
            nome: document.getElementById('user-nome').value,
            email: document.getElementById('user-email').value,
            senha: document.getElementById('user-senha').value,
            is_admin: isAdmin
        };
        
        // Apenas adicionar cliente_id se não for admin do SaaS
        if (!isAdmin) {
            dados.cliente_id = parseInt(document.getElementById('user-cliente').value);
            
            // Coletar restaurantes selecionados com permissões
            const restaurantesSelecionados = [];
            const checkboxes = document.querySelectorAll('input[name="restaurante"]:checked');
            
            checkboxes.forEach(checkbox => {
                const restauranteId = parseInt(checkbox.value);
                const isAdminRestaurante = document.querySelector(`input[name="role-${restauranteId}"]:checked`)?.value === 'admin';
                
                restaurantesSelecionados.push({
                    tenant_id: restauranteId,
                    is_admin_restaurante: isAdminRestaurante
                });
            });
            
            // Adicionar restaurantes ao payload
            if (restaurantesSelecionados.length > 0) {
                dados.restaurantes = restaurantesSelecionados;
            }
        } else {
            dados.cliente_id = null; // Admin do SaaS não tem empresa
        }
        
        await api('/admin/usuarios', {
            method: 'POST',
            body: JSON.stringify(dados)
        });
        notify('Usuário criado com sucesso!');
        e.target.reset();
        toggleEmpresaField(); // Resetar visibilidade do campo
        document.getElementById('user-restaurantes-list').innerHTML = '';
        loadUsuarios();
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function editUser(id) {
    try {
        const u = await api(`/admin/usuarios/${id}`);
        
        // Preencher modal
        document.getElementById('edit-user-id').value = u.id;
        document.getElementById('edit-user-nome').value = u.nome;
        document.getElementById('edit-user-email').value = u.email;
        document.getElementById('edit-user-senha').value = ''; // Sempre vazio
        document.getElementById('edit-user-ativo').checked = u.ativo;
        
        // Carregar restaurantes se não for admin do SaaS
        const restaurantesGroup = document.getElementById('edit-user-restaurantes-group');
        if (!u.is_admin && u.cliente_id) {
            restaurantesGroup.style.display = 'block';
            await carregarRestaurantesParaEdicao(u.cliente_id, u.id);
        } else {
            restaurantesGroup.style.display = 'none';
        }
        
        // Abrir modal
        document.getElementById('modal-edit-user').classList.add('active');
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function salvarUserEdit(e) {
    e.preventDefault();
    const id = document.getElementById('edit-user-id').value;
    const novaSenha = document.getElementById('edit-user-senha').value;
    
    const dados = {
        nome: document.getElementById('edit-user-nome').value,
        email: document.getElementById('edit-user-email').value,
        ativo: document.getElementById('edit-user-ativo').checked
        // is_admin não é enviado, mantendo o valor original
    };
    
    // Adicionar senha somente se foi preenchida
    if (novaSenha) {
        dados.senha = novaSenha;
    }
    
    // Coletar restaurantes selecionados com permissões (se visível)
    const restaurantesGroup = document.getElementById('edit-user-restaurantes-group');
    if (restaurantesGroup.style.display !== 'none') {
        const restaurantesSelecionados = [];
        const checkboxes = document.querySelectorAll('input[name="edit-restaurante"]:checked');
        
        checkboxes.forEach(checkbox => {
            const restauranteId = parseInt(checkbox.value);
            const isAdminRestaurante = document.querySelector(`input[name="edit-role-${restauranteId}"]:checked`)?.value === 'admin';
            
            restaurantesSelecionados.push({
                tenant_id: restauranteId,
                is_admin_restaurante: isAdminRestaurante
            });
        });
        
        dados.restaurantes = restaurantesSelecionados;
    }
    
    try {
        await api(`/admin/usuarios/${id}`, {
            method: 'PUT',
            body: JSON.stringify(dados)
        });
        
        notify('Usuário atualizado com sucesso!');
        fecharModal('modal-edit-user');
        loadUsuarios();
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function delUser(id) {
    if (!confirm('Deletar este usuário?')) return;
    try {
        await api(`/admin/usuarios/${id}`, { method: 'DELETE' });
        notify('Deletado!');
        loadUsuarios();
    } catch (e) {
        notify(e.message, 'error');
    }
}

// ===== NAVEGAÇÃO =====
document.querySelectorAll('[data-tab]').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.preventDefault();
        document.querySelectorAll('.section').forEach(s => s.style.display = 'none');
        document.querySelectorAll('[data-tab]').forEach(b => b.classList.remove('active'));
        const tab = btn.dataset.tab;
        document.getElementById(tab).style.display = 'block';
        btn.classList.add('active');
        
        if (tab === 'clientes') loadClientes();
        if (tab === 'restaurantes') { loadClientesDropdown(); loadRestaurantes(); }
        if (tab === 'usuarios') { loadClientesDropdown(); loadUsuarios(); }
    });
});

// ===== LOGOUT =====
document.getElementById('logout').addEventListener('click', () => {
    localStorage.clear();
    window.location.href = '/admin/login.html';
});

// Carrega página inicial
window.addEventListener('DOMContentLoaded', () => {
    loadClientes();
    
    // Fechar modal ao clicar fora do conteúdo
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
});
