<template>
  <div class="chat-interface h-full flex flex-col relative">
    
    <!-- Chat History Area -->
    <div class="flex-1 overflow-y-auto px-4 py-6 scroll-smooth" ref="chatContainer">
      <div class="max-w-4xl mx-auto flex flex-col gap-6">
        
        <!-- Welcome State -->
        <div v-if="history.length === 0 && !result && !loading" class="text-center py-20 animate-fadeIn">
          <div class="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl mx-auto flex items-center justify-center mb-6 shadow-glow">
            <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="white" stroke-width="2">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
            </svg>
          </div>
          <h2 class="text-3xl font-bold mb-3 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-400">
            How can I help you today?
          </h2>
          <p class="text-secondary max-w-lg mx-auto mb-8">
            Select an agent and ask questions about your data. I can generate SQL, visualize results, and provide insights.
          </p>
          
          <div class="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-2xl mx-auto">
             <button 
              v-for="ex in examples" 
              :key="ex"
              class="p-4 bg-card border border-color rounded-xl hover:border-accent hover:bg-subtle transition text-left text-sm"
              @click="question = ex"
            >
              "{{ ex }}"
            </button>
          </div>
        </div>

        <!-- Chat Items -->
        <div v-for="item in history" :key="item.id" class="flex flex-col gap-4 animate-fadeIn">
          <!-- User Message -->
          <div class="flex justify-end">
            <div class="bg-accent text-white px-5 py-3 rounded-2xl rounded-tr-sm max-w-[80%] shadow-md">
              <p>{{ item.question }}</p>
            </div>
          </div>
          
          <!-- AI Response -->
          <div class="flex justify-start w-full">
            <div class="flex gap-3 max-w-full w-full">
              <div class="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex-shrink-0 flex items-center justify-center text-xs font-bold text-white shadow-glow">
                AI
              </div>
              <div class="flex-1 flex flex-col gap-3 overflow-hidden">
                <!-- Response Card -->
                <div class="bg-card border border-color rounded-2xl rounded-tl-sm p-5 shadow-sm w-full">
                   <!-- Meta Info -->
                   <div class="flex items-center gap-2 mb-3 text-xs">
                      <span class="bg-subtle text-secondary px-2 py-1 rounded border border-color uppercase tracking-wider font-semibold">
                        {{ item.result.intent_type || 'Query' }}
                      </span>
                      <span v-if="item.result.database_used" class="bg-subtle text-accent px-2 py-1 rounded border border-color flex items-center gap-1">
                         <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                         {{ item.result.database_used.name }}
                      </span>
                      <span class="text-secondary ml-auto">{{ formatTime(item.timestamp) }}</span>
                   </div>

                   <!-- SQL Block (Collapsible?) -->
                   <div class="mb-4">
                     <div class="flex justify-between items-center mb-2">
                       <span class="text-xs font-semibold text-secondary uppercase">Generated SQL</span>
                       <button class="text-xs text-accent hover:underline flex items-center gap-1" @click="copySQL(item.result.sql)">
                          <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                          Copy
                       </button>
                     </div>
                     <div class="bg-dark rounded-lg p-3 overflow-x-auto border border-color">
                       <pre class="text-sm font-mono text-green-400 whitespace-pre-wrap">{{ item.result.sql }}</pre>
                     </div>
                   </div>
                   
                   <!-- Explanation -->
                   <p class="text-secondary text-sm leading-relaxed mb-4 border-l-2 border-accent pl-3">
                     {{ item.result.explanation }}
                   </p>

                   <!-- Data/Chart Visualization Area - Render dynamically if needed, 
                        but for history we might keep it simple or re-render chart. 
                        Ideally charts should be components. For now simplified. -->
                    <div v-if="item.result.data && item.result.data.rows" class="border-t border-color pt-4">
                        <div class="flex items-center justify-between mb-2">
                           <span class="font-semibold text-sm">Result Data</span>
                           <span class="text-xs text-secondary">{{ item.result.data.row_count }} rows found</span>
                        </div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-sm text-left">
                                <thead class="text-xs text-secondary uppercase bg-subtle">
                                    <tr>
                                        <th v-for="col in item.result.data.columns" :key="col" class="px-3 py-2 whitespace-nowrap">{{ col }}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="(row, idx) in item.result.data.rows.slice(0, 5)" :key="idx" class="border-b border-color hover:bg-subtle">
                                        <td v-for="(cell, cidx) in row" :key="cidx" class="px-3 py-2 whitespace-nowrap text-secondary">{{ formatCell(cell) }}</td>
                                    </tr>
                                </tbody>
                            </table>
                            <div v-if="item.result.data.rows.length > 5" class="text-center text-xs text-secondary mt-2 italic">
                                Showing first 5 rows...
                            </div>
                        </div>
                    </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Current Loading State -->
        <div v-if="loading" class="flex justify-start w-full animate-fadeIn">
             <div class="flex gap-3 max-w-full">
              <div class="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center text-xs font-bold text-white shadow-glow">AI</div>
              <div class="bg-card border border-color rounded-2xl rounded-tl-sm p-4 shadow-sm flex items-center gap-3">
                 <div class="typing-indicator">
                    <span></span><span></span><span></span>
                 </div>
                 <span class="text-sm text-secondary">Analyzing query and generating SQL...</span>
              </div>
            </div>
        </div>

      </div>
    </div>

    <!-- Input Area (Fixed Bottom) -->
    <div class="p-4 border-t border-color bg-glass backdrop-blur-md z-10 w-full max-w-4xl mx-auto">
      <form @submit.prevent="submitQuery" class="relative">
        <!-- Agent Selector (Inline) -->
        <div class="absolute -top-12 left-0 flex items-center gap-2" v-if="agents.length > 0">
           <span class="text-xs text-secondary uppercase font-semibold bg-dark px-2 py-1 rounded border border-color">Using Agent:</span>
            <div class="relative">
                <select v-model="selectedAgentId" class="appearance-none bg-card border border-color text-sm text-primary rounded pl-3 pr-8 py-1 cursor-pointer hover:border-accent focus:outline-none focus:border-accent">
                    <option :value="null">Default System</option>
                    <option v-for="agent in agents" :key="agent.id" :value="agent.id">{{ agent.name }}</option>
                </select>
                <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-secondary">
                  <svg class="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
                </div>
            </div>
        </div>

        <div class="relative">
          <input
            v-model="question"
            type="text"
            class="w-full bg-input border border-color rounded-xl pl-5 pr-12 py-4 text-primary focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent shadow-lg text-base"
            placeholder="Ask a question about your data..."
            :disabled="loading"
          />
          <button 
            type="submit" 
            class="absolute right-2 top-2 bottom-2 aspect-square bg-accent hover:bg-accent-hover text-white rounded-lg flex items-center justify-center transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :disabled="loading || !question.trim()"
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
          </button>
        </div>
      </form>
      <div class="text-center mt-2">
         <p class="text-xs text-muted">AI Query Agent can make mistakes. Verify important results.</p>
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
const history = ref([]) // Chat history array
const result = ref(null) // Current result (redundant with history but useful for state)
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
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight
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
/* Utility classes mocking Tailwind */
.flex { display: flex; }
.flex-col { flex-direction: column; }
.flex-1 { flex: 1 1 0%; }
.h-full { height: 100%; }
.w-full { width: 100%; }
.max-w-4xl { max-width: 56rem; }
.max-w-2xl { max-width: 42rem; }
.mx-auto { margin-left: auto; margin-right: auto; }
.relative { position: relative; }
.absolute { position: absolute; }
.fixed { position: fixed; }
.top-2 { top: 0.5rem; }
.right-2 { right: 0.5rem; }
.bottom-2 { bottom: 0.5rem; }
.-top-12 { top: -3rem; }
.left-0 { left: 0; }
.inset-y-0 { top: 0; bottom: 0; }
.px-4 { padding-left: 1rem; padding-right: 1rem; }
.py-6 { padding-top: 1.5rem; padding-bottom: 1.5rem; }
.p-4 { padding: 1rem; }
.p-5 { padding: 1.25rem; }
.px-5 { padding-left: 1.25rem; padding-right: 1.25rem; }
.py-3 { padding-top: 0.75rem; padding-bottom: 0.75rem; }
.pt-4 { padding-top: 1rem; }
.mt-2 { margin-top: 0.5rem; }
.mb-2 { margin-bottom: 0.5rem; }
.mb-3 { margin-bottom: 0.75rem; }
.mb-4 { margin-bottom: 1rem; }
.mb-6 { margin-bottom: 1.5rem; }
.mb-8 { margin-bottom: 2rem; }
.gap-2 { gap: 0.5rem; }
.gap-3 { gap: 0.75rem; }
.gap-4 { gap: 1rem; }
.gap-6 { gap: 1.5rem; }
.bg-card { background-color: var(--bg-card); }
.bg-dark { background-color: var(--bg-dark); }
.bg-subtle { background-color: rgba(255,255,255,0.03); }
.bg-input { background-color: var(--bg-input); }
.bg-glass { background-color: rgba(15, 17, 21, 0.8); }
.backdrop-blur-md { backdrop-filter: blur(12px); }
.bg-accent { background-color: var(--accent-primary); }
.bg-accent-hover:hover { background-color: var(--accent-hover); }
.text-white { color: white; }
.text-primary { color: var(--text-primary); }
.text-secondary { color: var(--text-secondary); }
.text-accent { color: var(--accent-primary); }
.text-muted { color: var(--text-muted); }
.text-green-400 { color: #4ade80; }
.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.font-medium { font-weight: 500; }
.font-mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.text-3xl { font-size: 1.875rem; line-height: 2.25rem; }
.text-base { font-size: 1rem; line-height: 1.5rem; }
.text-sm { font-size: 0.875rem; line-height: 1.25rem; }
.text-xs { font-size: 0.75rem; line-height: 1rem; }
.text-center { text-align: center; }
.text-left { text-align: left; }
.text-transparent { color: transparent; }
.uppercase { text-transform: uppercase; }
.capitalize { text-transform: capitalize; }
.italic { font-style: italic; }
.tracking-wider { letter-spacing: 0.05em; }
.leading-relaxed { line-height: 1.625; }
.border { border-width: 1px; }
.border-t { border-top-width: 1px; }
.border-b { border-bottom-width: 1px; }
.border-l-2 { border-left-width: 2px; }
.border-color { border-color: var(--border-color); }
.rounded { border-radius: 0.25rem; }
.rounded-lg { border-radius: 0.5rem; }
.rounded-xl { border-radius: 0.75rem; }
.rounded-2xl { border-radius: 1rem; }
.rounded-full { border-radius: 9999px; }
.rounded-tr-sm { border-top-right-radius: 0.125rem; }
.rounded-tl-sm { border-top-left-radius: 0.125rem; }
.shadow-sm { box-shadow: var(--shadow-sm); }
.shadow-md { box-shadow: var(--shadow-md); }
.shadow-lg { box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05); }
.shadow-glow { box-shadow: var(--shadow-glow); }
.overflow-hidden { overflow: hidden; }
.overflow-y-auto { overflow-y: auto; }
.overflow-x-auto { overflow-x: auto; }
.whitespace-nowrap { white-space: nowrap; }
.whitespace-pre-wrap { white-space: pre-wrap; }
.cursor-pointer { cursor: pointer; }
.cursor-not-allowed { cursor: not-allowed; }
.pointer-events-none { pointer-events: none; }
.hover\:underline:hover { text-decoration: underline; }
.hover\:bg-subtle:hover { background-color: rgba(255,255,255,0.05); }
.hover\:border-accent:hover { border-color: var(--accent-primary); }
.focus\:outline-none:focus { outline: 2px solid transparent; outline-offset: 2px; }
.focus\:ring-2:focus { box-shadow: 0 0 0 2px var(--bg-dark), 0 0 0 4px var(--accent-primary); }
.transition { transition-property: background-color, border-color, color, fill, stroke, opacity, box-shadow, transform; transition-duration: 200ms; }
.transition-colors { transition-property: background-color, border-color, color, fill, stroke; transition-duration: 200ms; }
.opacity-50 { opacity: 0.5; }
.z-10 { z-index: 10; }
.appearance-none { -webkit-appearance: none; appearance: none; }
.grid { display: grid; }
.grid-cols-1 { grid-template-cols: repeat(1, minmax(0, 1fr)); }
.flex-shrink-0 { flex-shrink: 0; }
.scroll-smooth { scroll-behavior: smooth; }

/* Custom Gradients */
.bg-gradient-to-r { background-image: linear-gradient(to right, var(--tw-gradient-stops)); }
.bg-gradient-to-br { background-image: linear-gradient(to bottom right, var(--tw-gradient-stops)); }
.from-blue-500 { --tw-gradient-from: #3b82f6; --tw-gradient-stops: var(--tw-gradient-from), var(--tw-gradient-to, rgba(59, 130, 246, 0)); }
.to-purple-600 { --tw-gradient-to: #9333ea; }
.from-blue-400 { --tw-gradient-from: #60a5fa; --tw-gradient-stops: var(--tw-gradient-from), var(--tw-gradient-to, rgba(96, 165, 250, 0)); }
.to-purple-400 { --tw-gradient-to: #c084fc; }
.from-purple-500 { --tw-gradient-from: #a855f7; --tw-gradient-stops: var(--tw-gradient-from), var(--tw-gradient-to, rgba(168, 85, 247, 0)); }
.to-indigo-600 { --tw-gradient-to: #4f46e5; }
.bg-clip-text { -webkit-background-clip: text; background-clip: text; }

/* Aspect Ratio */
.aspect-square { aspect-ratio: 1 / 1; }

.typing-indicator span {
  display: inline-block;
  width: 6px; 
  height: 6px;
  background-color: var(--text-secondary);
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out both;
  margin: 0 2px;
}

.typing-indicator span:nth-child(1) { animation-delay: -0.32s; }
.typing-indicator span:nth-child(2) { animation-delay: -0.16s; }

@keyframes typing {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}

@media (min-width: 768px) {
  .md\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
</style>
