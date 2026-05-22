<template>
  <div class="home-page">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-content">
        <div class="hero-badge">
          <span class="badge-dot"></span>
          世界观推演引擎
        </div>
        <h1 class="hero-title">
          <span class="title-brand">WORLDFISH</span>
          <span class="title-sub">创世鱼缸</span>
        </h1>
        <p class="hero-desc">
          创造属于你的世界，并让它不断进化。
        </p>
        <div class="hero-actions">
          <router-link to="/world-builder" class="btn btn-primary hero-btn-primary">
            构建世界观 →
          </router-link>
          <button class="btn btn-secondary hero-btn-secondary" @click="scrollToWorlds">
            已有世界观
          </button>
        </div>
      </div>
      <div class="hero-visual">
        <div class="visual-orb"></div>
        <div class="visual-ring"></div>
        <div class="visual-ring ring-2"></div>
        <img src="/worldfish_logo.svg" alt="WORLDFISH" class="visual-logo" />
      </div>
    </section>

    <!-- Worlds Dashboard -->
    <section class="worlds-section" ref="worldsSection">
      <div class="section-top">
        <h2 class="section-title">你的世界观</h2>
        <router-link to="/world-builder" class="btn btn-primary btn-sm">
          + 新建
        </router-link>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="state-message">
        <div class="loading-spinner"></div>
        <p>加载中...</p>
      </div>

      <!-- Error -->
      <div v-else-if="loadError" class="state-message">
        <p class="message-error">{{ loadError }}</p>
        <button class="btn btn-secondary" @click="fetchWorlds">重试</button>
      </div>

      <!-- Empty -->
      <div v-else-if="worlds.length === 0" class="empty-state">
        <div class="empty-icon">🌍</div>
        <h3>还没有世界观</h3>
        <p>开始构建你的第一个世界观，AI 将帮你从文本中提取角色、组织、事件和设定。</p>
        <router-link to="/world-builder" class="btn btn-primary">
          开始构建
        </router-link>
      </div>

      <!-- World Cards -->
      <div v-else class="worlds-grid">
        <div
          v-for="world in worlds"
          :key="world.id"
          class="world-card card"
        >
          <div class="world-card-top">
            <h3 class="world-name">{{ world.name || '未命名世界观' }}</h3>
            <span v-if="world.era" class="tag tag-primary">{{ world.era }}</span>
          </div>
          <p class="world-desc">{{ world.description || '暂无描述' }}</p>
          <div class="world-meta">
            <span v-if="world.entities_count > 0">{{ world.entities_count }} 实体</span>
            <span v-if="world.events_count > 0">{{ world.events_count }} 事件</span>
            <span v-if="world.anchor_time">{{ world.anchor_time }}</span>
          </div>
          <div class="world-card-actions">
            <router-link :to="'/world-builder?worldId=' + world.id" class="btn btn-accent btn-sm">
              编辑
            </router-link>
            <router-link :to="'/rag?worldId=' + world.id" class="btn btn-accent btn-sm">
              知识库
            </router-link>
            <router-link :to="'/simulation/new?worldId=' + world.id" class="btn btn-primary btn-sm">
              开始推演 →
            </router-link>
          </div>
        </div>
      </div>
    </section>

    <!-- Footer -->
    <footer class="home-footer">
      <span>WORLDFISH</span>
      <span class="footer-divider">·</span>
      <span>基于 LLM 驱动</span>
    </footer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { worldApi } from '../api/world'

const worlds = ref([])
const loading = ref(true)
const loadError = ref('')
const worldsSection = ref(null)

async function fetchWorlds() {
  loading.value = true
  loadError.value = ''
  try {
    const res = await worldApi.listWorlds()
    worlds.value = res.worlds || []
  } catch (e) {
    loadError.value = '加载世界观列表失败: ' + (e.message || '网络错误')
  } finally {
    loading.value = false
  }
}

function scrollToWorlds() {
  worldsSection.value?.scrollIntoView({ behavior: 'smooth' })
}

onMounted(fetchWorlds)
</script>

<style scoped>
.home-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: var(--spacing-2xl) var(--spacing-lg);
}

/* Hero */
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-2xl);
  padding: var(--spacing-2xl) 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  margin-bottom: var(--spacing-2xl);
}

.hero-content {
  flex: 1;
  max-width: 600px;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: 13px;
  color: var(--wf-accent);
  font-weight: 500;
  margin-bottom: var(--spacing-lg);
  font-family: var(--font-mono);
}

.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--wf-accent);
  box-shadow: 0 0 10px var(--wf-accent-glow);
  animation: pulseGlow 2s infinite;
}

.hero-title {
  font-size: 3.5rem;
  line-height: 1.15;
  margin-bottom: var(--spacing-lg);
}

.title-brand {
  display: block;
  font-family: var(--font-display);
  font-weight: 700;
  letter-spacing: 3px;
  color: var(--wf-accent);
  font-size: 2.4rem;
  margin-bottom: var(--spacing-sm);
  text-shadow: 0 0 30px var(--wf-accent-glow);
}

.title-sub {
  font-family: var(--font-sans);
  font-weight: 600;
  color: var(--wf-text-primary);
}

.hero-desc {
  font-size: 1.05rem;
  line-height: 1.75;
  color: var(--wf-text-secondary);
  margin-bottom: var(--spacing-xl);
}

.hero-actions {
  display: flex;
  gap: var(--spacing-md);
}

.hero-btn-primary {
  padding: 14px 32px;
  font-size: 15px;
  border-radius: var(--radius-2xl);
}

.hero-btn-secondary {
  padding: 14px 32px;
  font-size: 15px;
  border-radius: var(--radius-2xl);
}

/* Hero Visual */
.hero-visual {
  flex: 0.6;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  height: 280px;
}

.visual-orb {
  width: 160px;
  height: 160px;
  border-radius: 50%;
  background: radial-gradient(circle, var(--wf-accent) 0%, transparent 70%);
  opacity: 0.12;
  position: absolute;
  box-shadow: 0 0 60px var(--wf-accent-glow);
}

.visual-ring {
  width: 220px;
  height: 220px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.10);
  position: absolute;
  animation: spin 20s linear infinite;
}

.ring-2 {
  width: 280px;
  height: 280px;
  animation-direction: reverse;
  animation-duration: 30s;
  opacity: 0.5;
}

.visual-logo {
  position: absolute;
  height: 200px;
  width: auto;
  z-index: 2;
  /* 将 SVG 转为纯白色 */
  filter: brightness(0) invert(1);
  pointer-events: none;
  user-select: none;
}

/* Section */
.worlds-section {
  padding-bottom: var(--spacing-2xl);
}

.section-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.section-title {
  font-family: var(--font-display);
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--wf-text-primary);
  letter-spacing: 1px;
}

.btn-sm {
  padding: 8px 20px;
  font-size: 13px;
  border-radius: var(--radius-2xl);
}

/* States */
.state-message {
  text-align: center;
  padding: var(--spacing-2xl);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-md);
}

.empty-state {
  text-align: center;
  padding: var(--spacing-2xl) var(--spacing-lg);
  border: 1px dashed var(--wf-border);
  border-radius: var(--radius-xl);
  background: rgba(255, 255, 255, 0.02);
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: var(--spacing-md);
}

.empty-state h3 {
  color: var(--wf-text-primary);
  margin-bottom: var(--spacing-sm);
}

.empty-state p {
  color: var(--wf-text-secondary);
  max-width: 480px;
  margin: 0 auto var(--spacing-lg);
  font-size: 0.95rem;
  line-height: 1.6;
}

/* World Cards */
.worlds-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--spacing-lg);
}

.world-card {
  display: flex;
  flex-direction: column;
}

.world-card-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.world-name {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--wf-text-primary);
}

.world-desc {
  font-size: 0.85rem;
  color: var(--wf-text-secondary);
  line-height: 1.55;
  flex: 1;
  margin-bottom: var(--spacing-sm);
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.world-meta {
  display: flex;
  gap: var(--spacing-md);
  font-size: 0.75rem;
  color: var(--wf-text-muted);
  margin-bottom: var(--spacing-md);
}

.world-card-actions {
  display: flex;
  gap: var(--spacing-sm);
}

/* Footer */
.home-footer {
  text-align: center;
  padding: var(--spacing-xl) 0;
  color: var(--wf-text-muted);
  font-size: 0.8rem;
  font-family: var(--font-mono);
  letter-spacing: 1px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.footer-divider {
  margin: 0 var(--spacing-sm);
  color: var(--wf-border-light);
}

/* Responsive */
@media (max-width: 768px) {
  .hero {
    flex-direction: column;
    text-align: center;
  }
  .hero-content { max-width: 100%; }
  .hero-actions { justify-content: center; }
  .hero-title { font-size: 2.5rem; }
  .title-brand { font-size: 1.5rem; }
  .worlds-grid { grid-template-columns: 1fr; }
  .hero-visual { display: none; }
}
</style>
