/**
 * Zimbermanne Retail OS Engine - Frontend Client Core
 * Synchronized with Database REST Routing Architecture
 */

// Global State Caches (Synchronized directly with database queries via API calls)
let catalogItemsCache = [];
let currentPOSCart = [];
let activeUserToken = localStorage.getItem('auth_token') || null;
let activeUserRole = localStorage.getItem('user_role') || 'employee';

// --- CORE REST NETWORK HANDLER ---
async function apiCall(endpoint, method = 'GET', body = null) {
    const baseUrl = '/api';
    const headers = {
        'Content-Type': 'application/json'
    };
    
    if (activeUserToken) {
        headers['Authorization'] = `Bearer ${activeUserToken}`;
    }
    
    const config = {
        method,
        headers
    };
    
    if (body && (method === 'POST' || method === 'PUT')) {
        config.body = JSON.stringify(body);
    }
    
    try {
        const response = await fetch(`${baseUrl}${endpoint}`, config);
        
        if (response.status === 401 || response.status === 403) {
            // Token expired or insufficient privileges
            handleLogoutAction();
            throw new Error("Authentication failure. Please log in again.");
        }
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Server responded with status code: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error(`API Call Failure [${method} ${endpoint}]:`, error);
        alert(`Operation Failed: ${error.message}`);
        throw error;
    }
}

// --- APP INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    setupAppViewRouting();
    if (activeUserToken) {
        showDashboardView();
    } else {
        showLoginView();
    }
});

function setupAppViewRouting() {
    // Wire up navigation links
    document.querySelectorAll('[data-target-view]').forEach(navElement => {
        navElement.addEventListener('click', (e) => {
            e.preventDefault();
            const targetView = e.target.getAttribute('data-target-view');
            switchViewContext(targetView);
        });
    });
    
    // Bind login form submission
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', handleLoginSubmit);
    }
    
    // Bind checkout submission
    const checkoutForm = document.getElementById('pos-checkout-action');
    if (checkoutForm) {
        checkoutForm.addEventListener('click', handleCartCheckoutSubmit);
    }
}

function switchViewContext(viewId) {
    document.querySelectorAll('.app-view-panel').forEach(panel => {
        panel.classList.add('hidden-view-state');
    });
    
    const activePanel = document.getElementById(viewId);
    if (activePanel) {
        activePanel.classList.remove('hidden-view-state');
    }
    
    // Lazy-load data depending on view focus
    if (viewId === 'view-dashboard') loadDashboardMetrics();
    if (viewId === 'view-pos') initializePOSModule();
    if (viewId === 'view-debtors') loadDebtorsLedger();
    if (viewId === 'view-creditors') loadCreditorsLedger();
}

// --- AUTHENTICATION MODULE ---
async function handleLoginSubmit(e) {
    e.preventDefault();
    const usernameInput = document.getElementById('login-username').value;
    const passwordInput = document.getElementById('login-password').value;
    const loginButton = document.getElementById('login-submit-btn');
    
    if (loginButton) loginButton.disabled = true;
    
    try {
        // Build URL-encoded form body expected by OAuth2PasswordBearer specification
        const formData = new URLSearchParams();
        formData.append('username', usernameInput);
        formData.append('password', passwordInput);
        
        const response = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });
        
        if (!response.ok) throw new Error("Invalid username or password credentials.");
        
        const tokenData = await response.json();
        activeUserToken = tokenData.access_token;
        localStorage.setItem('auth_token', activeUserToken);
        
        // Fetch current profile metrics to extract organizational access roles safely
        const profile = await apiCall('/users/me');
        activeUserRole = profile.role;
        localStorage.setItem('user_role', activeUserRole);
        
        showDashboardView();
    } catch (err) {
        alert(err.message);
    } finally {
        if (loginButton) loginButton.disabled = false;
    }
}

function handleLogoutAction() {
    activeUserToken = null;
    activeUserRole = 'employee';
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_role');
    showLoginView();
}

function showLoginView() {
    document.getElementById('auth-container').classList.remove('hidden-view-state');
    document.getElementById('main-app-layout').classList.add('hidden-view-state');
}

function showDashboardView() {
    document.getElementById('auth-container').classList.add('hidden-view-state');
    document.getElementById('main-app-layout').classList.remove('hidden-view-state');
    switchViewContext('view-dashboard');
}

// --- DASHBOARD ANALYTICS MODULE ---
async function loadDashboardMetrics() {
    try {
        const summary = await apiCall('/reports/daily-summary');
        
        document.getElementById('dash-earnings').innerText = `TZS ${summary.total_earnings_tzs.toLocaleString()}`;
        document.getElementById('dash-items-sold').innerText = summary.items_sold;
        document.getElementById('dash-low-stock').innerText = summary.low_stock_count;
        
        // Trigger low-stock warning highlighting dynamically
        const lowStockBox = document.getElementById('dash-low-stock-card');
        if (lowStockBox) {
            if (summary.low_stock_count > 0) {
                lowStockBox.classList.add('alert-warning-border');
            } else {
                lowStockBox.classList.remove('alert-warning-border');
            }
        }
    } catch (e) {
        console.error("Failed to load dashboard metrics:", e);
    }
}

// --- POS POINT OF SALE MODULE ---
async function initializePOSModule() {
    try {
        // Query the live relational inventory catalog endpoints directly
        catalogItemsCache = await apiCall('/inventory');
        renderPOSCatalog(catalogItemsCache);
        renderPOSCart();
    } catch (e) {
        console.error("Failed to initialize active catalog profiles:", e);
    }
}

function renderPOSCatalog(items) {
    const catalogContainer = document.getElementById('pos-catalog-grid');
    if (!catalogContainer) return;
    
    catalogContainer.innerHTML = '';
    
    if (items.length === 0) {
        catalogContainer.innerHTML = `<div class="empty-notice">No warehouse inventory records matching criteria.</div>`;
        return;
    }
    
    items.forEach(item => {
        const card = document.createElement('div');
        card.className = `catalog-product-card ${item.quantity <= item.reorder_point ? 'low-stock-dim' : ''}`;
        card.innerHTML = `
            <h4>${item.name}</h4>
            <p class="category-tag">${item.category || 'General Store'}</p>
            <div class="stock-badge">Stock: <strong>${item.quantity} units</strong></div>
            <div class="price-tag">TZS ${item.price.toLocaleString()}</div>
            <button class="add-to-cart-btn" onclick="addProductToCart(${item.id})" ${item.quantity <= 0 ? 'disabled' : ''}>
                ${item.quantity <= 0 ? 'Out of Stock' : 'Add to Receipt'}
            </button>
        `;
        catalogContainer.appendChild(card);
    });
}

window.addProductToCart = function(productId) {
    const itemMatch = catalogItemsCache.find(i => i.id === productId);
    if (!itemMatch) return;
    
    const existingCartItem = currentPOSCart.find(c => c.id === productId);
    
    if (existingCartItem) {
        if (existingCartItem.qty >= itemMatch.quantity) {
            alert(`Inoperable quantity load. Stock capacity reached (${itemMatch.quantity} units available).`);
            return;
        }
        existingCartItem.qty += 1;
    } else {
        currentPOSCart.push({
            id: itemMatch.id,
            name: itemMatch.name,
            price: itemMatch.price,
            qty: 1
        });
    }
    renderPOSCart();
};

window.updateCartQty = function(index, alteration) {
    const cartItem = currentPOSCart[index];
    const itemMatch = catalogItemsCache.find(i => i.id === cartItem.id);
    
    if (!cartItem || !itemMatch) return;
    
    cartItem.qty += alteration;
    
    if (cartItem.qty <= 0) {
        currentPOSCart.splice(index, 1);
    } else if (cartItem.qty > itemMatch.quantity) {
        alert(`Cannot exceed stock limits. Only ${itemMatch.quantity} units available in database store.`);
        cartItem.qty = itemMatch.quantity;
    }
    
    renderPOSCart();
};

function renderPOSCart() {
    const cartTableBody = document.getElementById('pos-cart-tbody');
    const invoiceTotalLabel = document.getElementById('pos-invoice-total');
    if (!cartTableBody || !invoiceTotalLabel) return;
    
    cartTableBody.innerHTML = '';
    let runningTotal = 0;
    
    if (currentPOSCart.length === 0) {
        cartTableBody.innerHTML = `<tr><td colspan="4" class="text-center-muted">Shopping invoice is completely empty.</td></tr>`;
        invoiceTotalLabel.innerText = "TZS 0";
        return;
    }
    
    currentPOSCart.forEach((item, idx) => {
        const rowTotal = item.price * item.qty;
        runningTotal += rowTotal;
        
        // REPAIRED: Clean, valid, accessible standard HTML table layout row string injections
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><strong>${item.name}</strong></td>
            <td class="text-right">TZS ${item.price.toLocaleString()}</td>
            <td class="text-center">
                <div class="quantity-counter-controls">
                    <button class="qty-control-btn" onclick="updateCartQty(${idx}, -1)">-</button>
                    <span class="qty-count-display">${item.qty}</span>
                    <button class="qty-control-btn" onclick="updateCartQty(${idx}, 1)">+</button>
                </div>
            </td>
            <td class="text-right font-semibold">TZS ${rowTotal.toLocaleString()}</td>
        `;
        cartTableBody.appendChild(row);
    });
    
    invoiceTotalLabel.innerText = `TZS ${runningTotal.toLocaleString()}`;
}

async function handleCartCheckoutSubmit() {
    if (currentPOSCart.length === 0) {
        alert("Cannot execute checkout processing over empty shopping carts.");
        return;
    }
    
    const checkoutButton = document.getElementById('pos-checkout-action');
    const customerName = document.getElementById('pos-customer-name').value.trim();
    const companyName = document.getElementById('pos-company-name').value.trim();
    const paymentMode = document.getElementById('pos-payment-mode').value;
    
    const checkoutPayload = {
        customer_name: customerName || "Walk-In Customer",
        company_name: companyName || "Individual",
        payment_mode: paymentMode,
        items: currentPOSCart
    };
    
    // Prevent double-clicking issues during connection latency
    if (checkoutButton) checkoutButton.disabled = true;
    
    try {
        const orderReceipt = await apiCall('/sales/checkout', 'POST', checkoutPayload);
        alert(`Transaction Verified! Total Receipt Value: TZS ${orderReceipt.invoice_total.toLocaleString()} via Mode: ${orderReceipt.mode}`);
        
        // Reset inputs and fields on successful database deduction entries
        currentPOSCart = [];
        document.getElementById('pos-customer-name').value = '';
        document.getElementById('pos-company-name').value = '';
        renderPOSCart();
        
        // Refresh catalog window to correctly display decremented balances
        initializePOSModule();
    } catch (e) {
        console.error("Order workflow execution crashed:", e);
    } finally {
        if (checkoutButton) checkoutButton.disabled = false;
    }
}

// --- LEDGERS MODULE (DEBTORS & CREDITORS) ---
async function loadDebtorsLedger() {
    const container = document.getElementById('debtors-list-tbody');
    if (!container) return;
    
    container.innerHTML = `<tr><td colspan="5" class="text-center-muted">Fetching records...</td></tr>`;
    
    try {
        const data = await apiCall('/ledgers/debtors');
        container.innerHTML = '';
        
        if (data.length === 0) {
            container.innerHTML = `<tr><td colspan="5" class="text-center-muted">No pending customer debts (Deni) reported.</td></tr>`;
            return;
        }
        
        data.forEach(debtor => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${debtor.customer_name}</strong></td>
                <td>${debtor.company}</td>
                <td class="amount-alert-red font-semibold">TZS ${debtor.amount_owed.toLocaleString()}</td>
                <td><span class="date-stamp">${debtor.date || 'N/A'}</span></td>
                <td>
                    <button class="action-pay-btn" onclick="executeDebtorPaymentPrompt(${debtor.id}, ${debtor.amount_owed})">Record Payment</button>
                </td>
            `;
            container.appendChild(tr);
        });
    } catch (e) {
        container.innerHTML = `<tr><td colspan="5" class="text-center-muted data-error">Error loading debtor profiles.</td></tr>`;
    }
}

window.executeDebtorPaymentPrompt = async function(debtorId, totalOwed) {
    const inputAmount = prompt(`Enter customer collection payment processing amount (Max: TZS ${totalOwed.toLocaleString()}):`);
    if (inputAmount === null) return;
    
    const cleanAmount = parseFloat(inputAmount.replace(/,/g, ''));
    if (isNaN(cleanAmount) || cleanAmount <= 0 || cleanAmount > totalOwed) {
        alert("Invalid input value processing parameter context. Please confirm numbers.");
        return;
    }
    
    try {
        await apiCall(`/ledgers/debtors/pay/${debtorId}`, 'POST', { amount: cleanAmount });
        alert("Payment logged and database updated successfully!");
        loadDebtorsLedger();
    } catch (e) {
        console.error("Failed to commit ledger clearing adjustment rows:", e);
    }
};

async function loadCreditorsLedger() {
    const container = document.getElementById('creditors-list-tbody');
    if (!container) return;
    
    container.innerHTML = `<tr><td colspan="5" class="text-center-muted">Fetching records...</td></tr>`;
    
    try {
        const data = await apiCall('/ledgers/creditors');
        container.innerHTML = '';
        
        if (data.length === 0) {
            container.innerHTML = `<tr><td colspan="5" class="text-center-muted">No outstanding supplier balances (Madeni ya Wauzaji).</td></tr>`;
            return;
        }
        
        data.forEach(creditor => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${creditor.supplier_name}</strong></td>
                <td>${creditor.invoice_no}</td>
                <td class="amount-alert-orange font-semibold">TZS ${creditor.amount_due.toLocaleString()}</td>
                <td><span class="date-stamp">${creditor.date || 'N/A'}</span></td>
                <td><span class="status-badge state-${creditor.status.toLowerCase()}">${creditor.status}</span></td>
            `;
            container.appendChild(tr);
        });
    } catch (e) {
        container.innerHTML = `<tr><td colspan="5" class="text-center-muted data-error">Error loading supplier structures.</td></tr>`;
    }
}