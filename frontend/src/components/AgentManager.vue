<template>
  <div class="agent-manager">
    <div class="container">
      <div class="header-section">
        <h2>Agent Management</h2>
        <button class="btn btn-primary" @click="openCreateModal">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          New Agent
        </button>
      </div>

      <!-- Agent List -->
      <div class="agent-grid">
        <div v-for="agent in agents" :key="agent.id" class="agent-card card">
          <div class="agent-header">
            <h3>{{ agent.name }}</h3>
            <span class="badge" :class="agent.is_active ? 'badge-success' : 'badge-secondary'">
              {{ agent.is_active ? 'Active' : 'Inactive' }}
            </span>
          </div>
          <p class="agent-desc">{{ agent.description || 'No description' }}</p>
          
          <div class="agent-stats">
            <div class="stat-item">
              <span class="stat-label">Databases</span>
              <span class="stat-value">{{ agent.databases.length }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">Routing</span>
              <span class="stat-value">{{ agent.auto_route ? 'Auto' : 'Manual' }}</span>
            </div>
          </div>

          <div class="agent-actions">
            <button class="btn btn-sm btn-ghost" @click="editAgent(agent)">Edit</button>
            <button class="btn btn-sm btn-ghost text-error" @click="deleteAgent(agent)">Delete</button>
          </div>
        </div>
      </div>

      <!-- Modal -->
      <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
        <div class="modal card">
          <div class="modal-header">
            <h3>{{ isEditing ? 'Edit Agent' : 'Create Agent' }}</h3>
            <button class="btn btn-ghost btn-sm" @click="closeModal">×</button>
          </div>
          
          <div class="modal-body">
            <form @submit.prevent="saveAgent">
              <div class="form-group">
                <label>Name</label>
                <input v-model="form.name" type="text" class="input" required>
              </div>
              
              <div class="form-group">
                <label>Description</label>
                <textarea v-model="form.description" class="input textarea"></textarea>
              </div>

              <div class="form-group checkbox-group">
                <label>
                  <input v-model="form.auto_route" type="checkbox">
                  Enable Automatic Routing
                </label>
              </div>
              
              <div v-if="isEditing" class="form-group">
                <label>Databases</label>
                <div class="db-list">
                  <div v-for="db in form.databases" :key="db.id || db.tempId" class="db-item">
                    <span>{{ db.name }} ({{ db.db_type }})</span>
                    <button type="button" class="btn btn-xs btn-ghost text-error" @click="removeDatabase(db)">×</button>
                  </div>
                  <button type="button" class="btn btn-sm btn-secondary w-full" @click="openDbModal">
                    + Add Database
                  </button>
                </div>
              </div>

              <div class="modal-actions">
                <button type="button" class="btn btn-ghost" @click="closeModal">Cancel</button>
                <button type="submit" class="btn btn-primary" :disabled="loading">
                  {{ loading ? 'Saving...' : 'Save' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      <!-- Database Modal -->
      <div v-if="showDbModal" class="modal-overlay" @click.self="closeDbModal">
        <div class="modal card">
           <div class="modal-header">
            <h3>Add Database Source</h3>
            <button class="btn btn-ghost btn-sm" @click="closeDbModal">×</button>
          </div>
          <div class="modal-body">
             <form @submit.prevent="addDatabase">
                <div class="form-group">
                    <label>Display Name</label>
                    <input v-model="dbForm.name" type="text" class="input" required>
                </div>
                <div class="form-group">
                    <label>Type</label>
                    <select v-model="dbForm.db_type" class="input" required>
                        <option value="sqlite">SQLite</option>
                        <option value="mysql">MySQL</option>
                        <option value="postgresql">PostgreSQL</option>
                        <option value="sqlserver">SQL Server</option>
                        <option value="elasticsearch">Elasticsearch</option>
                        <option value="opensearch">OpenSearch</option>
                    </select>
                </div>

                <!-- Connection Details -->
                <div class="form-group" v-if="dbForm.db_type !== 'sqlite'">
                     <label>Host</label>
                     <input v-model="dbForm.host" type="text" class="input" placeholder="localhost">
                </div>
                <div class="form-group" v-if="dbForm.db_type !== 'sqlite'">
                     <label>Port</label>
                     <input v-model.number="dbForm.port" type="number" class="input" placeholder="0 (default)">
                </div>
                
                 <!-- SQLite Path or DB Name -->
                <div class="form-group">
                     <label>{{ dbForm.db_type === 'sqlite' ? 'File Path' : 'Database Name' }}</label>
                     <input v-model="dbForm.database" type="text" class="input" required>
                </div>

                <div class="form-group" v-if="dbForm.db_type !== 'sqlite'">
                     <label>Username</label>
                     <input v-model="dbForm.username" type="text" class="input">
                </div>
                <div class="form-group" v-if="dbForm.db_type !== 'sqlite'">
                     <label>Password</label>
                     <input v-model="dbForm.password" type="password" class="input">
                </div>

                <div class="modal-actions">
                    <button type="button" class="btn btn-ghost" @click="closeDbModal">Cancel</button>
                    <button type="submit" class="btn btn-primary">Add</button>
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
    db_type: 'postgres',
    host: 'localhost',
    port: 0,
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
        port: 0,
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
</script>

<style scoped>
.container {
  max-width: 1000px;
  margin: 0 auto;
}

.header-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
}

.agent-card {
  padding: 24px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  transition: transform 0.2s;
}

.agent-card:hover {
  transform: translateY(-2px);
  border-color: var(--accent-primary);
}

.agent-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 12px;
}

.agent-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.agent-desc {
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 20px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.agent-stats {
  display: flex;
  gap: 16px;
  margin-bottom: 20px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 12px;
  color: var(--text-muted);
}

.stat-value {
  font-size: 16px;
  font-weight: 600;
}

.agent-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.modal {
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 0;
  background: var(--bg-card);
  animation: modalSlide 0.3s ease;
}

@keyframes modalSlide {
  from { transform: translateY(20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.modal-body {
  padding: 24px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 32px;
}

.db-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.db-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  font-size: 14px;
}

.text-error {
    color: var(--accent-error);
}

.w-full {
    width: 100%;
}

.btn-xs {
    padding: 2px 6px;
    font-size: 12px;
}
</style>
