/**
 * NNRT Web Interface — Application Logic (v2 with Filters)
 */

const API_BASE = 'http://localhost:5050/api';

// State
let currentResult = null;
let examples = [];
let history = [];
let logs = [];
let useLLM = false;
let showLogs = false;
let showMetadata = false;
let outputMode = 'prose';  // prose, structured, raw
let fastMode = false;      // no_prose mode

// Filter state for each panel
const filters = {
    atomicStatements: 'all',    // all, observation, claim, interpretation, quote
    statements: 'all',          // all + dynamic types
    entities: 'all',            // all, reporter, subject, witness, organization, location
    events: 'all',              // all, action, state, speech
    diagnostics: 'all',         // all, error, warning, info
};

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
        modeSelect: document.getElementById('modeSelect'),
        fastModeToggle: document.getElementById('fastModeToggle'),
        statusIndicator: document.getElementById('statusIndicator'),
        statusText: document.getElementById('statusText'),
        stats: document.getElementById('stats'),
        outputText: document.getElementById('outputText'),
        outputBadge: document.getElementById('outputBadge'),
        // NEW: Atomic statements
        atomicStatementsList: document.getElementById('atomicStatementsList'),
        atomicStatementsBadge: document.getElementById('atomicStatementsBadge'),
        // Legacy statements
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
        metadataToggle: document.getElementById('metadataToggle'),
        metadataPanel: document.getElementById('metadataPanel'),
        metadataGrid: document.getElementById('metadataGrid'),
        metadataBadge: document.getElementById('metadataBadge'),
        extractedPanel: document.getElementById('extractedPanel'),
        extractedGrid: document.getElementById('extractedGrid'),
        extractedBadge: document.getElementById('extractedBadge'),
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

    // Mode selector
    elements.modeSelect?.addEventListener('change', (e) => {
        outputMode = e.target.value;
        savePrefs();
        addLog(`Output mode: ${outputMode}`);
        // Disable fast mode for raw (it's already no-prose)
        if (outputMode === 'raw') {
            elements.fastModeToggle.checked = false;
            fastMode = false;
        }
    });

    // Fast mode (no prose)
    elements.fastModeToggle?.addEventListener('change', (e) => {
        fastMode = e.target.checked;
        savePrefs();
        addLog(fastMode ? '⚡ Fast mode enabled (no prose)' : 'Fast mode disabled');
    });

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
    elements.metadataToggle?.addEventListener('change', (e) => {
        showMetadata = e.target.checked;
        savePrefs();
        const metadataPanel = document.getElementById('metadataPanel');
        const extractedPanel = document.getElementById('extractedPanel');
        if (showMetadata) {
            metadataPanel?.classList.remove('hidden');
            metadataPanel?.classList.remove('collapsed');
            extractedPanel?.classList.remove('hidden');
            extractedPanel?.classList.remove('collapsed');
        } else {
            metadataPanel?.classList.add('hidden');
            extractedPanel?.classList.add('hidden');
        }
    });
    elements.exampleSearch?.addEventListener('input', filterExamples);

    // Load data
    loadExamples();
    loadHistory();
    loadPrefs();

    // Add collapse footers to panels
    initPanelFooters();

    // Initialize scroll-to-top button
    initScrollToTop();

    console.log('NNRT v2 initialized');
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

function initPanelFooters() {
    // Add collapse footer to all panels with panel-content
    const panels = document.querySelectorAll('.panel');
    panels.forEach(panel => {
        const content = panel.querySelector('.panel-content');
        if (!content) return;

        // Check if footer already exists
        if (content.querySelector('.panel-footer')) return;

        const panelId = panel.id;
        const footer = document.createElement('div');
        footer.className = 'panel-footer';
        footer.innerHTML = `
            <button class="collapse-btn" onclick="collapsePanel('${panelId}')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="18 15 12 9 6 15"></polyline>
                </svg>
                <span>Collapse</span>
            </button>
        `;
        content.appendChild(footer);
    });
}

function initScrollToTop() {
    const scrollBtn = document.getElementById('scrollToTop');
    const mainContent = document.querySelector('.main-content');

    if (!scrollBtn || !mainContent) return;

    // Show/hide button based on scroll position
    mainContent.addEventListener('scroll', () => {
        if (mainContent.scrollTop > 300) {
            scrollBtn.classList.add('visible');
        } else {
            scrollBtn.classList.remove('visible');
        }
    });
}

function scrollToTop() {
    const mainContent = document.querySelector('.main-content');
    if (mainContent) {
        mainContent.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

// =============================================================================
// Filter Functions
// =============================================================================

function setFilter(panel, value) {
    filters[panel] = value;

    // Update active state on filter chips
    const filterBar = document.querySelector(`[data-filter-panel="${panel}"]`);
    if (filterBar) {
        filterBar.querySelectorAll('.filter-chip').forEach(chip => {
            chip.classList.toggle('active', chip.dataset.filter === value);
        });
    }

    // Re-render the panel with the filter
    if (currentResult) {
        reRenderFilteredPanel(panel);
    }
}

function reRenderFilteredPanel(panel) {
    if (!currentResult) return;

    switch (panel) {
        case 'atomicStatements':
            renderAtomicStatements(currentResult.atomic_statements || []);
            break;
        case 'statements':
            renderStatements(currentResult.statements || []);
            break;
        case 'entities':
            renderEntities(currentResult.entities || []);
            break;
        case 'events':
            renderEvents(currentResult.events || []);
            break;
        case 'diagnostics':
            renderDiagnostics(currentResult.diagnostics || []);
            break;
    }
}

function buildFilterBar(panel, filterOptions) {
    return `
        <div class="filter-bar" data-filter-panel="${panel}">
            ${filterOptions.map(opt => `
                <button class="filter-chip ${filters[panel] === opt.value ? 'active' : ''} ${opt.color || ''}"
                        data-filter="${opt.value}"
                        onclick="setFilter('${panel}', '${opt.value}')">
                    ${opt.label}
                </button>
            `).join('')}
        </div>
    `;
}

// =============================================================================
// Copy to Clipboard
// =============================================================================

async function copyOutput() {
    const text = currentResult?.rendered_text;
    if (!text) return;

    try {
        await navigator.clipboard.writeText(text);
        // Show feedback
        const btn = document.getElementById('copyOutputBtn');
        if (btn) {
            const originalHTML = btn.innerHTML;
            btn.innerHTML = '✓ Copied';
            btn.classList.add('copied');
            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.classList.remove('copied');
            }, 1500);
        }
    } catch (err) {
        console.error('Failed to copy:', err);
    }
}

// =============================================================================
// Structured Document Formatter
// =============================================================================

function formatAsStructuredDocument(result) {
    const entities = result.entities || [];
    const events = result.events || [];
    const atomicStatements = result.atomic_statements || [];
    const identifiers = result.extracted || {};

    // Group entities by role
    const entityByRole = {};
    entities.forEach(e => {
        const role = (e.role || 'other').toUpperCase();
        if (!entityByRole[role]) entityByRole[role] = [];
        entityByRole[role].push(e.label || 'Unknown');
    });

    // Group atomic statements by type
    const statementsByType = {};
    atomicStatements.forEach(s => {
        const type = s.type || 'unknown';
        if (!statementsByType[type]) statementsByType[type] = [];
        statementsByType[type].push(s.text);
    });

    let html = '<div class="structured-document">';

    // ===== HEADER =====
    html += '<div class="doc-main-header">NEUTRALIZED REPORT</div>';

    // ===== PARTIES SECTION =====
    if (entities.length > 0) {
        html += '<div class="doc-section">';
        html += '<div class="doc-section-header">PARTIES</div>';
        html += '<div class="doc-grid">';
        for (const [role, names] of Object.entries(entityByRole)) {
            // Map role names to more general terms
            const roleLabel = role === 'AUTHORITY' ? 'AGENT' : role;
            html += `<div class="doc-row"><span class="doc-key">${roleLabel}:</span><span class="doc-value">${escapeHtml(names.join(', '))}</span></div>`;
        }
        html += '</div></div>';
    }

    // ===== REFERENCE DATA SECTION =====
    const hasIdentifiers = Object.keys(identifiers).length > 0;
    const meta = result.metadata || {};
    if (hasIdentifiers || meta.input_length) {
        html += '<div class="doc-section">';
        html += '<div class="doc-section-header">REFERENCE DATA</div>';
        html += '<div class="doc-grid">';
        // Add extracted identifiers
        for (const [type, items] of Object.entries(identifiers)) {
            if (items && items.length > 0) {
                const values = items.map(i => i.value || i).join(', ');
                html += `<div class="doc-row"><span class="doc-key">${type.charAt(0).toUpperCase() + type.slice(1)}:</span><span class="doc-value">${escapeHtml(values)}</span></div>`;
            }
        }
        html += '</div></div>';
    }

    // ===== ACCOUNT SUMMARY HEADER =====
    html += '<div class="doc-main-header doc-main-header-secondary">ACCOUNT SUMMARY</div>';

    // ===== OBSERVATIONS =====
    if (statementsByType['observation'] && statementsByType['observation'].length > 0) {
        html += '<div class="doc-section">';
        html += '<div class="doc-section-header">OBSERVATIONS</div>';
        html += '<ul class="doc-list">';
        statementsByType['observation'].forEach(text => {
            html += `<li>${escapeHtml(text)}</li>`;
        });
        html += '</ul></div>';
    }

    // ===== CLAIMS =====
    if (statementsByType['claim'] && statementsByType['claim'].length > 0) {
        html += '<div class="doc-section">';
        html += '<div class="doc-section-header">CLAIMS</div>';
        html += '<ul class="doc-list">';
        statementsByType['claim'].forEach(text => {
            html += `<li>${escapeHtml(text)}</li>`;
        });
        html += '</ul></div>';
    }

    // ===== STATEMENTS (Interpretations) =====
    if (statementsByType['interpretation'] && statementsByType['interpretation'].length > 0) {
        html += '<div class="doc-section">';
        html += '<div class="doc-section-header">STATEMENTS</div>';
        html += '<ul class="doc-list">';
        statementsByType['interpretation'].forEach(text => {
            html += `<li>${escapeHtml(text)}</li>`;
        });
        html += '</ul></div>';
    }

    // ===== PRESERVED QUOTES =====
    if (statementsByType['quote'] && statementsByType['quote'].length > 0) {
        html += '<div class="doc-section">';
        html += '<div class="doc-section-header">PRESERVED QUOTES</div>';
        html += '<div class="doc-quotes">';
        statementsByType['quote'].forEach(text => {
            html += `<div class="doc-quote">"${escapeHtml(text)}"</div>`;
        });
        html += '</div></div>';
    }

    // ===== EVENTS =====
    if (events.length > 0) {
        html += '<div class="doc-section">';
        html += '<div class="doc-section-header">RECORDED EVENTS</div>';
        html += '<ul class="doc-list doc-events">';
        events.forEach(e => {
            html += `<li>${escapeHtml(e.description || '')}</li>`;
        });
        html += '</ul></div>';
    }

    // ===== FULL COMPUTED OUTPUT =====
    if (result.rendered_text) {
        html += '<div class="doc-separator"></div>';
        html += '<div class="doc-section">';
        html += '<div class="doc-section-header">FULL NARRATIVE (Computed)</div>';
        html += `<div class="doc-narrative">${escapeHtml(result.rendered_text)}</div>`;
        html += '</div>';
    }

    html += '</div>';
    return html;
}

// =============================================================================
// Clear All Panels (before new transform)
// =============================================================================

function clearAllPanels() {
    // Clear output
    if (elements.outputText) {
        elements.outputText.innerHTML = '<span class="placeholder">Processing...</span>';
    }
    if (elements.outputBadge) elements.outputBadge.textContent = '—';

    // Clear atomic statements
    if (elements.atomicStatementsList) {
        elements.atomicStatementsList.innerHTML = '<div class="empty-state">Processing...</div>';
    }
    if (elements.atomicStatementsBadge) elements.atomicStatementsBadge.textContent = '—';

    // Clear statements
    if (elements.statementsList) {
        elements.statementsList.innerHTML = '<div class="empty-state">Processing...</div>';
    }
    if (elements.statementsBadge) elements.statementsBadge.textContent = '—';

    // Clear entities
    if (elements.entitiesList) {
        elements.entitiesList.innerHTML = '<div class="empty-state">Processing...</div>';
    }
    if (elements.entitiesBadge) elements.entitiesBadge.textContent = '—';

    // Clear events
    if (elements.eventsList) {
        elements.eventsList.innerHTML = '<div class="empty-state">Processing...</div>';
    }
    if (elements.eventsBadge) elements.eventsBadge.textContent = '—';

    // Clear diagnostics
    if (elements.diagnosticsList) {
        elements.diagnosticsList.innerHTML = '<div class="empty-state">Processing...</div>';
    }
    if (elements.diagnosticsBadge) elements.diagnosticsBadge.textContent = '—';

    // Clear transforms
    if (elements.transformsList) {
        elements.transformsList.innerHTML = '<div class="empty-state">Processing...</div>';
    }
    if (elements.transformsBadge) elements.transformsBadge.textContent = '—';

    // Clear stats
    if (elements.stats) {
        elements.stats.innerHTML = '<span class="stat">Processing...</span>';
    }
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

    // Clear all panels immediately for fresh start
    clearAllPanels();

    // Clear logs for fresh start
    logs = [];
    addLog(`Starting transform (${text.length} chars, mode=${outputMode}, fast=${fastMode})`);

    // Show logs panel during processing if enabled
    if (showLogs) {
        const logsPanel = document.getElementById('logsPanel');
        logsPanel?.classList.remove('hidden');
        logsPanel?.classList.remove('collapsed');
    }

    try {
        // Use streaming endpoint for real-time logs
        if (showLogs) {
            await transformWithStreaming(text);
        } else {
            await transformDirect(text);
        }

    } catch (error) {
        console.error('Transform error:', error);
        addLog(`Error: ${error.message}`, 'error');
        showStatus('error', `Error: ${error.message}`);
    } finally {
        if (elements.transformBtn) elements.transformBtn.disabled = false;
    }
}

async function transformDirect(text) {
    const response = await fetch(`${API_BASE}/transform`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            text,
            use_llm: useLLM,
            mode: outputMode,
            no_prose: fastMode
        }),
    });

    if (!response.ok) throw new Error(`HTTP ${response.status}`);

    currentResult = await response.json();
    addLog(`Complete: ${currentResult.status}`);

    displayResults(currentResult);
    saveToHistory(currentResult);
    showStatus('success', 'Transformed successfully');
}

async function transformWithStreaming(text) {
    return new Promise((resolve, reject) => {
        const body = JSON.stringify({
            text,
            use_llm: useLLM,
            mode: outputMode,
            no_prose: fastMode
        });

        // Use fetch for SSE (EventSource doesn't support POST)
        fetch(`${API_BASE}/transform-stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: body
        }).then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            function processChunk() {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        resolve();
                        return;
                    }

                    buffer += decoder.decode(value, { stream: true });

                    // Process complete SSE messages
                    const lines = buffer.split('\n');
                    buffer = lines.pop(); // Keep incomplete line in buffer

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                handleStreamEvent(data);
                            } catch (e) {
                                console.warn('Failed to parse SSE:', line);
                            }
                        }
                    }

                    processChunk();
                }).catch(reject);
            }

            processChunk();
        }).catch(reject);
    });
}

function handleStreamEvent(data) {
    if (data.type === 'log') {
        // Real-time log from server
        addLog(data.message, data.level);
    } else if (data.type === 'error') {
        addLog(`Error: ${data.message}`, 'error');
        showStatus('error', `Error: ${data.message}`);
    } else if (data.type === 'result') {
        // Final result
        currentResult = data;
        addLog(`Complete: ${currentResult.status}`);
        displayResults(currentResult);
        saveToHistory(currentResult);
        showStatus('success', 'Transformed successfully');
    } else if (data.type === 'keepalive') {
        // Ignore keepalive
    }
}

function displayResults(result) {
    // Stats
    if (elements.stats) {
        elements.stats.innerHTML = `
            <span class="stat"><span class="stat-value">${result.stats?.atomic_statements || 0}</span> atomic</span>
            <span class="stat"><span class="stat-value">${result.stats?.statements || 0}</span> statements</span>
            <span class="stat"><span class="stat-value">${result.stats?.entities || 0}</span> entities</span>
            <span class="stat"><span class="stat-value">${result.stats?.events || 0}</span> events</span>
            <span class="stat"><span class="stat-value">${result.metadata?.processing_time_ms || 0}</span>ms</span>
        `;
    }

    // Output - backend handles all formatting based on mode
    if (elements.outputText) {
        const mode = result.metadata?.mode || outputMode;

        if (result.rendered_text) {
            if (mode === 'structured' || mode === 'raw') {
                // Structured/Raw: Plain text with preserved formatting (from backend)
                elements.outputText.innerHTML = `<pre class="output-pre">${escapeHtml(result.rendered_text)}</pre>`;
            } else {
                // Prose: Show flowing neutral text
                elements.outputText.innerHTML = escapeHtml(result.rendered_text);
            }
        } else {
            elements.outputText.innerHTML = '<span class="placeholder">No output generated</span>';
        }
    }
    if (elements.outputBadge) {
        elements.outputBadge.textContent = result.rendered_text ? `${result.rendered_text.length} chars` : 'N/A';
    }
    expandPanel('outputPanel');

    // Atomic Statements with filter
    renderAtomicStatements(result.atomic_statements || []);
    if ((result.atomic_statements || []).length) expandPanel('atomicStatementsPanel');

    // Statements (Legacy) with filter
    renderStatements(result.statements || []);
    // Don't auto-expand legacy statements if we have atomic ones
    if ((result.statements || []).length && !(result.atomic_statements || []).length) expandPanel('statementsPanel');

    // Entities with filter
    renderEntities(result.entities || []);
    if ((result.entities || []).length) expandPanel('entitiesPanel');

    // Events with filter
    renderEvents(result.events || []);
    if ((result.events || []).length) expandPanel('eventsPanel');

    // Diagnostics with filter
    renderDiagnostics(result.diagnostics || []);
    if ((result.diagnostics || []).length) expandPanel('diagnosticsPanel');

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

    // Metadata
    const meta = result.metadata || {};
    const metaCount = Object.keys(meta).length;
    if (elements.metadataBadge) {
        elements.metadataBadge.textContent = metaCount > 0 ? metaCount : '—';
    }
    if (elements.metadataGrid) {
        elements.metadataGrid.innerHTML = `
            <div class="metadata-item">
                <div class="metadata-key">Request ID</div>
                <div class="metadata-value">${escapeHtml(meta.request_id || result.id || 'N/A')}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-key">Processing Time</div>
                <div class="metadata-value">${meta.processing_time_ms || '?'} ms</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-key">Input Length</div>
                <div class="metadata-value">${meta.input_length || result.input?.length || 0} chars</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-key">Output Length</div>
                <div class="metadata-value">${meta.output_length || result.rendered_text?.length || 0} chars</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-key">Pipeline</div>
                <div class="metadata-value">${escapeHtml(meta.pipeline || 'default')}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-key">LLM Mode</div>
                <div class="metadata-value">${meta.llm_mode ? 'Enabled' : 'Disabled'}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-key">Version</div>
                <div class="metadata-value">${escapeHtml(meta.version || '0.1.0')}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-key">Timestamp</div>
                <div class="metadata-value">${escapeHtml(result.timestamp || new Date().toISOString())}</div>
            </div>
        `;
    }
    // Only expand if metadata is enabled
    if (showMetadata) expandPanel('metadataPanel');

    // Extracted data (from content)
    const extracted = result.extracted || {};
    const identifiers = result.identifiers || [];
    const totalExtracted = Object.values(extracted).reduce((sum, arr) => sum + arr.length, 0);

    if (elements.extractedBadge) {
        elements.extractedBadge.textContent = totalExtracted;
    }

    if (elements.extractedGrid) {
        if (totalExtracted > 0) {
            // Pretty names for identifier types
            const typeNames = {
                'badge_number': '🎖️ Badge Numbers',
                'date': '📅 Dates',
                'time': '🕐 Times',
                'location': '📍 Locations',
                'name': '👤 Names',
                'vehicle_plate': '🚗 Vehicle Plates',
                'employee_id': '🪪 Employee IDs',
            };

            elements.extractedGrid.innerHTML = Object.entries(extracted).map(([type, items]) => {
                if (!items.length) return '';
                const typeName = typeNames[type] || type.replace('_', ' ').toUpperCase();
                return `
                    <div class="extracted-section">
                        <div class="extracted-section-title">
                            ${typeName}
                            <span class="extracted-section-count">${items.length}</span>
                        </div>
                        <div class="extracted-items">
                            ${items.map(item =>
                    `<span class="extracted-item ${type}" title="Confidence: ${Math.round((item.confidence || 0) * 100)}%">${escapeHtml(item.value)}</span>`
                ).join('')}
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            elements.extractedGrid.innerHTML = '<div class="empty-state">No identifiers extracted</div>';
        }
    }
    if (showMetadata && totalExtracted > 0) expandPanel('extractedPanel');
}

// =============================================================================
// Panel Render Functions (with filters)
// =============================================================================

function renderAtomicStatements(statements) {
    const filterOptions = [
        { value: 'all', label: 'All' },
        { value: 'observation', label: 'Observation', color: 'observation' },
        { value: 'claim', label: 'Claim', color: 'claim' },
        { value: 'interpretation', label: 'Interpretation', color: 'interpretation' },
        { value: 'quote', label: 'Quote', color: 'quote' },
    ];

    const filtered = filters.atomicStatements === 'all'
        ? statements
        : statements.filter(s => s.type === filters.atomicStatements);

    if (elements.atomicStatementsBadge) {
        elements.atomicStatementsBadge.textContent = `${filtered.length}/${statements.length}`;
    }

    if (elements.atomicStatementsList) {
        elements.atomicStatementsList.innerHTML = `
            ${buildFilterBar('atomicStatements', filterOptions)}
            <div class="filtered-items">
                ${filtered.length ? filtered.map(s => `
                    <div class="atomic-statement">
                        <div class="atomic-statement-header">
                            <span class="stmt-type-badge ${s.type}">${s.type}</span>
                            <div class="stmt-confidence" title="Confidence: ${(s.confidence * 100).toFixed(0)}%">
                                <div class="confidence-bar">
                                    <div class="confidence-fill" style="width: ${s.confidence * 100}%"></div>
                                </div>
                                <span>${(s.confidence * 100).toFixed(0)}%</span>
                            </div>
                            <span class="stmt-id">${s.id}</span>
                        </div>
                        <div class="atomic-statement-text">${escapeHtml(s.text)}</div>
                        <div class="atomic-statement-meta">
                            <span class="meta-tag clause">${s.clause_type}</span>
                            ${s.connector ? `<span class="meta-tag connector">${s.connector}</span>` : ''}
                            ${(s.flags || []).map(f => `<span class="meta-tag flag">${f}</span>`).join('')}
                        </div>
                        ${s.derived_from && s.derived_from.length ? `
                            <div class="provenance-link">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                                </svg>
                                <span>Derived from:</span>
                                <div class="provenance-ids">
                                    ${s.derived_from.map(id => `<span class="provenance-id">${id}</span>`).join('')}
                                </div>
                            </div>
                        ` : ''}
                    </div>
                `).join('') : `<div class="empty-state">No ${filters.atomicStatements === 'all' ? '' : filters.atomicStatements + ' '}statements</div>`}
            </div>
        `;
    }
}

function renderEntities(entities) {
    // Collect unique roles from entities
    const roles = [...new Set(entities.map(e => e.role).filter(Boolean))];
    const filterOptions = [
        { value: 'all', label: 'All' },
        ...roles.map(r => ({ value: r, label: r.charAt(0).toUpperCase() + r.slice(1) }))
    ];

    const filtered = filters.entities === 'all'
        ? entities
        : entities.filter(e => e.role === filters.entities);

    if (elements.entitiesBadge) {
        elements.entitiesBadge.textContent = `${filtered.length}/${entities.length}`;
    }

    if (elements.entitiesList) {
        elements.entitiesList.innerHTML = `
            ${entities.length > 0 ? buildFilterBar('entities', filterOptions) : ''}
            <div class="filtered-items">
                ${filtered.length ? filtered.map(e => `
                    <div class="item-card">
                        <div class="item-header">
                            <span class="item-type">${e.role || ''}</span>
                            <span class="item-id">${e.id || ''}</span>
                        </div>
                        <div class="item-text">${escapeHtml(e.label || '')}</div>
                    </div>
                `).join('') : '<div class="empty-state">No entities</div>'}
            </div>
        `;
    }
}

function renderEvents(events) {
    // Collect unique types from events
    const types = [...new Set(events.map(e => e.type).filter(Boolean))];
    const filterOptions = [
        { value: 'all', label: 'All' },
        ...types.map(t => ({ value: t, label: t.charAt(0).toUpperCase() + t.slice(1) }))
    ];

    const filtered = filters.events === 'all'
        ? events
        : events.filter(e => e.type === filters.events);

    if (elements.eventsBadge) {
        elements.eventsBadge.textContent = `${filtered.length}/${events.length}`;
    }

    if (elements.eventsList) {
        elements.eventsList.innerHTML = `
            ${events.length > 0 ? buildFilterBar('events', filterOptions) : ''}
            <div class="filtered-items">
                ${filtered.length ? filtered.map(e => `
                    <div class="item-card ${e.type || ''}">
                        <div class="item-header">
                            <span class="item-type">${e.type || ''}</span>
                            <span class="item-id">${e.id || ''}</span>
                        </div>
                        <div class="item-text">${escapeHtml(e.description || '')}</div>
                    </div>
                `).join('') : '<div class="empty-state">No events</div>'}
            </div>
        `;
    }
}

function renderDiagnostics(diagnostics) {
    const filterOptions = [
        { value: 'all', label: 'All' },
        { value: 'error', label: 'Error', color: 'error' },
        { value: 'warning', label: 'Warning', color: 'warning' },
        { value: 'info', label: 'Info', color: 'info' },
    ];

    const filtered = filters.diagnostics === 'all'
        ? diagnostics
        : diagnostics.filter(d => d.level === filters.diagnostics);

    if (elements.diagnosticsBadge) {
        elements.diagnosticsBadge.textContent = `${filtered.length}/${diagnostics.length}`;
    }

    if (elements.diagnosticsList) {
        elements.diagnosticsList.innerHTML = `
            ${diagnostics.length > 0 ? buildFilterBar('diagnostics', filterOptions) : ''}
            <div class="filtered-items">
                ${filtered.length ? filtered.map(d => `
                    <div class="item-card ${d.level || ''}">
                        <div class="item-header">
                            <span class="item-type ${d.level || ''}">${d.level || ''}</span>
                            <span class="item-id">${d.code || ''}</span>
                        </div>
                        <div class="item-text">${escapeHtml(d.message || '')}</div>
                    </div>
                `).join('') : '<div class="empty-state">No diagnostics</div>'}
            </div>
        `;
    }
}

function renderStatements(statements) {
    // Collect unique types from statements
    const types = [...new Set(statements.map(s => s.type).filter(Boolean))];
    const filterOptions = [
        { value: 'all', label: 'All' },
        ...types.map(t => ({ value: t, label: t.charAt(0).toUpperCase() + t.slice(1) }))
    ];

    const filtered = filters.statements === 'all'
        ? statements
        : statements.filter(s => s.type === filters.statements);

    if (elements.statementsBadge) {
        elements.statementsBadge.textContent = `${filtered.length}/${statements.length}`;
    }

    if (elements.statementsList) {
        elements.statementsList.innerHTML = `
            ${statements.length > 0 ? buildFilterBar('statements', filterOptions) : ''}
            <div class="filtered-items">
                ${filtered.length ? filtered.map(s => `
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
                `).join('') : '<div class="empty-state">No statements</div>'}
            </div>
        `;
    }
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
        if (p.showMetadata && elements.metadataToggle && elements.metadataPanel) {
            showMetadata = true;
            elements.metadataToggle.checked = true;
            elements.metadataPanel.classList.remove('hidden');
            elements.extractedPanel?.classList.remove('hidden');
        }
        if (p.outputMode && elements.modeSelect) {
            outputMode = p.outputMode;
            elements.modeSelect.value = outputMode;
        }
        if (p.fastMode && elements.fastModeToggle) {
            fastMode = true;
            elements.fastModeToggle.checked = true;
        }
    } catch (e) { }
}

function savePrefs() {
    localStorage.setItem('nnrt_prefs', JSON.stringify({ useLLM, showLogs, showMetadata, outputMode, fastMode }));
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

function clearHistory() {
    if (!confirm('Clear all transformation history?')) return;
    history = [];
    localStorage.removeItem('nnrt_history');
    renderHistory();
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
