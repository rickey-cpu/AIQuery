/**
 * AI Query Agent - Frontend Application
 * Handles chat, schema viewer, and query history
 */

// API Base URL
const API_BASE = '/api';

// State
let isLoading = false;
let currentView = 'chat';

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    loadSchema();
    loadHistory();
    autoResizeTextarea();
});

// Navigation
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const viewId = item.dataset.view;
            switchView(viewId);
            
            // Update active state
            navItems.forEach(n => n.classList.remove('active'));
            item.classList.add('active');
        });
    });
}

function switchView(viewId) {
    currentView = viewId;
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });
    document.getElementById(`${viewId}-view`).classList.add('active');
}

// Auto-resize textarea
function autoResizeTextarea() {
    const textarea = document.getElementById('query-input');
    textarea.addEventListener('input', () => {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
    });
}

// Handle keyboard shortcuts
function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendQuery();
    }
}

// Send example query
function sendExample(question) {
    document.getElementById('query-input').value = question;
    sendQuery();
}

// Send query
async function sendQuery() {
    const input = document.getElementById('query-input');
    const question = input.value.trim();
    
    if (!question || isLoading) return;
    
    isLoading = true;
    updateSendButton(true);
    
    // Clear welcome message and add user message
    const messagesContainer = document.getElementById('chat-messages');
    const welcome = messagesContainer.querySelector('.welcome-message');
    if (welcome) welcome.remove();
    
    addMessage('user', question);
    input.value = '';
    input.style.height = 'auto';
    
    // Add loading message
    const loadingId = addLoadingMessage();
    
    try {
        const response = await fetch(`${API_BASE}/query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question, execute: true })
        });
        
        const data = await response.json();
        
        // Remove loading
        removeMessage(loadingId);
        
        if (data.success) {
            addAssistantMessage(data);
        } else {
            addErrorMessage(data.error || 'Failed to process query');
        }
        
        // Refresh history
        loadHistory();
        
    } catch (error) {
        removeMessage(loadingId);
        addErrorMessage(`Connection error: ${error.message}`);
    }
    
    isLoading = false;
    updateSendButton(false);
}

// Add user message
function addMessage(type, content) {
    const container = document.getElementById('chat-messages');
    const avatar = type === 'user' ? '👤' : '🤖';
    
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    messageDiv.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-text">${escapeHtml(content)}</div>
        </div>
    `;
    
    container.appendChild(messageDiv);
    scrollToBottom();
}

// Add assistant message with SQL and results
function addAssistantMessage(data) {
    const container = document.getElementById('chat-messages');
    
    let dataTableHtml = '';
    if (data.data && data.data.columns && data.data.rows) {
        dataTableHtml = `
            <div class="data-table-container">
                <table class="data-table">
                    <thead>
                        <tr>${data.data.columns.map(col => `<th>${escapeHtml(col)}</th>`).join('')}</tr>
                    </thead>
                    <tbody>
                        ${data.data.rows.slice(0, 10).map(row => `
                            <tr>${row.map(cell => `<td>${escapeHtml(String(cell))}</td>`).join('')}</tr>
                        `).join('')}
                    </tbody>
                </table>
                ${data.data.rows.length > 10 ? `<p style="padding: 12px; color: var(--text-muted); font-size: 12px;">Showing 10 of ${data.data.row_count} rows</p>` : ''}
            </div>
        `;
    }
    
    const warningsHtml = data.warnings && data.warnings.length > 0 
        ? `<div style="margin-top: 12px; padding: 8px 12px; background: rgba(245, 158, 11, 0.1); border-radius: 8px; font-size: 13px; color: var(--warning);">
             ⚠️ ${data.warnings.join(', ')}
           </div>`
        : '';
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="message-text">${escapeHtml(data.explanation || 'Query completed successfully')}</div>
            <div class="sql-block">
                <div class="sql-header">
                    <span>SQL Query</span>
                    <button class="copy-btn" onclick="copySQL(this)">Copy</button>
                </div>
                <pre class="sql-code">${escapeHtml(data.sql)}</pre>
            </div>
            ${dataTableHtml}
            ${warningsHtml}
        </div>
    `;
    
    container.appendChild(messageDiv);
    scrollToBottom();
}

// Add loading message
function addLoadingMessage() {
    const container = document.getElementById('chat-messages');
    const id = 'loading-' + Date.now();
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.id = id;
    messageDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="message-text">
                <span class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </span>
                Analyzing your question...
            </div>
        </div>
    `;
    
    container.appendChild(messageDiv);
    scrollToBottom();
    return id;
}

// Add error message
function addErrorMessage(error) {
    const container = document.getElementById('chat-messages');
    
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="message-content">
            <div class="message-text" style="color: var(--error);">
                ❌ ${escapeHtml(error)}
            </div>
        </div>
    `;
    
    container.appendChild(messageDiv);
    scrollToBottom();
}

// Remove message by ID
function removeMessage(id) {
    const message = document.getElementById(id);
    if (message) message.remove();
}

// Copy SQL to clipboard
function copySQL(button) {
    const sql = button.closest('.sql-block').querySelector('.sql-code').textContent;
    navigator.clipboard.writeText(sql).then(() => {
        button.textContent = 'Copied!';
        setTimeout(() => button.textContent = 'Copy', 2000);
    });
}

// Update send button state
function updateSendButton(loading) {
    const btn = document.getElementById('send-btn');
    btn.disabled = loading;
    btn.innerHTML = loading 
        ? '<span class="loading-dots"><span></span><span></span><span></span></span>'
        : '<span class="send-icon">➤</span>';
}

// Scroll to bottom
function scrollToBottom() {
    const container = document.getElementById('chat-messages');
    container.scrollTop = container.scrollHeight;
}

// Load schema
async function loadSchema() {
    try {
        const response = await fetch(`${API_BASE}/schema`);
        const data = await response.json();
        
        const container = document.getElementById('schema-content');
        container.innerHTML = data.tables.map(table => `
            <div class="schema-table">
                <div class="schema-table-header">
                    <h3>📋 ${table.name}</h3>
                    <p>${table.description || 'No description'}</p>
                </div>
                <div class="schema-columns">
                    ${table.columns.map(col => `
                        <div class="schema-column">
                            <span class="column-name">
                                ${col.primary_key ? '🔑 ' : ''}${col.name}
                            </span>
                            <span class="column-type">${col.type}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load schema:', error);
    }
}

// Load history
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/history`);
        const data = await response.json();
        
        const container = document.getElementById('history-list');
        
        if (!data.items || data.items.length === 0) {
            container.innerHTML = '<p style="color: var(--text-muted); text-align: center;">No queries yet</p>';
            return;
        }
        
        container.innerHTML = data.items.reverse().map(item => `
            <div class="history-item" onclick="loadFromHistory('${escapeHtml(item.question)}')">
                <div class="history-question">${escapeHtml(item.question)}</div>
                <div class="history-sql">${escapeHtml(item.sql)}</div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

// Load query from history
function loadFromHistory(question) {
    switchView('chat');
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector('[data-view="chat"]').classList.add('active');
    
    document.getElementById('query-input').value = question;
}

// Clear history
async function clearHistory() {
    try {
        await fetch(`${API_BASE}/history`, { method: 'DELETE' });
        loadHistory();
    } catch (error) {
        console.error('Failed to clear history:', error);
    }
}

// Escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
