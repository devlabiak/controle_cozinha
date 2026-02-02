const API = `${window.location.protocol}//${window.location.hostname.replace('admin.', '')}/api`;
const TOKEN = localStorage.getItem('token');

console.log('Dashboard Init:', { API, TOKEN: TOKEN ? '✓' : '✗ (nulo)' });

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
            <tr>
                <td>${c.nome_empresa}</td>
                <td>${c.email}</td>
                <td>${c.telefone || '-'}</td>
                <td>
                    <button class="btn-small" onclick="editCliente(${c.id})"><i class="fas fa-edit"></i> Editar</button>
                    <button class="btn-small danger" onclick="delCliente(${c.id})"><i class="fas fa-trash"></i> Deletar</button>
                </td>
            </tr>
        `).join('');
        document.getElementById('clientes-list').innerHTML = `<table><thead><tr><th>Nome</th><th>Email</th><th>Telefone</th><th>Ações</th></tr></thead><tbody>${html}</tbody></table>`;
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
                email: document.getElementById('cli-email').value,
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
        document.getElementById('edit-cli-email').value = c.email;
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
                email: document.getElementById('edit-cli-email').value,
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

// ===== RESTAURANTES =====
async function loadRestaurantes() {
    try {
        const rests = await api('/admin/restaurantes');
        const html = rests.map(r => `
            <tr>
                <td>${r.nome}</td>
                <td><code>${r.slug}</code></td>
                <td>${r.cliente_id}</td>
                <td>
                    <button class="btn-small" onclick="editRest(${r.id})"><i class="fas fa-edit"></i> Editar</button>
                    <button class="btn-small danger" onclick="delRest(${r.id})"><i class="fas fa-trash"></i> Deletar</button>
                </td>
            </tr>
        `).join('');
        document.getElementById('rests-list').innerHTML = `<table><thead><tr><th>Nome</th><th>Slug</th><th>Cliente</th><th>Ações</th></tr></thead><tbody>${html}</tbody></table>`;
    } catch (e) {
        document.getElementById('rests-list').innerHTML = `<p style="color:red">Erro: ${e.message}</p>`;
    }
}

async function loadClientesDropdown() {
    try {
        const clientes = await api('/admin/clientes');
        const html = clientes.map(c => `<option value="${c.id}">${c.nome_empresa}</option>`).join('');
        document.getElementById('rest-cliente').innerHTML = `<option value="">Selecione</option>${html}`;
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
                email: document.getElementById('rest-email').value
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
        document.getElementById('edit-rest-email').value = r.email;
        
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
                email: document.getElementById('edit-rest-email').value
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

// ===== USUÁRIOS =====
async function loadUsuarios() {
    try {
        const users = await api('/admin/usuarios');
        const html = users.map(u => `
            <tr>
                <td>${u.nome}</td>
                <td>${u.email}</td>
                <td>${u.is_admin ? 'Sim' : 'Não'}</td>
                <td>
                    <button class="btn-small" onclick="editUser(${u.id})"><i class="fas fa-edit"></i> Editar</button>
                    <button class="btn-small danger" onclick="delUser(${u.id})"><i class="fas fa-trash"></i> Deletar</button>
                </td>
            </tr>
        `).join('');
        document.getElementById('users-list').innerHTML = `<table><thead><tr><th>Nome</th><th>Email</th><th>Admin</th><th>Ações</th></tr></thead><tbody>${html}</tbody></table>`;
    } catch (e) {
        document.getElementById('users-list').innerHTML = `<p style="color:red">Erro: ${e.message}</p>`;
    }
}

async function addUser(e) {
    e.preventDefault();
    try {
        await api('/admin/usuarios', {
            method: 'POST',
            body: JSON.stringify({
                cliente_id: parseInt(document.getElementById('user-cliente').value),
                nome: document.getElementById('user-nome').value,
                email: document.getElementById('user-email').value,
                senha: document.getElementById('user-senha').value,
                is_admin: document.getElementById('user-admin').checked
            })
        });
        notify('Usuário criado!');
        e.target.reset();
        loadUsuarios();
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function editUser(id) {
    try {
        const u = await api(`/admin/usuarios/${id}`);
        const nome = prompt('Nome:', u.nome);
        if (!nome) return;
        await api(`/admin/usuarios/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ nome, email: u.email, is_admin: u.is_admin, ativo: u.ativo })
        });
        notify('Atualizado!');
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
