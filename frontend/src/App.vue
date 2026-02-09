<template>
  <div class="app-layout">
    <!-- Sidebar Navigation -->
    <aside class="sidebar glass">
      <div class="logo-container">
        <div class="logo-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        </div>
        <div class="logo-text">
          <h1>AI Query</h1>
        </div>
      </div>
      
      <nav class="nav-menu">
        <button 
          class="nav-item" 
          :class="{ active: currentView === 'chat' }"
          @click="currentView = 'chat'"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
          Chat Output
        </button>
        <button 
          class="nav-item" 
          :class="{ active: currentView === 'agents' }"
          @click="currentView = 'agents'"
        >
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
            <circle cx="9" cy="7" r="4"></circle>
            <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
            <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
          </svg>
          Agent Manager
        </button>
      </nav>
      
      <div class="sidebar-footer">
        <div class="connection-status">
          <div class="status-dot" :class="connected ? 'connected' : 'disconnected'"></div>
          <span>{{ connected ? 'System Online' : 'Disconnected' }}</span>
        </div>
      </div>
    </aside>
    
    <!-- Main Content Area -->
    <main class="main-content">
      <!-- Top Bar -->
      <header class="top-bar">
        <div class="breadcrumbs">
          <span class="text-muted">App</span>
          <span class="separator">/</span>
          <span class="current-view">{{ currentView === 'chat' ? 'Chat Interface' : 'Agent Management' }}</span>
        </div>
        
        <div class="top-actions">
           <button class="icon-btn" @click="toggleHistory" title="History">
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polyline points="12 6 12 12 16 14"/>
            </svg>
          </button>
          <div class="user-profile">
            <div class="avatar">A</div>
          </div>
        </div>
      </header>
      
      <!-- View Content -->
      <div class="content-wrapper animate-fadeIn">
        <keep-alive>
          <component 
            :is="currentViewComponent" 
            :show-history="showHistory"
            @update:showHistory="showHistory = $event"
            ref="viewRef"
          />
        </keep-alive>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import ChatInterface from './components/ChatInterface.vue'
import AgentManager from './components/AgentManager.vue'

// State
const currentView = ref('chat')
const showHistory = ref(false)
const connected = ref(true)
const viewRef = ref(null)

const currentViewComponent = computed(() => {
  return currentView.value === 'chat' ? ChatInterface : AgentManager
})

const api = axios.create({
  baseURL: '/api'
})

function toggleHistory() {
    showHistory.value = !showHistory.value
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

<style>
/* Modern CSS Reset & Variables */
:root {
  --bg-dark: #f5f7fb;
  --bg-sidebar: #ffffff;
  --bg-card: #ffffff;
  --bg-input: #f1f5f9;
  --bg-tertiary: #e2e8f0;
  --bg-hover: #eef2ff;
  
  --text-primary: #0f172a;
  --text-secondary: #475569;
  --text-muted: #94a3b8;
  
  --accent-primary: #2563eb;
  --accent-hover: #1d4ed8;
  --accent-success: #16a34a;
  --accent-danger: #dc2626;
  --accent-warning: #d97706;
  
  --border-color: #e2e8f0;
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-lg: 16px;
  
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.08);
  --shadow-md: 0 8px 20px rgba(15, 23, 42, 0.08);
  --shadow-glow: 0 0 20px rgba(37, 99, 235, 0.18);
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  background-color: var(--bg-dark);
  color: var(--text-primary);
  line-height: 1.5;
  overflow: hidden; /* App handles scroll */
}

/* App Layout */
.app-layout {
  display: flex;
  height: 100vh;
  width: 100vw;
}

/* Sidebar */
.sidebar {
  width: 260px;
  background-color: var(--bg-sidebar);
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  padding: 20px;
  z-index: 100;
}

.logo-container {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 40px;
  padding: 0 10px;
}

.logo-icon {
  width: 36px;
  height: 36px;
  background: linear-gradient(135deg, var(--accent-primary) 0%, #a78bfa 100%);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  box-shadow: var(--shadow-glow);
}

.logo-icon svg {
  width: 20px;
  height: 20px;
}

.logo-text h1 {
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.5px;
}

.nav-menu {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  font-weight: 500;
  font-size: 14px;
}

.nav-item svg {
  opacity: 0.7;
}

.nav-item:hover {
  background: rgba(37, 99, 235, 0.08);
  color: var(--text-primary);
}

.nav-item.active {
  background: rgba(37, 99, 235, 0.12);
  color: var(--accent-primary);
}

.nav-item.active svg {
  opacity: 1;
}

.sidebar-footer {
  margin-top: auto;
  padding-top: 20px;
  border-top: 1px solid var(--border-color);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 0 10px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--border-color);
}

.status-dot.connected {
  background: var(--accent-success);
  box-shadow: 0 0 8px rgba(35, 134, 54, 0.4);
}

.status-dot.disconnected {
  background: var(--accent-danger);
}

/* Main Content */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--bg-dark);
}

.top-bar {
  height: 64px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
}

.breadcrumbs {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.separator {
  color: var(--text-muted);
}

.current-view {
  color: var(--text-primary);
  font-weight: 500;
}

.top-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}

.icon-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.2s;
}

.icon-btn:hover {
  background: var(--bg-card);
  border-color: var(--border-color);
  color: var(--text-primary);
}

.user-profile {
  display: flex;
  align-items: center;
}

.avatar {
  width: 32px;
  height: 32px;
  background: var(--accent-primary);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  color: white;
}

/* Content Area */
.content-wrapper {
  flex: 1;
  overflow: hidden;
  position: relative;
  /* Custom scrollbar handled by children */
}

/* Global Component Styles */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.btn-primary {
  background: var(--accent-primary);
  color: white;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.2);
}

.btn-primary:hover {
  background: var(--accent-hover);
  transform: translateY(-1px);
}

.btn-secondary {
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
}

.btn-secondary:hover {
  background: var(--bg-sidebar);
  border-color: var(--text-secondary);
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
}

.btn-ghost:hover {
  background: rgba(37, 99, 235, 0.08);
  color: var(--text-primary);
}

.input, .select-input, .textarea {
  width: 100%;
  background: var(--bg-input);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  font-size: 14px;
  transition: all 0.2s;
}

.input:focus, .select-input:focus, .textarea:focus {
  outline: none;
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.15);
}

/* Scrollbar styling */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--text-muted);
}

/* Animation */
.animate-fadeIn {
  animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Responsive */
@media (max-width: 768px) {
  .app-layout {
    flex-direction: column;
  }
  
  .sidebar {
    width: 100%;
    height: 60px;
    flex-direction: row;
    align-items: center;
    padding: 0 20px;
    justify-content: space-between;
  }
  
  .logo-container {
    margin-bottom: 0;
  }
  
  .nav-menu {
    flex-direction: row;
    flex: 0;
  }
  
  .nav-item span {
    display: none;
  }
  
  .sidebar-footer {
    display: none;
  }
  
  .top-bar {
    display: none;
  }
}
</style>
