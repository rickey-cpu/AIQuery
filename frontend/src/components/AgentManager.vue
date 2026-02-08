<template>
  <div class="agent-manager p-6">
    <div class="container mx-auto max-w-6xl">
      <!-- Header -->
      <div class="flex justify-between items-center mb-8">
        <div>
          <h2 class="text-2xl font-bold mb-2">My Agents</h2>
          <p class="text-secondary text-sm">Manage your AI assistants and their data sources</p>
        </div>
        <button class="btn btn-primary" @click="openCreateModal">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          Create New Agent
        </button>
      </div>

      <!-- Agent Grid -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="agent in agents" :key="agent.id" class="agent-card card group">
          <!-- Card Header -->
          <div class="p-5 border-b border-color">
            <div class="flex justify-between items-start mb-3">
              <div class="agent-icon">
                {{ agent.name.charAt(0).toUpperCase() }}
              </div>
              <span class="badge" :class="agent.is_active ? 'badge-success' : 'badge-inactive'">
                {{ agent.is_active ? 'Active' : 'Paused' }}
              </span>
            </div>
            <h3 class="text-lg font-semibold mb-1 truncate">{{ agent.name }}</h3>
            <p class="text-secondary text-sm h-10 line-clamp-2">{{ agent.description || 'No description provided' }}</p>
          </div>
          
          <!-- Card Body -->
          <div class="p-5 bg-subtle">
            <div class="flex flex-col gap-3 mb-4">
              <div class="flex justify-between items-center text-sm">
                <span class="text-secondary">Databases</span>
                <span class="font-medium bg-tag px-2 py-0.5 rounded">{{ agent.databases.length }} Sources</span>
              </div>
              <div class="flex justify-between items-center text-sm">
                <span class="text-secondary">Routing</span>
                <span class="font-medium text-accent" v-if="agent.auto_route">Automatic (AI)</span>
                 <span class="font-medium text-secondary" v-else>Manual</span>
              </div>
            </div>
            
            <!-- Database Preview Icons -->
            <div class="flex gap-2 mb-2 h-6">
              <div 
                v-for="db in agent.databases.slice(0, 5)" 
                :key="db.id"
                class="db-mini-icon"
                :title="db.name + ' (' + db.db_type + ')'"
              >
                 <svg v-if="['postgresql', 'mysql', 'sqlserver'].includes(db.db_type)" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                 <svg v-else-if="['elasticsearch', 'opensearch'].includes(db.db_type)" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <svg v-else viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
              </div>
            </div>
          </div>
          
          <!-- Card Footer -->
          <div class="p-4 border-t border-color flex justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button class="btn btn-sm btn-ghost" @click="editAgent(agent)">Edit Config</button>
            <button class="btn btn-sm btn-ghost text-error" @click="deleteAgent(agent)">Delete</button>
          </div>
        </div>
        
        <!-- Empty State -->
        <div v-if="agents.length === 0 && !loading" class="col-span-full py-12 text-center border border-dashed border-color rounded-xl">
          <div class="w-16 h-16 mx-auto bg-subtle rounded-full flex items-center justify-center mb-4 text-secondary">
             <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
          </div>
          <h3 class="text-lg font-medium mb-2">No Agents Yet</h3>
          <p class="text-secondary mb-6 max-w-md mx-auto">Create your first AI agent to start querying your databases using natural language.</p>
          <button class="btn btn-primary" @click="openCreateModal">Create Agent</button>
        </div>
      </div>

      <!-- Agent Modal -->
      <div v-if="showModal" class="modal-backdrop" @click.self="closeModal">
        <div class="modal card">
          <div class="modal-header">
            <h3 class="text-xl font-bold">{{ isEditing ? 'Edit Agent' : 'Create New Agent' }}</h3>
            <button class="btn-icon" @click="closeModal">×</button>
          </div>
          
          <div class="modal-body">
            <form @submit.prevent="saveAgent">
              <div class="form-group mb-4">
                <label class="label">Agent Name</label>
                <input v-model="form.name" type="text" class="input" placeholder="e.g. Sales Analyst" required>
              </div>
              
              <div class="form-group mb-4">
                <label class="label">Description</label>
                <textarea v-model="form.description" class="input textarea" placeholder="What is this agent for?"></textarea>
              </div>

              <div class="form-group mb-6 p-4 bg-subtle rounded-lg border border-color">
                <label class="flex items-center gap-3 cursor-pointer">
                  <input v-model="form.auto_route" type="checkbox" class="checkbox">
                  <div>
                    <span class="font-medium block">Enable Smart Routing</span>
                    <span class="text-xs text-secondary">Automatically direct queries to the most relevant database</span>
                  </div>
                </label>
              </div>
              
              <div class="form-group mb-4">
                <div class="flex justify-between items-center mb-2">
                  <label class="label mb-0">Database Sources</label>
                  <button type="button" class="text-accent text-sm hover:underline" @click="openDbModal">+ Add Source</button>
                </div>
                
                <div class="db-list space-y-2">
                  <div v-for="db in form.databases" :key="db.id || db.tempId" class="db-item">
                    <div class="flex items-center gap-3">
                      <div class="db-icon-sm" :class="db.db_type">
                        <span>{{ getDbTypeInitials(db.db_type) }}</span>
                      </div>
                      <div>
                        <div class="font-medium">{{ db.name }}</div>
                        <div class="text-xs text-secondary capitalize">{{ db.db_type }} • {{ db.host || 'Local' }}</div>
                      </div>
                    </div>
                    <button type="button" class="btn-icon text-error" @click="removeDatabase(db)">×</button>
                  </div>
                   <div v-if="form.databases.length === 0" class="text-center py-4 text-secondary bg-subtle rounded border border-dashed border-color text-sm">
                    No databases connected. Add one to start.
                  </div>
                </div>
              </div>

              <div class="modal-footer">
                <button type="button" class="btn btn-ghost" @click="closeModal">Cancel</button>
                <button type="submit" class="btn btn-primary" :disabled="loading">
                  {{ loading ? 'Saving...' : 'Save Agent' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      <!-- DB Config Modal -->
      <div v-if="showDbModal" class="modal-backdrop" @click.self="closeDbModal">
        <div class="modal card max-w-md">
           <div class="modal-header">
            <h3 class="text-lg font-bold">Add Database Source</h3>
            <button class="btn-icon" @click="closeDbModal">×</button>
          </div>
          <div class="modal-body">
             <form @submit.prevent="addDatabase">
                <div class="form-group mb-4">
                    <label class="label">Display Name</label>
                    <input v-model="dbForm.name" type="text" class="input" placeholder="e.g. Production DB" required>
                </div>
                <div class="form-group mb-4">
                    <label class="label">Database Type</label>
                    <select v-model="dbForm.db_type" class="input select-input" required>
                        <option value="postgresql">PostgreSQL</option>
                        <option value="mysql">MySQL</option>
                        <option value="sqlserver">SQL Server</option>
                        <option value="elasticsearch">Elasticsearch</option>
                         <option value="opensearch">OpenSearch</option>
                        <option value="sqlite">SQLite</option>
                    </select>
                </div>

                <!-- Connection Details -->
                <div v-if="dbForm.db_type !== 'sqlite'" class="grid grid-cols-2 gap-4 mb-4">
                  <div class="form-group">
                       <label class="label">Host</label>
                       <input v-model="dbForm.host" type="text" class="input" placeholder="localhost">
                  </div>
                  <div class="form-group">
                       <label class="label">Port</label>
                       <input v-model.number="dbForm.port" type="number" class="input" placeholder="Default">
                  </div>
                </div>
                
                <div class="form-group mb-4">
                     <label class="label">{{ dbForm.db_type === 'sqlite' ? 'File Path' : 'Database Name / Index' }}</label>
                     <input v-model="dbForm.database" type="text" class="input" required>
                </div>

                <div v-if="dbForm.db_type !== 'sqlite'" class="grid grid-cols-2 gap-4 mb-6">
                  <div class="form-group">
                       <label class="label">Username</label>
                       <input v-model="dbForm.username" type="text" class="input">
                  </div>
                  <div class="form-group">
                       <label class="label">Password</label>
                       <input v-model="dbForm.password" type="password" class="input">
                  </div>
                </div>

                <div class="modal-footer">
                    <button type="button" class="btn btn-ghost" @click="closeDbModal">Cancel</button>
                    <button type="submit" class="btn btn-primary w-full">Connect Database</button>
                </div>
             </form>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

// State
const agents = ref([])
const loading = ref(false)
const showModal = ref(false)
const showDbModal = ref(false)
const isEditing = ref(false)

const form = ref({
  id: null,
  name: '',
  description: '',
  auto_route: true,
  databases: []
})

const dbForm = ref({
    name: '',
    db_type: 'postgresql',
    host: 'localhost',
    port: null,
    database: '',
    username: '',
    password: ''
})

const api = axios.create({
  baseURL: '/api'
})

// Lifecycle
onMounted(() => {
  fetchAgents()
})

// Methods
async function fetchAgents() {
  try {
    const res = await api.get('/agents')
    agents.value = res.data
  } catch (e) {
    console.error(e)
  }
}

function openCreateModal() {
  isEditing.value = false
  form.value = {
    name: '',
    description: '',
    auto_route: true,
    databases: []
  }
  showModal.value = true
}

function editAgent(agent) {
  isEditing.value = true
  // Deep copy
  form.value = JSON.parse(JSON.stringify(agent))
  showModal.value = true
}

async function deleteAgent(agent) {
  if (!confirm(`Delete agent "${agent.name}"?`)) return
  try {
    await api.delete(`/agents/${agent.id}`)
    fetchAgents()
  } catch (e) {
    alert('Failed to delete agent')
  }
}

async function saveAgent() {
  loading.value = true
  try {
    if (isEditing.value) {
      await api.put(`/agents/${form.value.id}`, form.value)
    } else {
      await api.post('/agents', form.value)
    }
    showModal.value = false
    fetchAgents()
  } catch (e) {
    alert('Failed to save agent')
    console.error(e)
  } finally {
    loading.value = false
  }
}

function openDbModal() {
    dbForm.value = {
        name: '',
        db_type: 'postgresql',
        host: 'localhost',
        port: null,
        database: '',
        username: '',
        password: '',
        is_default: false
    }
    showDbModal.value = true
}

function closeDbModal() {
    showDbModal.value = false
}

function addDatabase() {
    form.value.databases.push({
        ...dbForm.value,
        port: dbForm.value.port || 0,
        tempId: Date.now()
    })
    closeDbModal()
}

function removeDatabase(db) {
    const idx = form.value.databases.indexOf(db)
    if (idx > -1) {
        form.value.databases.splice(idx, 1)
    }
}

function closeModal() {
  showModal.value = false
}

function getDbTypeInitials(type) {
  if (type === 'postgresql') return 'PG'
  if (type === 'mysql') return 'MY'
  if (type === 'sqlserver') return 'SQ'
  if (type === 'elasticsearch') return 'ES'
    if (type === 'opensearch') return 'OS'
  if (type === 'sqlite') return 'LT'
  return 'DB'
}
</script>

<style scoped>
/* Tailwind-like utilities */
.p-4 { padding: 1rem; }
.p-5 { padding: 1.25rem; }
.p-6 { padding: 1.5rem; }
.py-0\.5 { padding-top: 0.125rem; padding-bottom: 0.125rem; }
.px-2 { padding-left: 0.5rem; padding-right: 0.5rem; }
.py-4 { padding-top: 1rem; padding-bottom: 1rem; }
.py-12 { padding-top: 3rem; padding-bottom: 3rem; }
.mb-1 { margin-bottom: 0.25rem; }
.mb-2 { margin-bottom: 0.5rem; }
.mb-3 { margin-bottom: 0.75rem; }
.mb-4 { margin-bottom: 1rem; }
.mb-6 { margin-bottom: 1.5rem; }
.mb-8 { margin-bottom: 2rem; }
.gap-2 { gap: 0.5rem; }
.gap-3 { gap: 0.75rem; }
.gap-4 { gap: 1rem; }
.gap-6 { gap: 1.5rem; }
.w-full { width: 100%; }
.h-6 { height: 1.5rem; }
.h-10 { height: 2.5rem; }
.w-16 { width: 4rem; }
.h-16 { height: 4rem; }
.max-w-md { max-width: 28rem; }
.max-w-6xl { max-width: 72rem; }
.mx-auto { margin-left: auto; margin-right: auto; }
.text-center { text-align: center; }
.flex { display: flex; }
.flex-col { flex-direction: column; }
.justify-between { justify-content: space-between; }
.justify-center { justify-content: center; }
.justify-end { justify-content: flex-end; }
.items-center { align-items: center; }
.items-start { align-items: flex-start; }
.grid { display: grid; }
.col-span-full { grid-column: 1 / -1; }
.border-b { border-bottom-width: 1px; }
.border-t { border-top-width: 1px; }
.border { border-width: 1px; }
.border-dashed { border-style: dashed; }
.rounded { border-radius: 0.25rem; }
.rounded-lg { border-radius: 0.5rem; }
.rounded-xl { border-radius: 0.75rem; }
.rounded-full { border-radius: 9999px; }
.font-bold { font-weight: 700; }
.font-semibold { font-weight: 600; }
.font-medium { font-weight: 500; }
.text-2xl { font-size: 1.5rem; line-height: 2rem; }
.text-xl { font-size: 1.25rem; line-height: 1.75rem; }
.text-lg { font-size: 1.125rem; line-height: 1.75rem; }
.text-sm { font-size: 0.875rem; line-height: 1.25rem; }
.text-xs { font-size: 0.75rem; line-height: 1rem; }
.truncate { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.line-clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.capitalize { text-transform: capitalize; }
.cursor-pointer { cursor: pointer; }
.group:hover .group-hover\:opacity-100 { opacity: 1; }
.transition-opacity { transition-property: opacity; transition-duration: 200s; }
.opacity-0 { opacity: 0; }

/* Grid Responsive */
@media (min-width: 768px) {
  .md\:grid-cols-2 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (min-width: 1024px) {
  .lg\:grid-cols-3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}

/* Custom Colors & Themes */
.text-secondary { color: var(--text-secondary); }
.text-accent { color: var(--accent-primary); }
.text-error { color: var(--accent-danger); }
.bg-subtle { background: rgba(255,255,255,0.03); }
.bg-tag { background: rgba(255,255,255,0.08); }
.border-color { border-color: var(--border-color); }

.agent-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, var(--bg-tertiary) 0%, var(--bg-card) 100%);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: var(--accent-primary);
}

.db-mini-icon {
  width: 24px;
  height: 24px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
}

.db-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  transition: border-color 0.2s;
}

.db-item:hover {
  border-color: var(--text-muted);
}

.db-icon-sm {
  width: 32px;
  height: 32px;
  border-radius: 6px;
  background: var(--bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
}

.badge-success { background: rgba(35, 134, 54, 0.15); color: #3fb950; border: 1px solid rgba(35, 134, 54, 0.2); }
.badge-inactive { background: rgba(110, 118, 129, 0.15); color: #8b949e; border: 1px solid rgba(110, 118, 129, 0.2); }

/* Modal specific */
.modal-backdrop {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}

.modal {
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
}

.modal-header, .modal-footer {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.modal-footer {
  border-bottom: none;
  border-top: 1px solid var(--border-color);
  justify-content: flex-end;
  gap: 12px;
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
}

.btn-icon {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}
.btn-icon:hover { color: var(--text-primary); background: rgba(255,255,255,0.05); }

.label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 6px;
  color: var(--text-secondary);
}

.checkbox {
  width: 16px; 
  height: 16px;
  accent-color: var(--accent-primary);
}
</style>
