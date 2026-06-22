// API Configuration
const API_BASE_URL = 'http://localhost:8000/api';

// State Management
let currentToken = localStorage.getItem('token');
let currentUser = null;

// DOM Elements
const loginScreen = document.getElementById('login-screen');
const dashboardScreen = document.getElementById('dashboard-screen');
const loginForm = document.getElementById('login-form');
const loginError = document.getElementById('login-error');

// Utility Functions
function showScreen(screen) {
    document.querySelectorAll('.screen').forEach(s => s.classList.add('hidden'));
    screen.classList.remove('hidden');
}

function showError(message) {
    loginError.textContent = message;
    loginError.classList.remove('hidden');
    setTimeout(() => {
        loginError.classList.add('hidden');
    }, 5000);
}

async function apiCall(endpoint, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
    };

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
            throw new Error('Unauthorized');
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'API call failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API call error:', error);
        throw error;
    }
}

// Authentication Functions
async function login(username, password) {
    try {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error('Invalid credentials');
        }

        const data = await response.json();
        currentToken = data.access_token;
        localStorage.setItem('token', currentToken);
        
        await loadCurrentUser();
        showScreen(dashboardScreen);
        initializeDashboard();
    } catch (error) {
        showError(error.message);
    }
}

async function loadCurrentUser() {
    try {
        currentUser = await apiCall('/auth/me');
        updateUIForUserRole();
    } catch (error) {
        console.error('Failed to load current user:', error);
    }
}

function logout() {
    currentToken = null;
    currentUser = null;
    localStorage.removeItem('token');
    showScreen(loginScreen);
}

function updateUIForUserRole() {
    if (currentUser && (currentUser.role === 'admin' || currentUser.role === 'manager')) {
        document.getElementById('users-link').style.display = 'block';
        document.getElementById('activity-link').style.display = 'block';
    }
    
    if (currentUser && currentUser.role === 'admin') {
        document.getElementById('backup-link').style.display = 'block';
    }
}

// Dashboard Functions
function initializeDashboard() {
    loadInventory();
    loadSales();
    loadPurchases();
    loadExpenses();
    loadReports();
    
    if (currentUser && (currentUser.role === 'admin' || currentUser.role === 'manager')) {
        loadUsers();
        loadActivityLogs();
    }
    
    if (currentUser && currentUser.role === 'admin') {
        loadBackups();
    }
}

// Navigation
document.querySelectorAll('.nav-links a[data-section]').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const section = link.dataset.section;
        
        // Update active link
        document.querySelectorAll('.nav-links a').forEach(l => l.classList.remove('active'));
        link.classList.add('active');
        
        // Show corresponding section
        document.querySelectorAll('.content-section').forEach(s => s.classList.add('hidden'));
        document.getElementById(`${section}-section`).classList.remove('hidden');
        
        // Load data for the section
        switch(section) {
            case 'inventory': loadInventory(); break;
            case 'sales': loadSales(); break;
            case 'purchases': loadPurchases(); break;
            case 'expenses': loadExpenses(); break;
            case 'reports': loadReports(); break;
            case 'users': loadUsers(); break;
            case 'activity': loadActivityLogs(); break;
            case 'backup': loadBackups(); break;
        }
    });
});

// Inventory Functions
async function loadInventory() {
    try {
        const items = await apiCall('/inventory/');
        renderInventoryTable(items);
        
        const metrics = await apiCall('/inventory/metrics');
        renderInventoryMetrics(metrics);
    } catch (error) {
        console.error('Failed to load inventory:', error);
    }
}

function renderInventoryTable(items) {
    const container = document.getElementById('inventory-table-container');
    
    if (items.length === 0) {
        container.innerHTML = '<p>No inventory items found.</p>';
        return;
    }
    
    let html = `
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Name</th>
                        <th>Quantity</th>
                        <th>Price</th>
                        <th>Category</th>
                        <th>Reorder Point</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    items.forEach(item => {
        html += `
            <tr>
                <td>${item.id}</td>
                <td>${item.name}</td>
                <td>${item.quantity}</td>
                <td>TZS ${item.price.toLocaleString()}</td>
                <td>${item.category || '-'}</td>
                <td>${item.reorder_point}</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="editInventoryItem(${item.id})">Edit</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteInventoryItem(${item.id})">Delete</button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function renderInventoryMetrics(metrics) {
    const container = document.getElementById('inventory-metrics');
    container.innerHTML = `
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Total Items</h3>
                <div class="value">${metrics.total_items}</div>
            </div>
            <div class="metric-card">
                <h3>Total Value</h3>
                <div class="value">TZS ${metrics.total_value.toLocaleString()}</div>
            </div>
            <div class="metric-card">
                <h3>Average Price</h3>
                <div class="value">TZS ${metrics.average_price.toLocaleString()}</div>
            </div>
            <div class="metric-card">
                <h3>Low Stock Items</h3>
                <div class="value">${metrics.low_stock_items}</div>
            </div>
        </div>
    `;
}

// Sales Functions
async function loadSales() {
    try {
        const sales = await apiCall('/sales/');
        renderSalesTable(sales);
        
        const summary = await apiCall('/sales/stats/summary');
        renderSalesSummary(summary);
    } catch (error) {
        console.error('Failed to load sales:', error);
    }
}

function renderSalesTable(sales) {
    const container = document.getElementById('sales-table-container');
    
    if (sales.length === 0) {
        container.innerHTML = '<p>No sales found.</p>';
        return;
    }
    
    let html = `
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Date</th>
                        <th>Item ID</th>
                        <th>Quantity</th>
                        <th>Unit Price</th>
                        <th>Total</th>
                        <th>Customer</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    sales.forEach(sale => {
        html += `
            <tr>
                <td>${sale.id}</td>
                <td>${new Date(sale.sale_date).toLocaleDateString()}</td>
                <td>${sale.item_id}</td>
                <td>${sale.quantity}</td>
                <td>TZS ${sale.unit_price.toLocaleString()}</td>
                <td>TZS ${sale.total_amount.toLocaleString()}</td>
                <td>${sale.customer_name || '-'}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function renderSalesSummary(summary) {
    const container = document.getElementById('sales-summary');
    container.innerHTML = `
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Total Sales</h3>
                <div class="value">${summary.total_sales}</div>
            </div>
            <div class="metric-card">
                <h3>Total Revenue</h3>
                <div class="value">TZS ${summary.total_revenue.toLocaleString()}</div>
            </div>
            <div class="metric-card">
                <h3>Quantity Sold</h3>
                <div class="value">${summary.total_quantity_sold}</div>
            </div>
            <div class="metric-card">
                <h3>Avg Order Value</h3>
                <div class="value">TZS ${summary.average_order_value.toLocaleString()}</div>
            </div>
        </div>
    `;
}

// Purchases Functions
async function loadPurchases() {
    try {
        const purchases = await apiCall('/purchases/');
        renderPurchasesTable(purchases);
        
        const summary = await apiCall('/purchases/stats/summary');
        renderPurchasesSummary(summary);
    } catch (error) {
        console.error('Failed to load purchases:', error);
    }
}

function renderPurchasesTable(purchases) {
    const container = document.getElementById('purchases-table-container');
    
    if (purchases.length === 0) {
        container.innerHTML = '<p>No purchases found.</p>';
        return;
    }
    
    let html = `
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Date</th>
                        <th>Item ID</th>
                        <th>Quantity</th>
                        <th>Unit Cost</th>
                        <th>Total Cost</th>
                        <th>Supplier</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    purchases.forEach(purchase => {
        html += `
            <tr>
                <td>${purchase.id}</td>
                <td>${new Date(purchase.purchase_date).toLocaleDateString()}</td>
                <td>${purchase.item_id}</td>
                <td>${purchase.quantity}</td>
                <td>TZS ${purchase.unit_cost.toLocaleString()}</td>
                <td>TZS ${purchase.total_cost.toLocaleString()}</td>
                <td>${purchase.supplier_name || '-'}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function renderPurchasesSummary(summary) {
    const container = document.getElementById('purchases-summary');
    container.innerHTML = `
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Total Purchases</h3>
                <div class="value">${summary.total_purchases}</div>
            </div>
            <div class="metric-card">
                <h3>Total Cost</h3>
                <div class="value">TZS ${summary.total_cost.toLocaleString()}</div>
            </div>
            <div class="metric-card">
                <h3>Quantity Purchased</h3>
                <div class="value">${summary.total_quantity_purchased}</div>
            </div>
            <div class="metric-card">
                <h3>Avg Order Value</h3>
                <div class="value">TZS ${summary.average_order_value.toLocaleString()}</div>
            </div>
        </div>
    `;
}

// Expenses Functions
async function loadExpenses() {
    try {
        const expenses = await apiCall('/expenses/');
        renderExpensesTable(expenses);
        
        const summary = await apiCall('/expenses/stats/summary');
        renderExpensesSummary(summary);
    } catch (error) {
        console.error('Failed to load expenses:', error);
    }
}

function renderExpensesTable(expenses) {
    const container = document.getElementById('expenses-table-container');
    
    if (expenses.length === 0) {
        container.innerHTML = '<p>No expenses found.</p>';
        return;
    }
    
    let html = `
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Date</th>
                        <th>Category</th>
                        <th>Amount</th>
                        <th>Description</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    expenses.forEach(expense => {
        html += `
            <tr>
                <td>${expense.id}</td>
                <td>${new Date(expense.expense_date).toLocaleDateString()}</td>
                <td>${expense.category}</td>
                <td>TZS ${expense.amount.toLocaleString()}</td>
                <td>${expense.description || '-'}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function renderExpensesSummary(summary) {
    const container = document.getElementById('expenses-summary');
    container.innerHTML = `
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Total Expenses</h3>
                <div class="value">${summary.total_expenses}</div>
            </div>
            <div class="metric-card">
                <h3>Total Amount</h3>
                <div class="value">TZS ${summary.total_amount.toLocaleString()}</div>
            </div>
        </div>
    `;
}

// Reports Functions
async function loadReports() {
    try {
        const financialSummary = await apiCall('/reports/financial-summary');
        renderFinancialSummary(financialSummary);
        
        const profitLoss = await apiCall('/reports/profit-loss');
        renderProfitLoss(profitLoss);
    } catch (error) {
        console.error('Failed to load reports:', error);
    }
}

function renderFinancialSummary(summary) {
    const container = document.getElementById('financial-summary');
    const profitClass = summary.profit_loss >= 0 ? 'text-success' : 'text-danger';
    
    container.innerHTML = `
        <h3>Financial Summary</h3>
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Total Sales</h3>
                <div class="value">TZS ${summary.total_sales.toLocaleString()}</div>
            </div>
            <div class="metric-card">
                <h3>Total Purchases</h3>
                <div class="value">TZS ${summary.total_purchases.toLocaleString()}</div>
            </div>
            <div class="metric-card">
                <h3>Total Expenses</h3>
                <div class="value">TZS ${summary.total_expenses.toLocaleString()}</div>
            </div>
            <div class="metric-card">
                <h3>Profit/Loss</h3>
                <div class="value ${profitClass}">TZS ${summary.profit_loss.toLocaleString()}</div>
            </div>
        </div>
    `;
}

function renderProfitLoss(report) {
    const container = document.getElementById('profit-loss-report');
    
    container.innerHTML = `
        <h3>Profit & Loss Report</h3>
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Gross Profit</h3>
                <div class="value">TZS ${report.profit_summary.gross_profit.toLocaleString()}</div>
            </div>
            <div class="metric-card">
                <h3>Net Profit</h3>
                <div class="value">TZS ${report.profit_summary.net_profit.toLocaleString()}</div>
            </div>
            <div class="metric-card">
                <h3>Profit Margin</h3>
                <div class="value">${report.profit_summary.profit_margin.toFixed(2)}%</div>
            </div>
        </div>
    `;
}

// Users Functions
async function loadUsers() {
    try {
        const users = await apiCall('/users/');
        renderUsersTable(users);
    } catch (error) {
        console.error('Failed to load users:', error);
    }
}

function renderUsersTable(users) {
    const container = document.getElementById('users-table-container');
    
    if (users.length === 0) {
        container.innerHTML = '<p>No users found.</p>';
        return;
    }
    
    let html = `
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Role</th>
                        <th>Active</th>
                        <th>Created</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    users.forEach(user => {
        html += `
            <tr>
                <td>${user.id}</td>
                <td>${user.username}</td>
                <td>${user.email || '-'}</td>
                <td>${user.role}</td>
                <td>${user.is_active ? 'Yes' : 'No'}</td>
                <td>${new Date(user.created_at).toLocaleDateString()}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// Activity Logs Functions
async function loadActivityLogs() {
    try {
        const logs = await apiCall('/activity/');
        renderActivityTable(logs);
        
        const stats = await apiCall('/activity/stats');
        renderActivityStats(stats);
    } catch (error) {
        console.error('Failed to load activity logs:', error);
    }
}

function renderActivityTable(logs) {
    const container = document.getElementById('activity-table-container');
    
    if (logs.length === 0) {
        container.innerHTML = '<p>No activity logs found.</p>';
        return;
    }
    
    let html = `
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Timestamp</th>
                        <th>User</th>
                        <th>Action</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    logs.forEach(log => {
        html += `
            <tr>
                <td>${log.id}</td>
                <td>${new Date(log.timestamp).toLocaleString()}</td>
                <td>${log.user}</td>
                <td>${log.action}</td>
                <td>${log.details || '-'}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

function renderActivityStats(stats) {
    const container = document.getElementById('activity-stats');
    container.innerHTML = `
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>Total Logs</h3>
                <div class="value">${stats.total_logs}</div>
            </div>
        </div>
    `;
}

// Backup Functions
async function loadBackups() {
    try {
        const backups = await apiCall('/backup/list');
        renderBackupsList(backups);
    } catch (error) {
        console.error('Failed to load backups:', error);
    }
}

function renderBackupsList(backups) {
    const container = document.getElementById('backups-list');
    
    if (backups.length === 0) {
        container.innerHTML = '<p>No backups found.</p>';
        return;
    }
    
    let html = `
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Filename</th>
                        <th>Created</th>
                        <th>Size</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    backups.forEach(backup => {
        html += `
            <tr>
                <td>${backup.filename}</td>
                <td>${new Date(backup.created_at).toLocaleString()}</td>
                <td>${(backup.size / 1024).toFixed(2)} KB</td>
                <td>
                    <button class="btn btn-secondary btn-sm" onclick="restoreBackup('${backup.filename}')">Restore</button>
                    <button class="btn btn-danger btn-sm" onclick="deleteBackup('${backup.filename}')">Delete</button>
                </td>
            </tr>
        `;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// Modal Functions
const modal = document.getElementById('modal');
const modalTitle = document.getElementById('modal-title');
const modalBody = document.getElementById('modal-body');
const closeBtn = document.querySelector('.close-btn');

function openModal(title, content) {
    modalTitle.textContent = title;
    modalBody.innerHTML = content;
    modal.classList.remove('hidden');
}

function closeModal() {
    modal.classList.add('hidden');
}

closeBtn.addEventListener('click', closeModal);

// Event Listeners
loginForm.addEventListener('submit', (e) => {
    e.preventDefault();
    const username = document.getElementById('login-username').value;
    const password = document.getElementById('login-password').value;
    login(username, password);
});

document.getElementById('logout-btn').addEventListener('click', logout);

document.getElementById('add-item-btn').addEventListener('click', () => {
    openModal('Add Inventory Item', `
        <form class="modal-form" id="add-item-form">
            <div class="form-group">
                <label>Name:</label>
                <input type="text" id="item-name" required>
            </div>
            <div class="form-group">
                <label>Quantity:</label>
                <input type="number" id="item-quantity" required>
            </div>
            <div class="form-group">
                <label>Price:</label>
                <input type="number" id="item-price" step="0.01" required>
            </div>
            <div class="form-group">
                <label>Category:</label>
                <input type="text" id="item-category">
            </div>
            <div class="form-group">
                <label>Reorder Point:</label>
                <input type="number" id="item-reorder-point" value="10">
            </div>
            <div class="modal-form-buttons">
                <button type="submit" class="btn btn-primary">Add Item</button>
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
            </div>
        </form>
    `);
    
    document.getElementById('add-item-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const itemData = {
            name: document.getElementById('item-name').value,
            quantity: parseInt(document.getElementById('item-quantity').value),
            price: parseFloat(document.getElementById('item-price').value),
            category: document.getElementById('item-category').value || null,
            reorder_point: parseInt(document.getElementById('item-reorder-point').value)
        };
        
        try {
            await apiCall('/inventory/', {
                method: 'POST',
                body: JSON.stringify(itemData)
            });
            closeModal();
            loadInventory();
        } catch (error) {
            alert('Failed to add item: ' + error.message);
        }
    });
});

document.getElementById('add-sale-btn').addEventListener('click', async () => {
    try {
        const inventory = await apiCall('/inventory/');
        const itemOptions = inventory.map(item => 
            `<option value="${item.id}">${item.name} (Qty: ${item.quantity}, Price: TZS ${item.price})</option>`
        ).join('');
        
        openModal('New Sale', `
            <form class="modal-form" id="add-sale-form">
                <div class="form-group">
                    <label>Item:</label>
                    <select id="sale-item-id" required>${itemOptions}</select>
                </div>
                <div class="form-group">
                    <label>Quantity:</label>
                    <input type="number" id="sale-quantity" required>
                </div>
                <div class="form-group">
                    <label>Unit Price:</label>
                    <input type="number" id="sale-unit-price" step="0.01" required>
                </div>
                <div class="form-group">
                    <label>Customer Name:</label>
                    <input type="text" id="sale-customer-name">
                </div>
                <div class="modal-form-buttons">
                    <button type="submit" class="btn btn-primary">Create Sale</button>
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            </form>
        `);
        
        document.getElementById('add-sale-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const saleData = {
                item_id: parseInt(document.getElementById('sale-item-id').value),
                quantity: parseInt(document.getElementById('sale-quantity').value),
                unit_price: parseFloat(document.getElementById('sale-unit-price').value),
                customer_name: document.getElementById('sale-customer-name').value || null
            };
            
            try {
                await apiCall('/sales/', {
                    method: 'POST',
                    body: JSON.stringify(saleData)
                });
                closeModal();
                loadSales();
            } catch (error) {
                alert('Failed to create sale: ' + error.message);
            }
        });
    } catch (error) {
        alert('Failed to load inventory: ' + error.message);
    }
});

document.getElementById('add-purchase-btn').addEventListener('click', async () => {
    try {
        const inventory = await apiCall('/inventory/');
        const itemOptions = inventory.map(item => 
            `<option value="${item.id}">${item.name}</option>`
        ).join('');
        
        openModal('New Purchase', `
            <form class="modal-form" id="add-purchase-form">
                <div class="form-group">
                    <label>Item:</label>
                    <select id="purchase-item-id" required>${itemOptions}</select>
                </div>
                <div class="form-group">
                    <label>Quantity:</label>
                    <input type="number" id="purchase-quantity" required>
                </div>
                <div class="form-group">
                    <label>Unit Cost:</label>
                    <input type="number" id="purchase-unit-cost" step="0.01" required>
                </div>
                <div class="form-group">
                    <label>Supplier Name:</label>
                    <input type="text" id="purchase-supplier-name">
                </div>
                <div class="modal-form-buttons">
                    <button type="submit" class="btn btn-primary">Create Purchase</button>
                    <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                </div>
            </form>
        `);
        
        document.getElementById('add-purchase-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const purchaseData = {
                item_id: parseInt(document.getElementById('purchase-item-id').value),
                quantity: parseInt(document.getElementById('purchase-quantity').value),
                unit_cost: parseFloat(document.getElementById('purchase-unit-cost').value),
                supplier_name: document.getElementById('purchase-supplier-name').value || null
            };
            
            try {
                await apiCall('/purchases/', {
                    method: 'POST',
                    body: JSON.stringify(purchaseData)
                });
                closeModal();
                loadPurchases();
            } catch (error) {
                alert('Failed to create purchase: ' + error.message);
            }
        });
    } catch (error) {
        alert('Failed to load inventory: ' + error.message);
    }
});

document.getElementById('add-expense-btn').addEventListener('click', () => {
    openModal('Add Expense', `
        <form class="modal-form" id="add-expense-form">
            <div class="form-group">
                <label>Category:</label>
                <input type="text" id="expense-category" required>
            </div>
            <div class="form-group">
                <label>Amount:</label>
                <input type="number" id="expense-amount" step="0.01" required>
            </div>
            <div class="form-group">
                <label>Description:</label>
                <textarea id="expense-description"></textarea>
            </div>
            <div class="modal-form-buttons">
                <button type="submit" class="btn btn-primary">Add Expense</button>
                <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
            </div>
        </form>
    `);
    
    document.getElementById('add-expense-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const expenseData = {
            category: document.getElementById('expense-category').value,
            amount: parseFloat(document.getElementById('expense-amount').value),
            description: document.getElementById('expense-description').value || null
        };
        
        try {
            await apiCall('/expenses/', {
                method: 'POST',
                body: JSON.stringify(expenseData)
            });
            closeModal();
            loadExpenses();
        } catch (error) {
            alert('Failed to add expense: ' + error.message);
        }
    });
});

// Refresh buttons
document.getElementById('refresh-inventory-btn').addEventListener('click', loadInventory);
document.getElementById('refresh-sales-btn').addEventListener('click', loadSales);
document.getElementById('refresh-purchases-btn').addEventListener('click', loadPurchases);
document.getElementById('refresh-expenses-btn').addEventListener('click', loadExpenses);
document.getElementById('refresh-reports-btn').addEventListener('click', loadReports);
document.getElementById('refresh-users-btn').addEventListener('click', loadUsers);
document.getElementById('refresh-activity-btn').addEventListener('click', loadActivityLogs);
document.getElementById('refresh-backups-btn').addEventListener('click', loadBackups);

// Backup operations
document.getElementById('create-backup-btn').addEventListener('click', async () => {
    try {
        await apiCall('/backup/create', { method: 'POST' });
        alert('Backup created successfully');
        loadBackups();
    } catch (error) {
        alert('Failed to create backup: ' + error.message);
    }
});

async function restoreBackup(filename) {
    if (confirm(`Are you sure you want to restore backup ${filename}?`)) {
        try {
            await apiCall(`/backup/restore/${filename}`, { method: 'POST' });
            alert('Backup restored successfully');
        } catch (error) {
            alert('Failed to restore backup: ' + error.message);
        }
    }
}

async function deleteBackup(filename) {
    if (confirm(`Are you sure you want to delete backup ${filename}?`)) {
        try {
            await apiCall(`/backup/${filename}`, { method: 'DELETE' });
            alert('Backup deleted successfully');
            loadBackups();
        } catch (error) {
            alert('Failed to delete backup: ' + error.message);
        }
    }
}

// Initialize
if (currentToken) {
    loadCurrentUser().then(() => {
        if (currentUser) {
            showScreen(dashboardScreen);
            initializeDashboard();
        } else {
            showScreen(loginScreen);
        }
    });
} else {
    showScreen(loginScreen);
}