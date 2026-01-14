/**
 * NNRT Web Interface — Application Logic (FIXED)
 */

const API_BASE = 'http://localhost:5050/api';

// State
let currentResult = null;
let examples = [];
let history = [];
let logs = [];
let useLLM = false;
let showLogs = false;

// DOM Elements - cached on load
let elements = {};

// =============================================================================
// Initialize
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Cache DOM elements
    elements = {
        inputText: document.getElementById('inputText'),
        charCount: document.getElementById('charCount'),
        transformBtn: document.getElementById('transformBtn'),
        clearBtn: document.getElementById('clearBtn'),
        historyBtn: document.getElementById('historyBtn'),
        examplesBtn: document.getElementById('examplesBtn'),
        llmToggle: document.getElementById('llmToggle'),
        logsToggle: document.getElementById('logsToggle'),
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
        logsPanel: document.getElementById('logsPanel'),
        logsOutput: document.getElementById('logsOutput'),
        logsBadge: document.getElementById('logsBadge'),
        historyList: document.getElementById('historyList'),
        examplesList: document.getElementById('examplesList'),
        exampleSearch: document.getElementById('exampleSearch'),
        findOnlineBtn: document.getElementById('findOnlineBtn'),
        sidebarBackdrop: document.getElementById('sidebarBackdrop'),
    };

    // Event listeners
    elements.inputText?.addEventListener('input', updateCharCount);
    elements.inputText?.addEventListener('keydown', handleKeyDown);
    elements.transformBtn?.addEventListener('click', transformText);
    elements.clearBtn?.addEventListener('click', clearInput);
    elements.historyBtn?.addEventListener('click', () => openSidebar('historySidebar'));
    elements.examplesBtn?.addEventListener('click', () => openSidebar('examplesSidebar'));
    elements.findOnlineBtn?.addEventListener('click', findOnlineResources);
    elements.llmToggle?.addEventListener('change', (e) => {
        useLLM = e.target.checked;
        savePrefs();
        addLog(useLLM ? 'LLM mode enabled' : 'LLM mode disabled');
    });
    elements.logsToggle?.addEventListener('change', (e) => {
        showLogs = e.target.checked;
        savePrefs();
        const logsPanel = document.getElementById('logsPanel');
        if (showLogs) {
            logsPanel?.classList.remove('hidden');
            logsPanel?.classList.remove('collapsed');
        } else {
            logsPanel?.classList.add('hidden');
        }
    });
    elements.exampleSearch?.addEventListener('input', filterExamples);

    // Load data
    loadExamples();
    loadHistory();
    loadPrefs();

    console.log('NNRT initialized');
});

// =============================================================================
// Panel Toggle - Simple and correct
// =============================================================================

function togglePanel(panelId) {
    const panel = document.getElementById(panelId);
    if (!panel) return;

    if (panel.classList.contains('collapsed')) {
        panel.classList.remove('collapsed');
    } else {
        panel.classList.add('collapsed');
    }
}

function expandPanel(panelId) {
    document.getElementById(panelId)?.classList.remove('collapsed');
}

function collapsePanel(panelId) {
    document.getElementById(panelId)?.classList.add('collapsed');
}

// =============================================================================
// Transform
// =============================================================================

async function transformText() {
    const text = elements.inputText?.value.trim();
    if (!text) {
        showStatus('error', 'Please enter some text');
        return;
    }

    showStatus('processing', 'Transforming...');
    if (elements.transformBtn) elements.transformBtn.disabled = true;
    addLog(`Starting transform (${text.length} chars)`);

    try {
        const response = await fetch(`${API_BASE}/transform`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, use_llm: useLLM }),
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        currentResult = await response.json();
        addLog(`Complete: ${currentResult.status}`);

        // Populate and expand panels
        displayResults(currentResult);
        saveToHistory(currentResult);
        showStatus('success', 'Transformed successfully');

    } catch (error) {
        console.error('Transform error:', error);
        addLog(`Error: ${error.message}`, 'error');
        showStatus('error', `Error: ${error.message}`);
    } finally {
        if (elements.transformBtn) elements.transformBtn.disabled = false;
    }
}

function displayResults(result) {
    // Stats
    if (elements.stats) {
        elements.stats.innerHTML = `
            <span class="stat"><span class="stat-value">${result.stats?.statements || 0}</span> statements</span>
            <span class="stat"><span class="stat-value">${result.stats?.entities || 0}</span> entities</span>
            <span class="stat"><span class="stat-value">${result.stats?.events || 0}</span> events</span>
            <span class="stat"><span class="stat-value">${result.stats?.transformations || 0}</span> transforms</span>
        `;
    }

    // Output
    if (elements.outputText) {
        elements.outputText.innerHTML = result.rendered_text
            ? escapeHtml(result.rendered_text)
            : '<span class="placeholder">No output</span>';
    }
    if (elements.outputBadge) {
        elements.outputBadge.textContent = `${result.rendered_text?.length || 0} chars`;
    }
    expandPanel('outputPanel');

    // Statements
    const statements = result.statements || [];
    if (elements.statementsBadge) elements.statementsBadge.textContent = statements.length;
    if (elements.statementsList) {
        elements.statementsList.innerHTML = statements.length ? statements.map(s => `
            <div class="item-card ${s.type || ''}">
                <div class="item-header">
                    <span class="item-type ${s.type || ''}">${s.type || 'unknown'}</span>
                    <span class="item-id">${s.id || ''}</span>
                </div>
                <div class="item-text">${escapeHtml(s.original || '')}</div>
                ${s.neutral ? `<div class="item-neutral">→ ${escapeHtml(s.neutral)}</div>` : ''}
                ${(s.transformations || []).length ? `
                    <div class="item-meta">${s.transformations.map(t => `<span class="meta-tag">${t.rule_id}</span>`).join('')}</div>
                ` : ''}
            </div>
        `).join('') : '<div class="empty-state">No statements</div>';
    }
    if (statements.length) expandPanel('statementsPanel');

    // Entities
    const entities = result.entities || [];
    if (elements.entitiesBadge) elements.entitiesBadge.textContent = entities.length;
    if (elements.entitiesList) {
        elements.entitiesList.innerHTML = entities.length ? entities.map(e => `
            <div class="item-card">
                <div class="item-header">
                    <span class="item-type">${e.role || ''}</span>
                    <span class="item-id">${e.id || ''}</span>
                </div>
                <div class="item-text">${escapeHtml(e.label || '')}</div>
            </div>
        `).join('') : '<div class="empty-state">No entities</div>';
    }
    if (entities.length) expandPanel('entitiesPanel');

    // Events
    const events = result.events || [];
    if (elements.eventsBadge) elements.eventsBadge.textContent = events.length;
    if (elements.eventsList) {
        elements.eventsList.innerHTML = events.length ? events.map(e => `
            <div class="item-card ${e.type || ''}">
                <div class="item-header">
                    <span class="item-type">${e.type || ''}</span>
                    <span class="item-id">${e.id || ''}</span>
                </div>
                <div class="item-text">${escapeHtml(e.description || '')}</div>
            </div>
        `).join('') : '<div class="empty-state">No events</div>';
    }
    if (events.length) expandPanel('eventsPanel');

    // Diagnostics
    const diagnostics = result.diagnostics || [];
    if (elements.diagnosticsBadge) elements.diagnosticsBadge.textContent = diagnostics.length;
    if (elements.diagnosticsList) {
        elements.diagnosticsList.innerHTML = diagnostics.length ? diagnostics.map(d => `
            <div class="item-card ${d.level || ''}">
                <div class="item-header">
                    <span class="item-type ${d.level || ''}">${d.level || ''}</span>
                    <span class="item-id">${d.code || ''}</span>
                </div>
                <div class="item-text">${escapeHtml(d.message || '')}</div>
            </div>
        `).join('') : '<div class="empty-state">No diagnostics</div>';
    }
    if (diagnostics.length) expandPanel('diagnosticsPanel');

    // Transformations
    const transforms = (result.statements || []).flatMap(s => s.transformations || []);
    if (elements.transformsBadge) elements.transformsBadge.textContent = transforms.length;
    if (elements.transformsList) {
        elements.transformsList.innerHTML = transforms.length ? transforms.map(t => `
            <div class="item-card">
                <div class="item-header">
                    <span class="item-type">${t.action || ''}</span>
                    <span class="item-id">${t.rule_id || ''}</span>
                </div>
                ${t.original ? `<div class="item-original">${escapeHtml(t.original.substring(0, 100))}</div>` : ''}
                ${t.replacement ? `<div class="item-neutral">→ ${escapeHtml(t.replacement.substring(0, 100))}</div>` : ''}
            </div>
        `).join('') : '<div class="empty-state">No transformations</div>';
    }
    if (transforms.length) expandPanel('transformsPanel');
}

// =============================================================================
// Status & Logging
// =============================================================================

function showStatus(type, message) {
    if (elements.statusIndicator) elements.statusIndicator.className = `status-indicator ${type}`;
    if (elements.statusText) elements.statusText.textContent = message;
}

function addLog(message, level = 'info') {
    const time = new Date().toLocaleTimeString();
    logs.push({ time, message, level });
    if (logs.length > 50) logs = logs.slice(-50);

    if (elements.logsBadge) elements.logsBadge.textContent = logs.length;
    if (elements.logsOutput) {
        elements.logsOutput.innerHTML = logs.map(l =>
            `<span class="log-entry ${l.level}">[${l.time}] ${escapeHtml(l.message)}</span>`
        ).join('\n');
        elements.logsOutput.scrollTop = elements.logsOutput.scrollHeight;
    }
}

// =============================================================================
// Input
// =============================================================================

function updateCharCount() {
    if (elements.charCount && elements.inputText) {
        elements.charCount.textContent = `${elements.inputText.value.length} chars`;
    }
}

function handleKeyDown(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        transformText();
    }
}

function clearInput() {
    if (elements.inputText) {
        elements.inputText.value = '';
        updateCharCount();
        elements.inputText.focus();
    }
}

// =============================================================================
// Preferences
// =============================================================================

function loadPrefs() {
    try {
        const p = JSON.parse(localStorage.getItem('nnrt_prefs') || '{}');
        if (p.useLLM && elements.llmToggle) {
            useLLM = true;
            elements.llmToggle.checked = true;
        }
        if (p.showLogs && elements.logsToggle && elements.logsPanel) {
            showLogs = true;
            elements.logsToggle.checked = true;
            elements.logsPanel.classList.remove('hidden');
        }
    } catch (e) { }
}

function savePrefs() {
    localStorage.setItem('nnrt_prefs', JSON.stringify({ useLLM, showLogs }));
}

// =============================================================================
// Sidebars
// =============================================================================

function openSidebar(id) {
    closeAllSidebars();
    document.getElementById(id)?.classList.add('open');
    elements.sidebarBackdrop?.classList.add('visible');
}

function closeSidebar(id) {
    document.getElementById(id)?.classList.remove('open');
    elements.sidebarBackdrop?.classList.remove('visible');
}

function closeAllSidebars() {
    document.querySelectorAll('.sidebar').forEach(s => s.classList.remove('open'));
    elements.sidebarBackdrop?.classList.remove('visible');
}

// =============================================================================
// History
// =============================================================================

async function loadHistory() {
    try {
        const r = await fetch(`${API_BASE}/history`);
        if (r.ok) history = await r.json();
    } catch (e) {
        history = JSON.parse(localStorage.getItem('nnrt_history') || '[]');
    }
    renderHistory();
}

function renderHistory() {
    if (!elements.historyList) return;
    elements.historyList.innerHTML = history.length
        ? history.map(h => `
            <div class="history-item" onclick="loadHistoryItem('${h.id}')">
                <div class="history-time">${formatTime(h.timestamp)}</div>
                <div class="history-preview">${escapeHtml(h.preview || '')}</div>
            </div>
        `).join('')
        : '<div class="empty-state">No history yet</div>';
}

async function loadHistoryItem(id) {
    try {
        const r = await fetch(`${API_BASE}/history/${id}`);
        if (r.ok) {
            const item = await r.json();
            if (elements.inputText) elements.inputText.value = item.input || '';
            updateCharCount();
            displayResults(item);
            closeSidebar('historySidebar');
        }
    } catch (e) { }
}

async function saveToHistory(result) {
    try {
        await fetch(`${API_BASE}/history`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(result),
        });
    } catch (e) {
        history.unshift({ id: result.id, timestamp: result.timestamp, preview: (result.input || '').substring(0, 80) + '...', status: result.status });
        history = history.slice(0, 50);
        localStorage.setItem('nnrt_history', JSON.stringify(history));
    }
    loadHistory();
}

// =============================================================================
// Examples
// =============================================================================

async function loadExamples() {
    try {
        const r = await fetch(`${API_BASE}/examples`);
        if (r.ok) examples = await r.json();
        renderExamples(examples);
    } catch (e) {
        if (elements.examplesList) elements.examplesList.innerHTML = '<div class="empty-state">Server not connected</div>';
    }
}

function renderExamples(list) {
    if (!elements.examplesList) return;
    elements.examplesList.innerHTML = list.length
        ? list.map(ex => `
            <div class="example-item" onclick="useExample('${ex.id}')">
                <div class="example-category">${ex.category || ''}</div>
                <div class="example-name">${escapeHtml(ex.name || '')}</div>
                <div class="example-preview">${escapeHtml((ex.text || '').substring(0, 80))}...</div>
            </div>
        `).join('')
        : '<div class="empty-state">No examples</div>';
}

function filterExamples() {
    const q = (elements.exampleSearch?.value || '').toLowerCase();
    renderExamples(examples.filter(ex =>
        (ex.name || '').toLowerCase().includes(q) ||
        (ex.text || '').toLowerCase().includes(q)
    ));
}

function useExample(id) {
    const ex = examples.find(e => e.id === id);
    if (ex && elements.inputText) {
        elements.inputText.value = ex.text || '';
        updateCharCount();
        closeSidebar('examplesSidebar');
        elements.inputText.focus();
    }
}

function findOnlineResources() {
    window.open('https://www.google.com/search?q=police+incident+report+example+filetype:pdf', '_blank');
}

// =============================================================================
// Utilities
// =============================================================================

function escapeHtml(text) {
    if (!text) return '';
    const d = document.createElement('div');
    d.textContent = String(text);
    return d.innerHTML;
}

function formatTime(iso) {
    if (!iso) return 'Unknown';
    try {
        const d = new Date(iso);
        const diff = Date.now() - d.getTime();
        if (diff < 60000) return 'Just now';
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
        return d.toLocaleDateString();
    } catch (e) { return 'Unknown'; }
}

// Global exports for onclick handlers
window.togglePanel = togglePanel;
window.closeSidebar = closeSidebar;
window.closeAllSidebars = closeAllSidebars;
window.loadHistoryItem = loadHistoryItem;
window.useExample = useExample;
