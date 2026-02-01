console.log('=== DASHBOARD.JS CARREGADO ===', new Date().toLocaleTimeString());
alert('DASHBOARD.JS CARREGADO - VERSAO: ' + new Date().toLocaleTimeString());

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
        console.log('Clicou em:', btn.dataset.section);
        
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
        
        btn.classList.add('active');
        const sec = btn.dataset.section;
        document.getElementById(sec).classList.add('active');
        
        console.log('Carregando:', sec);
        if (sec === 'empresas') loadEmpresas();
        if (sec === 'restaurantes') { loadEmpresas(); loadRestaurantes(); }
        if (sec === 'usuarios') { 
            console.log('=== ABA USUÁRIOS CLICADA ===');
            console.log('Chamando loadEmpresas()...');
            loadEmpresas().then(() => {
                console.log('loadEmpresas() concluído');
                loadUsuarios();
            }).catch(err => {
                console.error('Erro em loadEmpresas():', err);
            });
        }
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
    console.log('=== loadEmpresas INICIADO ===' + new Date().toLocaleTimeString());
    try {
        console.log('loadEmpresas iniciado');
        const empresas = await api('/admin/clientes') || [];
        console.log('Empresas recebidas:', empresas);
        console.log('Número de empresas:', empresas.length);
        
        let html = '<table><thead><tr><th>Nome</th><th>Email</th><th>Telefone</th><th>Ação</th></tr></thead><tbody>';
        if (empresas.length === 0) {
            html += '<tr><td colspan="4" style="text-align:center;padding:20px;color:#999;">Nenhuma empresa cadastrada</td></tr>';
        }
        empresas.forEach(e => {
            html += `<tr><td>${e.nome_empresa}</td><td>${e.email}</td><td>${e.telefone || '-'}</td><td><button class="btn-sm danger" onclick="delEmpresa(${e.id})">Deletar</button></td></tr>`;
        });
        html += '</tbody></table>';
        const empresasListEl = document.getElementById('empresas-list');
        if (empresasListEl) empresasListEl.innerHTML = html;
        
        // Popular select de restaurantes e usuários
        let opts = '<option value="">Selecione uma empresa</option>';
        empresas.forEach(e => {
            opts += `<option value="${e.id}">${e.nome_empresa}</option>`;
        });
        
        console.log('Options HTML:', opts);
        console.log('Número de empresas:', empresas.length);
        
        // Popular selects de forma síncrona
        const restEmpSelect = document.querySelector('select#rest-emp');
        const usrEmpSelect = document.querySelector('select#usr-emp');
        
        console.log('Procurando select#rest-emp:', restEmpSelect);
        console.log('Procurando select#usr-emp:', usrEmpSelect);
        console.log('select#usr-emp visível?', usrEmpSelect ? window.getComputedStyle(usrEmpSelect.parentElement.parentElement).display : 'N/A');
        
        if (restEmpSelect) {
            restEmpSelect.innerHTML = opts;
            console.log('✓ rest-emp preenchido com', empresas.length, 'opções');
        } else {
            console.warn('✗ rest-emp não encontrado');
        }
        
        if (usrEmpSelect) {
            console.log('✓ usr-emp ENCONTRADO!');
            console.log('  - Elemento:', usrEmpSelect);
            console.log('  - Pai:', usrEmpSelect.parentElement);
            console.log('  - Display do pai:', window.getComputedStyle(usrEmpSelect.parentElement).display);
            console.log('  - Seção ativa:', document.getElementById('usuarios').classList.contains('active'));
            console.log('  - innerHTML ANTES:', usrEmpSelect.innerHTML);
            
            usrEmpSelect.innerHTML = opts;
            
            console.log('  - innerHTML DEPOIS:', usrEmpSelect.innerHTML.substring(0, 150));
            console.log('  - options.length:', usrEmpSelect.options.length);
            console.log('✓ usr-emp preenchido com', empresas.length, 'opções');
        } else {
            console.warn('✗ usr-emp não encontrado');
        }
        
    } catch (e) {
        console.error('=== ERRO em loadEmpresas ===');
        console.error('Mensagem:', e.message);
        console.error('Stack:', e.stack);
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
async function loadRestosForUser() {
    try {
        const empId = document.getElementById('usr-emp').value;
        if (!empId) {
            document.getElementById('usr-rests').innerHTML = '';
            return;
        }
        
        const rests = await api(`/admin/clientes/${empId}/restaurantes`);
        let html = '';
        rests.forEach(r => {
            html += `<label style="display: block; margin: 8px 0; cursor: pointer;">
                <input type="checkbox" name="rest-${r.id}" value="${r.id}" class="usr-rest-check">
                ${r.nome}
            </label>`;
        });
        document.getElementById('usr-rests').innerHTML = html || '<p>Nenhum restaurante para esta empresa</p>';
    } catch (e) {
        notify(e.message, 'error');
    }
}

async function addUsuario(e) {
    e.preventDefault();
    
    const rests = Array.from(document.querySelectorAll('.usr-rest-check:checked')).map(c => parseInt(c.value));
    if (rests.length === 0) {
        notify('Selecione ao menos um restaurante!', 'error');
        return;
    }
    
    try {
        await api('/admin/usuarios', {
            method: 'POST',
            body: JSON.stringify({
                cliente_id: parseInt(document.getElementById('usr-emp').value),
                nome: document.getElementById('usr-nome').value,
                email: document.getElementById('usr-email').value,
                senha: document.getElementById('usr-senha').value,
                is_admin: document.getElementById('usr-admin').checked,
                restaurantes: rests
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

// Carregar dados da aba ativa inicial (empresas)
const abaInicial = document.querySelector('.nav-btn.active');
if (abaInicial && abaInicial.dataset.section === 'empresas') {
    loadEmpresas();
}
