// Meto Log Viewer App

// State
let logFiles = [];
let currentFile = null;
let currentData = null;
let searchQuery = '';
let errorOnly = false;

// DOM Elements
const logList = document.getElementById('log-list');
const logContent = document.getElementById('log-content');
const searchContainer = document.getElementById('search-container');
const searchInput = document.getElementById('search-input');
const searchCount = document.getElementById('search-count');
const errorOnlyCheckbox = document.getElementById('error-only');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadLogFiles();
    setupSearch();
    setupErrorFilter();
});

// Setup search functionality
function setupSearch() {
    searchInput.addEventListener('input', (e) => {
        searchQuery = e.target.value.trim().toLowerCase();
        if (currentData) {
            renderLogContent(currentData);
        }
    });
}

// Setup error-only filter
function setupErrorFilter() {
    errorOnlyCheckbox.addEventListener('change', (e) => {
        errorOnly = e.target.checked;
        if (currentData) {
            renderLogContent(currentData);
        }
    });
}

// Load list of log files
async function loadLogFiles() {
    try {
        const response = await fetch('/api/logs');
        logFiles = await response.json();
        renderLogList();
    } catch (error) {
        logList.innerHTML = `<div class="error">Failed to load log files: ${error.message}</div>`;
    }
}

// Render log file list
function renderLogList() {
    if (logFiles.length === 0) {
        logList.innerHTML = '<div class="empty">No log files found</div>';
        return;
    }

    logList.innerHTML = logFiles.map(file => `
        <div class="log-file ${currentFile === file.filename ? 'active' : ''}"
             onclick="selectFile('${file.filename}')">
            <div class="filename">${escapeHtml(file.filename)}</div>
            <div class="meta">${formatSize(file.size)} • ${formatDate(file.modified)}</div>
        </div>
    `).join('');
}

// Select and load a log file
async function selectFile(filename) {
    currentFile = filename;
    renderLogList(); // Update active state

    logContent.innerHTML = '<div class="loading">Loading...</div>';
    logContent.classList.add('loading');

    // Show search bar when a file is loaded
    searchContainer.classList.remove('hidden');

    try {
        const response = await fetch(`/api/logs/${encodeURIComponent(filename)}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        currentData = await response.json();
        renderLogContent(currentData);
    } catch (error) {
        logContent.innerHTML = `<div class="error">Failed to load log: ${error.message}</div>`;
    } finally {
        logContent.classList.remove('loading');
    }
}

// Render log content with timeline view
function renderLogContent(data) {
    const { entries, total_tokens, tokens_per_turn } = data;

    // Filter entries
    let filteredEntries = entries;

    // Apply error-only filter
    if (errorOnly) {
        filteredEntries = filteredEntries.filter(entry => entry.level === 'ERROR');
    }

    // Apply search filter
    if (searchQuery) {
        filteredEntries = filteredEntries.filter(entry =>
            entry.message.toLowerCase().includes(searchQuery) ||
            entry.agent_name.toLowerCase().includes(searchQuery) ||
            (entry.turn !== null && entry.turn.toString().includes(searchQuery))
        );
    }

    // Update search count
    if (searchQuery || errorOnly) {
        searchCount.textContent = `${filteredEntries.length} of ${entries.length} entries`;
    } else {
        searchCount.textContent = '';
    }

    // Group entries by turn
    const turns = groupByTurn(filteredEntries);

    let html = `
        <div class="token-summary">
            <div class="stat">
                <span class="value">${formatNumber(total_tokens.prompt)}</span>
                <span class="label">Prompt Tokens</span>
            </div>
            <div class="stat">
                <span class="value">${formatNumber(total_tokens.cached)}</span>
                <span class="label">Cached Tokens</span>
            </div>
            <div class="stat">
                <span class="value">${formatNumber(total_tokens.completion)}</span>
                <span class="label">Completion Tokens</span>
            </div>
        </div>
        <div class="timeline">
    `;

    if (filteredEntries.length === 0 && (searchQuery || errorOnly)) {
        html += '<div class="no-results">No entries match your filters</div>';
    } else {
        // Render each turn as a timeline item
        for (const [turnNum, turnEntries] of turns) {
            const turnTokens = tokens_per_turn[turnNum.toString()] || tokens_per_turn[turnNum];
            html += renderTurn(turnNum, turnEntries, turnTokens);
        }
    }

    html += '</div>';
    logContent.innerHTML = html;
}

// Group entries by turn number
function groupByTurn(entries) {
    const turns = new Map();

    for (const entry of entries) {
        const turnKey = entry.turn !== null ? entry.turn : 'pre';
        if (!turns.has(turnKey)) {
            turns.set(turnKey, []);
        }
        turns.get(turnKey).push(entry);
    }

    // Sort by turn number (put 'pre' entries first)
    return new Map([...turns.entries()].sort((a, b) => {
        if (a[0] === 'pre') return -1;
        if (b[0] === 'pre') return 1;
        return a[0] - b[0];
    }));
}

// Render a turn in the timeline
function renderTurn(turnNum, entries, turnTokens) {
    const isPreTurn = turnNum === 'pre';
    const turnLabel = isPreTurn ? 'Initialization' : `Turn ${turnNum}`;

    // Classify entries
    const classified = classifyEntries(entries);

    // Build token usage display
    let tokenHtml = '';
    if (turnTokens && (turnTokens.prompt > 0 || turnTokens.completion > 0)) {
        tokenHtml = `
            <div class="turn-tokens">
                <span class="token-item" title="Prompt tokens">📝 ${formatNumber(turnTokens.prompt)}</span>
                ${turnTokens.cached > 0 ? `<span class="token-item cached" title="Cached tokens">⚡ ${formatNumber(turnTokens.cached)}</span>` : ''}
                <span class="token-item" title="Completion tokens">💬 ${formatNumber(turnTokens.completion)}</span>
            </div>
        `;
    }

    let html = `
        <div class="turn-block ${isPreTurn ? 'turn-pre' : ''}">
            <div class="turn-header">
                <span class="turn-number">${turnLabel}</span>
                <span class="turn-count">${entries.length} entries</span>
                ${tokenHtml}
            </div>
            <div class="turn-content">
    `;

    // Render entries by type with icons
    if (classified.userInput) {
        html += renderEntryWithType(classified.userInput, 'user', '→');
    }

    if (classified.reasoning.length > 0) {
        for (const entry of classified.reasoning) {
            html += renderEntryWithType(entry, 'reasoning', '💭');
        }
    }

    if (classified.toolCalls.length > 0) {
        for (const entry of classified.toolCalls) {
            html += renderEntryWithType(entry, 'tool', '🔧');
        }
    }

    if (classified.toolResults.length > 0) {
        for (const entry of classified.toolResults) {
            const isError = entry.level === 'ERROR';
            html += renderEntryWithType(entry, isError ? 'error' : 'result', isError ? '❌' : '✓');
        }
    }

    if (classified.other.length > 0) {
        for (const entry of classified.other) {
            const icon = entry.level === 'ERROR' ? '❌' : '•';
            html += renderEntryWithType(entry, entry.level.toLowerCase(), icon);
        }
    }

    html += '</div></div>';
    return html;
}

// Classify entries by type
function classifyEntries(entries) {
    return {
        userInput: entries.find(e => e.message.startsWith('User input:')),
        reasoning: entries.filter(e => e.message.includes('reasoning:') || e.message.includes('reasoning:')),
        toolCalls: entries.filter(e => e.message.startsWith('Tool selected:')),
        toolResults: entries.filter(e => e.message.includes('result:')),
        other: entries.filter(e =>
            !e.message.startsWith('User input:') &&
            !e.message.includes('reasoning:') &&
            !e.message.startsWith('Tool selected:') &&
            !e.message.includes('result:')
        )
    };
}

// Render entry with type-specific styling
function renderEntryWithType(entry, type, icon) {
    const levelClass = entry.level.toLowerCase();
    const highlightedMessage = searchQuery
        ? highlightText(escapeHtml(entry.message), searchQuery)
        : escapeHtml(entry.message);

    // Add error class for error entries
    const errorClass = entry.level === 'ERROR' ? 'entry-error' : '';

    return `
        <div class="entry ${levelClass} entry-${type} ${errorClass}">
            <div class="entry-header">
                <span class="entry-icon">${icon}</span>
                <span class="timestamp">${formatTimestamp(entry.timestamp)}</span>
                <span class="level">${escapeHtml(entry.level)}</span>
                <span class="agent-name">${escapeHtml(entry.agent_name)}</span>
            </div>
            <div class="message">${highlightedMessage}</div>
        </div>
    `;
}

// Highlight matching text
function highlightText(text, query) {
    if (!query) return text;

    const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
}

// Escape regex special characters
function escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Render a single entry (legacy, used for non-timeline views)
function renderEntry(entry) {
    const levelClass = entry.level.toLowerCase();
    return `
        <div class="entry ${levelClass}">
            <div class="header">
                <span class="timestamp">${formatTimestamp(entry.timestamp)}</span>
                <span class="level">${escapeHtml(entry.level)}</span>
                <span class="agent-name">${escapeHtml(entry.agent_name)}</span>
                ${entry.turn !== null ? `<span class="turn">Turn ${entry.turn}</span>` : ''}
            </div>
            <div class="message">${escapeHtml(entry.message)}</div>
        </div>
    `;
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

function formatTimestamp(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleTimeString();
}

function formatNumber(num) {
    return num.toLocaleString();
}
