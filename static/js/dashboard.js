let ws = null;
let opportunities = [];
let reconnectInterval = null;

document.addEventListener('DOMContentLoaded', function() {
    initWebSocket();
    fetchStatus();
    fetchOpportunities();
    fetchSummary();
    
    document.getElementById('startBtn').addEventListener('click', startScanner);
    document.getElementById('stopBtn').addEventListener('click', stopScanner);
    document.getElementById('scanBtn').addEventListener('click', triggerScan);
    document.getElementById('applyFilters').addEventListener('click', fetchOpportunities);
    document.getElementById('modalClose').addEventListener('click', closeModal);
    document.getElementById('copyPlan').addEventListener('click', copyTradePlan);
    
    document.getElementById('modal').addEventListener('click', function(e) {
        if (e.target === this) closeModal();
    });
    
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') closeModal();
    });
});

function initWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function() {
        updateConnectionStatus(true);
        if (reconnectInterval) {
            clearInterval(reconnectInterval);
            reconnectInterval = null;
        }
    };
    
    ws.onclose = function() {
        updateConnectionStatus(false);
        if (!reconnectInterval) {
            reconnectInterval = setInterval(initWebSocket, 5000);
        }
    };
    
    ws.onerror = function() {
        updateConnectionStatus(false);
    };
    
    ws.onmessage = function(event) {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };
}

function handleWebSocketMessage(message) {
    switch(message.type) {
        case 'new_opportunity':
            addOrUpdateOpportunity(message.data);
            fetchSummary();
            break;
        case 'opportunity_expired':
            removeOpportunity(message.opportunity_id);
            fetchSummary();
            break;
        case 'scan_complete':
            document.getElementById('marketsScanned').textContent = message.data.markets.toLocaleString();
            document.getElementById('lastScan').textContent = 'Last scan: Just now';
            fetchSummary();
            break;
        case 'status_update':
            updateScannerStatus(message.data);
            break;
    }
}

function updateConnectionStatus(connected) {
    const statusDot = document.querySelector('.status-dot');
    const statusText = document.querySelector('.status-text');
    
    if (connected) {
        statusDot.classList.add('connected');
        statusText.textContent = 'Connected';
    } else {
        statusDot.classList.remove('connected');
        statusText.textContent = 'Disconnected';
    }
}

async function fetchStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        updateScannerStatus(data);
    } catch (error) {
        console.error('Failed to fetch status:', error);
    }
}

function updateScannerStatus(status) {
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    
    if (status.is_running) {
        startBtn.disabled = true;
        stopBtn.disabled = false;
    } else {
        startBtn.disabled = false;
        stopBtn.disabled = true;
    }
    
    if (status.last_scan_at) {
        const date = new Date(status.last_scan_at);
        document.getElementById('lastScan').textContent = 'Last scan: ' + date.toLocaleTimeString();
    }
    
    if (status.markets_scanned !== undefined) {
        document.getElementById('marketsScanned').textContent = status.markets_scanned.toLocaleString();
    }
}

async function fetchSummary() {
    try {
        const response = await fetch('/api/summary');
        const data = await response.json();
        
        document.getElementById('activeCount').textContent = data.active_opportunities || 0;
        document.getElementById('totalProfit').textContent = '$' + (data.total_profit_potential || 0).toFixed(4);
        document.getElementById('marketsScanned').textContent = (data.markets_scanned || 0).toLocaleString();
        document.getElementById('bestOpportunity').textContent = (data.best_opportunity_percent || 0).toFixed(2) + '%';
    } catch (error) {
        console.error('Failed to fetch summary:', error);
    }
}

async function fetchOpportunities() {
    const minProfit = document.getElementById('minProfit').value || 0;
    const sortBy = document.getElementById('sortBy').value;
    
    try {
        const response = await fetch(`/api/opportunities?min_profit=${minProfit}&sort=${sortBy}&limit=100`);
        opportunities = await response.json();
        renderOpportunities();
    } catch (error) {
        console.error('Failed to fetch opportunities:', error);
    }
}

function addOrUpdateOpportunity(opp) {
    const index = opportunities.findIndex(o => o.id === opp.id);
    if (index >= 0) {
        opportunities[index] = opp;
    } else {
        opportunities.unshift(opp);
    }
    renderOpportunities();
}

function removeOpportunity(oppId) {
    opportunities = opportunities.filter(o => o.id !== oppId);
    renderOpportunities();
}

function renderOpportunities() {
    const tbody = document.getElementById('opportunitiesBody');
    
    if (opportunities.length === 0) {
        tbody.innerHTML = `
            <tr class="no-data">
                <td colspan="9">No opportunities found. Start the scanner to detect arbitrage.</td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = opportunities.map(opp => {
        const profitClass = opp.net_profit_percent > 2 ? 'profit-high' : 
                           opp.net_profit_percent > 1 ? 'profit-medium' : 'profit-low';
        
        const detectedAt = new Date(opp.detected_at);
        const timeAgo = getTimeAgo(detectedAt);
        
        return `
            <tr onclick="showOpportunityDetail('${opp.id}')">
                <td title="${opp.market_question}">${truncate(opp.market_question, 50)}</td>
                <td>${formatArbitrageType(opp.arbitrage_type)}</td>
                <td>$${opp.total_cost.toFixed(4)}</td>
                <td>$${opp.guaranteed_payout.toFixed(2)}</td>
                <td class="profit-high">$${opp.net_profit.toFixed(4)}</td>
                <td class="${profitClass}">${opp.net_profit_percent.toFixed(2)}%</td>
                <td>$${(opp.min_liquidity || 0).toLocaleString()}</td>
                <td title="${detectedAt.toLocaleString()}">${timeAgo}</td>
                <td><button class="btn btn-primary btn-view" onclick="event.stopPropagation(); showOpportunityDetail('${opp.id}')">View</button></td>
            </tr>
        `;
    }).join('');
}

function showOpportunityDetail(oppId) {
    const opp = opportunities.find(o => o.id === oppId);
    if (!opp) return;
    
    document.getElementById('modalTitle').textContent = 'Opportunity Details';
    document.getElementById('modalQuestion').textContent = opp.market_question;
    document.getElementById('modalEvent').textContent = opp.event_title || 'N/A';
    document.getElementById('modalType').textContent = formatArbitrageType(opp.arbitrage_type);
    document.getElementById('modalCost').textContent = '$' + opp.total_cost.toFixed(4);
    document.getElementById('modalPayout').textContent = '$' + opp.guaranteed_payout.toFixed(2);
    document.getElementById('modalGross').textContent = '$' + opp.gross_profit.toFixed(4);
    document.getElementById('modalFees').textContent = '$' + opp.estimated_fees.toFixed(4);
    document.getElementById('modalNet').textContent = '$' + opp.net_profit.toFixed(4);
    document.getElementById('modalPercent').textContent = opp.net_profit_percent.toFixed(2) + '%';
    
    const tradeLegsHtml = (opp.trade_legs || []).map(leg => `
        <div class="trade-leg">
            <span><strong>${leg.side}</strong> ${leg.outcome}</span>
            <span>$${leg.price.toFixed(4)}</span>
        </div>
    `).join('');
    document.getElementById('tradeLegs').innerHTML = tradeLegsHtml || 'No trade legs available';
    
    const polymarketLink = document.getElementById('polymarketLink');
    if (opp.slug) {
        polymarketLink.href = `https://polymarket.com/event/${opp.slug}`;
        polymarketLink.style.display = 'inline-block';
    } else {
        polymarketLink.style.display = 'none';
    }
    
    document.getElementById('modal').classList.add('active');
    document.getElementById('modal').dataset.currentOpp = JSON.stringify(opp);
}

function closeModal() {
    document.getElementById('modal').classList.remove('active');
}

function copyTradePlan() {
    const oppData = document.getElementById('modal').dataset.currentOpp;
    if (!oppData) return;
    
    const opp = JSON.parse(oppData);
    let plan = `ARBITRAGE TRADE PLAN\n`;
    plan += `====================\n\n`;
    plan += `Market: ${opp.market_question}\n`;
    plan += `Type: ${formatArbitrageType(opp.arbitrage_type)}\n\n`;
    plan += `TRADES:\n`;
    
    (opp.trade_legs || []).forEach(leg => {
        plan += `  - ${leg.side} ${leg.outcome} at $${leg.price.toFixed(4)}\n`;
    });
    
    plan += `\nSUMMARY:\n`;
    plan += `  Total Cost: $${opp.total_cost.toFixed(4)}\n`;
    plan += `  Guaranteed Payout: $${opp.guaranteed_payout.toFixed(2)}\n`;
    plan += `  Net Profit: $${opp.net_profit.toFixed(4)} (${opp.net_profit_percent.toFixed(2)}%)\n`;
    
    if (opp.slug) {
        plan += `\nLink: https://polymarket.com/event/${opp.slug}\n`;
    }
    
    navigator.clipboard.writeText(plan).then(() => {
        const btn = document.getElementById('copyPlan');
        btn.textContent = 'Copied!';
        setTimeout(() => btn.textContent = 'Copy Trade Plan', 2000);
    });
}

async function startScanner() {
    try {
        const response = await fetch('/api/start', { method: 'POST' });
        const data = await response.json();
        fetchStatus();
    } catch (error) {
        console.error('Failed to start scanner:', error);
    }
}

async function stopScanner() {
    try {
        const response = await fetch('/api/stop', { method: 'POST' });
        const data = await response.json();
        fetchStatus();
    } catch (error) {
        console.error('Failed to stop scanner:', error);
    }
}

async function triggerScan() {
    const btn = document.getElementById('scanBtn');
    btn.disabled = true;
    btn.textContent = 'Scanning...';
    
    try {
        const response = await fetch('/api/scan', { method: 'POST' });
        const data = await response.json();
        await fetchOpportunities();
        await fetchSummary();
        fetchStatus();
    } catch (error) {
        console.error('Failed to trigger scan:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Scan Now';
    }
}

function truncate(str, length) {
    if (!str) return '';
    return str.length > length ? str.substring(0, length) + '...' : str;
}

function formatArbitrageType(type) {
    const types = {
        'BINARY_MISPRICING': 'Binary',
        'DUTCH_BOOK_UNDER': 'Dutch Book',
        'MULTI_MARKET_INCONSISTENCY': 'Multi-Market'
    };
    return types[type] || type;
}

function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    
    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return Math.floor(seconds / 60) + 'm ago';
    if (seconds < 86400) return Math.floor(seconds / 3600) + 'h ago';
    return Math.floor(seconds / 86400) + 'd ago';
}
