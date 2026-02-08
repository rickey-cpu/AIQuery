<template>
  <div class="agent-manager">
    <div class="manager-container">
      <!-- Header -->
      <div class="header-row">
        <div class="header-text">
          <h2 class="page-title">My Agents</h2>
          <p class="page-subtitle">Manage your AI assistants and their data sources</p>
        </div>
        <button class="create-btn" @click="openCreateModal">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          Create New Agent
        </button>
      </div>

      <!-- Agent Grid -->
      <div class="agent-grid">
        <div v-for="agent in agents" :key="agent.id" class="agent-card">
          <!-- Card Header -->
          <div class="card-header">
            <div class="agent-identity">
              <div class="agent-icon">
                {{ agent.name.charAt(0).toUpperCase() }}
              </div>
              <span class="status-badge" :class="agent.is_active ? 'active' : 'inactive'">
                {{ agent.is_active ? 'Active' : 'Paused' }}
              </span>
            </div>
            <h3 class="agent-name">{{ agent.name }}</h3>
            <p class="agent-description">{{ agent.description || 'No description provided' }}</p>
          </div>
          
          <!-- Card Body -->
          <div class="card-body">
            <div class="stats-row">
              <div class="stat">
                <span class="stat-label">Databases</span>
                <span class="stat-value">{{ agent.databases.length }} Sources</span>
              </div>
              <div class="stat">
                <span class="stat-label">Routing</span>
                <span class="routing-value" v-if="agent.auto_route">Automatic (AI)</span>
                 <span class="routing-value manual" v-else>Manual</span>
              </div>
            </div>
            
            <!-- Database Preview Icons -->
            <div class="db-params">
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
          <div class="card-footer">
            <button class="action-btn" @click="editAgent(agent)">Edit Config</button>
            <button class="action-btn" @click="openSemanticManager(agent)">Manage Knowledge</button>
            <button class="action-btn delete" @click="deleteAgent(agent)">Delete</button>
          </div>
        </div>
        
        <!-- Empty State -->
        <div v-if="agents.length === 0 && !loading" class="empty-state">
          <div class="empty-icon">
             <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
          </div>
          <h3 class="empty-title">No Agents Yet</h3>
          <p class="empty-text">Create your first AI agent to start querying your databases using natural language.</p>
          <button class="create-btn" @click="openCreateModal">Create Agent</button>
        </div>
      </div>

      <!-- Semantic Manager Modal -->
      <div v-if="showSemanticManager" class="modal-backdrop" @click.self="closeSemanticManager">
        <div class="modal lg-modal">
           <SemanticManager 
             :agent-id="selectedAgentForSemantic.id"
             :agent-name="selectedAgentForSemantic.name"
             @close="closeSemanticManager"
           />
        </div>
      </div>

      <!-- Agent Modal -->
      <div v-if="showModal" class="modal-backdrop" @click.self="closeModal">
        <div class="modal">
          <div class="modal-header">
            <h3 class="modal-title">{{ isEditing ? 'Edit Agent' : 'Create New Agent' }}</h3>
            <button class="close-btn" @click="closeModal">×</button>
          </div>
          
          <div class="modal-body">
            <form @submit.prevent="saveAgent">
              <div class="form-group">
                <label class="label">Agent Name</label>
                <input v-model="form.name" type="text" class="input" placeholder="e.g. Sales Analyst" required>
              </div>
              
              <div class="form-group">
                <label class="label">Description</label>
                <textarea v-model="form.description" class="textarea" placeholder="What is this agent for?"></textarea>
              </div>

              <div class="form-group checkbox-wrapper">
                <label class="checkbox-label">
                  <input v-model="form.auto_route" type="checkbox" class="checkbox">
                  <div>
                    <span class="checkbox-title">Enable Smart Routing</span>
                    <span class="checkbox-desc">Automatically direct queries to the most relevant database</span>
                  </div>
                </label>
              </div>
              
              <div class="form-group">
                <div class="section-header">
                  <label class="label">Database Sources</label>
                  <button type="button" class="add-link" @click="openDbModal">+ Add Source</button>
                </div>
                
                <div class="db-list">
                  <div v-for="db in form.databases" :key="db.id || db.tempId" class="db-item">
                    <div class="db-info">
                      <div class="db-type-icon" :class="db.db_type">
                        <span>{{ getDbTypeInitials(db.db_type) }}</span>
                      </div>
                      <div class="db-details">
                        <div class="db-name">{{ db.name }}</div>
                        <div class="db-meta">{{ db.db_type }} • {{ db.host || 'Local' }}</div>
                      </div>
                    </div>
                    <button type="button" class="remove-btn" @click="removeDatabase(db)">×</button>
                  </div>
                   <div v-if="form.databases.length === 0" class="db-empty">
                    No databases connected. Add one to start.
                  </div>
                </div>
              </div>

              <div class="modal-footer">
                <button type="button" class="cancel-btn" @click="closeModal">Cancel</button>
                <button type="submit" class="save-btn" :disabled="loading">
                  {{ loading ? 'Saving...' : 'Save Agent' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      <!-- DB Config Modal -->
      <div v-if="showDbModal" class="modal-backdrop" @click.self="closeDbModal">
        <div class="modal sm-modal">
           <div class="modal-header">
            <h3 class="modal-title">Add Database Source</h3>
            <button class="close-btn" @click="closeDbModal">×</button>
          </div>
          <div class="modal-body">
             <form @submit.prevent="addDatabase">
                <div class="form-group">
                    <label class="label">Display Name</label>
                    <input v-model="dbForm.name" type="text" class="input" placeholder="e.g. Production DB" required>
                </div>
                <div class="form-group">
                    <label class="label">Database Type</label>
                    <select v-model="dbForm.db_type" class="select" required>
                        <option value="postgresql">PostgreSQL</option>
                        <option value="mysql">MySQL</option>
                        <option value="sqlserver">SQL Server</option>
                        <option value="elasticsearch">Elasticsearch</option>
                         <option value="opensearch">OpenSearch</option>
                        <option value="sqlite">SQLite</option>
                    </select>
                </div>

                <!-- Connection Details -->
                <div v-if="dbForm.db_type !== 'sqlite'" class="form-row">
                  <div class="form-group">
                       <label class="label">Host</label>
                       <input v-model="dbForm.host" type="text" class="input" placeholder="localhost">
                  </div>
                  <div class="form-group">
                       <label class="label">Port</label>
                       <input v-model.number="dbForm.port" type="number" class="input" placeholder="Default">
                  </div>
                </div>
                
                <div class="form-group">
                     <label class="label">{{ dbForm.db_type === 'sqlite' ? 'File Path' : 'Database Name / Index' }}</label>
                     <input v-model="dbForm.database" type="text" class="input" required>
                </div>

                <div v-if="dbForm.db_type !== 'sqlite'" class="form-row">
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
                    <button type="button" class="cancel-btn" @click="closeDbModal">Cancel</button>
                    <button type="submit" class="save-btn full-width">Connect Database</button>
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
import SemanticManager from './SemanticManager.vue'

// State
const agents = ref([])
const loading = ref(false)
const showModal = ref(false)
const showDbModal = ref(false)
const showSemanticManager = ref(false)
const selectedAgentForSemantic = ref(null)
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

function openSemanticManager(agent) {
  selectedAgentForSemantic.value = agent
  showSemanticManager.value = true
}

function closeSemanticManager() {
  showSemanticManager.value = false
  selectedAgentForSemantic.value = null
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
.agent-manager {
  padding: 32px;
  height: 100%;
  overflow-y: auto;
  background-color: var(--bg-dark);
}

.manager-container {
  max-width: 1200px;
  margin: 0 auto;
}

/* Header */
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  margin-bottom: 4px;
}

.page-subtitle {
  color: var(--text-secondary);
  font-size: 14px;
}

.create-btn {
  background: var(--accent-primary);
  color: white;
  border: none;
  padding: 6px 16px;
  border-radius: 8px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.create-btn:hover {
  background: var(--accent-hover);
  transform: translateY(-2px);
}

/* Grid */
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
}

.agent-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.2s;
  display: flex;
  flex-direction: column;
}

.agent-card:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 4px 20px rgba(0,0,0,0.2);
}

.card-header {
  padding: 20px;
  border-bottom: 1px solid var(--border-color);
}

.agent-identity {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.agent-icon {
  width: 48px;
  height: 48px;
  background: linear-gradient(135deg, rgba(88, 166, 255, 0.1) 0%, rgba(139, 92, 246, 0.1) 100%);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  font-weight: 700;
  color: var(--accent-primary);
}

.status-badge {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}
.status-badge.active { background: rgba(35, 134, 54, 0.15); color: #3fb950; border: 1px solid rgba(35, 134, 54, 0.2); }
.status-badge.inactive { background: rgba(110, 118, 129, 0.15); color: #8b949e; border: 1px solid rgba(110, 118, 129, 0.2); }

.agent-name {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-description {
  font-size: 14px;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  height: 40px;
}

.card-body {
  padding: 20px;
  background: rgba(255, 255, 255, 0.01);
  flex: 1;
}

.stats-row {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.stat {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
}

.stat-label { color: var(--text-secondary); }
.stat-value { font-weight: 600; background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; }
.routing-value { font-weight: 600; color: var(--accent-primary); }
.routing-value.manual { color: var(--text-secondary); }

.db-params {
  display: flex;
  gap: 6px;
  height: 24px;
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

.card-footer {
  padding: 16px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  background: var(--bg-card);
}

.action-btn {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  padding: 4px 8px;
  cursor: pointer;
  border-radius: 4px;
}
.action-btn:hover { background: rgba(255,255,255,0.05); color: var(--text-primary); }
.action-btn.delete:hover { color: #f85149; background: rgba(248, 81, 73, 0.1); }

/* Empty State */
.empty-state {
  grid-column: 1 / -1;
  text-align: center;
  padding: 60px;
  border: 1px dashed var(--border-color);
  border-radius: 12px;
}
.empty-icon { color: var(--text-secondary); margin-bottom: 16px; }
.empty-title { font-size: 18px; margin-bottom: 8px; }
.empty-text { color: var(--text-secondary); margin-bottom: 24px; }

/* Modal */
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
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 50px rgba(0,0,0,0.5);
}
.sm-modal { max-width: 450px; }
.lg-modal { max-width: 800px; height: 600px; }

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-title { font-size: 18px; font-weight: 700; margin: 0; }
.close-btn { background: transparent; border: none; font-size: 24px; color: var(--text-secondary); cursor: pointer; }

.modal-body {
  padding: 24px;
  overflow-y: auto;
}

.form-group { margin-bottom: 20px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

.label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 8px; color: var(--text-secondary); }

.input, .textarea, .select {
  width: 100%;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 10px 12px;
  border-radius: 6px;
  font-size: 14px;
}
.input:focus, .textarea:focus, .select:focus { outline: none; border-color: var(--accent-primary); box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }
.textarea { min-height: 80px; resize: vertical; }

.checkbox-wrapper {
  background: rgba(255,255,255,0.03);
  padding: 16px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
}
.checkbox-label { display: flex; gap: 12px; cursor: pointer; }
.checkbox { width: 18px; height: 18px; margin-top: 2px; }
.checkbox-title { display: block; font-weight: 600; font-size: 14px; }
.checkbox-desc { font-size: 12px; color: var(--text-secondary); }

.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.add-link { background: transparent; border: none; color: var(--accent-primary); font-size: 13px; cursor: pointer; }
.add-link:hover { text-decoration: underline; }

.db-list { display: flex; flex-direction: column; gap: 8px; }
.db-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  border-radius: 8px;
}
.db-info { display: flex; gap: 12px; align-items: center; }
.db-type-icon {
  width: 36px; height: 36px;
  background: var(--bg-tertiary);
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700;
}
.db-details { display: flex; flex-direction: column; }
.db-name { font-weight: 500; font-size: 14px; }
.db-meta { font-size: 12px; color: var(--text-secondary); text-transform: capitalize; }
.remove-btn { background: transparent; border: none; color: #f85149; font-size: 18px; cursor: pointer; padding: 4px; }
.db-empty { text-align: center; padding: 20px; color: var(--text-secondary); font-size: 13px; border: 1px dashed var(--border-color); border-radius: 8px; }

.modal-footer {
  padding: 20px 24px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.cancel-btn { background: transparent; border: 1px solid var(--border-color); color: var(--text-primary); padding: 8px 16px; border-radius: 6px; cursor: pointer; }
.save-btn { background: var(--accent-primary); color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 600; cursor: pointer; }
.save-btn:disabled { opacity: 0.7; cursor: not-allowed; }
.full-width { width: 100%; }

</style>
