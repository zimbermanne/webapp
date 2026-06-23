// Dynamic Base URL Path Configuration (Supports Cloud & Local Environments instantly)
const API_BASE_URL = '/api';

// Authentication State Engine
let currentToken = localStorage.getItem('token');
let currentUser = null;
let currentProfile = 'Zimbermanne Hardware';

// Global Universal Fetch Wrapper with Token Injection
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
            throw new Error('Session Expired. Please Log In again.');
        }

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Action processing failed.');
        return data;
    } catch (error) {
        console.error(`API Error [${endpoint}]:`, error);
        throw error;
    }
}

// POS Grid Controller
async function processPOSSale(cartItems, trackingType, customerName = "") {
    if (cartItems.length === 0) {
        alert("Empty Cart");
        return;
    }

    const payload = {
        items: cartItems,
        payment_method: trackingType, // 'Cash', 'M-Pesa', 'AirtelMoney', 'Deni' (Credit)
        customer_name: customerName,
        timestamp: new Date().toISOString()
    };

    try {
        const result = await apiCall('/sales/pos-sale', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        alert('Sale completed successfully!');
        return result;
    } catch (err) {
        alert('Error recording transaction: ' + err.message);
    }
}

// Live TZS Ticker Metrics Loader
async function updateDashboardMetrics() {
    try {
        const summary = await apiCall('/reports/daily-summary');
        
        // Update DOM safely if identifiers match
        if(document.getElementById('ticker-revenue')) {
            document.getElementById('ticker-revenue').innerText = `${summary.total_earnings_tzs.toLocaleString()} TZS`;
        }
        if(document.getElementById('low-stock-alert-count')) {
            document.getElementById('low-stock-alert-count').innerText = summary.low_stock_count;
        }
    } catch (e) {
        console.log("Error binding pipeline counters.");
    }
}

function logout() {
    localStorage.removeItem('token');
    currentToken = null;
    window.location.reload();
}
