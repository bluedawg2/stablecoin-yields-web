/**
 * Yield Terminal - Frontend JavaScript
 * Premium DeFi Dashboard
 */

// API base URL
const API_BASE = '/api';

// State
let currentData = [];
let isLoading = false;
let showHidden = false;
let hiddenIds = new Set();

// Local storage key for hidden items
const HIDDEN_STORAGE_KEY = 'yield-terminal-hidden-items';

// DOM Elements
const filterForm = document.getElementById('filter-form');
const refreshBtn = document.getElementById('refresh-btn');
const clearFiltersBtn = document.getElementById('clear-filters');
const filterToggle = document.getElementById('filter-toggle');
const filterCollapse = document.getElementById('filter-collapse');
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

// Hidden items elements
const showHiddenCheckbox = document.getElementById('show-hidden');
const unhideAllBtn = document.getElementById('unhide-all');
const hiddenCountEl = document.getElementById('hidden-count');

/**
 * Initialize the application
 */
document.addEventListener('DOMContentLoaded', () => {
    // Bind event listeners
    filterForm.addEventListener('submit', handleFilterSubmit);
    refreshBtn.addEventListener('click', handleRefresh);
    clearFiltersBtn.addEventListener('click', handleClearFilters);

    // Filter toggle
    if (filterToggle && filterCollapse) {
        filterToggle.addEventListener('click', () => {
            filterCollapse.classList.toggle('show');
        });
    }

    // Hidden items controls
    if (showHiddenCheckbox) {
        showHiddenCheckbox.addEventListener('change', handleShowHiddenToggle);
    }
    if (unhideAllBtn) {
        unhideAllBtn.addEventListener('click', handleUnhideAll);
    }

    // Load hidden items from localStorage
    loadHiddenItems();

    // Create tooltip element
    createTooltip();

    // Bind hide button clicks via event delegation
    tableBody.addEventListener('click', handleHideClick);

    // Load initial data
    fetchOpportunities();
});

/**
 * Load hidden items from localStorage
 */
function loadHiddenItems() {
    try {
        const stored = localStorage.getItem(HIDDEN_STORAGE_KEY);
        if (stored) {
            hiddenIds = new Set(JSON.parse(stored));
        }
    } catch (e) {
        console.error('Failed to load hidden items:', e);
        hiddenIds = new Set();
    }
    updateHiddenCount();
}

/**
 * Save hidden items to localStorage
 */
function saveHiddenItems() {
    try {
        localStorage.setItem(HIDDEN_STORAGE_KEY, JSON.stringify([...hiddenIds]));
    } catch (e) {
        console.error('Failed to save hidden items:', e);
    }
    updateHiddenCount();
}

/**
 * Update hidden count display
 */
function updateHiddenCount() {
    if (hiddenCountEl) {
        hiddenCountEl.textContent = hiddenIds.size;
    }
}

/**
 * Generate unique ID for an opportunity
 */
function getOpportunityId(opp) {
    const key = `${opp.category}|${opp.protocol}|${opp.chain}|${opp.stablecoin}|${opp.source_url}`;
    // Simple hash function
    let hash = 0;
    for (let i = 0; i < key.length; i++) {
        const char = key.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return hash.toString(16);
}

/**
 * Check if an opportunity is hidden
 */
function isHidden(opp) {
    return hiddenIds.has(getOpportunityId(opp));
}

/**
 * Toggle hidden state for an opportunity
 */
function toggleHidden(opp) {
    const id = getOpportunityId(opp);
    if (hiddenIds.has(id)) {
        hiddenIds.delete(id);
    } else {
        hiddenIds.add(id);
    }
    saveHiddenItems();
}

/**
 * Handle show hidden checkbox toggle
 */
function handleShowHiddenToggle() {
    showHidden = showHiddenCheckbox.checked;
    updateTable(currentData);
}

/**
 * Handle unhide all button click
 */
function handleUnhideAll() {
    hiddenIds.clear();
    saveHiddenItems();
    updateTable(currentData);
}

/**
 * Handle hide button click (event delegation)
 */
function handleHideClick(e) {
    const hideBtn = e.target.closest('.hide-btn');
    if (hideBtn) {
        const rowIndex = parseInt(hideBtn.dataset.index, 10);
        const visibleData = showHidden ? currentData : currentData.filter(o => !isHidden(o));
        if (rowIndex >= 0 && rowIndex < visibleData.length) {
            toggleHidden(visibleData[rowIndex]);
            updateTable(currentData);
        }
    }
}

// Tooltip element reference
let tooltipElement = null;

/**
 * Create the tooltip element
 */
function createTooltip() {
    tooltipElement = document.createElement('div');
    tooltipElement.className = 'loop-tooltip';
    tooltipElement.id = 'loop-tooltip';
    document.body.appendChild(tooltipElement);

    // Add event listeners for tooltip
    document.addEventListener('mouseover', handleTooltipShow);
    document.addEventListener('mouseout', handleTooltipHide);
    document.addEventListener('mousemove', handleTooltipMove);
}

/**
 * Handle showing tooltip on hover
 */
function handleTooltipShow(e) {
    const target = e.target.closest('.apy-with-info');
    if (target && target.dataset.tooltip) {
        // Decode HTML entities and render as HTML
        const decoded = target.dataset.tooltip
            .replace(/&quot;/g, '"')
            .replace(/&lt;/g, '<')
            .replace(/&gt;/g, '>');
        tooltipElement.innerHTML = decoded;
        tooltipElement.classList.add('visible');
    }
}

/**
 * Handle hiding tooltip
 */
function handleTooltipHide(e) {
    const target = e.target.closest('.apy-with-info');
    if (target) {
        tooltipElement.classList.remove('visible');
    }
}

/**
 * Handle tooltip position following mouse
 */
function handleTooltipMove(e) {
    if (tooltipElement.classList.contains('visible')) {
        const x = e.clientX + 15;
        const y = e.clientY + 15;

        // Keep tooltip within viewport
        const rect = tooltipElement.getBoundingClientRect();
        const maxX = window.innerWidth - rect.width - 20;
        const maxY = window.innerHeight - rect.height - 20;

        tooltipElement.style.left = Math.min(x, maxX) + 'px';
        tooltipElement.style.top = Math.min(y, maxY) + 'px';
    }
}

/**
 * Handle filter form submission
 */
function handleFilterSubmit(e) {
    e.preventDefault();
    // For filter changes, just fetch from cache (fast), no background refresh needed
    fetchFilteredData();
}

/**
 * Fetch filtered data from cache only (fast, stale ok)
 */
async function fetchFilteredData() {
    try {
        let queryString = buildQueryString(false);
        queryString += (queryString ? '&' : '') + 'stale_ok=true';
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
        console.error('Error fetching filtered data:', error);
        showError(error.message);
    }
}

/**
 * Handle refresh button click
 */
async function handleRefresh() {
    refreshBtn.classList.add('refreshing');
    // Force refresh shows loading overlay
    await fetchOpportunities(true);
    refreshBtn.classList.remove('refreshing');
}

/**
 * Handle clear filters button click
 */
function handleClearFilters() {
    filterForm.reset();
    fetchFilteredData();
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
    const excludeYt = document.getElementById('exclude_yt').value;

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
    if (excludeYt) params.append('exclude_yt', excludeYt);
    if (forceRefresh) params.append('refresh', 'true');

    return params.toString();
}

/**
 * Fetch opportunities from API with cache-first strategy
 * Shows cached data immediately (even if stale), then refreshes in background
 */
async function fetchOpportunities(forceRefresh = false) {
    if (isLoading) return;

    isLoading = true;
    hideError();

    // If forcing refresh, show full loading overlay
    if (forceRefresh) {
        showLoading(true);
        await doFetch(true, false);
        showLoading(false);
        isLoading = false;
        return;
    }

    // Cache-first strategy: fetch stale cached data first (instant)
    try {
        // Show loading only if we have no data yet
        const showLoadingOverlay = currentData.length === 0;
        if (showLoadingOverlay) {
            showLoading(true);
        }

        // Fetch with stale_ok=true for instant response
        const cachedData = await doFetch(false, true);

        if (showLoadingOverlay) {
            showLoading(false);
        }

        // Always start background refresh to get fresh data
        setTimeout(() => {
            backgroundRefresh();
        }, 100);

    } catch (error) {
        console.error('Error fetching cached data:', error);
        showLoading(false);
        showError(error.message);
    }

    isLoading = false;
}

/**
 * Perform the actual fetch
 * @param {boolean} forceRefresh - Force refresh from scrapers
 * @param {boolean} staleOk - Accept stale cached data
 */
async function doFetch(forceRefresh, staleOk = false) {
    try {
        let queryString = buildQueryString(forceRefresh);
        if (staleOk) {
            queryString += (queryString ? '&' : '') + 'stale_ok=true';
        }
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

        return data.opportunities;

    } catch (error) {
        console.error('Error fetching data:', error);
        showError(error.message);
        if (currentData.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="10" class="empty-state">
                        <div class="empty-content">
                            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                                <circle cx="12" cy="12" r="10"/>
                                <line x1="12" y1="8" x2="12" y2="12"/>
                                <line x1="12" y1="16" x2="12.01" y2="16"/>
                            </svg>
                            <span>Failed to load data. Please try again.</span>
                        </div>
                    </td>
                </tr>
            `;
        }
        throw error;
    }
}

// Background refresh state
let isBackgroundRefreshing = false;

/**
 * Refresh data in background without blocking UI
 */
async function backgroundRefresh() {
    if (isBackgroundRefreshing) return;

    isBackgroundRefreshing = true;
    showBackgroundRefreshIndicator(true);

    try {
        const queryString = buildQueryString(true); // force refresh
        const url = `${API_BASE}/opportunities${queryString ? '?' + queryString : ''}`;

        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok) {
            console.error('Background refresh failed:', data.error);
            return;
        }

        // Check if data actually changed
        const newCount = data.opportunities.length;
        const oldCount = currentData.length;

        currentData = data.opportunities;
        updateTable(currentData);
        updateStatistics(currentData);
        updateLastUpdated(data.timestamp);
        resultCount.textContent = `${data.count} results`;

        // Show subtle notification if data changed
        if (newCount !== oldCount) {
            showDataUpdatedNotification(newCount - oldCount);
        }

    } catch (error) {
        console.error('Background refresh error:', error);
    } finally {
        isBackgroundRefreshing = false;
        showBackgroundRefreshIndicator(false);
    }
}

/**
 * Show/hide background refresh indicator
 */
function showBackgroundRefreshIndicator(show) {
    let indicator = document.getElementById('bg-refresh-indicator');

    if (show) {
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.id = 'bg-refresh-indicator';
            indicator.className = 'bg-refresh-indicator';
            indicator.innerHTML = `
                <div class="bg-refresh-spinner"></div>
                <span>Refreshing data...</span>
            `;
            document.body.appendChild(indicator);
        }
        // Trigger animation
        requestAnimationFrame(() => {
            indicator.classList.add('visible');
        });
    } else if (indicator) {
        indicator.classList.remove('visible');
        // Remove after animation
        setTimeout(() => {
            if (indicator && !indicator.classList.contains('visible')) {
                indicator.remove();
            }
        }, 300);
    }
}

/**
 * Show notification when data is updated
 */
function showDataUpdatedNotification(diff) {
    let notification = document.getElementById('data-updated-notification');

    if (!notification) {
        notification = document.createElement('div');
        notification.id = 'data-updated-notification';
        notification.className = 'data-updated-notification';
        document.body.appendChild(notification);
    }

    const message = diff > 0
        ? `+${diff} new opportunities found`
        : diff < 0
            ? `${Math.abs(diff)} opportunities removed`
            : 'Data refreshed';

    notification.textContent = message;
    notification.classList.add('visible');

    // Auto-hide after 3 seconds
    setTimeout(() => {
        notification.classList.remove('visible');
    }, 3000);
}

/**
 * Update the data table with opportunities
 */
function updateTable(opportunities) {
    if (!opportunities || opportunities.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="10" class="no-results">
                    <div class="empty-content">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <circle cx="11" cy="11" r="8"/>
                            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
                        </svg>
                        <span>No opportunities match your filters</span>
                        <small style="color: var(--text-muted);">Try adjusting your filter criteria</small>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    // Filter out hidden items unless showHidden is true
    const visibleOpportunities = showHidden ? opportunities : opportunities.filter(o => !isHidden(o));

    if (visibleOpportunities.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="10" class="no-results">
                    <div class="empty-content">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                            <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/>
                            <line x1="1" y1="1" x2="23" y2="23"/>
                        </svg>
                        <span>All matching opportunities are hidden</span>
                        <small style="color: var(--text-muted);">Toggle "Show hidden" to see them</small>
                    </div>
                </td>
            </tr>
        `;
        return;
    }

    const rows = visibleOpportunities.map((opp, index) => createTableRow(opp, index)).join('');
    tableBody.innerHTML = rows;
}

/**
 * Create a table row for an opportunity
 */
function createTableRow(opp, index) {
    const apyClass = getApyClass(opp.apy);
    const riskClass = getRiskClass(opp.risk_score);
    const leverageClass = opp.leverage === 1.0 ? 'leverage-1x' : 'leverage-high';

    const formattedApy = formatApy(opp.apy);
    const formattedTvl = formatTvl(opp.tvl);
    const formattedLeverage = formatLeverage(opp.leverage);

    const linkHtml = opp.source_url
        ? `<a href="${escapeHtml(opp.source_url)}" target="_blank" rel="noopener" class="source-link" title="View opportunity">
             <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                 <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
                 <polyline points="15 3 21 3 21 9"/>
                 <line x1="10" y1="14" x2="21" y2="3"/>
             </svg>
           </a>`
        : '<span style="color: var(--text-muted);">-</span>';

    // Check if this is a YT opportunity
    const isYt = opp.is_yt || false;
    const ytBadge = isYt ? '<span class="yt-badge">YT</span>' : '';
    const rowClass = isYt ? 'yt-row' : '';

    // Format stablecoin/asset display
    let stablecoinDisplay = formatStablecoin(opp);

    // Check if this is a looping strategy and generate tooltip
    const loopTooltip = getLoopMathTooltip(opp);
    const hasLoopInfo = loopTooltip !== null;
    const loopClass = hasLoopInfo ? 'has-loop-info' : '';

    // Stagger animation delay for each row
    const delay = Math.min(index * 0.02, 0.5);

    // APY cell with tooltip for loop strategies
    let apyHtml = `<span class="${apyClass}">${formattedApy}</span>`;
    if (hasLoopInfo) {
        // Encode tooltip for data attribute (double encode since we'll decode in handler)
        const encodedTooltip = loopTooltip.replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        apyHtml = `<span class="${apyClass} apy-with-info" data-tooltip="${encodedTooltip}">${formattedApy}<span class="info-icon">i</span></span>`;
    }

    // Check if this opportunity is hidden
    const oppHidden = isHidden(opp);
    const hiddenRowClass = oppHidden ? 'hidden-row' : '';

    return `
        <tr style="animation-delay: ${delay}s;" class="${rowClass} ${loopClass} ${hiddenRowClass}">
            <td class="hide-cell">
                <button class="hide-btn ${oppHidden ? 'is-hidden' : ''}" data-index="${index}" title="${oppHidden ? 'Unhide' : 'Hide'}">
                    ${oppHidden ?
                        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>' :
                        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>'
                    }
                </button>
            </td>
            <td class="category-cell">${escapeHtml(opp.category)}${ytBadge}</td>
            <td class="protocol-cell">${escapeHtml(opp.protocol)}</td>
            <td><span class="chain-badge">${escapeHtml(opp.chain)}</span></td>
            <td class="stablecoin-cell">${stablecoinDisplay}</td>
            <td class="text-right apy-cell">${apyHtml}</td>
            <td class="text-right tvl-cell">${formattedTvl}</td>
            <td class="text-center"><span class="risk-badge ${riskClass}">${escapeHtml(opp.risk_score)}</span></td>
            <td class="text-center"><span class="leverage-badge ${leverageClass}">${formattedLeverage}</span></td>
            <td class="text-center">${linkHtml}</td>
        </tr>
    `;
}

/**
 * Update statistics cards
 */
function updateStatistics(opportunities) {
    // Filter out hidden items for stats unless showHidden is true
    const visibleOpportunities = showHidden ? opportunities : (opportunities || []).filter(o => !isHidden(o));

    if (!visibleOpportunities || visibleOpportunities.length === 0) {
        animateValue(statCount, 0);
        statAvgApy.textContent = '-';
        statMaxApy.textContent = '-';
        statTotalTvl.textContent = '-';
        animateValue(statProtocols, 0);
        animateValue(statChains, 0);
        return;
    }

    // Count
    animateValue(statCount, visibleOpportunities.length);

    // APY statistics
    const apys = visibleOpportunities.map(o => o.apy);
    const avgApy = apys.reduce((a, b) => a + b, 0) / apys.length;
    const maxApy = Math.max(...apys);

    statAvgApy.textContent = formatApy(avgApy);
    statMaxApy.textContent = formatApy(maxApy);

    // TVL
    const totalTvl = visibleOpportunities
        .filter(o => o.tvl)
        .reduce((sum, o) => sum + o.tvl, 0);
    statTotalTvl.textContent = formatTvl(totalTvl);

    // Unique protocols and chains
    const protocols = new Set(visibleOpportunities.map(o => o.protocol));
    const chains = new Set(visibleOpportunities.map(o => o.chain));

    animateValue(statProtocols, protocols.size);
    animateValue(statChains, chains.size);
}

/**
 * Animate a numeric value change
 */
function animateValue(element, target) {
    const current = parseInt(element.textContent) || 0;
    const increment = (target - current) / 20;
    let value = current;

    const animate = () => {
        value += increment;
        if ((increment > 0 && value >= target) || (increment < 0 && value <= target)) {
            element.textContent = target.toLocaleString();
            return;
        }
        element.textContent = Math.round(value).toLocaleString();
        requestAnimationFrame(animate);
    };

    requestAnimationFrame(animate);
}

/**
 * Update last updated timestamp
 */
function updateLastUpdated(timestamp, isFresh = false) {
    if (!timestamp) {
        lastUpdated.textContent = 'Connected';
        return;
    }

    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    let timeText;
    if (diffMins < 1) {
        timeText = 'just now';
    } else if (diffMins < 60) {
        timeText = `${diffMins}m ago`;
    } else {
        timeText = date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    lastUpdated.textContent = `Updated ${timeText}`;

    // Update status dot color based on freshness
    const statusDot = document.querySelector('.status-dot');
    if (statusDot) {
        if (diffMins < 5) {
            statusDot.style.background = 'var(--accent-green)';
        } else if (diffMins < 15) {
            statusDot.style.background = 'var(--risk-medium)';
        } else {
            statusDot.style.background = 'var(--risk-high)';
        }
    }
}

/**
 * Format APY value
 */
function formatApy(apy) {
    if (apy === null || apy === undefined) return 'N/A';
    if (apy >= 1000) return (apy / 1000).toFixed(1) + 'K%';
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
    if (tvl >= 1_000) return '$' + (tvl / 1_000).toFixed(0) + 'K';
    return '$' + tvl.toFixed(0);
}

/**
 * Format leverage value
 */
function formatLeverage(leverage) {
    if (leverage === 1.0) return '1x';
    return leverage.toFixed(1) + 'x';
}

/**
 * Format stablecoin/asset display based on opportunity type
 * - Looping strategies: show "COLLATERAL->BORROW" with maturity date
 * - YT opportunities: show "YT-TOKEN" prefix
 * - Pairs: show "TOKEN1-TOKEN2"
 */
function formatStablecoin(opp) {
    const stablecoin = opp.stablecoin;
    const isYt = opp.is_yt || false;
    const additional = opp.additional_info || {};

    if (!stablecoin) return 'N/A';

    // Check if this is a looping strategy
    if (additional.borrow_asset && additional.collateral) {
        let collateral = additional.collateral;
        const borrowAsset = additional.borrow_asset;

        // Add maturity date to PT tokens
        if (collateral.startsWith('PT-') && opp.maturity_date) {
            const date = new Date(opp.maturity_date);
            const dateStr = date.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' }).replace(',', '').replace(' ', '');
            collateral = `${collateral}-${dateStr}`;
        }

        return `<span class="loop-asset">${escapeHtml(collateral)}</span><span class="loop-arrow">→</span><span class="loop-borrow">${escapeHtml(borrowAsset)}</span>`;
    }

    // Add YT prefix for YT opportunities if not already present
    if (isYt && !stablecoin.toUpperCase().startsWith('YT')) {
        return `<span class="yt-prefix">YT-</span>${escapeHtml(stablecoin)}`;
    }

    return escapeHtml(stablecoin);
}

/**
 * Generate loop math tooltip content
 */
function getLoopMathTooltip(opp) {
    const additional = opp.additional_info || {};

    if (!additional.borrow_asset || !additional.collateral) {
        return null;
    }

    const collateralYield = additional.collateral_yield || additional.pt_fixed_yield;
    const borrowRate = additional.borrow_rate;
    const lltv = additional.lltv;
    const liquidity = additional.liquidity;
    const leverage = opp.leverage;
    const isEstimated = additional.estimated_rate || false;

    let tooltipLines = [];

    // Collateral info
    let collateral = additional.collateral;
    if (collateral.startsWith('PT-') && opp.maturity_date) {
        const date = new Date(opp.maturity_date);
        const dateStr = date.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' }).replace(',', '').replace(' ', '');
        collateral = `${collateral}-${dateStr}`;
    }

    tooltipLines.push(`<strong>Loop Strategy</strong>`);
    tooltipLines.push(`Collateral: ${escapeHtml(collateral)}${collateralYield ? ` (${collateralYield.toFixed(2)}% yield)` : ''}`);
    tooltipLines.push(`Borrow: ${escapeHtml(additional.borrow_asset)}${borrowRate ? ` (${borrowRate.toFixed(2)}%${isEstimated ? ' est' : ''})` : ''}`);

    if (lltv) {
        tooltipLines.push(`LLTV: ${lltv.toFixed(1)}%`);
    }

    if (liquidity && liquidity >= 1000) {
        const liqStr = liquidity >= 1_000_000 ? `$${(liquidity / 1_000_000).toFixed(2)}M` : `$${(liquidity / 1_000).toFixed(0)}K`;
        tooltipLines.push(`Liquidity: ${liqStr}`);
    }

    // Show the math calculation
    if (collateralYield && borrowRate && leverage > 1) {
        const calcApy = collateralYield * leverage - borrowRate * (leverage - 1);
        tooltipLines.push(`<span class="math-line">Math: ${collateralYield.toFixed(2)}% × ${leverage.toFixed(1)}x − ${borrowRate.toFixed(2)}% × ${(leverage - 1).toFixed(1)}x = <strong>${calcApy.toFixed(2)}%</strong></span>`);
    }

    return tooltipLines.join('<br>');
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
