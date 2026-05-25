<template>
  <div class="app-shell">
    <nav class="wf-navbar">
      <div class="wf-navbar-left">
        <router-link to="/" class="wf-home-link">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          <span>首页</span>
        </router-link>

      </div>
      <div class="wf-navbar-center">
        <slot name="nav-center"></slot>
      </div>
      <div class="wf-navbar-right">
        <router-link to="/settings/llm" class="wf-config-link">LLM 配置</router-link>
        <slot name="nav-right"></slot>
      </div>
    </nav>
    <main class="wf-content">
      <slot></slot>
    </main>
  </div>
</template>

<script setup>
</script>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--wf-bg-primary);
}

.wf-navbar {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-lg);
  background: rgba(9, 9, 11, 0.85);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
  z-index: 100;
}

.wf-navbar-left {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.wf-home-link {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
  border-radius: var(--radius-sm);
  color: var(--wf-text-muted);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all var(--transition-fast);
  border: 1px solid transparent;
}
.wf-home-link:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--wf-text-primary);
  border-color: rgba(255, 255, 255, 0.1);
}

.wf-navbar-center {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.wf-navbar-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.wf-config-link {
  padding: 5px 12px;
  border-radius: var(--radius-sm);
  color: var(--wf-accent);
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  border: 1px solid var(--wf-border-light);
  transition: all var(--transition-fast);
}
.wf-config-link:hover {
  background: var(--wf-accent-muted);
  border-color: var(--wf-accent);
  color: var(--wf-accent-hover);
}

.wf-content {
  flex: 1;
  overflow-y: auto;
}
</style>
