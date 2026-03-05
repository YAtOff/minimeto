// Meto Log Viewer - Frontend JavaScript

/**
 * @typedef {Object} LogEntry
 * @property {string} message
 * @property {number|null} turn
 * @property {string} timestamp
 * @property {string|null} agent_name
 * @property {string} level
 * @property {string} type
 */

/**
 * @typedef {Object} TurnGroup
 * @property {number} turnNumber
 * @property {LogEntry[]} entries
 * @property {{prompt: number, cached: number, completion: number}|null} tokenUsage
 * @property {boolean} [hasMatches]
 */

/**
 * @typedef {Object} LogData
 * @property {LogEntry[]} entries
 * @property {{prompt: number, cached: number, completion: number}|null} token_usage
 * @property {Object<string, {prompt: number, cached: number, completion: number}>} turn_tokens
 */

document.addEventListener('DOMContentLoaded', () => {
    const logFileSelect = document.getElementById('log-file');
    const refreshBtn = document.getElementById('refresh-btn');
    const logContent = document.getElementById('log-content');

    // === Search State ===
    /** @type {string} */
    let currentSearchTerm = '';

    /** @type {number|null} */
    let searchDebounceTimer = null;

    const SEARCH_DEBOUNCE_MS = 150;

    /** @type {LogData|null} */
    let currentLogData = null;

    /** @type {Set<string>} */
    let activeFilters = new Set();

    // Load log files on page load
    loadLogFiles();

    // Event listeners
    logFileSelect.addEventListener('change', (e) => {
        if (e.target.value) {
            loadLogFile(e.target.value);
        } else {
            // Hide search container and reset state
            document.getElementById('search-container').style.display = 'none';
            document.getElementById('search-input').value = '';
            currentSearchTerm = '';
            currentLogData = null;
            activeFilters.clear();
            
            // Reset filter buttons
            document.querySelectorAll('.filter-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            logContent.innerHTML = '<p class="placeholder">Select a log file to view its contents.</p>';
        }
    });

    refreshBtn.addEventListener('click', () => {
        loadLogFiles();
        if (logFileSelect.value) {
            loadLogFile(logFileSelect.value);
        }
    });

    // === Search Functionality ===

    const searchContainer = document.getElementById('search-container');
    const searchInput = document.getElementById('search-input');
    const searchClearBtn = document.getElementById('search-clear-btn');

    // Search input with debounce
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => {
            handleSearch(e.target.value);
        }, SEARCH_DEBOUNCE_MS);
    });

    // Clear button
    searchClearBtn.addEventListener('click', () => {
        searchInput.value = '';
        handleSearch('');
        searchInput.focus();
    });

    // Keyboard shortcut: Ctrl+F to focus search
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            if (searchContainer.style.display !== 'none') {
                e.preventDefault();
                searchInput.focus();
                searchInput.select();
            }
        }
    });

    // Filter button click handlers
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const type = btn.dataset.type;
            if (activeFilters.has(type)) {
                activeFilters.delete(type);
                btn.classList.remove('active');
            } else {
                activeFilters.add(type);
                btn.classList.add('active');
            }
            handleSearch(currentSearchTerm);  // Re-render with new filter
        });
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
     * Classify entry type based on level field and message content
     * @param {Object} entry - Log entry object
     * @returns {string} Entry type: 'error', 'warning', 'user-input', 'reasoning', 'tool-call', 'result', or 'other'
     */
    function classifyEntryType(entry) {
        // Check level field first for errors and warnings
        if (entry.level === 'ERROR') {
            return 'error';
        }
        if (entry.level === 'WARNING') {
            return 'warning';
        }
        
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
     * Group entries by turn number with token usage
     * @param {Array} entries - Array of log entries
     * @param {Object} turnTokens - Dict mapping turn number (as string) to token usage
     * @returns {Array} Sorted array of turn groups
     */
    function groupEntriesByTurn(entries, turnTokens) {
        const turnGroups = {};
        
        entries.forEach(entry => {
            const turnNum = entry.turn !== null ? entry.turn : 0;
            const turnKey = `turn-${turnNum}`;
            
            if (!turnGroups[turnKey]) {
                // JSON serialization converts int keys to strings, so use string lookup
                turnGroups[turnKey] = {
                    turnNumber: turnNum,
                    entries: [],
                    tokenUsage: turnTokens[String(turnNum)] || null
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

    /**
     * Display log content (entry point)
     * Stores data for search filtering and shows search UI
     * @param {LogData} data - Log data from API
     */
    function displayLogContent(data) {
        // Store for search filtering
        currentLogData = data;
        
        // Show search container
        document.getElementById('search-container').style.display = 'flex';
        
        // Clear any existing search
        document.getElementById('search-input').value = '';
        currentSearchTerm = '';
        
        // Render (no filter)
        displayLogContentFiltered(data, '');
    }

    /**
     * Handle search input changes
     * @param {string} searchTerm - The search term
     */
    function handleSearch(searchTerm) {
        currentSearchTerm = searchTerm.trim().toLowerCase();
        
        if (!currentLogData) return;
        
        // Re-render with filter
        displayLogContentFiltered(currentLogData, currentSearchTerm);
    }

    /**
     * Display log content with optional filtering
     * @param {LogData} data - Log data object
     * @param {string} searchTerm - Search term for filtering (empty = show all)
     */
    function displayLogContentFiltered(data, searchTerm) {
        const container = document.getElementById('log-content');
        
        if (!data.entries || data.entries.length === 0) {
            container.innerHTML = '<p class="placeholder">No entries found in this log file.</p>';
            updateSearchCount(0, 0);
            return;
        }

        // Create container for all content
        const fragment = document.createDocumentFragment();
        
        // Token summary at top (unchanged by filtering)
        if (data.token_usage) {
            const tokenSummary = createTokenSummary(data.token_usage);
            fragment.appendChild(tokenSummary);
        }
        
        // Group entries by turn
        const turnGroups = groupEntriesByTurn(data.entries, data.turn_tokens || {});
        
        // Filter and count matches
        let totalMatches = 0;
        const filteredGroups = [];
        
        turnGroups.forEach(group => {
            const filteredEntries = [];
            let groupHasMatches = false;
            
            group.entries.forEach(entry => {
                // Check both search term and type filters
                const matchesSearch = searchTerm === '' || 
                    entry.message.toLowerCase().includes(searchTerm);
                const matchesFilter = activeFilters.size === 0 || 
                    activeFilters.has(entry.type);
                const matches = matchesSearch && matchesFilter;
                
                if (matches) {
                    filteredEntries.push(entry);
                    groupHasMatches = true;
                    if (searchTerm !== '' || activeFilters.size > 0) {
                        totalMatches++;
                    }
                }
            });
            
            if ((searchTerm === '' && activeFilters.size === 0) || groupHasMatches) {
                filteredGroups.push({
                    ...group,
                    entries: filteredEntries,
                    hasMatches: groupHasMatches
                });
            }
        });
        
        // Build timeline
        const timeline = document.createElement('div');
        timeline.className = 'timeline';
        
        if (filteredGroups.length === 0 && (searchTerm !== '' || activeFilters.size > 0)) {
            // No matches found
            const noResults = document.createElement('div');
            noResults.className = 'no-results';
            noResults.innerHTML = `
                <i class="fas fa-search"></i>
                <p>No entries match your criteria</p>
                <p style="margin-top: 8px; font-size: 13px;">Try a different search term or clear filters</p>
            `;
            timeline.appendChild(noResults);
        } else {
            filteredGroups.forEach(group => {
                const turnElement = createTurnElementFiltered(group, searchTerm);
                timeline.appendChild(turnElement);
            });
        }
        
        fragment.appendChild(timeline);
        
        // Clear and render
        container.innerHTML = '';
        container.appendChild(fragment);
        
        // Update match count
        const isFiltering = searchTerm !== '' || activeFilters.size > 0;
        const totalEntries = isFiltering ? data.entries.length : 0;
        updateSearchCount(totalMatches, totalEntries);
    }

    function createTokenSummary(tokenUsage) {
        const div = document.createElement('div');
        div.className = 'token-summary';
        const total = tokenUsage.prompt + tokenUsage.completion;
        div.innerHTML = `
            <strong>Token Summary:</strong>
            <span class="token-total">${total.toLocaleString()} total</span>
            <span class="token-detail">(Prompt: ${tokenUsage.prompt.toLocaleString()}, Cached: ${tokenUsage.cached.toLocaleString()}, Completion: ${tokenUsage.completion.toLocaleString()})</span>
        `;
        return div;
    }

    /**
     * Create turn element with filtering support
     * @param {TurnGroup} turnGroup - Turn group data
     * @param {string} searchTerm - Current search term
     * @returns {HTMLElement}
     */
    function createTurnElementFiltered(turnGroup, searchTerm) {
        const turnDiv = document.createElement('div');
        turnDiv.className = 'turn-group';
        turnDiv.setAttribute('data-turn', turnGroup.turnNumber);
        
        if (!turnGroup.hasMatches && searchTerm !== '') {
            turnDiv.classList.add('partial-match');
        }
        
        // Turn header with marker
        const header = document.createElement('div');
        header.className = 'turn-header';
        
        const marker = document.createElement('div');
        marker.className = 'turn-marker';
        marker.innerHTML = `<span class="turn-number">${turnGroup.turnNumber === 0 ? 'Init' : turnGroup.turnNumber}</span>`;
        header.appendChild(marker);
        
        // Token usage (unchanged - shows original turn tokens)
        if (turnGroup.tokenUsage) {
            const tokens = document.createElement('span');
            tokens.className = 'turn-tokens';
            tokens.innerHTML = `
                <span class="token-prompt">${turnGroup.tokenUsage.prompt.toLocaleString()} in</span>
                <span class="token-cached">(${turnGroup.tokenUsage.cached.toLocaleString()} cached)</span>
                <span class="token-completion">${turnGroup.tokenUsage.completion.toLocaleString()} out</span>
            `;
            header.appendChild(tokens);
        }
        
        turnDiv.appendChild(header);
        
        // Entries container
        const entriesDiv = document.createElement('div');
        entriesDiv.className = 'turn-entries';
        
        turnGroup.entries.forEach(entry => {
            const entryElement = createEntryElementFiltered(entry, searchTerm);
            entriesDiv.appendChild(entryElement);
        });
        
        turnDiv.appendChild(entriesDiv);
        
        return turnDiv;
    }

    /**
     * Create entry element with search highlighting
     * @param {LogEntry} entry - Log entry
     * @param {string} searchTerm - Current search term
     * @returns {HTMLElement}
     */
    function createEntryElementFiltered(entry, searchTerm) {
        const entryDiv = document.createElement('div');
        entryDiv.className = `log-entry entry-${entry.type}`;
        
        const iconMap = {
            'user-input': 'fa-user',
            'reasoning': 'fa-brain',
            'tool-call': 'fa-wrench',
            'result': 'fa-check-circle',
            'other': 'fa-circle',
            'error': 'fa-exclamation-triangle',
            'warning': 'fa-exclamation-circle'
        };
        
        const typeLabelMap = {
            'user-input': 'User',
            'reasoning': 'Reasoning',
            'tool-call': 'Tool',
            'result': 'Result',
            'other': 'Info',
            'error': 'Error',
            'warning': 'Warning'
        };
        
        // Highlight message if searching
        const messageHtml = searchTerm !== '' 
            ? highlightText(escapeHtml(entry.message), searchTerm)
            : escapeHtml(entry.message);
        
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
                <div class="message">${messageHtml}</div>
            </div>
        `;
        
        return entryDiv;
    }

    /**
     * Highlight search term in text (case-insensitive)
     * IMPORTANT: Text must already be HTML-escaped before calling this function
     * @param {string} text - Already escaped HTML text
     * @param {string} searchTerm - Search term to highlight
     * @returns {string} Text with <span class="highlight"> wrapped matches
     */
    function highlightText(text, searchTerm) {
        if (!searchTerm) return text;
        
        // Escape special regex characters in search term
        const escapedTerm = searchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        
        // Case-insensitive match
        const regex = new RegExp(`(${escapedTerm})`, 'gi');
        
        return text.replace(regex, '<span class="highlight">$1</span>');
    }

    /**
     * Update search match count display
     * @param {number} matches - Number of matching entries
     * @param {number} total - Total entries (only shown when filtering)
     */
    function updateSearchCount(matches, total) {
        const searchCount = document.getElementById('search-count');
        
        if (total === 0) {
            // No search/filter active
            searchCount.textContent = '';
            searchCount.className = 'search-count';
        } else if (matches === 0) {
            searchCount.textContent = 'No matches';
            searchCount.className = 'search-count no-matches';
        } else {
            const filterNames = Array.from(activeFilters).map(t => 
                t.charAt(0).toUpperCase() + t.slice(1)
            ).join(', ');
            const filterText = filterNames ? ` (filtered: ${filterNames})` : '';
            searchCount.textContent = `${matches} of ${total} entries${filterText}`;
            searchCount.className = 'search-count has-matches';
        }
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
