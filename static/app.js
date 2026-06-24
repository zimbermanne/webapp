const API_BASE_URL = '/api';

let currentToken = localStorage.getItem('token');

// ── Google OAuth: pick up ?token= from the redirect URL ──────────────────────
(function handleGoogleOAuthRedirect() {
    const params = new URLSearchParams(window.location.search);
    const tokenFromGoogle = params.get('token');
    if (tokenFromGoogle) {
        localStorage.setItem('token', tokenFromGoogle);
        currentToken = tokenFromGoogle;
        // Clean the URL so the token isn't visible in the address bar
        window.history.replaceState({}, document.title, window.location.pathname);
    }
})();
let currentUser = null;
let catalogItemsCache = [];
let shoppingCart = [];

const loginScreen = document.getElementById('login-screen');
const dashboardScreen = document.getElementById('dashboard-screen');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');

async function apiCall(endpoint, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (currentToken) {
        headers['Authorization'] = `Bearer ${currentToken}`;
    }
    try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            ...options,
            headers: { ...headers, ...options.headers }
        });
        if (response.status === 401) { logout(); throw new Error('Unauthorized'); }
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'API breakdown');
        return data;
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        throw error;
    }
}

function showScreen(screen) {
    document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
    screen.classList.remove('hidden');
}

// Sidebar View Controller
document.querySelectorAll('.nav-links a[data-section]').forEach(link => {
    link.addEventListener('click', async (e) => {
        e.preventDefault();
        const section = link.dataset.section;
        
        document.querySelectorAll('.nav-links a').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        
        document.querySelectorAll('.content-section').forEach(s => s.classList.add('hidden'));
        const targetSection = document.getElementById(`${section}-section`);
        if (targetSection) targetSection.classList.remove('hidden');
        
        switch(section) {
            case 'dashboard': loadDashboardMetrics(); break;
            case 'pos': initializePOSModule(); break;
            case 'reports': executeFinancialPLSummary(); loadLedgerDashboards(); break;
        }
    });
});

// POS Module Processing Engine
async function initializePOSModule() {
    try {
        // Fallback or active list fetch logic
        catalogItemsCache = [
            {id: 1, name: "PVC Pipe 1/2 Inch", quantity: 45, price: 12000},
            {id: 2, name: "Fabric Roll Premium", quantity: 12, price: 85000}
        ];
        renderPOSCatalog(catalogItemsCache);
        renderPOSCart();
    } catch (e) {
        console.error("Failed loading inventory catalog context.");
    }
}

function renderPOSCatalog(items) {
    const grid = document.getElementById('pos-grid-container');
    if (!grid) return;
    grid.innerHTML = items.map(item => `
        <div class="product-tap-card" style="border:1px solid #ddd; padding:10px; margin:5px; cursor:pointer;" onclick="addProductToCart(${item.id})">
            <h4>${item.name}</h4>
            <span>Qty: ${item.quantity}</span><br>
            <span style="color:green; font-weight:bold;">TZS ${item.price.toLocaleString()}</span>
        </div>
    `).join('');
}

function addProductToCart(itemId) {
    const matchedProduct = catalogItemsCache.find(i => i.id === itemId);
    const existingCartIndex = shoppingCart.findIndex(c => c.id === itemId);
    
    if (existingCartIndex > -1) {
        shoppingCart[existingCartIndex].qty++;
    } else {
        shoppingCart.push({ ...matchedProduct, qty: 1 });
    }
    renderPOSCart();
}

function updateCartQty(index, offset) {
    shoppingCart[index].qty += offset;
    if (shoppingCart[index].qty <= 0) shoppingCart.splice(index, 1);
    renderPOSCart();
}

function renderPOSCart() {
    const wrapper = document.getElementById('pos-cart-items-wrapper');
    if (!wrapper) return;
    if (shoppingCart.length === 0) {
        wrapper.innerHTML = '<div>Cart is empty.</div>';
        document.getElementById('pos-cart-total').innerText = '0 TZS';
        return;
    }
    
    let total = 0;
    wrapper.innerHTML = shoppingCart.map((item, idx) => {
        const rowTotal = item.price * item.qty;
        total += rowTotal;
        return `
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <td>${item.name} (x${item.qty})</td>
                <td>TZS ${rowTotal.toLocaleString()}</td>
                <button onclick="updateCartQty(${idx}, -1)">-</button>
                <button onclick="updateCartQty(${idx}, 1)">+</button>
            </div>
        `;
    }).join('');
    
    document.getElementById('pos-cart-total').innerText = `TZS ${total.toLocaleString()}`;
}

// Dynamic checkout handler capturing customer and company details
document.getElementById('pos-checkout-btn')?.addEventListener('click', async () => {
    if (shoppingCart.length === 0) return alert("Cart is empty.");
    
    const customer = document.getElementById('pos-customer-name')?.value || "Walk-In Client";
    const company = document.getElementById('pos-company-name')?.value || "Individual";
    const paymentMode = document.getElementById('pos-payment-mode')?.value || "Cash";
    
    try {
        await apiCall('/sales/checkout', {
            method: 'POST',
            body: JSON.stringify({
                customer_name: customer,
                company_name: company,
                payment_mode: paymentMode,
                items: shoppingCart
            })
        });
        
        alert("Transaction recorded successfully!");
        shoppingCart = [];
        renderPOSCart();
    } catch (e) {
        alert("Error during checkout processing: " + e.message);
    }
});

// Debtors and Creditors dynamic UI loader
async function loadLedgerDashboards() {
    try {
        const debtors = await apiCall('/ledgers/debtors');
        const creditors = await apiCall('/ledgers/creditors');
        
        const debtContainer = document.getElementById('debtors-ledger-view');
        if (debtContainer) {
            debtContainer.innerHTML = debtors.map(d => `
                <div style="border-bottom:1px solid #ccc; padding:6px 0;">
                    <strong>${d.customer_name} (${d.company})</strong> - 
                    <span style="color:red;">Owes TZS ${d.amount_owed.toLocaleString()}</span> [${d.status}]
                </div>
            `).join('');
        }

        const credContainer = document.getElementById('creditors-ledger-view');
        if (credContainer) {
            credContainer.innerHTML = creditors.map(c => `
                <div style="border-bottom:1px solid #ccc; padding:6px 0;">
                    <strong>${c.supplier_name} (Inv: ${c.invoice_no})</strong> - 
                    <span style="color:darkorange;">We Owe TZS ${c.amount_due.toLocaleString()}</span> [${c.status}]
                </div>
            `).join('');
        }
    } catch (err) {
        console.error("Ledger rendering matrix initialization failure:", err);
    }
}

async function executeFinancialPLSummary() {
    try {
        const auditData = await apiCall('/reports/full-audit');
        document.getElementById('pl-expenses').innerText = `TZS ${auditData.expenditure_report.total_expenses.toLocaleString()}`;
    } catch (err) {
        console.error("Failed executing execution summaries:", err);
    }
}

function logout() {
    currentToken = null;
    localStorage.removeItem('token');
    window.location.reload();
}