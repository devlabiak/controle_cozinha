const API = `${window.location.protocol}//${window.location.hostname}/api`;
const TOKEN = localStorage.getItem('token');

if (!TOKEN) {
    window.location.href = '/painelfoods/login.html';
}

function notify(msg, type = 'success') {
    const div = document.createElement('div');
    div.className = `notification ${type}`;
    div.innerHTML = `<i class="fas fa-${type === 'success' ? 'check' : 'exclamation'}-circle"></i> ${msg}`;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 3000);
}

async function api(path, opts = {}) {
    const res = await fetch(`${API}${path}`, {
        ...opts,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${TOKEN}`,
            ...opts.headers
        }
    });

    const text = await res.text();
    const data = text ? JSON.parse(text) : null;

    if (!res.ok) {
        throw new Error(data?.detail || `Erro ${res.status}`);
    }
    return data;
}

// Navegação
document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        
        btn.classList.add('active');
        const sec = btn.dataset.section;
        document.getElementById(sec).classList.add('active');
        
        if (sec === 'empresas') loadEmpresas();
        if (sec === 'restaurantes') { loadEmpresas(); loadRestaurantes(); }
        if (sec === 'usuarios') { loadEmpresas(); loadUsuarios(); }
    });
});

// ===== EMPRESAS =====
async function addEmpresa(e) {
    e.preventDefault();
    try {
        await api('/admin/clientes', {
            method: 'POST',
            body: JSON.stringify({
                nome_empresa: document.getElementById('emp-nome').value,
                email: document.getElementById('emp-email').value,
                telefone: document.getElementById('emp-tel').value || null
            })
        });
        notify('Empresa criada!');
        e.target.reset();
        loadEmpresas();
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function loadEmpresas() {
    try {
        const empresas = await api('/admin/clientes');
        let html = '<table><thead><tr><th>Nome</th><th>Email</th><th>Telefone</th><th>Ação</th></tr></thead><tbody>';
        empresas.forEach(e => {
            html += `<tr><td>${e.nome_empresa}</td><td>${e.email}</td><td>${e.telefone || '-'}</td><td><button class="btn-sm danger" onclick="delEmpresa(${e.id})">Deletar</button></td></tr>`;
        });
        html += '</tbody></table>';
        document.getElementById('empresas-list').innerHTML = html;
        
        // Popular select de restaurantes e usuários
        let opts = '<option value="">Selecione</option>';
        empresas.forEach(e => {
            opts += `<option value="${e.id}">${e.nome_empresa}</option>`;
        });
        document.getElementById('rest-emp').innerHTML = opts;
        document.getElementById('usr-emp').innerHTML = opts;
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function delEmpresa(id) {
    if (!confirm('Deletar empresa? Isso vai deletar restaurantes e usuários também!')) return;
    try {
        await api(`/admin/clientes/${id}`, { method: 'DELETE' });
        notify('Deletado!');
        loadEmpresas();
    } catch (e) {
        notify(e.message, 'error');
    }
}

// ===== RESTAURANTES =====
async function addRestaurante(e) {
    e.preventDefault();
    try {
        await api('/admin/restaurantes', {
            method: 'POST',
            body: JSON.stringify({
                cliente_id: parseInt(document.getElementById('rest-emp').value),
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

async function loadRestaurantes() {
    try {
        const rests = await api('/admin/restaurantes');
        let html = '<table><thead><tr><th>Nome</th><th>Slug</th><th>Email</th><th>Ação</th></tr></thead><tbody>';
        rests.forEach(r => {
            html += `<tr><td>${r.nome}</td><td><code>${r.slug}</code></td><td>${r.email}</td><td><button class="btn-sm danger" onclick="delRestaurante(${r.id})">Deletar</button></td></tr>`;
        });
        html += '</tbody></table>';
        document.getElementById('restaurantes-list').innerHTML = html;
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function delRestaurante(id) {
    if (!confirm('Deletar restaurante?')) return;
    try {
        await api(`/admin/restaurantes/${id}`, { method: 'DELETE' });
        notify('Deletado!');
        loadRestaurantes();
    } catch (e) {
        notify(e.message, 'error');
    }
}

// ===== USUÁRIOS =====
async function addUsuario(e) {
    e.preventDefault();
    try {
        await api('/admin/usuarios', {
            method: 'POST',
            body: JSON.stringify({
                cliente_id: parseInt(document.getElementById('usr-emp').value),
                nome: document.getElementById('usr-nome').value,
                email: document.getElementById('usr-email').value,
                senha: document.getElementById('usr-senha').value,
                is_admin: document.getElementById('usr-admin').checked
            })
        });
        notify('Usuário criado!');
        e.target.reset();
        loadUsuarios();
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function loadUsuarios() {
    try {
        const users = await api('/admin/usuarios');
        let html = '<table><thead><tr><th>Nome</th><th>Email</th><th>Admin</th><th>Ação</th></tr></thead><tbody>';
        users.forEach(u => {
            html += `<tr><td>${u.nome}</td><td>${u.email}</td><td>${u.is_admin ? 'Sim' : 'Não'}</td><td><button class="btn-sm danger" onclick="delUsuario(${u.id})">Deletar</button></td></tr>`;
        });
        html += '</tbody></table>';
        document.getElementById('usuarios-list').innerHTML = html;
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function delUsuario(id) {
    if (!confirm('Deletar usuário?')) return;
    try {
        await api(`/admin/usuarios/${id}`, { method: 'DELETE' });
        notify('Deletado!');
        loadUsuarios();
    } catch (e) {
        notify(e.message, 'error');
    }
}

// Logout
document.getElementById('logout').addEventListener('click', () => {
    localStorage.clear();
    window.location.href = '/painelfoods/login.html';
});

// Load inicial
loadEmpresas();
