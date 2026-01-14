/**
 * NNRT Web Interface — Application Logic
 */

// =============================================================================
// Configuration
// =============================================================================

const API_BASE = 'http://localhost:5050/api';

// =============================================================================
// State
// =============================================================================

let currentResult = null;
let examples = [];
let history = [];

// =============================================================================
// DOM Elements
// =============================================================================

const elements = {
    inputText: document.getElementById('inputText'),
    charCount: document.getElementById('charCount'),
    transformBtn: document.getElementById('transformBtn'),
    clearBtn: document.getElementById('clearBtn'),
    historyBtn: document.getElementById('historyBtn'),
    examplesBtn: document.getElementById('examplesBtn'),

    statusIndicator: document.getElementById('statusIndicator'),
    statusText: document.getElementById('statusText'),
    stats: document.getElementById('stats'),

    outputText: document.getElementById('outputText'),
    outputBadge: document.getElementById('outputBadge'),

    statementsList: document.getElementById('statementsList'),
    statementsBadge: document.getElementById('statementsBadge'),

    entitiesList: document.getElementById('entitiesList'),
    entitiesBadge: document.getElementById('entitiesBadge'),

    eventsList: document.getElementById('eventsList'),
    eventsBadge: document.getElementById('eventsBadge'),

    diagnosticsList: document.getElementById('diagnosticsList'),
    diagnosticsBadge: document.getElementById('diagnosticsBadge'),

    transformsList: document.getElementById('transformsList'),
    transformsBadge: document.getElementById('transformsBadge'),

    historySidebar: document.getElementById('historySidebar'),
    historyList: document.getElementById('historyList'),

    examplesSidebar: document.getElementById('examplesSidebar'),
    examplesList: document.getElementById('examplesList'),
    exampleSearch: document.getElementById('exampleSearch'),
    findOnlineBtn: document.getElementById('findOnlineBtn'),

    sidebarBackdrop: document.getElementById('sidebarBackdrop'),
};

// =============================================================================
// Event Listeners
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Input handling
    elements.inputText.addEventListener('input', updateCharCount);
    elements.inputText.addEventListener('keydown', handleKeyDown);

    // Buttons
    elements.transformBtn.addEventListener('click', transformText);
    elements.clearBtn.addEventListener('click', clearInput);
    elements.historyBtn.addEventListener('click', () => openSidebar('historySidebar'));
    elements.examplesBtn.addEventListener('click', () => openSidebar('examplesSidebar'));
    elements.findOnlineBtn.addEventListener('click', findOnlineResources);

    // Example search
    elements.exampleSearch.addEventListener('input', filterExamples);

    // Load initial data
    loadExamples();
    loadHistory();
});

// =============================================================================
// Transform Logic
// =============================================================================

async function transformText() {
    const text = elements.inputText.value.trim();

    if (!text) {
        showStatus('error', 'Please enter some text');
        return;
    }

    showStatus('processing', 'Transforming...');
    elements.transformBtn.disabled = true;

    try {
        const response = await fetch(`${API_BASE}/transform`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text }),
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        currentResult = await response.json();
        displayResult(currentResult);
        saveToHistory(currentResult);
        showStatus('success', `Transformed successfully`);

    } catch (error) {
        console.error('Transform error:', error);
        showStatus('error', `Error: ${error.message}`);
    } finally {
        elements.transformBtn.disabled = false;
    }
}

function displayResult(result) {
    // Stats
    elements.stats.innerHTML = `
        <span class="stat"><span class="stat-value">${result.stats.statements}</span> statements</span>
        <span class="stat"><span class="stat-value">${result.stats.entities}</span> entities</span>
        <span class="stat"><span class="stat-value">${result.stats.events}</span> events</span>
        <span class="stat"><span class="stat-value">${result.stats.transformations}</span> transforms</span>
    `;

    // Output
    elements.outputText.innerHTML = result.rendered_text || '<span class="placeholder">No output</span>';
    elements.outputBadge.textContent = `${result.rendered_text?.length || 0} chars`;

    // Statements
    elements.statementsBadge.textContent = result.statements.length;
    elements.statementsList.innerHTML = result.statements.map(s => `
        <div class="item-card ${s.type}">
            <div class="item-header">
                <span class="item-type ${s.type}">${s.type}</span>
                <span class="item-id">${s.id}</span>
            </div>
            <div class="item-text">${escapeHtml(s.original)}</div>
            ${s.neutral ? `
                <div class="item-neutral">→ ${escapeHtml(s.neutral)}</div>
            ` : ''}
            ${s.transformations?.length ? `
                <div class="item-meta">
                    ${s.transformations.map(t => `<span class="meta-tag">${t.rule_id}</span>`).join('')}
                </div>
            ` : ''}
        </div>
    `).join('') || '<div class="empty-state">No statements</div>';

    // Entities
    elements.entitiesBadge.textContent = result.entities.length;
    elements.entitiesList.innerHTML = result.entities.map(e => `
        <div class="item-card">
            <div class="item-header">
                <span class="item-type">${e.role}</span>
                <span class="item-id">${e.id}</span>
            </div>
            <div class="item-text">${escapeHtml(e.label)}</div>
            <div class="item-meta">
                <span class="meta-tag">${e.type}</span>
            </div>
        </div>
    `).join('') || '<div class="empty-state">No entities</div>';

    // Events
    elements.eventsBadge.textContent = result.events.length;
    elements.eventsList.innerHTML = result.events.map(e => `
        <div class="item-card ${e.type}">
            <div class="item-header">
                <span class="item-type">${e.type}</span>
                <span class="item-id">${e.id}</span>
            </div>
            <div class="item-text">${escapeHtml(e.description || 'No description')}</div>
        </div>
    `).join('') || '<div class="empty-state">No events</div>';

    // Diagnostics
    elements.diagnosticsBadge.textContent = result.diagnostics.length;
    elements.diagnosticsList.innerHTML = result.diagnostics.map(d => `
        <div class="item-card ${d.level}">
            <div class="item-header">
                <span class="item-type">${d.level}</span>
                <span class="item-id">${d.code}</span>
            </div>
            <div class="item-text">${escapeHtml(d.message)}</div>
        </div>
    `).join('') || '<div class="empty-state">No diagnostics</div>';

    // Transformations
    const allTransforms = result.statements.flatMap(s => s.transformations || []);
    elements.transformsBadge.textContent = allTransforms.length;
    elements.transformsList.innerHTML = allTransforms.map(t => `
        <div class="item-card">
            <div class="item-header">
                <span class="item-type">${t.action}</span>
                <span class="item-id">${t.rule_id}</span>
            </div>
            ${t.original && t.replacement ? `
                <div class="item-original">${escapeHtml(t.original.substring(0, 100))}</div>
                <div class="item-neutral">→ ${escapeHtml(t.replacement.substring(0, 100))}</div>
            ` : ''}
        </div>
    `).join('') || '<div class="empty-state">No transformations</div>';

    // Expand output panel
    const outputPanel = document.getElementById('outputPanel');
    outputPanel.querySelector('.panel-content').classList.remove('collapsed');
}

// =============================================================================
// Panel Toggle
// =============================================================================

function togglePanel(panelId) {
    const panel = document.getElementById(panelId);
    const content = panel.querySelector('.panel-content');
    content.classList.toggle('collapsed');
}

// =============================================================================
// Status Display
// =============================================================================

function showStatus(type, message) {
    elements.statusIndicator.className = `status-indicator ${type}`;
    elements.statusText.textContent = message;
}

// =============================================================================
// Input Handling
// =============================================================================

function updateCharCount() {
    const count = elements.inputText.value.length;
    elements.charCount.textContent = `${count} chars`;
}

function handleKeyDown(e) {
    // Ctrl/Cmd + Enter to transform
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        transformText();
    }
}

function clearInput() {
    elements.inputText.value = '';
    updateCharCount();
    elements.inputText.focus();
}

// =============================================================================
// Sidebars
// =============================================================================

function openSidebar(sidebarId) {
    closeAllSidebars();
    document.getElementById(sidebarId).classList.add('open');
    elements.sidebarBackdrop.classList.add('visible');
}

function closeSidebar(sidebarId) {
    document.getElementById(sidebarId).classList.remove('open');
    elements.sidebarBackdrop.classList.remove('visible');
}

function closeAllSidebars() {
    document.querySelectorAll('.sidebar').forEach(s => s.classList.remove('open'));
    elements.sidebarBackdrop.classList.remove('visible');
}

// =============================================================================
// History
// =============================================================================

async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/history`);
        if (response.ok) {
            history = await response.json();
            renderHistory();
        }
    } catch (error) {
        console.log('Could not load history from server, using local');
        history = JSON.parse(localStorage.getItem('nnrt_history') || '[]');
        renderHistory();
    }
}

async function saveToHistory(result) {
    try {
        await fetch(`${API_BASE}/history`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(result),
        });
    } catch (error) {
        // Fallback to local storage
        history.unshift({
            id: result.id,
            timestamp: result.timestamp,
            preview: result.input.substring(0, 100) + '...',
            status: result.status,
        });
        history = history.slice(0, 50);
        localStorage.setItem('nnrt_history', JSON.stringify(history));
    }
    loadHistory();
}

function renderHistory() {
    if (!history.length) {
        elements.historyList.innerHTML = '<div class="empty-state">No history yet</div>';
        return;
    }

    elements.historyList.innerHTML = history.map(item => `
        <div class="history-item" onclick="loadHistoryItem('${item.id}')">
            <div class="history-time">${formatTime(item.timestamp)}</div>
            <div class="history-preview">${escapeHtml(item.preview)}</div>
        </div>
    `).join('');
}

async function loadHistoryItem(id) {
    try {
        const response = await fetch(`${API_BASE}/history/${id}`);
        if (response.ok) {
            const item = await response.json();
            elements.inputText.value = item.input;
            updateCharCount();
            displayResult(item);
            closeSidebar('historySidebar');
        }
    } catch (error) {
        console.error('Could not load history item:', error);
    }
}

// =============================================================================
// Examples
// =============================================================================

async function loadExamples() {
    try {
        const response = await fetch(`${API_BASE}/examples`);
        if (response.ok) {
            examples = await response.json();
            renderExamples(examples);
        }
    } catch (error) {
        console.log('Could not load examples from server');
        elements.examplesList.innerHTML = '<div class="empty-state">Server not connected</div>';
    }
}

function renderExamples(list) {
    if (!list.length) {
        elements.examplesList.innerHTML = '<div class="empty-state">No examples</div>';
        return;
    }

    elements.examplesList.innerHTML = list.map(ex => `
        <div class="example-item" onclick="useExample('${ex.id}')">
            <div class="example-category">${ex.category}</div>
            <div class="example-name">${escapeHtml(ex.name)}</div>
            <div class="example-preview">${escapeHtml(ex.text.substring(0, 100))}...</div>
        </div>
    `).join('');
}

function filterExamples() {
    const query = elements.exampleSearch.value.toLowerCase();
    const filtered = examples.filter(ex =>
        ex.name.toLowerCase().includes(query) ||
        ex.category.toLowerCase().includes(query) ||
        ex.text.toLowerCase().includes(query)
    );
    renderExamples(filtered);
}

function useExample(id) {
    const example = examples.find(ex => ex.id === id);
    if (example) {
        elements.inputText.value = example.text;
        updateCharCount();
        closeSidebar('examplesSidebar');
        elements.inputText.focus();
    }
}

// =============================================================================
// Online Resources
// =============================================================================

function findOnlineResources() {
    // Open search for police report examples
    const queries = [
        'police incident report example',
        'witness statement template',
        'use of force report sample',
    ];
    const randomQuery = queries[Math.floor(Math.random() * queries.length)];
    const searchUrl = `https://www.google.com/search?q=${encodeURIComponent(randomQuery + ' filetype:pdf')}`;
    window.open(searchUrl, '_blank');
}

// =============================================================================
// Utilities
// =============================================================================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(isoString) {
    if (!isoString) return 'Unknown';
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
    return date.toLocaleDateString();
}

// Make functions available globally for onclick handlers
window.togglePanel = togglePanel;
window.closeSidebar = closeSidebar;
window.closeAllSidebars = closeAllSidebars;
window.loadHistoryItem = loadHistoryItem;
window.useExample = useExample;
