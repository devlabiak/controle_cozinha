const API_BASE = `${window.location.protocol}//${window.location.hostname.replace('admin.', '')}/api`;
const TOKEN = localStorage.getItem('token');
let usuarioAtual = JSON.parse(localStorage.getItem('user') || '{}');

console.log('Dashboard Loaded:', { API_BASE, TOKEN: !!TOKEN, usuario: usuarioAtual.nome });

// ===== NOTIFICATION SYSTEM =====
function showNotification(message, type = 'success', duration = 4000) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    
    const icons = {
        success: 'fas fa-check-circle',
        error: 'fas fa-exclamation-circle',
        warning: 'fas fa-exclamation-triangle',
        info: 'fas fa-info-circle'
    };

    notification.innerHTML = `
        <i class="${icons[type]}"></i>
        <span>${message}</span>
    `;

    document.body.appendChild(notification);

    if (duration > 0) {
        setTimeout(() => {
            notification.remove();
        }, duration);
    }

    return notification;
}

// ===== CLEAR ERRORS =====
function clearErrors() {
    document.querySelectorAll('.error-message').forEach(el => {
        el.classList.remove('show');
    });
    document.querySelectorAll('input, select, textarea').forEach(el => {
        el.classList.remove('error');
    });
}

// ===== VALIDATION =====
function validarEmail(email) {
    const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return regex.test(email);
}

// ===== NAVIGATION =====
document.querySelectorAll('[data-section]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        navigateTo(link.dataset.section);
    });
});

function navigateTo(section) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
    document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));

    // Show selected section
    const sectionEl = document.getElementById(section);
    if (sectionEl) {
        sectionEl.classList.add('active');
        document.querySelector(`[data-section="${section}"]`).classList.add('active');

        // Update page title
        const titles = {
            'home': 'Dashboard',
            'clientes': 'Gerenciar Clientes',
            'restaurantes': 'Gerenciar Restaurantes',
            'usuarios': 'Gerenciar Usuários'
        };
        document.getElementById('page-title').textContent = titles[section] || 'Dashboard';

        // Load data if needed
        if (section === 'clientes') carregarClientes();
        if (section === 'restaurantes') {
            carregarClientesSelect();
            carregarRestaurantes();
        }
        if (section === 'usuarios') {
            carregarClientesSelect();
            carregarUsuarios();
        }
    }
}

// ===== AUTH =====
function logout() {
    if (confirm('Tem certeza que deseja sair?')) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/admin/login.html';
    }
}

// ===== HELPERS =====
function authHeaders() {
    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${TOKEN}`
    };
    console.log('Auth Headers:', { Authorization: headers.Authorization ? 'Bearer ...' : 'MISSING' });
    return headers;
}

// ===== LOAD CLIENTES SELECT =====
async function carregarClientesSelect() {
    try {
        const response = await fetch(`${API_BASE}/admin/clientes`, {
            headers: authHeaders()
        });
        
        if (!response.ok) throw new Error('Erro ao carregar clientes');
        
        const clientes = await response.json();
        
        // Preencher select de restaurante
        const selectRestaurante = document.getElementById('restaurante-cliente');
        const selectUsuario = document.getElementById('usuario-cliente');
        
        selectRestaurante.innerHTML = '<option value="">Selecione um cliente</option>';
        selectUsuario.innerHTML = '<option value="">Selecione um cliente</option>';
        
        clientes.forEach(cliente => {
            const option1 = document.createElement('option');
            option1.value = cliente.id;
            option1.textContent = cliente.nome_empresa;
            selectRestaurante.appendChild(option1);
            
            const option2 = document.createElement('option');
            option2.value = cliente.id;
            option2.textContent = cliente.nome_empresa;
            selectUsuario.appendChild(option2);
        });
    } catch (error) {
        console.error('Erro:', error);
    }
}

// ===== CLIENTES =====
async function adicionarCliente(e) {
    e.preventDefault();
    clearErrors();

    const nome = document.getElementById('cliente-nome').value.trim();
    const email = document.getElementById('cliente-email').value.trim().toLowerCase();
    const telefone = document.getElementById('cliente-telefone').value.trim() || null;
    const cnpj = document.getElementById('cliente-cnpj').value.trim() || null;
    const endereco = document.getElementById('cliente-endereco').value.trim() || null;
    const cidade = document.getElementById('cliente-cidade').value.trim() || null;
    const estado = document.getElementById('cliente-estado').value || null;
    const ativo = document.getElementById('cliente-ativo').value === 'true';

    if (!nome || !email) {
        showNotification('Preencha os campos obrigatórios', 'error');
        if (!nome) document.getElementById('cliente-nome').classList.add('error');
        if (!email) document.getElementById('cliente-email').classList.add('error');
        return;
    }

    if (!validarEmail(email)) {
        showNotification('Email inválido', 'error');
        document.getElementById('cliente-email').classList.add('error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/admin/clientes`, {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({
                nome_empresa: nome,
                email,
                telefone,
                cnpj,
                endereco,
                cidade,
                estado,
                ativo
            })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('✓ Cliente cadastrado com sucesso!', 'success');
            document.getElementById('form-cliente').reset();
            carregarClientes();
            carregarClientesSelect();
        } else {
            showNotification(data.detail || 'Erro ao cadastrar cliente', 'error');
        }
    } catch (error) {
        showNotification('Erro de conexão: ' + error.message, 'error');
    }
}

async function carregarClientes() {
    try {
        const response = await fetch(`${API_BASE}/admin/clientes`, {
            headers: authHeaders()
        });

        if (!response.ok) {
            console.error('Erro ao carregar clientes:', response.status, response.statusText);
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }

        const clientes = await response.json();
        const container = document.getElementById('clientes-list');

        if (clientes.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <h3>Nenhum cliente cadastrado</h3>
                    <p>Comece criando um novo cliente no formulário acima</p>
                </div>
            `;
            return;
        }

        let html = '<table><thead><tr><th>Nome</th><th>Email</th><th>Telefone</th><th>Status</th><th>Ações</th></tr></thead><tbody>';

        clientes.forEach(cliente => {
            const status = cliente.ativo ? 'active' : 'inactive';
            const statusText = cliente.ativo ? 'Ativo' : 'Inativo';

            html += `
                <tr>
                    <td>${cliente.nome_empresa}</td>
                    <td>${cliente.email}</td>
                    <td>${cliente.telefone || '-'}</td>
                    <td><span class="status-badge ${status}">${statusText}</span></td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn-icon" title="Editar" onclick="editarCliente(${cliente.id})">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn-icon danger" title="Deletar" onclick="deletarCliente(${cliente.id})">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Erro:', error);
        document.getElementById('clientes-list').innerHTML = '<p style="text-align: center; color: #a0aec0;">Erro ao carregar clientes</p>';
    }
}

function editarCliente(id) {
    showNotification('Edição em desenvolvimento', 'info');
}

async function deletarCliente(id) {
    if (!confirm('Tem certeza que deseja deletar este cliente?\n\nISSO VAI EXCLUIR:\n- Todos os restaurantes\n- Todos os usuários\n- Todos os dados associados')) return;

    try {
        const response = await fetch(`${API_BASE}/admin/clientes/${id}`, {
            method: 'DELETE',
            headers: authHeaders()
        });

        if (response.ok) {
            showNotification('✓ Cliente deletado com sucesso!', 'success');
            carregarClientes();
            carregarClientesSelect();
        } else {
            const data = await response.json();
            showNotification(data.detail || 'Erro ao deletar cliente', 'error');
        }
    } catch (error) {
        showNotification('Erro de conexão: ' + error.message, 'error');
    }
}

// ===== RESTAURANTES =====
document.getElementById('restaurante-slug')?.addEventListener('input', (e) => {
    document.getElementById('slug-preview').textContent = e.target.value.toLowerCase().replace(/\s+/g, '-') || 'restaurante';
});

async function adicionarRestaurante(e) {
    e.preventDefault();
    clearErrors();

    const cliente_id = document.getElementById('restaurante-cliente').value;
    const nome = document.getElementById('restaurante-nome').value.trim();
    const slug = document.getElementById('restaurante-slug').value.trim().toLowerCase().replace(/\s+/g, '-');
    const email = document.getElementById('restaurante-email').value.trim().toLowerCase();
    const telefone = document.getElementById('restaurante-telefone').value.trim() || null;
    const cnpj = document.getElementById('restaurante-cnpj').value.trim() || null;
    const endereco = document.getElementById('restaurante-endereco').value.trim() || null;
    const cidade = document.getElementById('restaurante-cidade').value.trim() || null;
    const ativo = document.getElementById('restaurante-ativo').value === 'true';

    if (!cliente_id || !nome || !slug || !email) {
        showNotification('Preencha os campos obrigatórios', 'error');
        if (!cliente_id) document.getElementById('restaurante-cliente').classList.add('error');
        if (!nome) document.getElementById('restaurante-nome').classList.add('error');
        if (!slug) document.getElementById('restaurante-slug').classList.add('error');
        if (!email) document.getElementById('restaurante-email').classList.add('error');
        return;
    }

    if (!validarEmail(email)) {
        showNotification('Email inválido', 'error');
        document.getElementById('restaurante-email').classList.add('error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/admin/restaurantes`, {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({
                cliente_id: parseInt(cliente_id),
                nome,
                slug,
                email,
                telefone,
                cnpj,
                endereco,
                cidade,
                ativo
            })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('✓ Restaurante cadastrado com sucesso!', 'success');
            document.getElementById('form-restaurante').reset();
            carregarRestaurantes();
        } else {
            showNotification(data.detail || 'Erro ao cadastrar restaurante', 'error');
        }
    } catch (error) {
        showNotification('Erro de conexão: ' + error.message, 'error');
    }
}

async function carregarRestaurantes() {
    try {
        const response = await fetch(`${API_BASE}/admin/restaurantes`, {
            headers: authHeaders()
        });

        if (!response.ok) throw new Error('Erro ao carregar restaurantes');

        const restaurantes = await response.json();
        const container = document.getElementById('restaurantes-list');

        if (restaurantes.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <h3>Nenhum restaurante cadastrado</h3>
                    <p>Comece criando um novo restaurante no formulário acima</p>
                </div>
            `;
            return;
        }

        let html = '<table><thead><tr><th>Nome</th><th>Slug</th><th>Email</th><th>Cliente</th><th>Status</th><th>Ações</th></tr></thead><tbody>';

        restaurantes.forEach(r => {
            const status = r.ativo ? 'active' : 'inactive';
            const statusText = r.ativo ? 'Ativo' : 'Inativo';
            const clienteNome = r.cliente?.nome_empresa || 'N/A';

            html += `
                <tr>
                    <td>${r.nome}</td>
                    <td><code style="background: #f7fafc; padding: 2px 6px; border-radius: 3px;">${r.slug}</code></td>
                    <td>${r.email}</td>
                    <td>${clienteNome}</td>
                    <td><span class="status-badge ${status}">${statusText}</span></td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn-icon" title="Editar" onclick="editarRestaurante(${r.id})">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn-icon danger" title="Deletar" onclick="deletarRestaurante(${r.id})">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Erro:', error);
        document.getElementById('restaurantes-list').innerHTML = '<p style="text-align: center; color: #a0aec0;">Erro ao carregar restaurantes</p>';
    }
}

function editarRestaurante(id) {
    showNotification('Edição em desenvolvimento', 'info');
}

async function deletarRestaurante(id) {
    if (!confirm('Tem certeza que deseja deletar este restaurante?\n\nISSO VAI EXCLUIR:\n- Todos os alimentos\n- Todos os lotes\n- Todos os registros de movimentação')) return;

    try {
        const response = await fetch(`${API_BASE}/admin/restaurantes/${id}`, {
            method: 'DELETE',
            headers: authHeaders()
        });

        if (response.ok) {
            showNotification('✓ Restaurante deletado com sucesso!', 'success');
            carregarRestaurantes();
        } else {
            const data = await response.json();
            showNotification(data.detail || 'Erro ao deletar restaurante', 'error');
        }
    } catch (error) {
        showNotification('Erro de conexão: ' + error.message, 'error');
    }
}

// ===== USUARIOS =====
async function adicionarUsuario(e) {
    e.preventDefault();
    clearErrors();

    const cliente_id = document.getElementById('usuario-cliente').value;
    const nome = document.getElementById('usuario-nome').value.trim();
    const email = document.getElementById('usuario-email').value.trim().toLowerCase();
    const senha = document.getElementById('usuario-senha').value;
    const is_admin = document.getElementById('usuario-admin').value === 'true';
    const ativo = document.getElementById('usuario-ativo').value === 'true';

    if (!cliente_id || !nome || !email || !senha) {
        showNotification('Preencha os campos obrigatórios', 'error');
        if (!cliente_id) document.getElementById('usuario-cliente').classList.add('error');
        if (!nome) document.getElementById('usuario-nome').classList.add('error');
        if (!email) document.getElementById('usuario-email').classList.add('error');
        if (!senha) document.getElementById('usuario-senha').classList.add('error');
        return;
    }

    if (senha.length < 6) {
        showNotification('Senha deve ter no mínimo 6 caracteres', 'error');
        document.getElementById('usuario-senha').classList.add('error');
        return;
    }

    if (!validarEmail(email)) {
        showNotification('Email inválido', 'error');
        document.getElementById('usuario-email').classList.add('error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/admin/usuarios`, {
            method: 'POST',
            headers: authHeaders(),
            body: JSON.stringify({
                cliente_id: parseInt(cliente_id),
                nome,
                email,
                senha,
                is_admin,
                ativo
            })
        });

        const data = await response.json();

        if (response.ok) {
            showNotification('✓ Usuário cadastrado com sucesso!', 'success');
            document.getElementById('form-usuario').reset();
            carregarUsuarios();
        } else {
            showNotification(data.detail || 'Erro ao cadastrar usuário', 'error');
        }
    } catch (error) {
        showNotification('Erro de conexão: ' + error.message, 'error');
    }
}

async function carregarUsuarios() {
    try {
        const response = await fetch(`${API_BASE}/admin/usuarios`, {
            headers: authHeaders()
        });

        if (!response.ok) throw new Error('Erro ao carregar usuários');

        const usuarios = await response.json();
        const container = document.getElementById('usuarios-list');

        if (usuarios.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <h3>Nenhum usuário cadastrado</h3>
                    <p>Comece criando um novo usuário no formulário acima</p>
                </div>
            `;
            return;
        }

        let html = '<table><thead><tr><th>Nome</th><th>Email</th><th>Cliente</th><th>Admin</th><th>Status</th><th>Ações</th></tr></thead><tbody>';

        usuarios.forEach(u => {
            const status = u.ativo ? 'active' : 'inactive';
            const statusText = u.ativo ? 'Ativo' : 'Inativo';
            const adminText = u.is_admin ? 'Sim' : 'Não';
            const clienteNome = u.cliente?.nome_empresa || 'N/A';

            html += `
                <tr>
                    <td>${u.nome}</td>
                    <td>${u.email}</td>
                    <td>${clienteNome}</td>
                    <td>${adminText}</td>
                    <td><span class="status-badge ${status}">${statusText}</span></td>
                    <td>
                        <div class="action-buttons">
                            <button class="btn-icon" title="Editar" onclick="editarUsuario(${u.id})">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn-icon danger" title="Deletar" onclick="deletarUsuario(${u.id})">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        });

        html += '</tbody></table>';
        container.innerHTML = html;
    } catch (error) {
        console.error('Erro:', error);
        document.getElementById('usuarios-list').innerHTML = '<p style="text-align: center; color: #a0aec0;">Erro ao carregar usuários</p>';
    }
}

function editarUsuario(id) {
    showNotification('Edição em desenvolvimento', 'info');
}

async function deletarUsuario(id) {
    if (!confirm('Tem certeza que deseja deletar este usuário?')) return;

    try {
        const response = await fetch(`${API_BASE}/admin/usuarios/${id}`, {
            method: 'DELETE',
            headers: authHeaders()
        });

        if (response.ok) {
            showNotification('✓ Usuário deletado com sucesso!', 'success');
            carregarUsuarios();
        } else {
            const data = await response.json();
            showNotification(data.detail || 'Erro ao deletar usuário', 'error');
        }
    } catch (error) {
        showNotification('Erro de conexão: ' + error.message, 'error');
    }
}

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOMContentLoaded:', { TOKEN: !!TOKEN, usuario: usuarioAtual.nome });
    
    if (!TOKEN) {
        console.warn('Token não encontrado, redirecionando para login');
        window.location.href = '/admin/login.html';
        return;
    }

    // Não redirecionar infinitamente
    document.getElementById('user-name').textContent = usuarioAtual.nome || 'Administrador';
    
    // Carregar dados iniciais
    console.log('Carregando dados iniciais...');
    carregarClientesSelect();
    navigateTo('home');
});
