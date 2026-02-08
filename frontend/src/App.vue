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
        
        <!-- Navigation -->
        <nav class="nav-links">
          <button 
            class="nav-btn" 
            :class="{ active: currentView === 'chat' }"
            @click="currentView = 'chat'"
          >
            Chat
          </button>
          <button 
            class="nav-btn" 
            :class="{ active: currentView === 'agents' }"
            @click="currentView = 'agents'"
          >
            Agents
          </button>
        </nav>
        
        <div class="header-actions">
          <button class="btn btn-ghost" @click="toggleHistory">
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
      <keep-alive>
        <component 
          :is="currentViewComponent" 
          :show-history="showHistory"
          @update:showHistory="showHistory = $event"
          ref="viewRef"
        />
      </keep-alive>
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
/* Global Styles */
:root {
  --bg-primary: #0f172a;
  --bg-secondary: #1e293b;
  --bg-tertiary: #334155;
  --bg-card: rgba(30, 41, 59, 0.7);
  
  --text-primary: #f8fafc;
  --text-secondary: #cbd5e1;
  --text-muted: #94a3b8;
  
  --accent-primary: #3b82f6;
  --accent-secondary: #6366f1;
  --accent-success: #10b981;
  --accent-warning: #f59e0b;
  --accent-error: #ef4444;
  
  --border-color: rgba(148, 163, 184, 0.1);
  --glass-bg: rgba(15, 23, 42, 0.8);
  --glass-border: rgba(255, 255, 255, 0.05);
  
  --gradient-primary: linear-gradient(135deg, #60a5fa 0%, #a78bfa 100%);
  --gradient-card: linear-gradient(180deg, rgba(59, 130, 246, 0.05) 0%, rgba(15, 23, 42, 0) 100%);
  
  --radius-sm: 6px;
  --radius-md: 12px;
  --radius-lg: 24px;
}

* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: 'Inte', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background-color: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.5;
}

/* Utilities */
.glass {
  background: var(--glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid var(--glass-border);
}

.card {
  background: var(--bg-card);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.card-glow {
  box-shadow: 0 0 40px -10px rgba(59, 130, 246, 0.15);
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  font-weight: 500;
  transition: all 0.2s;
  border: none;
  cursor: pointer;
  font-size: 14px;
}

.btn-primary {
  background: var(--accent-primary);
  color: white;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-1px);
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-secondary {
    background: var(--bg-tertiary);
    color: var(--text-primary);
}

.btn-secondary:hover {
    background: var(--bg-secondary);
}

.btn-ghost {
  background: transparent;
  color: var(--text-secondary);
}

.btn-ghost:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
}

.input {
  width: 100%;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  transition: all 0.2s;
}
.input.textarea {
    min-height: 80px;
    resize: vertical;
}

.input:focus {
  outline: none;
  border-color: var(--accent-primary);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2);
}

.badge {
  display: inline-flex;
  padding: 4px 10px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.badge-info {
  background: rgba(59, 130, 246, 0.15);
  color: #60a5fa;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.badge-success {
  background: rgba(16, 185, 129, 0.15);
  color: #34d399;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.badge-secondary {
    background: var(--bg-tertiary);
    color: var(--text-secondary);
}

.badge-warning {
    background: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.2);
}

/* Animations */
.animate-fadeIn {
  animation: fadeIn 0.4s ease-out forwards;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.loader {
  width: 18px;
  height: 18px;
  border: 2px solid #fff;
  border-bottom-color: transparent;
  border-radius: 50%;
  display: inline-block;
  box-sizing: border-box;
  animation: rotation 1s linear infinite;
}

@keyframes rotation {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Scrollbar */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-primary);
}

::-webkit-scrollbar-thumb {
  background: var(--bg-tertiary);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #475569;
}
</style>

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

/* Navigation */
.nav-links {
    display: flex;
    gap: 8px;
    background: var(--bg-secondary);
    padding: 4px;
    border-radius: 8px;
}

.nav-btn {
    background: transparent;
    border: none;
    color: var(--text-secondary);
    padding: 6px 16px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    border-radius: 6px;
    transition: all 0.2s;
}

.nav-btn:hover {
    color: var(--text-primary);
}

.nav-btn.active {
    background: var(--bg-tertiary);
    color: var(--text-primary);
    box-shadow: 0 1px 2px rgba(0,0,0,0.2);
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
  position: relative;
}

@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 16px;
  }
  
  .nav-links {
      order: 3;
      width: 100%;
      justify-content: center;
  }
  
  .header-actions {
      width: 100%;
      justify-content: space-between;
  }
}
</style>
