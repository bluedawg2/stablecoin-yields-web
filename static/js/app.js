/**
 * Stablecoin Yield Summarizer - Frontend JavaScript
 */

// API base URL
const API_BASE = '/api';

// State
let currentData = [];
let isLoading = false;

// DOM Elements
const filterForm = document.getElementById('filter-form');
const refreshBtn = document.getElementById('refresh-btn');
const clearFiltersBtn = document.getElementById('clear-filters');
const loadingDiv = document.getElementById('loading');
const errorDiv = document.getElementById('error-message');
const errorText = document.getElementById('error-text');
const tableBody = document.getElementById('opportunities-body');
const resultCount = document.getElementById('result-count');
const lastUpdated = document.getElementById('last-updated');

// Statistics elements
const statCount = document.getElementById('stat-count');
const statAvgApy = document.getElementById('stat-avg-apy');
const statMaxApy = document.getElementById('stat-max-apy');
const statTotalTvl = document.getElementById('stat-total-tvl');
const statProtocols = document.getElementById('stat-protocols');
const statChains = document.getElementById('stat-chains');

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', () => {
    // Bind event listeners
    filterForm.addEventListener('submit', handleFilterSubmit);
    refreshBtn.addEventListener('click', handleRefresh);
    clearFiltersBtn.addEventListener('click', handleClearFilters);

    // Load initial data
    fetchOpportunities();
});

/**
 * Handle filter form submission
 */
function handleFilterSubmit(e) {
    e.preventDefault();
    fetchOpportunities();
}

/**
 * Handle refresh button click
 */
async function handleRefresh() {
    refreshBtn.classList.add('refreshing');
    await fetchOpportunities(true);
    refreshBtn.classList.remove('refreshing');
}

/**
 * Handle clear filters button click
 */
function handleClearFilters() {
    filterForm.reset();
    fetchOpportunities();
}

/**
 * Build query string from filter form
 */
function buildQueryString(forceRefresh = false) {
    const params = new URLSearchParams();

    // Get form values
    const category = document.getElementById('category').value;
    const chain = document.getElementById('chain').value;
    const stablecoin = document.getElementById('stablecoin').value;
    const protocol = document.getElementById('protocol').value;
    const minApy = document.getElementById('min_apy').value;
    const maxRisk = document.getElementById('max_risk').value;
    const maxLeverage = document.getElementById('max_leverage').value;
    const minTvl = document.getElementById('min_tvl').value;
    const sortBy = document.getElementById('sort_by').value;
    const ascending = document.getElementById('ascending').value;

    // Add non-empty values to params
    if (category) params.append('category', category);
    if (chain) params.append('chain', chain);
    if (stablecoin) params.append('stablecoin', stablecoin);
    if (protocol) params.append('protocol', protocol);
    if (minApy) params.append('min_apy', minApy);
    if (maxRisk) params.append('max_risk', maxRisk);
    if (maxLeverage) params.append('max_leverage', maxLeverage);
    if (minTvl) params.append('min_tvl', minTvl);
    if (sortBy) params.append('sort_by', sortBy);
    if (ascending) params.append('ascending', ascending);
    if (forceRefresh) params.append('refresh', 'true');

    return params.toString();
}

/**
 * Fetch opportunities from API
 */
async function fetchOpportunities(forceRefresh = false) {
    if (isLoading) return;

    isLoading = true;
    showLoading(true);
    hideError();

    try {
        const queryString = buildQueryString(forceRefresh);
        const url = `${API_BASE}/opportunities${queryString ? '?' + queryString : ''}`;

        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Failed to fetch data');
        }

        currentData = data.opportunities;
        updateTable(currentData);
        updateStatistics(currentData);
        updateLastUpdated(data.timestamp);
        resultCount.textContent = `${data.count} results`;

    } catch (error) {
        console.error('Error fetching data:', error);
        showError(error.message);
        tableBody.innerHTML = `
            <tr>
                <td colspan="9" class="text-center text-danger py-4">
                    <i class="bi bi-exclamation-triangle"></i> Failed to load data. Please try again.
                </td>
            </tr>
        `;
    } finally {
        isLoading = false;
        showLoading(false);
    }
}

/**
 * Update the data table with opportunities
 */
function updateTable(opportunities) {
    if (!opportunities || opportunities.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="9" class="no-results">
                    <i class="bi bi-search"></i> No opportunities match your filters.
                    <br><small>Try adjusting your filter criteria.</small>
                </td>
            </tr>
        `;
        return;
    }

    const rows = opportunities.map(opp => createTableRow(opp)).join('');
    tableBody.innerHTML = rows;
}

/**
 * Create a table row for an opportunity
 */
function createTableRow(opp) {
    const apyClass = getApyClass(opp.apy);
    const riskClass = getRiskClass(opp.risk_score);
    const leverageClass = opp.leverage === 1.0 ? 'leverage-1x' : 'leverage-high';

    const formattedApy = formatApy(opp.apy);
    const formattedTvl = formatTvl(opp.tvl);
    const formattedLeverage = formatLeverage(opp.leverage);

    const linkHtml = opp.source_url
        ? `<a href="${escapeHtml(opp.source_url)}" target="_blank" rel="noopener" class="source-link">
             <i class="bi bi-box-arrow-up-right"></i>
           </a>`
        : '-';

    return `
        <tr>
            <td class="category-name">${escapeHtml(opp.category)}</td>
            <td class="protocol-name">${escapeHtml(opp.protocol)}</td>
            <td><span class="badge chain-badge">${escapeHtml(opp.chain)}</span></td>
            <td class="stablecoin-name">${escapeHtml(opp.stablecoin)}</td>
            <td class="text-end ${apyClass}">${formattedApy}</td>
            <td class="text-end tvl-value">${formattedTvl}</td>
            <td class="text-center"><span class="badge ${riskClass}">${escapeHtml(opp.risk_score)}</span></td>
            <td class="text-center"><span class="badge ${leverageClass} leverage-badge">${formattedLeverage}</span></td>
            <td class="text-center">${linkHtml}</td>
        </tr>
    `;
}

/**
 * Update statistics cards
 */
function updateStatistics(opportunities) {
    if (!opportunities || opportunities.length === 0) {
        statCount.textContent = '0';
        statAvgApy.textContent = '-';
        statMaxApy.textContent = '-';
        statTotalTvl.textContent = '-';
        statProtocols.textContent = '0';
        statChains.textContent = '0';
        return;
    }

    // Count
    statCount.textContent = opportunities.length.toLocaleString();

    // APY statistics
    const apys = opportunities.map(o => o.apy);
    const avgApy = apys.reduce((a, b) => a + b, 0) / apys.length;
    const maxApy = Math.max(...apys);

    statAvgApy.textContent = formatApy(avgApy);
    statMaxApy.textContent = formatApy(maxApy);

    // TVL
    const totalTvl = opportunities
        .filter(o => o.tvl)
        .reduce((sum, o) => sum + o.tvl, 0);
    statTotalTvl.textContent = formatTvl(totalTvl);

    // Unique protocols and chains
    const protocols = new Set(opportunities.map(o => o.protocol));
    const chains = new Set(opportunities.map(o => o.chain));

    statProtocols.textContent = protocols.size.toLocaleString();
    statChains.textContent = chains.size.toLocaleString();
}

/**
 * Update last updated timestamp
 */
function updateLastUpdated(timestamp) {
    if (!timestamp) return;

    const date = new Date(timestamp);
    const formatted = date.toLocaleTimeString([], {
        hour: '2-digit',
        minute: '2-digit'
    });
    lastUpdated.textContent = `Updated: ${formatted}`;
}

/**
 * Format APY value
 */
function formatApy(apy) {
    if (apy === null || apy === undefined) return 'N/A';
    if (apy >= 100) return apy.toLocaleString(undefined, { maximumFractionDigits: 1 }) + '%';
    return apy.toFixed(2) + '%';
}

/**
 * Format TVL value
 */
function formatTvl(tvl) {
    if (tvl === null || tvl === undefined) return 'N/A';
    if (tvl >= 1_000_000_000) return '$' + (tvl / 1_000_000_000).toFixed(2) + 'B';
    if (tvl >= 1_000_000) return '$' + (tvl / 1_000_000).toFixed(2) + 'M';
    if (tvl >= 1_000) return '$' + (tvl / 1_000).toFixed(2) + 'K';
    return '$' + tvl.toFixed(2);
}

/**
 * Format leverage value
 */
function formatLeverage(leverage) {
    if (leverage === 1.0) return '1x';
    return leverage.toFixed(1) + 'x';
}

/**
 * Get CSS class for APY value
 */
function getApyClass(apy) {
    if (apy >= 15) return 'apy-excellent';
    if (apy >= 5) return 'apy-good';
    return 'apy-low';
}

/**
 * Get CSS class for risk level
 */
function getRiskClass(risk) {
    const riskLower = risk.toLowerCase().replace(' ', '-');
    return `risk-${riskLower}`;
}

/**
 * Show/hide loading indicator
 */
function showLoading(show) {
    loadingDiv.style.display = show ? 'flex' : 'none';
}

/**
 * Show error message
 */
function showError(message) {
    errorText.textContent = message;
    errorDiv.style.display = 'flex';
}

/**
 * Hide error message
 */
function hideError() {
    errorDiv.style.display = 'none';
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
