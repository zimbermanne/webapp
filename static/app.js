// Base API Route Setting for Cloud & Container Isolation Environments
const API_BASE_URL = '/api';

// Core State Engine Store
let currentToken = localStorage.getItem('token');
let currentUser = null;
let currentProfileName = 'Zimbermanne Hardware';
let catalogItemsCache = [];
let shoppingCart = [];

// DOM Element Handlers
const loginScreen = document.getElementById('login-screen');
const dashboardScreen = document.getElementById('dashboard-screen');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');

// Universal API Data Fetch Pipeline 
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
        if (response.status === 401) {
            logout();
            throw new Error('Unauthorized Session Access.');
        }
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Endpoint response breakdown.');
        return data;
    } catch (error) {
        console.error(`API Error Pipeline Execution Failure [${endpoint}]:`, error);
        throw error;
    }
}

// Global System Routing Layouts
function showScreen(screen) {
    document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
    screen.classList.remove('hidden');
}

// Sidebar View Section Changer
document.querySelectorAll('.nav-links a[data-section]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const section = link.dataset.section;
        
        document.querySelectorAll('.nav-links a').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        
        document.querySelectorAll('.content-section').forEach(s => s.classList.add('hidden'));
        document.getElementById(`${section}-section`).classList.remove('hidden');
        
        document.getElementById('section-title').textContent = link.textContent.substring(3);
        
        // Contextual Engine Dispatchers
        switch(section) {
            case 'dashboard': loadDashboardMetrics(); break;
            case 'pos': initializePOSModule(); break;
            case 'inventory': loadInventoryData(); break;
            case 'reports': executeFinancialPLSummary(); break;
        }
    });
});

// Authentication System Functions
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const profileSelect = document.getElementById('login-profile');
    currentProfileName = profileSelect.options[profileSelect.selectedIndex].text;
    document.getElementById('current-profile-label').textContent = currentProfileName;

    const usernameInput = document.getElementById('login-username').value;
    const passwordInput = document.getElementById('login-password').value;

    try {
        const formData = new URLSearchParams();
        formData.append('username', usernameInput);
        formData.append('password', passwordInput);

        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });

        if (!response.ok) throw new Error('Invalid system credentials verification.');
        
        const data = await response.json();
        currentToken = data.access_token;
        localStorage.setItem('token', currentToken);
        
        await fetchUserMetadata();
        showScreen(dashboardScreen);
        loadDashboardMetrics();
    } catch (err) {
        loginError.textContent = err.message;
        loginError.classList.remove('hidden');
    }
});

async function fetchUserMetadata() {
    try {
        currentUser = await apiCall('/auth/me');
        document.getElementById('user-display-name').textContent = currentUser.username;
        document.getElementById('user-display-role').textContent = currentUser.role;
        document.getElementById('user-avatar').textContent = currentUser.username.substring(0,2).toUpperCase();
        
        // Handle view layout privileges by role
        if (currentUser.role === 'admin' || currentUser.role === 'root') {
            document.getElementById('users-link').style.display = 'block';
            document.getElementById('activity-link').style.display = 'block';
            document.getElementById('admin-group-title').style.display = 'block';
        }
    } catch (e) {
        console.error("Failed to load user profile variables.");
    }
}

// Dashboard Summary Counters Loader
async function loadDashboardMetrics() {
    try {
        const metrics = await apiCall('/inventory/metrics');
        const summary = await apiCall('/reports/daily-summary');
        
        document.getElementById('kpi-today-sales').innerText = `TZS ${summary.total_earnings_tzs.toLocaleString()}`;
        document.getElementById('kpi-tx-count').innerText = `${summary.items_sold} sold`;
        document.getElementById('kpi-total-items').innerText = `${metrics.total_items} items`;
        document.getElementById('kpi-low-stock').innerText = `${metrics.low_stock_items} items`;
        document.getElementById('kpi-debtors').innerText = `TZS 55,000`; 
        document.getElementById('kpi-net-profit').innerText = `TZS ${metrics.total_value.toLocaleString()}`;
        
        // Fetch low-stock items cache and build alerts row
        const inventory = await apiCall('/inventory/');
        const lowStockBody = document.getElementById('dashboard-low-stock-table');
        lowStockBody.innerHTML = inventory.filter(i => i.quantity <= i.reorder_point).map(item => `
            <tr class="text-danger">
                <td><strong>${item.name}</strong></td>
                <td>${item.quantity}</td>
                <td>TZS ${item.price.toLocaleString()}</td>
                <td>Supplier Hook</td>
            </tr>
        `).join('') || '<tr><td colspan="4">All stock limits are currently healthy.</td></tr>';
    } catch (err) {
        console.error("Metrics engine reporting failed.");
    }
}

// POS Sales Operations
async function initializePOSModule() {
    try {
        catalogItemsCache = await apiCall('/inventory/');
        renderPOSCatalog(catalogItemsCache);
        renderPOSCart();
    } catch (e) {
        console.error("Failed loading inventory catalog context.");
    }
}

function renderPOSCatalog(items) {
    const grid = document.getElementById('pos-grid-container');
    grid.innerHTML = items.map(item => `
        <div class="product-tap-card" onclick="addProductToCart(${item.id})">
            <h4>${item.name}</h4>
            <span>Qty: ${item.quantity}</span>
            <span class="text-success font-weight-bold">TZS ${item.price.toLocaleString()}</span>
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

// Render POS Cart Wrapper Element Layouts
function renderPOSCart() {
    const wrapper = document.getElementById('pos-cart-items-wrapper');
    if (shoppingCart.length === 0) {
        wrapper.innerHTML = '<div class="empty-state-text">Cart is empty. Tap products to add.</div>';
        document.getElementById('pos-cart-total').innerText = '0 TZS';
        return;
    }
    
    let total = 0;
    wrapper.innerHTML = shoppingCart.map((item, idx) => {
        const rowTotal = item.price * item.qty;
        total += rowTotal;
        return `
            <div class="cart-item-row">
                <div>
                    <div><strong>${item.name}</strong></div>
                    <div class="text-muted" style="font-size:12px;">TZS ${item.price.toLocaleString()}</div>
                </div>
                <div class="cart-qty-controls">
                    <button type="button" onclick="updateCartQty(${idx}, -1)">-</button>
                    <span class="mono-text" style="padding:0 8px;">${item.qty}</span>
                    <button type="button" onclick="updateCartQty(${idx}, 1)">+</button>
                </div>
                <div class="mono-text">TZS ${rowTotal.toLocaleString()}</div>
            </div>
        `;
    }).join('');
    
    document.getElementById('pos-cart-total').innerText = `TZS ${total.toLocaleString()}`;
}

document.getElementById('pos-checkout-btn').addEventListener('click', async () => {
    if (shoppingCart.length === 0) return alert("Cart is empty.");
    const customer = document.getElementById('pos-customer-name').value;
    const paymentMode = document.getElementById('pos-payment-mode').value;
    
    if (paymentMode === 'Deni' && !customer) {
        return alert("Error: A customer identifier name is required to process Credit (Deni) sales allocations.");
    }
    
    try {
        for (let product of shoppingCart) {
            await apiCall('/sales/', {
                method: 'POST',
                body: JSON.stringify({
                    item_id: product.id,
                    quantity: product.qty,
                    unit_price: product.price,
                    customer_name: customer || "Walk-In Customer"
                })
            });
        }
        alert("Transaction complete.");
        shoppingCart = [];
        document.getElementById('pos-customer-name').value = '';
        initializePOSModule();
    } catch (e) {
        alert("Sale registration error: " + e.message);
    }
});

// Financial Management Engine (P&L Rendering Logic Connected to ReportGenerator)
async function executeFinancialPLSummary() {
    try {
        const auditData = await apiCall('/reports/full-audit');
        const expenditureReport = auditData.expenditure_report;
        
        // Dynamically update the expenses field with real tracking info from expenses.json
        document.getElementById('pl-expenses').innerText = `TZS ${expenditureReport.total_expenses.toLocaleString()}`;
        
        console.log("Live background data synced successfully at:", auditData.generated_at);
    } catch (err) {
        console.error("Failed executing live unified P&L summary calculations:", err);
    }
}

// Live Internal Tracking System Clock Core Execution
setInterval(() => {
    document.getElementById('live-clock').innerText = new Date().toLocaleTimeString();
}, 1000);

function logout() {
    currentToken = null;
    currentUser = null;
    localStorage.removeItem('token');
    window.location.reload();
}

document.getElementById('logout-btn').addEventListener('click', logout);

// Initialize application state matching parameters
if (currentToken) {
    fetchUserMetadata().then(() => {
        showScreen(dashboardScreen);
        loadDashboardMetrics();
    });
} else {
    showScreen(loginScreen);
}