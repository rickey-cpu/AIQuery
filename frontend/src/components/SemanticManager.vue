<template>
  <div class="semantic-manager">
    <div class="header">
      <h3>Knowledge Base: {{ agentName }}</h3>
      <button class="close-btn" @click="$emit('close')">×</button>
    </div>

    <div class="tabs">
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'entities' }"
        @click="activeTab = 'entities'"
      >
        Entities
      </button>
      <button 
        class="tab-btn" 
        :class="{ active: activeTab === 'metrics' }"
        @click="activeTab = 'metrics'"
      >
        Metrics
      </button>
    </div>

    <div class="content-area">
      <!-- Entities Tab -->
      <div v-if="activeTab === 'entities'" class="tab-content">
        <div class="actions">
          <button class="add-btn" @click="openAddEntity">+ Add Entity</button>
        </div>
        
        <div class="list-container">
          <div v-if="entities.length === 0" class="empty-state">
            No entities defined for this agent.
          </div>
          <div v-for="entity in entities" :key="entity.name" class="item-card">
            <div class="item-header">
              <span class="item-name">{{ entity.name }}</span>
              <div class="item-controls">
                <span class="item-type">Entity</span>
                <button class="icon-btn edit-btn" @click="editEntity(entity)" title="Edit">✎</button>
                <button class="icon-btn delete-btn" @click="deleteEntity(entity.name)" title="Delete">🗑</button>
              </div>
            </div>
            <p class="item-desc">{{ entity.description }}</p>
            <div class="item-meta">
              <span class="meta-label">Synonyms:</span> {{ entity.synonyms.join(', ') || 'None' }}
            </div>
          </div>
        </div>

        <!-- Add Entity Modal -->
        <div v-if="showAddEntity" class="mini-modal">
          <h4>{{ isEditing ? 'Edit' : 'New' }} Entity</h4>
          <form @submit.prevent="saveEntity">
            <input v-model="newEntity.name" placeholder="Name (e.g. Customer)" required class="input" :disabled="isEditing">
            <input v-model="newEntity.table_name" placeholder="Table (e.g. customers)" class="input">
            <input v-model="newEntity.primary_key" placeholder="Primary Key (e.g. id)" class="input">
            <MarkdownEditor
              v-model="newEntity.description"
              title="Description"
              placeholder="Write the entity description in Markdown..."
              required
            />
            <input v-model="newEntity.synonyms_str" placeholder="Synonyms (comma separated)" class="input">
            <div class="form-actions">
              <button type="button" @click="showAddEntity = false" class="cancel-btn">Cancel</button>
              <button type="submit" class="save-btn">Save</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Metrics Tab -->
      <div v-if="activeTab === 'metrics'" class="tab-content">
        <div class="actions">
          <button class="add-btn" @click="openAddMetric">+ Add Metric</button>
        </div>

        <div class="list-container">
           <div v-if="metrics.length === 0" class="empty-state">
            No metrics defined for this agent.
          </div>
          <div v-for="metric in metrics" :key="metric.name" class="item-card">
            <div class="item-header">
              <span class="item-name">{{ metric.name }}</span>
               <div class="item-controls">
                <span class="item-type metric">Metric</span>
                <button class="icon-btn edit-btn" @click="editMetric(metric)" title="Edit">✎</button>
                <button class="icon-btn delete-btn" @click="deleteMetric(metric.name)" title="Delete">🗑</button>
              </div>
            </div>
            <p class="item-desc">{{ metric.description }}</p>
            <div class="item-meta">
               <code>{{ metric.definition }}</code>
            </div>
          </div>
        </div>

        <!-- Add Metric Modal -->
        <div v-if="showAddMetric" class="mini-modal">
          <h4>{{ isEditing ? 'Edit' : 'New' }} Metric</h4>
          <form @submit.prevent="saveMetric">
            <input v-model="newMetric.name" placeholder="Name (e.g. Revenue)" required class="input" :disabled="isEditing">
            <input v-model="newMetric.definition" placeholder="SQL Definition (e.g. SUM(amount))" required class="input">
            <MarkdownEditor
              v-model="newMetric.description"
              title="Description"
              placeholder="Write the metric description in Markdown..."
              required
            />
            <input v-model="newMetric.condition" placeholder="Condition (e.g. status='paid')" class="input">
            <input v-model="newMetric.synonyms_str" placeholder="Synonyms (comma separated)" class="input">
            <div class="form-actions">
              <button type="button" @click="showAddMetric = false" class="cancel-btn">Cancel</button>
              <button type="submit" class="save-btn">Save</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import axios from 'axios'
import MarkdownEditor from './MarkdownEditor.vue'

const props = defineProps({
  agentId: String,
  agentName: String
})

const emit = defineEmits(['close'])

const activeTab = ref('entities')
const entities = ref([])
const metrics = ref([])
const showAddEntity = ref(false)
const showAddMetric = ref(false)

const newEntity = reactive({
  name: '',
  table_name: '',
  primary_key: '',
  description: '',
  synonyms_str: ''
})

const newMetric = reactive({
  name: '',
  definition: '',
  description: '',
  condition: '',
  synonyms_str: ''
})

const api = axios.create({ baseURL: '/api' })

onMounted(() => {
  fetchData()
})

const isEditing = ref(false)

async function fetchData() {
  if (!props.agentId) return
  try {
    const [eRes, mRes] = await Promise.all([
      api.get(`/agents/${props.agentId}/semantic/entities`),
      api.get(`/agents/${props.agentId}/semantic/metrics`)
    ])
    entities.value = eRes.data
    metrics.value = mRes.data
  } catch (e) {
    console.error(e)
  }
}

// --- Entities ---

function openAddEntity() {
  isEditing.value = false
  Object.assign(newEntity, { name: '', table_name: '', primary_key: '', description: '', synonyms_str: '' })
  showAddEntity.value = true
}

function editEntity(entity) {
  isEditing.value = true
  Object.assign(newEntity, {
    name: entity.name,
    table_name: entity.table_name || '',
    primary_key: entity.primary_key || '',
    description: entity.description || '',
    synonyms_str: (entity.synonyms || []).join(', ')
  })
  showAddEntity.value = true
}

async function saveEntity() {
  try {
    const payload = {
      ...newEntity,
      synonyms: newEntity.synonyms_str.split(',').map(s => s.trim()).filter(s => s)
    }
    
    if (isEditing.value) {
      await api.put(`/agents/${props.agentId}/semantic/entities`, payload)
    } else {
      await api.post(`/agents/${props.agentId}/semantic/entities`, payload)
    }
    
    showAddEntity.value = false
    fetchData()
  } catch (e) {
    alert('Failed to save entity: ' + (e.response?.data?.detail || e.message))
  }
}

async function deleteEntity(name) {
  if (!confirm(`Are you sure you want to delete entity '${name}'?`)) return
  try {
    await api.delete(`/agents/${props.agentId}/semantic/entities/${name}`)
    fetchData()
  } catch (e) {
    alert('Failed to delete entity: ' + (e.response?.data?.detail || e.message))
  }
}

// --- Metrics ---

function openAddMetric() {
  isEditing.value = false
  Object.assign(newMetric, { name: '', definition: '', description: '', condition: '', synonyms_str: '' })
  showAddMetric.value = true
}

function editMetric(metric) {
  isEditing.value = true
  Object.assign(newMetric, {
    name: metric.name,
    definition: metric.definition || '',
    description: metric.description || '',
    condition: metric.condition || '',
    synonyms_str: (metric.synonyms || []).join(', ')
  })
  showAddMetric.value = true
}

async function saveMetric() {
  try {
    const payload = {
      ...newMetric,
      synonyms: newMetric.synonyms_str.split(',').map(s => s.trim()).filter(s => s)
    }
    
    if (isEditing.value) {
      await api.put(`/agents/${props.agentId}/semantic/metrics`, payload)
    } else {
      await api.post(`/agents/${props.agentId}/semantic/metrics`, payload)
    }

    showAddMetric.value = false
    fetchData()
  } catch (e) {
    alert('Failed to save metric: ' + (e.response?.data?.detail || e.message))
  }
}

async function deleteMetric(name) {
  if (!confirm(`Are you sure you want to delete metric '${name}'?`)) return
  try {
    await api.delete(`/agents/${props.agentId}/semantic/metrics/${name}`)
    fetchData()
  } catch (e) {
    alert('Failed to delete metric: ' + (e.response?.data?.detail || e.message))
  }
}
</script>

<style scoped>
.semantic-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--bg-card);
  color: var(--text-primary);
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid var(--border-color);
}

.header h3 { margin: 0; font-size: 16px; }
.close-btn { background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-secondary); }

.tabs {
  display: flex;
  border-bottom: 1px solid var(--border-color);
}

.tab-btn {
  flex: 1;
  padding: 12px;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
}

.tab-btn.active {
  color: var(--accent-primary);
  border-bottom-color: var(--accent-primary);
  font-weight: 600;
}

.content-area {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  position: relative;
}

.actions {
  margin-bottom: 16px;
  display: flex;
  justify-content: flex-end;
}

.add-btn {
  background: var(--accent-primary);
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.list-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.item-card {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  padding: 12px;
  border-radius: 8px;
}

.item-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.item-name { font-weight: 600; font-size: 14px; }
.item-type { font-size: 10px; text-transform: uppercase; background: rgba(88, 166, 255, 0.1); color: var(--accent-primary); padding: 2px 6px; border-radius: 4px; }
.item-type.metric { background: rgba(139, 92, 246, 0.1); color: #a78bfa; }

.item-desc { font-size: 13px; color: var(--text-secondary); margin-bottom: 8px; }
.item-meta { font-size: 12px; color: var(--text-muted); }
.meta-label { font-weight: 500; }

.empty-state { text-align: center; color: var(--text-secondary); padding: 20px; font-style: italic; }

/* Mini Modal for Add Forms */
.mini-modal {
  position: absolute;
  top: 16px; left: 16px; right: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  box-shadow: 0 16px 30px rgba(15, 23, 42, 0.15);
  padding: 16px;
  border-radius: 8px;
  z-index: 10;
}

.mini-modal h4 { margin-top: 0; margin-bottom: 12px; }

.mini-modal input, .mini-modal textarea {
  width: 100%;
  margin-bottom: 8px;
}

.mini-modal .markdown-editor {
  margin-bottom: 8px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}

.save-btn { background: var(--accent-primary); color: white; border: none; padding: 6px 12px; border-radius: 4px; cursor: pointer; }
.cancel-btn { background: transparent; border: 1px solid var(--border-color); color: var(--text-secondary); padding: 6px 12px; border-radius: 4px; cursor: pointer; }

.item-controls {
  display: flex;
  align-items: center;
  gap: 8px;
}

.icon-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 2px 4px;
  border-radius: 4px;
  color: var(--text-secondary);
  transition: all 0.2s;
}

.icon-btn:hover {
  background: var(--bg-hover);
  color: var(--text-primary);
}

.delete-btn:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

</style>
