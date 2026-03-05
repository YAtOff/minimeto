// Meto Log Viewer - Frontend JavaScript

document.addEventListener('DOMContentLoaded', () => {
    const logFileSelect = document.getElementById('log-file');
    const refreshBtn = document.getElementById('refresh-btn');
    const logContent = document.getElementById('log-content');

    // Load log files on page load
    loadLogFiles();

    // Event listeners
    logFileSelect.addEventListener('change', (e) => {
        if (e.target.value) {
            loadLogFile(e.target.value);
        } else {
            logContent.innerHTML = '<p class="placeholder">Select a log file to view its contents.</p>';
        }
    });

    refreshBtn.addEventListener('click', () => {
        loadLogFiles();
        if (logFileSelect.value) {
            loadLogFile(logFileSelect.value);
        }
    });

    async function loadLogFiles() {
        try {
            const response = await fetch('/api/logs');
            const logs = await response.json();
            
            // Clear existing options except placeholder
            logFileSelect.innerHTML = '<option value="">-- Select a log file --</option>';
            
            logs.forEach(log => {
                const option = document.createElement('option');
                option.value = log.filename;
                option.textContent = `${log.filename} (${formatSize(log.size)}) - ${formatDate(log.modified)}`;
                logFileSelect.appendChild(option);
            });
        } catch (error) {
            console.error('Failed to load log files:', error);
            logContent.innerHTML = '<p class="error">Failed to load log file list.</p>';
        }
    }

    async function loadLogFile(filename) {
        try {
            const response = await fetch(`/api/logs/${encodeURIComponent(filename)}`);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            displayLogContent(data);
        } catch (error) {
            console.error('Failed to load log file:', error);
            logContent.innerHTML = `<p class="error">Failed to load log file: ${error.message}</p>`;
        }
    }

    function displayLogContent(data) {
        if (!data.entries || data.entries.length === 0) {
            logContent.innerHTML = '<p class="placeholder">No entries found in this log file.</p>';
            return;
        }

        let html = '';
        
        // Token usage summary
        if (data.token_usage) {
            const tokens = data.token_usage;
            html += `<div class="token-summary">
                <strong>Token Usage:</strong> 
                Prompt: ${tokens.prompt.toLocaleString()}, 
                Cached: ${tokens.cached.toLocaleString()}, 
                Completion: ${tokens.completion.toLocaleString()}
            </div>`;
        }

        // Log entries
        data.entries.forEach(entry => {
            html += `
                <div class="log-entry">
                    <span class="timestamp">${formatDate(entry.timestamp)}</span>
                    <span class="level ${entry.level}">${entry.level}</span>
                    ${entry.agent_name ? `<span class="agent">[${entry.agent_name}]</span>` : ''}
                    ${entry.turn !== null ? `<span class="turn">(Turn ${entry.turn})</span>` : ''}
                    <div class="message">${escapeHtml(entry.message)}</div>
                </div>
            `;
        });

        logContent.innerHTML = html;
    }

    function formatSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function formatDate(dateStr) {
        const date = new Date(dateStr);
        return date.toLocaleString();
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
