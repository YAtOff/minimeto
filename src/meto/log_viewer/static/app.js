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

    // === Entry Classification ===

    /**
     * Classify entry type based on message content and level
     * @param {Object} entry - Log entry object
     * @returns {string} Entry type: 'user-input', 'reasoning', 'tool-call', 'result', or 'other'
     */
    function classifyEntryType(entry) {
        const message = entry.message.toLowerCase();
        
        // User input patterns
        if (message.includes('user input:') ||
            message.includes('user:') ||
            message.startsWith('processing user')) {
            return 'user-input';
        }
        
        // Tool call patterns
        if (message.includes('calling tool') ||
            message.includes('running tool') ||
            message.includes('executing tool') ||
            message.includes('function call') ||
            message.includes('tool call')) {
            return 'tool-call';
        }
        
        // Result patterns
        if (message.includes('tool result') ||
            message.includes('result:') ||
            message.includes('output:') ||
            message.includes('response:')) {
            return 'result';
        }
        
        // System/setup patterns (go to 'other')
        if (message.includes('system prompt') ||
            message.includes('session') ||
            message.includes('initializing')) {
            return 'other';
        }
        
        // Default to reasoning for INFO level
        return 'reasoning';
    }

    // === Turn Grouping ===

    /**
     * Group entries by turn number
     * @param {Array} entries - Array of log entries
     * @returns {Array} Sorted array of turn groups
     */
    function groupEntriesByTurn(entries) {
        const turnGroups = {};
        
        entries.forEach(entry => {
            const turnNum = entry.turn !== null ? entry.turn : 0;
            const turnKey = `turn-${turnNum}`;
            
            if (!turnGroups[turnKey]) {
                turnGroups[turnKey] = {
                    turnNumber: turnNum,
                    entries: []
                };
            }
            
            turnGroups[turnKey].entries.push({
                ...entry,
                type: classifyEntryType(entry)
            });
        });
        
        // Convert to sorted array
        return Object.values(turnGroups).sort((a, b) => a.turnNumber - b.turnNumber);
    }

    // === Rendering ===

    function displayLogContent(data) {
        const container = document.getElementById('log-content');
        
        if (!data.entries || data.entries.length === 0) {
            container.innerHTML = '<p class="placeholder">No entries found in this log file.</p>';
            return;
        }

        // Create container for all content
        const fragment = document.createDocumentFragment();
        
        // Token summary at top
        if (data.token_usage) {
            const tokenSummary = createTokenSummary(data.token_usage);
            fragment.appendChild(tokenSummary);
        }
        
        // Group entries by turn
        const turnGroups = groupEntriesByTurn(data.entries);
        
        // Build timeline
        const timeline = document.createElement('div');
        timeline.className = 'timeline';
        
        turnGroups.forEach(group => {
            const turnElement = createTurnElement(group);
            timeline.appendChild(turnElement);
        });
        
        fragment.appendChild(timeline);
        
        // Clear and render
        container.innerHTML = '';
        container.appendChild(fragment);
    }

    function createTokenSummary(tokenUsage) {
        const div = document.createElement('div');
        div.className = 'token-summary';
        div.innerHTML = `
            <strong>Token Summary:</strong>
            Prompt: ${tokenUsage.prompt.toLocaleString()},
            Cached: ${tokenUsage.cached.toLocaleString()},
            Completion: ${tokenUsage.completion.toLocaleString()}
        `;
        return div;
    }

    function createTurnElement(turnGroup) {
        const turnDiv = document.createElement('div');
        turnDiv.className = 'turn-group';
        turnDiv.setAttribute('data-turn', turnGroup.turnNumber);
        
        // Turn header with marker
        const header = document.createElement('div');
        header.className = 'turn-header';
        header.innerHTML = `
            <div class="turn-marker">
                <span class="turn-number">${turnGroup.turnNumber === 0 ? 'Init' : turnGroup.turnNumber}</span>
            </div>
        `;
        
        // Entries container
        const entriesDiv = document.createElement('div');
        entriesDiv.className = 'turn-entries';
        
        turnGroup.entries.forEach(entry => {
            const entryElement = createEntryElement(entry);
            entriesDiv.appendChild(entryElement);
        });
        
        turnDiv.appendChild(header);
        turnDiv.appendChild(entriesDiv);
        
        return turnDiv;
    }

    function createEntryElement(entry) {
        const entryDiv = document.createElement('div');
        entryDiv.className = `log-entry entry-${entry.type}`;
        
        const iconMap = {
            'user-input': 'fa-user',
            'reasoning': 'fa-brain',
            'tool-call': 'fa-wrench',
            'result': 'fa-check-circle',
            'other': 'fa-circle'
        };
        
        const typeLabelMap = {
            'user-input': 'User',
            'reasoning': 'Reasoning',
            'tool-call': 'Tool',
            'result': 'Result',
            'other': 'Info'
        };
        
        entryDiv.innerHTML = `
            <span class="entry-icon">
                <i class="fas ${iconMap[entry.type]}"></i>
            </span>
            <div class="entry-content">
                <div class="entry-header">
                    <span class="entry-type-label">${typeLabelMap[entry.type]}</span>
                    <span class="timestamp">${formatDate(entry.timestamp)}</span>
                    ${entry.agent_name ? `<span class="agent">[${entry.agent_name}]</span>` : ''}
                </div>
                <div class="message">${escapeHtml(entry.message)}</div>
            </div>
        `;
        
        return entryDiv;
    }

    // === Utility Functions ===

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
