<template>
  <div class="chat-interface">
    
    <!-- Chat History Area -->
    <div class="chat-history" ref="chatContainer">
      <div class="chat-content">
        
        <!-- Welcome State -->
        <div v-if="history.length === 0 && !result && !loading" class="welcome-state">
          <div class="welcome-icon">
            <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="white" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
          </div>
          <h2 class="welcome-title">
            How can I help you today?
          </h2>
          <p class="welcome-subtitle">
            Select an agent and ask questions about your data. I can generate SQL, visualize results, and provide insights.
          </p>
          
          <div class="suggestions-grid">
             <button 
              v-for="ex in examples" 
              :key="ex"
              class="suggestion-card"
              @click="question = ex"
            >
              "{{ ex }}"
            </button>
          </div>
        </div>

        <!-- Chat Items -->
        <div class="messages-list">
            <div v-for="item in history" :key="item.id" class="message-wrapper animate-slideIn">
            
            <!-- User Message -->
            <div class="message user">
                <div class="message-bubble user-bubble">
                <p>{{ item.question }}</p>
                </div>
            </div>
            
            <!-- AI Response -->
            <div class="message ai">
                <div class="avatar ai-avatar">AI</div>
                <div class="message-content">
                    <div class="response-card">
                        <!-- Meta Info -->
                        <div class="response-meta">
                            <span class="intent-badge">
                                {{ item.result.intent_type || 'Query' }}
                            </span>
                            <span v-if="item.result.database_used" class="db-badge">
                                <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                                {{ item.result.database_used.name }}
                            </span>
                            <span class="timestamp">{{ formatTime(item.timestamp) }}</span>
                        </div>

                        <!-- SQL Block -->
                        <div class="sql-block">
                            <div class="sql-header">
                                <span>Generated SQL</span>
                                <button class="copy-btn" @click="copySQL(item.result.sql)">
                                    <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                                    Copy
                                </button>
                            </div>
                            <div class="sql-code-container">
                                <pre class="sql-code">{{ item.result.sql }}</pre>
                            </div>
                        </div>
                        
                        <!-- Explanation -->
                        <div class="explanation">
                            <p>{{ item.result.explanation }}</p>
                        </div>

                        <!-- Data Table -->
                        <div v-if="item.result.data && item.result.data.rows" class="data-result">
                            <div class="data-header">
                                <span class="data-title">Result Data</span>
                                <span class="data-count">{{ item.result.data.row_count }} rows found</span>
                            </div>
                            <div class="table-wrapper">
                                <table class="result-table">
                                    <thead>
                                        <tr>
                                            <th v-for="col in item.result.data.columns" :key="col">{{ col }}</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="(row, idx) in item.result.data.rows.slice(0, 5)" :key="idx">
                                            <td v-for="(cell, cidx) in row" :key="cidx">{{ formatCell(cell) }}</td>
                                        </tr>
                                    </tbody>
                                </table>
                                <div v-if="item.result.data.rows.length > 5" class="table-more">
                                    Showing first 5 rows...
                                </div>
                            </div>
                        </div>
                        
                        <!-- Visualization Placeholder -->
                         <div v-if="item.result.visualization" class="viz-result">
                            <div class="data-header">
                                <span class="data-title">Visualization</span>
                            </div>
                            <div class="chart-placeholder">
                                Visualization available (Chart Integration Pending)
                            </div>
                         </div>
                    </div>
                </div>
            </div>
            </div>

            <!-- Current Loading State -->
            <div v-if="loading" class="message ai animate-pulse">
                <div class="avatar ai-avatar">AI</div>
                    <div class="message-content">
                        <div class="loading-bubble">
                            <div class="typing-indicator">
                                <span></span><span></span><span></span>
                            </div>
                            <span>Thinking...</span>
                        </div>
                </div>
            </div>
        </div>
      </div>
    </div>

    <!-- Input Area (Fixed Bottom) -->
    <div class="input-area">
      <form @submit.prevent="submitQuery" class="input-form">
        <!-- Agent Selector (Floating) -->
        <div class="agent-floater" v-if="agents.length > 0">
           <span class="agent-label">Using Agent:</span>
            <div class="select-wrapper">
                <select v-model="selectedAgentId" class="agent-select">
                    <option :value="null">Default System</option>
                    <option v-for="agent in agents" :key="agent.id" :value="agent.id">{{ agent.name }}</option>
                </select>
                <div class="select-icon">
                  <svg viewBox="0 0 20 20" fill="currentColor"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
                </div>
            </div>
        </div>

        <div class="input-wrapper">
          <input
            v-model="question"
            type="text"
            class="main-input"
            placeholder="Ask a question about your data..."
            :disabled="loading"
          />
          <button 
            type="submit" 
            class="send-btn"
            :disabled="loading || !question.trim()"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
      </form>
      <div class="disclaimer">
         <p>AI Query Agent can make mistakes. Verify important results.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import axios from 'axios'

// Props
const props = defineProps({
  showHistory: Boolean
})

// State
const question = ref('')
const loading = ref(false)
const history = ref([])
const result = ref(null)
const agents = ref([])
const selectedAgentId = ref(null)
const chatContainer = ref(null)

const examples = [
  'Show total revenue by month for last year',
  'List top 5 customers by order volume',
  'Find products with low stock levels'
]

const api = axios.create({
  baseURL: '/api',
  timeout: 120000
})

// Lifecycle
onMounted(async () => {
    await fetchAgents()
})

async function fetchAgents() {
    try {
        const response = await api.get('/agents')
        agents.value = response.data
    } catch (e) {
        console.error("Failed to fetch agents", e)
    }
}

// Watch history to scroll to bottom
watch(history.value, () => {
  scrollToBottom()
})

function scrollToBottom() {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight + 100
    }
  })
}

async function submitQuery() {
  if (!question.value.trim() || loading.value) return
  
  const q = question.value
  question.value = '' // Clear input immediately
  loading.value = true
  
  // Create optimistic user message
  const userMsgId = Date.now()
  history.value.push({
      id: userMsgId,
      question: q,
      timestamp: new Date(),
      result: null // Placeholder
  })
  scrollToBottom()
  
  try {
    const payload = {
      question: q,
      agent_id: selectedAgentId.value
    }
    
    const response = await api.post('/query/with-context', payload)
    
    // Replace last item with full result
    const idx = history.value.findIndex(x => x.id === userMsgId)
    if (idx !== -1) {
        history.value[idx].result = response.data
    }
    
  } catch (err) {
    console.error(err)
    // Handle error in chat
    const idx = history.value.findIndex(x => x.id === userMsgId)
    if (idx !== -1) {
        history.value[idx].result = {
            error: err.response?.data?.detail || err.message || 'Query failed',
            sql: '-- Error generating SQL',
            explanation: 'An error occurred while processing your request.',
            data: null
        }
    }
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function copySQL(sql) {
  if (sql) {
    navigator.clipboard.writeText(sql)
  }
}

function formatCell(value) {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') {
    return value.toLocaleString()
  }
  return String(value)
}

function formatTime(date) {
  const d = new Date(date)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
/* Component-Level CSS for Premium Feel */

.chat-interface {
  height: 100%; /* Fill parent */
  display: flex;
  flex-direction: column;
  position: relative;
  background-color: var(--bg-dark);
}

.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  scroll-behavior: smooth;
  padding-bottom: 140px; /* Space for fixed input */
}

.chat-content {
  max-width: 900px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* Welcome State */
.welcome-state {
  text-align: center;
  padding: 80px 20px;
  animation: fadeIn 0.8s ease-out;
}

.welcome-icon {
  width: 64px;
  height: 64px;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
  border-radius: 20px;
  margin: 0 auto 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 30px -10px rgba(59, 130, 246, 0.5);
}

.welcome-title {
  font-size: 32px;
  font-weight: 700;
  margin-bottom: 12px;
  background: linear-gradient(to right, #60a5fa, #c084fc);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.welcome-subtitle {
  font-size: 16px;
  color: var(--text-secondary);
  max-width: 500px;
  margin: 0 auto 40px;
  line-height: 1.6;
}

.suggestions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  max-width: 800px;
  margin: 0 auto;
}

.suggestion-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 16px;
  text-align: left;
  font-size: 14px;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.suggestion-card:hover {
  border-color: var(--accent-primary);
  background: rgba(255, 255, 255, 0.03);
  transform: translateY(-2px);
}

/* Messages */
.messages-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.message-wrapper {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  width: 100%;
}

.message.user {
  justify-content: flex-end;
}

.message.ai {
  justify-content: flex-start;
  gap: 12px;
}

.user-bubble {
  background: var(--accent-primary);
  color: white;
  padding: 12px 20px;
  border-radius: 20px;
  border-top-right-radius: 4px;
  max-width: 80%;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
  font-size: 15px;
  line-height: 1.5;
}

.ai-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  box-shadow: 0 0 15px rgba(139, 92, 246, 0.3);
}

.message-content {
  flex: 1;
  max-width: 100%;
  overflow: hidden;
}

.response-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  border-top-left-radius: 4px;
  padding: 20px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
  width: 100%;
}

.response-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
  font-size: 12px;
}

.intent-badge {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  padding: 2px 8px;
  border-radius: 4px;
  text-transform: uppercase;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.db-badge {
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  color: #60a5fa;
  padding: 2px 8px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 4px;
}

.timestamp {
  margin-left: auto;
  color: var(--text-muted);
}

/* SQL Block */
.sql-block {
  margin-bottom: 20px;
  background: #0d1117; /* Very dark for code */
  border: 1px solid var(--border-color);
  border-radius: 8px;
  overflow: hidden;
}

.sql-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border-bottom: 1px solid var(--border-color);
}

.sql-header span {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
}

.copy-btn {
  background: transparent;
  border: none;
  color: var(--accent-primary);
  font-size: 11px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 4px;
}

.copy-btn:hover {
  text-decoration: underline;
}

.sql-code-container {
  padding: 12px;
  overflow-x: auto;
}

.sql-code {
  font-family: 'Fira Code', 'Menlo', monospace;
  font-size: 13px;
  color: #4ade80; /* Bright Green */
  white-space: pre-wrap;
  margin: 0;
}

.explanation {
  margin-bottom: 20px;
  padding-left: 12px;
  border-left: 3px solid var(--accent-primary);
}

.explanation p {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.6;
}

/* Data Table */
.data-result {
  border-top: 1px solid var(--border-color);
  padding-top: 16px;
}

.data-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.data-title {
  font-weight: 600;
  font-size: 14px;
}

.data-count {
  font-size: 12px;
  color: var(--text-muted);
}

.table-wrapper {
  overflow-x: auto;
  border: 1px solid var(--border-color);
  border-radius: 8px;
}

.result-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  text-align: left;
}

.result-table th {
  background: rgba(255, 255, 255, 0.03);
  padding: 10px 16px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-color);
  white-space: nowrap;
}

.result-table td {
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-color);
  color: var(--text-secondary);
  white-space: nowrap;
}

.result-table tr:hover td {
  background: rgba(255, 255, 255, 0.02);
}

.result-table tr:last-child td {
  border-bottom: none;
}

.table-more {
  padding: 8px;
  text-align: center;
  font-size: 12px;
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.01);
  border-top: 1px solid var(--border-color);
  font-style: italic;
}

/* Loading Bubble */
.loading-bubble {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 20px;
  border-top-left-radius: 4px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  width: fit-content;
}

.loading-bubble span {
  font-size: 14px;
  color: var(--text-secondary);
}

.typing-indicator span {
  display: inline-block;
  width: 6px;
  height: 6px;
  background-color: var(--text-secondary);
  border-radius: 50%;
  margin: 0 2px;
  animation: typing 1.4s infinite ease-in-out both;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

/* Input Area */
.input-area {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 24px;
  background: rgba(15, 17, 21, 0.85); /* Glass effect background */
  backdrop-filter: blur(12px);
  border-top: 1px solid var(--border-color);
  z-index: 50;
}

.input-form {
  max-width: 900px;
  margin: 0 auto;
  position: relative;
}

.agent-floater {
  position: absolute;
  top: -40px;
  left: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-card);
  padding: 6px 12px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
}

.agent-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  background: #0f1115;
  padding: 2px 6px;
  border-radius: 4px;
}

.select-wrapper {
  position: relative;
}

.agent-select {
  appearance: none;
  background: transparent;
  border: none;
  color: var(--text-primary);
  font-size: 13px;
  padding-right: 20px;
  cursor: pointer;
}

.agent-select:focus {
  outline: none;
}

.select-icon {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 14px;
  height: 14px;
  pointer-events: none;
  color: var(--text-secondary);
}

.input-wrapper {
  position: relative;
}

.main-input {
  width: 100%;
  background: #1c2128;
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 16px 60px 16px 20px; /* Right padding for button */
  font-size: 16px;
  color: var(--text-primary);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  transition: all 0.2s;
}

.main-input:focus {
  outline: none;
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.2);
}

.send-btn {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 40px;
  background: var(--accent-primary);
  border: none;
  border-radius: 10px;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;
}

.send-btn:hover:not(:disabled) {
  background: var(--accent-hover);
  transform: translateY(-50%) scale(1.05);
}

.send-btn:disabled {
  background: #30363d;
  color: #8b949e;
  cursor: not-allowed;
}

.disclaimer {
  text-align: center;
  margin-top: 12px;
  font-size: 12px;
  color: var(--text-muted);
}

/* Animations */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.animate-slideIn {
  animation: slideIn 0.4s ease-out forwards;
}

.animate-pulse {
  animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: .7; }
}

@keyframes typing {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(0.6); opacity: 0.6; }
}
</style>
