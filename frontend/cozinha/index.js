const user = JSON.parse(localStorage.getItem('user') || '{}');
const token = localStorage.getItem('token');

if (!token || user.is_admin) {
    window.location.href = '/painelfoods/login.html';
}

function notify(msg, type = 'success') {
    const div = document.createElement('div');
    div.className = `notification ${type}`;
    div.innerHTML = `<i class="fas fa-${type === 'success' ? 'check' : 'exclamation'}-circle"></i> ${msg}`;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 3000);
}

// ===== SELETOR DE RESTAURANTE =====
function showSelector() {
    const opts = document.getElementById('rest-options');
    opts.innerHTML = '';
    
    user.restaurantes?.forEach(r => {
        const btn = document.createElement('button');
        btn.className = 'restaurant-btn';
        btn.innerHTML = `<i class="fas fa-store"></i><p>${r.nome}</p>`;
        btn.onclick = () => selectRestaurant(r);
        opts.appendChild(btn);
    });

    // Se tem só 1 restaurante, já seleciona
    if (user.restaurantes?.length === 1) {
        selectRestaurant(user.restaurantes[0]);
    } else {
        document.getElementById('selector').classList.add('active');
        document.getElementById('qrcode').classList.remove('active');
    }
}

function selectRestaurant(rest) {
    localStorage.setItem('tenant_id', rest.id);
    localStorage.setItem('tenant_slug', rest.slug);
    localStorage.setItem('restaurant_name', rest.nome);
    
    document.getElementById('rest-name').textContent = rest.nome;
    document.getElementById('selector').classList.remove('active');
    document.getElementById('qrcode').classList.add('active');
    
    // Focar input de QR code
    document.getElementById('qr-input').focus();
}

document.getElementById('trocar-rest').addEventListener('click', () => {
    document.getElementById('qrcode').classList.remove('active');
    document.getElementById('selector').classList.add('active');
});

document.getElementById('logout').addEventListener('click', () => {
    localStorage.clear();
    window.location.href = '/painelfoods/login.html';
});

// ===== LEITURA DE QR CODE =====
document.getElementById('qr-input').addEventListener('change', (e) => {
    const qr = e.target.value.trim();
    if (!qr) return;
    
    // TODO: Aqui você implementa a lógica de dar baixa no estoque
    console.log('QR Code lido:', qr);
    notify(`QR Code: ${qr}`);
    
    // Limpar input
    e.target.value = '';
});

// Carregar página
showSelector();
