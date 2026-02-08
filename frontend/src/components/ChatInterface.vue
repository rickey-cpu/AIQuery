<template>
  <div class="chat-interface">
    <div class="container">
      <!-- Query Section -->
      <section class="query-section animate-fadeIn">
        <div class="query-card card card-glow">
          <h2>Ask anything about your data</h2>
          
          <!-- Agent Selector -->
          <div v-if="agents.length > 0" class="agent-selector">
            <label for="agent-select">Using Agent:</label>
            <select id="agent-select" v-model="selectedAgentId" class="select-input">
              <option :value="null">Default Agent</option>
              <option v-for="agent in agents" :key="agent.id" :value="agent.id">
                {{ agent.name }}
              </option>
            </select>
            <div v-if="selectedAgentId" class="agent-info">
              <small>{{ getSelectedAgentDescription() }}</small>
            </div>
          </div>
          
          <form @submit.prevent="submitQuery">
            <div class="input-group">
              <input
                v-model="question"
                type="text"
                class="input query-input"
                placeholder="e.g., Show total revenue by month"
                :disabled="loading"
              />
              <button type="submit" class="btn btn-primary" :disabled="loading || !question.trim()">
                <span v-if="loading" class="loader"></span>
                <template v-else>
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="22" y1="2" x2="11" y2="13"/>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                  </svg>
                  Query
                </template>
              </button>
            </div>
          </form>
          
          <!-- Quick Examples -->
          <div class="examples">
            <span class="examples-label">Try:</span>
            <button 
              v-for="ex in examples" 
              :key="ex"
              class="example-btn"
              @click="question = ex"
            >
              {{ ex }}
            </button>
          </div>
        </div>
      </section>
      
      <!-- Results Section -->
      <section v-if="result" class="results-section animate-fadeIn">
        <!-- Intent Badge + DB Info -->
        <div class="result-meta">
          <span class="badge badge-info">{{ result.intent_type || 'data_retrieval' }}</span>
          <span v-if="result.cached" class="badge badge-success">Cached</span>
          <span v-if="result.database_used" class="badge badge-warning" :title="result.database_used.type">
            DB: {{ result.database_used.name }}
          </span>
        </div>
        
        <!-- SQL Display -->
        <div class="sql-card card">
          <div class="sql-header">
            <h3>Generated SQL</h3>
            <button class="btn btn-ghost" @click="copySQL">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
              Copy
            </button>
          </div>
          <pre class="code">{{ result.sql }}</pre>
          <p class="explanation">{{ result.explanation }}</p>
        </div>
        
        <!-- Visualization -->
        <div v-if="result.visualization" class="chart-card card">
          <h3>{{ result.visualization.title || 'Results' }}</h3>
          <div class="chart-container">
            <canvas ref="chartCanvas"></canvas>
          </div>
        </div>
        
        <!-- Data Table -->
        <div v-if="result.data && result.data.rows" class="data-card card">
          <div class="data-header">
            <h3>Data Results</h3>
            <span class="row-count">{{ result.data.row_count }} rows</span>
          </div>
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th v-for="col in result.data.columns" :key="col">{{ col }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(row, idx) in result.data.rows.slice(0, 50)" :key="idx">
                  <td v-for="(cell, cidx) in row" :key="cidx">{{ formatCell(cell) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
      
      <!-- Error Display -->
      <section v-if="error" class="error-section animate-fadeIn">
        <div class="error-card card">
          <div class="error-icon">
            <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
          <h3>Query Failed</h3>
          <p>{{ error }}</p>
        </div>
      </section>
      
      <!-- History Sidebar -->
      <aside v-if="showHistory" class="history-sidebar glass animate-fadeIn">
        <div class="sidebar-header">
          <h3>Query History</h3>
          <button class="btn btn-ghost" @click="toggleHistory(false)">×</button>
        </div>
        <div class="history-list">
          <div 
            v-for="item in history" 
            :key="item.id"
            class="history-item"
            @click="loadHistory(item)"
          >
            <p class="history-question">{{ item.question }}</p>
            <div class="history-meta">
              <span class="history-time">{{ formatTime(item.timestamp) }}</span>
              <span v-if="item.agent_id" class="history-agent">Agent</span>
            </div>
          </div>
          <p v-if="!history.length" class="empty-history">No queries yet</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, defineExpose, defineProps, toRef } from 'vue'
import axios from 'axios'
import Chart from 'chart.js/auto'

const props = defineProps({
  showHistory: Boolean
})

const emit = defineEmits(['update:showHistory'])

// State
const question = ref('')
const loading = ref(false)
const result = ref(null)
const error = ref(null)
const history = ref([])
const chartCanvas = ref(null)
const agents = ref([])
const selectedAgentId = ref(null)
let chartInstance = null

// Examples
const examples = [
  'Show revenue by month',
  'Top 10 customers by orders',
  'Sales trend last 6 months'
]

// API
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

function getSelectedAgentDescription() {
    const agent = agents.value.find(a => a.id === selectedAgentId.value)
    return agent ? agent.description : ''
}

function toggleHistory(val) {
    emit('update:showHistory', val)
}

// Submit query
async function submitQuery() {
  if (!question.value.trim() || loading.value) return
  
  loading.value = true
  error.value = null
  result.value = null
  
  try {
    const payload = {
      question: question.value,
      agent_id: selectedAgentId.value
    }
    
    // Use multi-database endpoint if agent selected, else context endpoint
    // Actually both use process_query but context one returns more info usually
    // Let's stick to /query/with-context but added agent_id support in backend
    const response = await api.post('/query/with-context', payload)
    
    result.value = response.data
    
    // Add to history
    history.value.unshift({
      id: Date.now(),
      question: question.value,
      timestamp: new Date(),
      result: response.data,
      agent_id: selectedAgentId.value
    })
    
    // Keep only last 20
    if (history.value.length > 20) {
      history.value = history.value.slice(0, 20)
    }
    
    // Render chart
    await nextTick()
    if (result.value.visualization) {
      renderChart()
    }
    
  } catch (err) {
    console.error(err)
    error.value = err.response?.data?.detail || err.message || 'Query failed'
  } finally {
    loading.value = false
  }
}

// Render Chart.js
function renderChart() {
  if (!chartCanvas.value || !result.value?.visualization) return
  
  // Destroy existing
  if (chartInstance) {
    chartInstance.destroy()
  }
  
  const viz = result.value.visualization
  const data = viz.options?.data
  
  if (!data) return
  
  const config = {
    type: viz.type === 'line' ? 'line' : viz.type === 'pie' ? 'doughnut' : 'bar',
    data: data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: '#94a3b8' }
        }
      },
      scales: viz.type !== 'pie' ? {
        x: {
          ticks: { color: '#64748b' },
          grid: { color: 'rgba(148, 163, 184, 0.1)' }
        },
        y: {
          ticks: { color: '#64748b' },
          grid: { color: 'rgba(148, 163, 184, 0.1)' }
        }
      } : {}
    }
  }
  
  chartInstance = new Chart(chartCanvas.value, config)
}

// Copy SQL
function copySQL() {
  if (result.value?.sql) {
    navigator.clipboard.writeText(result.value.sql)
  }
}

// Load from history
function loadHistory(item) {
  question.value = item.question
  result.value = item.result
  selectedAgentId.value = item.agent_id || null
  toggleHistory(false)
  
  nextTick(() => {
    if (result.value?.visualization) {
      renderChart()
    }
  })
}

// Format helpers
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

defineExpose({
    loadHistory
})
</script>

<style scoped>
.container {
  max-width: 1000px;
  margin: 0 auto;
}

/* Query Section */
.query-section {
  margin-bottom: 32px;
}

.query-card {
  text-align: center;
  padding: 48px 32px;
  background: var(--gradient-card), var(--bg-card);
}

.query-card h2 {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 24px;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.input-group {
  display: flex;
  gap: 12px;
  max-width: 700px;
  margin: 0 auto;
}

.query-input {
  font-size: 16px;
  padding: 16px 20px;
}

.agent-selector {
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.select-input {
  padding: 8px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-primary);
  min-width: 200px;
}

.agent-info {
    color: var(--text-muted);
    font-size: 12px;
}

.examples {
  margin-top: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.examples-label {
  color: var(--text-muted);
  font-size: 13px;
}

.example-btn {
  background: var(--bg-tertiary);
  border: none;
  padding: 6px 12px;
  border-radius: 9999px;
  font-size: 13px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.example-btn:hover {
  background: var(--accent-primary);
  color: white;
}

/* Results */
.results-section {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.result-meta {
  display: flex;
  gap: 8px;
}

.sql-card .sql-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.sql-card h3 {
  font-size: 16px;
  font-weight: 600;
}

.sql-card .code {
  margin-bottom: 16px;
  white-space: pre-wrap;
  word-break: break-word;
}

.explanation {
  color: var(--text-secondary);
  font-size: 14px;
}

/* Chart */
.chart-card {
  padding: 24px;
}

.chart-card h3 {
  margin-bottom: 16px;
  font-size: 16px;
}

.chart-container {
  height: 300px;
  position: relative;
}

/* Data Table */
.data-card .data-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.data-card h3 {
  font-size: 16px;
  font-weight: 600;
}

.row-count {
  color: var(--text-muted);
  font-size: 13px;
}

/* Error */
.error-card {
  text-align: center;
  padding: 32px;
  border-color: var(--accent-error);
}

.error-icon {
  color: var(--accent-error);
  margin-bottom: 16px;
}

.error-card h3 {
  color: var(--accent-error);
  margin-bottom: 8px;
}

.error-card p {
  color: var(--text-secondary);
}

/* History Sidebar */
.history-sidebar {
  position: fixed;
  right: 0;
  top: 0;
  bottom: 0;
  width: 320px;
  padding: 24px;
  border-left: 1px solid var(--border-color);
  overflow-y: auto;
  z-index: 200;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.sidebar-header h3 {
  font-size: 16px;
  font-weight: 600;
}

.history-item {
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
  margin-bottom: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  background: var(--bg-tertiary);
}

.history-question {
  font-size: 14px;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.history-time {
  font-size: 12px;
  color: var(--text-muted);
}

.history-agent {
    font-size: 10px;
    background: var(--bg-tertiary);
    padding: 2px 6px;
    border-radius: 4px;
    color: var(--text-secondary);
}

.empty-history {
  text-align: center;
  color: var(--text-muted);
  padding: 24px;
}

@media (max-width: 768px) {
  .query-card {
    padding: 32px 20px;
  }
  
  .query-card h2 {
    font-size: 22px;
  }
  
  .input-group {
    flex-direction: column;
  }
  
  .history-sidebar {
    width: 100%;
  }
}
</style>
