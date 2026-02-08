<template>
  <div class="app">
    <!-- Header -->
    <header class="header glass">
      <div class="header-content">
        <div class="logo">
          <div class="logo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M12 2L2 7l10 5 10-5-10-5z"/>
              <path d="M2 17l10 5 10-5"/>
              <path d="M2 12l10 5 10-5"/>
            </svg>
          </div>
          <div class="logo-text">
            <h1>AI Query Agent</h1>
            <span class="tagline">Natural Language → SQL</span>
          </div>
        </div>
        
        <div class="header-actions">
          <button class="btn btn-ghost" @click="showHistory = !showHistory">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
            History
          </button>
          <div class="status-dot" :class="connected ? 'connected' : 'disconnected'"></div>
        </div>
      </div>
    </header>
    
    <!-- Main Content -->
    <main class="main">
      <div class="container">
        <!-- Query Section -->
        <section class="query-section animate-fadeIn">
          <div class="query-card card card-glow">
            <h2>Ask anything about your data</h2>
            <form @submit.prevent="submitQuery">
              <div class="input-group">
                <input
                  v-model="question"
                  type="text"
                  class="input query-input"
                  placeholder="e.g., Show total revenue by month in Hanoi"
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
          <!-- Intent Badge -->
          <div class="result-meta">
            <span class="badge badge-info">{{ result.intent_type || 'data_retrieval' }}</span>
            <span v-if="result.cached" class="badge badge-success">Cached</span>
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
      </div>
    </main>
    
    <!-- History Sidebar -->
    <aside v-if="showHistory" class="history-sidebar glass animate-fadeIn">
      <div class="sidebar-header">
        <h3>Query History</h3>
        <button class="btn btn-ghost" @click="showHistory = false">×</button>
      </div>
      <div class="history-list">
        <div 
          v-for="item in history" 
          :key="item.id"
          class="history-item"
          @click="loadHistory(item)"
        >
          <p class="history-question">{{ item.question }}</p>
          <span class="history-time">{{ formatTime(item.timestamp) }}</span>
        </div>
        <p v-if="!history.length" class="empty-history">No queries yet</p>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import axios from 'axios'
import Chart from 'chart.js/auto'

// State
const question = ref('')
const loading = ref(false)
const result = ref(null)
const error = ref(null)
const connected = ref(true)
const showHistory = ref(false)
const history = ref([])
const chartCanvas = ref(null)
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
  timeout: 120000  // 2 minutes for LLM queries
})

// Submit query
async function submitQuery() {
  if (!question.value.trim() || loading.value) return
  
  loading.value = true
  error.value = null
  result.value = null
  
  try {
    const response = await api.post('/query/with-context', {
      question: question.value
    })
    
    result.value = response.data
    
    // Add to history
    history.value.unshift({
      id: Date.now(),
      question: question.value,
      timestamp: new Date(),
      result: response.data
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
  showHistory.value = false
  
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

// Check connection
onMounted(async () => {
  try {
    await api.get('/health')
    connected.value = true
  } catch {
    connected.value = false
  }
})
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Header */
.header {
  position: sticky;
  top: 0;
  z-index: 100;
  border-bottom: 1px solid var(--border-color);
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  background: var(--gradient-primary);
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.logo-icon svg {
  width: 22px;
  height: 22px;
}

.logo-text h1 {
  font-size: 18px;
  font-weight: 700;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.tagline {
  font-size: 12px;
  color: var(--text-muted);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.status-dot.connected {
  background: var(--accent-success);
  box-shadow: 0 0 8px var(--accent-success);
}

.status-dot.disconnected {
  background: var(--accent-error);
}

/* Main */
.main {
  flex: 1;
  padding: 32px 24px;
}

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

.history-time {
  font-size: 12px;
  color: var(--text-muted);
}

.empty-history {
  text-align: center;
  color: var(--text-muted);
  padding: 24px;
}

/* Responsive */
@media (max-width: 768px) {
  .header-content {
    padding: 12px 16px;
  }
  
  .logo-text h1 {
    font-size: 16px;
  }
  
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
