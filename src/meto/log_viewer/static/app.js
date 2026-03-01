// Meto Log Viewer App

// State
let logFiles = [];
let currentFile = null;

// DOM Elements
const logList = document.getElementById('log-list');
const logContent = document.getElementById('log-content');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadLogFiles();
});

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

    try {
        const response = await fetch(`/api/logs/${encodeURIComponent(filename)}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const data = await response.json();
        renderLogContent(data);
    } catch (error) {
        logContent.innerHTML = `<div class="error">Failed to load log: ${error.message}</div>`;
    } finally {
        logContent.classList.remove('loading');
    }
}

// Render log content
function renderLogContent(data) {
    const { entries, total_tokens } = data;

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
        <div class="entries">
    `;

    for (const entry of entries) {
        html += renderEntry(entry);
    }

    html += '</div>';
    logContent.innerHTML = html;
}

// Render a single entry
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
