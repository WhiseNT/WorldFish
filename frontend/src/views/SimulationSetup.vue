<template>
  <div class="sim-setup-page">
    <div class="setup-container">
      <!-- Step indicator -->
      <div class="setup-step-row">
        <StepIndicator :currentStep="1" :totalSteps="3" :stepLabels="['推演设置', '推演进化', '结果']" />
      </div>

      <!-- Loading world -->
      <div v-if="loadingWorld" class="state-box">
        <div class="loading-spinner"></div>
        <p>加载世界观数据...</p>
      </div>

      <!-- Error -->
      <div v-else-if="worldError" class="state-box">
        <p class="message-error">{{ worldError }}</p>
        <router-link to="/world-builder" class="btn btn-secondary">返回世界观构建</router-link>
      </div>

      <!-- Setup form -->
      <div v-else class="setup-content">
        <!-- World summary -->
        <div class="world-summary card">
          <h3 class="summary-title">{{ world.name || '未命名世界观' }}</h3>
          <div class="summary-meta">
            <span v-if="world.era" class="tag tag-primary">{{ world.era }}</span>
            <span v-if="world.anchor_time" class="tag tag-accent">{{ world.anchor_time }}</span>
            <span>{{ entities.length }} 实体</span>
            <span>{{ events.length }} 事件</span>
          </div>
          <p class="summary-desc">{{ world.description }}</p>
        </div>

        <!-- Scenario input -->
        <div class="scenario-section card">
          <h3 class="card-title">推演需求 / 场景</h3>
          <p class="card-hint">描述你希望世界观如何发展。例如："如果北方帝国突然入侵..."、"100年后的世界会变成什么样？"</p>
          <textarea
            v-model="scenario"
            class="scenario-input"
            placeholder="输入推演场景描述..."
            rows="8"
          ></textarea>
        </div>

        <!-- Parameters -->
        <div class="params-section card">
          <h3 class="card-title">推演参数</h3>
          <div class="params-grid">
            <div class="form-group">
              <label>推演轮次</label>
              <input type="number" v-model.number="config.rounds" min="1" max="20" class="form-input" />
              <span class="form-hint">1-20 轮，每轮代表一段时间推进</span>
            </div>
            <div class="form-group">
              <label>创意温度</label>
              <input type="range" v-model.number="config.temperature" min="0" max="1" step="0.1" class="form-range" />
              <span class="form-hint">{{ config.temperature }} — 越高越有创意</span>
            </div>
            <div class="form-group">
              <label>起始时间锚点</label>
              <input
                type="text"
                v-model.trim="config.time_span_start"
                class="form-input wide-input"
                :placeholder="world.anchor_time || '留空则自动解析场景或沿用父轮次时间'"
              />
              <span class="form-hint">留空时会优先使用父轮次时间，其次尝试解析场景中的时间提示，最后回退到世界观锚定时间。</span>
            </div>
            <div class="form-group">
              <label>起始事件锚点</label>
              <input
                type="text"
                v-model.trim="config.anchor_event"
                class="form-input wide-input"
                list="simulation-anchor-events"
                placeholder="可输入事件名或关键词，例如 王都政变"
              />
              <datalist id="simulation-anchor-events">
                <option v-for="eventName in eventOptions" :key="eventName" :value="eventName"></option>
              </datalist>
              <span class="form-hint">若填写，将优先从该事件发生后开始推演；也支持直接在“推演需求”里写事件名。</span>
            </div>
            <div class="form-group">
              <label>关注领域</label>
              <div class="checkbox-group">
                <label v-for="area in focusOptions" :key="area" class="checkbox-label">
                  <input type="checkbox" :value="area" v-model="config.focus_areas" />
                  {{ area }}
                </label>
              </div>
            </div>
          </div>
        </div>

        <div class="scenario-section card">
          <h3 class="card-title">文风来源</h3>
          <p class="card-hint">推演会自动使用当前世界观中保存的文风信息，这里不再需要手动填写。</p>
          <div class="style-readonly-box">
            <div class="style-readonly-item">
              <label>文风描述</label>
              <p>{{ worldStyle.writing_style || '未单独配置文风描述，推演将直接依据世界观正文与设定进行叙事。' }}</p>
            </div>
            <div v-if="worldStyle.reference_text" class="style-readonly-item">
              <label>参考文本</label>
              <p>{{ worldStyle.reference_text }}</p>
            </div>
          </div>
        </div>

        <!-- Action -->
        <div class="setup-actions">
          <button
            class="btn btn-primary btn-large"
            :disabled="!canStart || starting"
            @click="startEvolution"
          >
            <template v-if="starting">启动中...</template>
            <template v-else><span>开始推演</span><SvgIcon name="arrow-right" :size="16" /></template>
          </button>
          <p v-if="!hasLlmConfig" class="message-warning">请先在 LLM 配置中设置 API Key</p>
        </div>

        <p v-if="error" class="message-error">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { worldApi } from '../api/world'
import StepIndicator from '../components/StepIndicator.vue'
import SvgIcon from '../components/ui/SvgIcon.vue'

const route = useRoute()
const router = useRouter()

const worldId = ref(route.query.worldId || '')
const parentEvolutionId = ref(route.query.parentEvolutionId || '')
const parentRound = ref(parseInt(route.query.parentRound) || -1)
const evolutionType = ref(route.query.evolutionType || 'forward')  // "forward" | "branch"
const world = ref({})
const entities = ref([])
const events = ref([])
const settings = ref({})
const loadingWorld = ref(true)
const worldError = ref('')
const scenario = ref('')
const starting = ref(false)
const error = ref('')
const hasLlmConfig = ref(true) // Will be checked on mount

const config = ref({
  rounds: 5,
  temperature: 0.7,
  time_span_start: '',
  anchor_event: '',
  focus_areas: [],
})
const worldStyle = ref({
  writing_style: '',
  reference_text: '',
})

const focusOptions = ['政治军事', '经济发展', '文化变迁', '科技演进', '角色关系', '地理变化']

const canStart = computed(() => scenario.value.trim().length > 0 && hasLlmConfig.value)
const eventOptions = computed(() => (events.value || []).map(evt => String(evt?.name || '').trim()).filter(Boolean))

onMounted(async () => {
  // Check LLM config
  try {
    const res = await worldApi.getLlmConfig()
    hasLlmConfig.value = res.config?.api_key_configured || false
  } catch (e) { hasLlmConfig.value = false }

  // Load world
  if (!worldId.value) {
    worldError.value = '未指定世界观 ID'
    loadingWorld.value = false
    return
  }
  try {
    const res = await worldApi.getWorld(worldId.value)
    const w = res.world || {}
    world.value = { name: w.name, description: w.description, era: w.era, anchor_time: w.anchor_time }
    entities.value = w.entities || []
    events.value = w.events || []
    settings.value = w.settings || {}
    worldStyle.value = {
      writing_style: w.writing_style || '',
      reference_text: w.reference_text || '',
    }
  } catch (e) {
    worldError.value = '加载世界观失败: ' + (e.message || '')
  } finally {
    loadingWorld.value = false
  }
})

async function startEvolution() {
  if (!canStart.value || starting.value) return
  starting.value = true
  error.value = ''
  try {
    const { default: service } = await import('../api/index')
    const res = await service.post('/api/evolution/create', {
      world_id: worldId.value,
      scenario: scenario.value,
      config: config.value,
      evolution_type: evolutionType.value,
      parent_evolution_id: parentEvolutionId.value,
      parent_round: parentRound.value,
    })
    router.push({ name: 'SimulationEvolution', params: { id: res.evolution_id } })
  } catch (e) {
    error.value = '启动推演失败: ' + (e.message || '')
  } finally {
    starting.value = false
  }
}
</script>

<style scoped>
.sim-setup-page { max-width: 900px; margin: 0 auto; padding: var(--spacing-2xl) var(--spacing-lg); }
.setup-container { display: flex; flex-direction: column; gap: var(--spacing-lg); }
.setup-step-row { display: flex; justify-content: center; margin-bottom: var(--spacing-lg); }

.state-box { text-align: center; padding: var(--spacing-2xl); display: flex; flex-direction: column; align-items: center; gap: var(--spacing-md); }

.setup-content { display: flex; flex-direction: column; gap: var(--spacing-lg); }

.world-summary { }
.summary-title { font-size: 1.3rem; font-weight: 600; color: var(--wf-text-primary); margin-bottom: var(--spacing-sm); }
.summary-meta { display: flex; flex-wrap: wrap; gap: var(--spacing-sm); align-items: center; margin-bottom: var(--spacing-sm); font-size: 0.85rem; color: var(--wf-text-muted); }
.summary-desc { font-size: 0.9rem; color: var(--wf-text-secondary); line-height: 1.6; }

.card-title { font-size: 1rem; font-weight: 600; color: var(--wf-text-primary); margin-bottom: var(--spacing-sm); }
.card-hint { font-size: 0.85rem; color: var(--wf-text-muted); margin-bottom: var(--spacing-md); }

.scenario-input {
  width: 100%;
  background: var(--wf-bg-input);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  color: var(--wf-text-primary);
  padding: var(--spacing-md);
  font-family: var(--font-sans);
  resize: vertical;
  min-height: 160px;
}
.scenario-input:focus { outline: none; border-color: var(--wf-accent); box-shadow: 0 0 0 3px var(--wf-accent-muted); }

.params-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--spacing-md); }
.form-input { width: 100%; max-width: 100px; }
.form-range { width: 100%; max-width: 200px; accent-color: var(--wf-accent); }
.form-hint { display: block; font-size: 0.75rem; color: var(--wf-text-muted); margin-top: var(--spacing-xs); }
.checkbox-group { display: flex; flex-wrap: wrap; gap: var(--spacing-sm); }
.checkbox-label { display: flex; align-items: center; gap: 4px; font-size: 0.85rem; color: var(--wf-text-secondary); cursor: pointer; }
.checkbox-label input[type="checkbox"] { accent-color: var(--wf-accent); }

.setup-actions { display: flex; flex-direction: column; align-items: center; gap: var(--spacing-md); }
.btn-large { padding: 14px 48px; font-size: 16px; border-radius: var(--radius-2xl); }
.wide-input { width: 100%; max-width: 100%; }
.style-readonly-box {
  display: grid;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  background: rgba(148, 163, 184, 0.08);
  border: 1px solid rgba(148, 163, 184, 0.14);
}
.style-readonly-item label {
  display: block;
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--wf-text-secondary);
  margin-bottom: 6px;
}
.style-readonly-item p {
  margin: 0;
  font-size: 0.88rem;
  line-height: 1.7;
  color: var(--wf-text-primary);
  white-space: pre-wrap;
}
</style>
