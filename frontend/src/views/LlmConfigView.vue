<template>
  <div class="llm-config-page">
    <header class="config-hero">
      <div>
        <button class="back-link" @click="goBack">← 返回</button>
        <h1>LLM 配置中心</h1>
        <p>分别配置主 Agent、SubAgent、解析 Agent 与 RAG 向量化服务。</p>
      </div>
      <div class="hero-actions">
        <span v-if="feedback" class="feedback" :class="feedbackType">{{ feedback }}</span>
        <button class="btn-secondary" @click="loadConfig" :disabled="loading">刷新配置</button>
      </div>
    </header>

    <section class="overview-grid">
      <button
        v-for="role in roleCards"
        :key="role.id"
        class="overview-card"
        :class="{ active: activeRole === role.id }"
        @click="activeRole = role.id"
      >
        <span class="role-kicker">{{ role.kicker }}</span>
        <strong>{{ role.title }}</strong>
        <span class="role-desc">{{ role.description }}</span>
        <span class="role-status" :class="{ ready: roleStatus(role.id).api_key_configured }">
          {{ roleStatus(role.id).api_key_configured ? '已配置' : '未配置' }}
          <template v-if="roleStatus(role.id).resolved_from && roleStatus(role.id).resolved_from !== role.id">
            · 回退到 {{ roleLabel(roleStatus(role.id).resolved_from) }}
          </template>
        </span>
        <span class="role-model">{{ apiTypeLabel(roleStatus(role.id).api_type) }} · {{ roleStatus(role.id).model_name || '未设置模型' }}</span>
      </button>
    </section>

    <TransitionGroup name="toast" tag="div" class="toast-stack">
      <div v-for="toast in toasts" :key="toast.id" class="toast-card" :class="toast.type">
        <span class="toast-icon">{{ toast.type === 'error' ? '!' : '✓' }}</span>
        <span>{{ toast.text }}</span>
        <button type="button" @click="dismissToast(toast.id)">×</button>
      </div>
    </TransitionGroup>

    <main class="config-layout">
      <aside class="config-nav">
        <button v-for="role in roleCards" :key="role.id" :class="{ active: activeRole === role.id }" @click="activeRole = role.id">
          <span>{{ role.title }}</span>
          <small>{{ role.kicker }}</small>
        </button>
        <button :class="{ active: activeRole === 'advanced' }" @click="activeRole = 'advanced'">
          <span>高级参数</span>
          <small>Context / Thinking</small>
        </button>
      </aside>

      <section v-if="activeRole !== 'advanced'" class="config-panel">
        <div class="panel-header">
          <div>
            <span class="panel-kicker">{{ activeRoleMeta.kicker }}</span>
            <h2>{{ activeRoleMeta.title }}</h2>
            <p>{{ activeRoleMeta.description }}</p>
          </div>
          <div class="masked-key" v-if="roleStatus(activeRole).api_key_masked">
            当前 Key：{{ roleStatus(activeRole).api_key_masked }}
          </div>
        </div>

        <div class="form-grid">
          <label class="form-field full">
            <span>API Key</span>
            <input type="password" v-model="forms[activeRole].api_key" :placeholder="roleStatus(activeRole).api_key_configured ? '留空则保持当前 Key' : '输入 API Key'" />
          </label>
          <label class="form-field">
            <span>API 类型</span>
            <select v-model="forms[activeRole].api_type">
              <option value="openai_compatible">OpenAI 兼容</option>
              <option value="anthropic">Anthropic</option>
            </select>
          </label>
          <label class="form-field">
            <span>URL 模式</span>
            <select v-model="forms[activeRole].url_mode">
              <option value="base_url">Base URL 模式</option>
              <option value="full_url">完整 URL 模式</option>
            </select>
          </label>
          <label class="form-field">
            <span>{{ forms[activeRole].url_mode === 'full_url' ? '完整 URL' : 'Base URL' }}</span>
            <input v-model="forms[activeRole].base_url" :placeholder="urlPlaceholder(forms[activeRole])" />
          </label>
          <label class="form-field">
            <span>Model Name</span>
            <div class="model-row">
              <input v-model="forms[activeRole].model_name" placeholder="gpt-4o-mini / claude-3-5-sonnet-latest" />
              <button type="button" class="btn-secondary" :disabled="loadingModelsRole === activeRole" @click="fetchModels(activeRole)">
                {{ loadingModelsRole === activeRole ? '获取中...' : '获取模型' }}
              </button>
            </div>
          </label>
        </div>

        <div v-if="models[activeRole]?.length" class="model-list">
          <button v-for="model in models[activeRole]" :key="model" type="button" @click="forms[activeRole].model_name = model">{{ model }}</button>
        </div>

        <div class="hint-card" v-if="activeRole === 'embedding'">
          Embedding 未显式配置 API Key 时，会复用主 Agent 的 API Key 与 Base URL。
        </div>
        <div class="hint-card" v-if="forms[activeRole].url_mode === 'base_url'">
          Base URL 模式请填写到 /v1，例如 https://api.littlecold.cn/v1；如果填写 /v1/chat/completions，应用会自动按完整 URL 发送请求。
        </div>
        <div class="hint-card" v-else-if="roleStatus(activeRole).resolved_from && roleStatus(activeRole).resolved_from !== activeRole">
          当前用途未显式配置，将按后端规则回退使用 {{ roleLabel(roleStatus(activeRole).resolved_from) }}。
        </div>

        <div class="panel-actions">
          <button class="btn-secondary" :disabled="testingRole === activeRole" @click="testRole(activeRole)">
            {{ testingRole === activeRole ? '测试中...' : '测试连接' }}
          </button>
          <button class="btn-primary" :disabled="savingRole === activeRole" @click="saveRole(activeRole)">
            {{ savingRole === activeRole ? '保存中...' : '保存该用途配置' }}
          </button>
        </div>
      </section>

      <section v-else class="config-panel">
        <div class="panel-header">
          <div>
            <span class="panel-kicker">Advanced</span>
            <h2>高级参数</h2>
            <p>用于控制 Agent 思考、上下文窗口和压缩阈值。不了解时建议保持默认。</p>
          </div>
        </div>

        <div class="form-grid">
          <label class="form-field">
            <span>Thinking Enabled</span>
            <select v-model="advanced.thinking_enabled">
              <option :value="true">开启</option>
              <option :value="false">关闭</option>
            </select>
          </label>
          <label class="form-field">
            <span>Reasoning Effort</span>
            <select v-model="advanced.reasoning_effort">
              <option value="high">high</option>
              <option value="max">max</option>
            </select>
          </label>
          <label class="form-field">
            <span>Context Window Override</span>
            <input type="number" min="0" v-model.number="advanced.context_window" placeholder="0 表示自动" />
          </label>
          <label class="form-field">
            <span>Compression Threshold</span>
            <input type="number" min="0.5" max="0.95" step="0.01" v-model.number="advanced.compression_threshold" />
          </label>
        </div>

        <div class="hint-card">
          当前模型画像：{{ config.model_profile || 'openai-compatible' }}；上下文窗口：{{ config.context_window || '自动' }}。
        </div>

        <div class="panel-actions">
          <button class="btn-primary" :disabled="savingRole === 'advanced'" @click="saveAdvanced">
            {{ savingRole === 'advanced' ? '保存中...' : '保存高级参数' }}
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<script>
import { worldApi } from '../api/world'

const emptyForm = () => ({ api_key: '', api_type: 'openai_compatible', url_mode: 'base_url', base_url: '', model_name: '' })

export default {
  name: 'LlmConfigView',
  data() {
    return {
      loading: false,
      savingRole: '',
      testingRole: '',
      loadingModelsRole: '',
      activeRole: 'agent',
      feedback: '',
      feedbackType: 'success',
      toasts: [],
      toastSeed: 0,
      config: {},
      forms: {
        agent: emptyForm(),
        subagent: emptyForm(),
        parser: emptyForm(),
        embedding: emptyForm(),
      },
      models: {
        agent: [],
        subagent: [],
        parser: [],
        embedding: [],
      },
      advanced: {
        thinking_enabled: false,
        reasoning_effort: 'max',
        context_window: 0,
        compression_threshold: 0.7,
      },
      roleCards: [
        { id: 'agent', kicker: 'Agent', title: '主 Agent', description: '聊天、报告生成、工具调用的主模型。' },
        { id: 'subagent', kicker: 'SubAgent', title: 'SubAgent', description: '委派任务、并行分析和辅助写作。' },
        { id: 'parser', kicker: 'Parser', title: '解析 Agent', description: '世界观抽取、文件解析和结构化提取。' },
        { id: 'embedding', kicker: 'RAG', title: 'Embedding', description: '向量知识库索引与检索。' },
      ],
    }
  },
  computed: {
    activeRoleMeta() {
      return this.roleCards.find(role => role.id === this.activeRole) || this.roleCards[0]
    },
  },
  mounted() {
    this.loadConfig()
  },
  methods: {
    goBack() {
      if (window.history.length > 1) this.$router.back()
      else this.$router.push({ name: 'Home' })
    },
    roleLabel(role) {
      return ({ agent: '主 Agent', subagent: 'SubAgent', parser: '解析 Agent', embedding: 'Embedding' })[role] || role
    },
    apiTypeLabel(type) {
      return type === 'anthropic' ? 'Anthropic' : 'OpenAI 兼容'
    },
    roleStatus(role) {
      const key = role === 'agent' ? 'agent_llm' : role === 'subagent' ? 'subagent_llm' : role === 'parser' ? 'parser_llm' : 'embedding'
      return this.config[key] || {}
    },
    showFeedback(text, type = 'success') {
      this.feedback = text
      this.feedbackType = type
      window.clearTimeout(this._feedbackTimer)
      this._feedbackTimer = window.setTimeout(() => { this.feedback = '' }, 3500)
      this.showToast(text, type)
    },
    showToast(text, type = 'success') {
      const id = ++this.toastSeed
      this.toasts.push({ id, text, type })
      window.setTimeout(() => this.dismissToast(id), 4500)
    },
    dismissToast(id) {
      this.toasts = this.toasts.filter(toast => toast.id !== id)
    },
    errorMessage(error, fallback) {
      const responseMessage = error?.response?.data?.message || error?.response?.data?.error
      return responseMessage || error?.message || fallback
    },
    async loadConfig() {
      this.loading = true
      try {
        const response = await worldApi.getLlmConfig()
        this.config = response.config || {}
        ;['agent', 'subagent', 'parser', 'embedding'].forEach(role => {
          const status = this.roleStatus(role)
          this.forms[role] = {
            api_key: '',
            api_type: status.api_type || 'openai_compatible',
            url_mode: status.url_mode || 'base_url',
            base_url: status.base_url || '',
            model_name: status.model_name || '',
          }
        })
        this.advanced = {
          thinking_enabled: !!this.config.thinking_enabled,
          reasoning_effort: this.config.reasoning_effort || 'max',
          context_window: this.config.context_window_override || 0,
          compression_threshold: this.config.compression_threshold || 0.7,
        }
      } catch (error) {
        console.error('加载 LLM 配置失败:', error)
        this.showFeedback(this.errorMessage(error, '加载配置失败'), 'error')
      } finally {
        this.loading = false
      }
    },
    urlPlaceholder(form) {
      if (form.url_mode === 'full_url') {
        return form.api_type === 'anthropic' ? 'https://api.anthropic.com/v1/messages' : 'https://api.openai.com/v1/chat/completions'
      }
      return form.api_type === 'anthropic' ? 'https://api.anthropic.com' : 'https://api.openai.com/v1'
    },
    buildRolePayload(role) {
      const form = this.forms[role]
      const url = (form.base_url || '').trim()
      const looksLikeChatEndpoint = /\/(chat\/completions|messages|embeddings)\/?$/i.test(url)
      const payload = {
        role,
        api_type: form.api_type || 'openai_compatible',
        url_mode: looksLikeChatEndpoint ? 'full_url' : (form.url_mode || 'base_url'),
        base_url: url,
        model_name: form.model_name,
      }
      if ((form.api_key || '').trim()) payload.api_key = form.api_key.trim()
      return payload
    },
    async fetchModels(role) {
      this.loadingModelsRole = role
      try {
        const response = await worldApi.getLlmModels(this.buildRolePayload(role))
        this.models[role] = response.models || []
        this.showFeedback(this.models[role].length ? `已获取 ${this.models[role].length} 个模型` : '未获取到模型')
      } catch (error) {
        console.error('获取模型失败:', error)
        this.showFeedback(this.errorMessage(error, '获取模型失败'), 'error')
      } finally {
        this.loadingModelsRole = ''
      }
    },
    async saveRole(role) {
      this.savingRole = role
      try {
        await worldApi.saveLlmConfig(this.buildRolePayload(role))
        await this.loadConfig()
        this.showFeedback(`${this.roleLabel(role)} 配置已保存`)
      } catch (error) {
        console.error('保存 LLM 配置失败:', error)
        this.showFeedback(this.errorMessage(error, '保存失败'), 'error')
      } finally {
        this.savingRole = ''
      }
    },
    async testRole(role) {
      this.testingRole = role
      try {
        const response = await worldApi.testLlmConfig(this.buildRolePayload(role))
        const modelName = response?.test_result?.model || this.forms[role].model_name
        this.showFeedback(`${this.roleLabel(role)} 连接测试成功${modelName ? `：${modelName}` : ''}`)
      } catch (error) {
        console.error('测试 LLM 连接失败:', error)
        this.showFeedback(this.errorMessage(error, '连接测试失败'), 'error')
      } finally {
        this.testingRole = ''
      }
    },
    async saveAdvanced() {
      this.savingRole = 'advanced'
      try {
        await worldApi.saveLlmSettings(this.advanced)
        await this.loadConfig()
        this.showFeedback('高级参数已保存')
      } catch (error) {
        console.error('保存高级参数失败:', error)
        this.showFeedback(this.errorMessage(error, '保存失败'), 'error')
      } finally {
        this.savingRole = ''
      }
    },
  },
}
</script>

<style scoped>
.llm-config-page {
  min-height: calc(100vh - 56px);
  padding: var(--spacing-xl);
  max-width: 1320px;
  margin: 0 auto;
  color: var(--wf-text-primary);
}
.config-hero {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-lg);
  align-items: flex-start;
  margin-bottom: var(--spacing-xl);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--wf-border);
}
.back-link {
  padding: 0;
  margin-bottom: var(--spacing-md);
  background: transparent;
  color: var(--wf-text-muted);
}
.config-hero h1 { margin: 0 0 var(--spacing-sm); font-size: 2rem; }
.config-hero p { color: var(--wf-text-secondary); margin: 0; }
.hero-actions { display: flex; align-items: center; gap: var(--spacing-md); }
.feedback { padding: var(--spacing-sm) var(--spacing-md); border-radius: var(--radius-full); font-size: 13px; border: 1px solid var(--wf-border); color: var(--wf-text-secondary); }
.feedback.success { color: var(--wf-success); background: rgba(0, 212, 170, 0.08); }
.feedback.error { color: var(--wf-danger); background: rgba(255, 71, 87, 0.08); }
.toast-stack { position: fixed; top: 76px; right: var(--spacing-xl); z-index: 1000; display: grid; gap: var(--spacing-sm); width: min(420px, calc(100vw - 32px)); pointer-events: none; }
.toast-card { pointer-events: auto; display: grid; grid-template-columns: auto 1fr auto; align-items: center; gap: var(--spacing-sm); padding: var(--spacing-md); border-radius: var(--radius-lg); border: 1px solid var(--wf-border); background: rgba(18, 24, 38, 0.96); color: var(--wf-text-primary); box-shadow: var(--shadow-lg); backdrop-filter: blur(12px); }
.toast-card.success { border-color: rgba(0, 212, 170, 0.35); }
.toast-card.error { border-color: rgba(255, 71, 87, 0.4); }
.toast-icon { width: 22px; height: 22px; border-radius: 999px; display: inline-grid; place-items: center; font-weight: 700; font-size: 13px; }
.toast-card.success .toast-icon { color: var(--wf-text-on-accent); background: var(--wf-success); }
.toast-card.error .toast-icon { color: #fff; background: var(--wf-danger); }
.toast-card button { padding: 0; width: 24px; height: 24px; border: 0; background: transparent; color: var(--wf-text-muted); font-size: 18px; }
.toast-card button:hover { color: var(--wf-text-primary); }
.toast-enter-active, .toast-leave-active { transition: all .2s ease; }
.toast-enter-from, .toast-leave-to { opacity: 0; transform: translateX(18px); }
.overview-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: var(--spacing-md); margin-bottom: var(--spacing-xl); }
.overview-card { text-align: left; padding: var(--spacing-lg); border: 1px solid var(--wf-border); border-radius: var(--radius-xl); background: var(--wf-bg-card); color: var(--wf-text-primary); display: grid; gap: 6px; min-height: 170px; }
.overview-card:hover, .overview-card.active { border-color: var(--wf-accent); background: var(--wf-bg-hover); box-shadow: var(--shadow-glow); }
.role-kicker, .panel-kicker { color: var(--wf-accent); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
.role-desc { color: var(--wf-text-secondary); font-size: 13px; min-height: 40px; }
.role-status { color: var(--wf-warning); font-size: 12px; }
.role-status.ready { color: var(--wf-success); }
.role-model { color: var(--wf-text-muted); font-family: var(--font-mono); font-size: 12px; overflow: hidden; text-overflow: ellipsis; }
.config-layout { display: grid; grid-template-columns: 240px minmax(0, 1fr); gap: var(--spacing-lg); align-items: start; }
.config-nav { position: sticky; top: 72px; display: grid; gap: var(--spacing-sm); }
.config-nav button { text-align: left; display: grid; gap: 2px; background: transparent; border: 1px solid var(--wf-border); color: var(--wf-text-secondary); border-radius: var(--radius-md); padding: var(--spacing-md); }
.config-nav button.active { border-color: var(--wf-accent); color: var(--wf-accent); background: var(--wf-accent-muted); }
.config-nav small { color: var(--wf-text-muted); }
.config-panel { border: 1px solid var(--wf-border); border-radius: var(--radius-xl); background: var(--wf-bg-card); padding: var(--spacing-xl); }
.panel-header { display: flex; justify-content: space-between; gap: var(--spacing-lg); border-bottom: 1px solid var(--wf-border); padding-bottom: var(--spacing-lg); margin-bottom: var(--spacing-lg); }
.panel-header h2 { margin: 4px 0 var(--spacing-sm); }
.panel-header p { color: var(--wf-text-secondary); margin: 0; }
.masked-key { color: var(--wf-text-muted); font-family: var(--font-mono); font-size: 12px; white-space: nowrap; }
.btn-secondary { background: transparent; color: var(--wf-accent); border: 1px solid var(--wf-border-light); }
.btn-secondary:hover { border-color: var(--wf-accent); background: var(--wf-accent-muted); }
.form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--spacing-lg); }
.form-field { display: grid; gap: var(--spacing-sm); color: var(--wf-text-secondary); }
.form-field.full { grid-column: 1 / -1; }
.form-field input, .form-field select { width: 100%; }
.model-row { display: flex; gap: var(--spacing-sm); }
.model-row input { flex: 1; }
.model-row button { white-space: nowrap; }
.model-list { display: flex; flex-wrap: wrap; gap: var(--spacing-sm); margin-top: var(--spacing-lg); }
.model-list button { border: 1px solid var(--wf-border-light); background: var(--wf-bg-hover); color: var(--wf-text-secondary); border-radius: var(--radius-full); padding: 6px 10px; font-family: var(--font-mono); font-size: 12px; }
.model-list button:hover { border-color: var(--wf-accent); color: var(--wf-accent); }
.hint-card { margin-top: var(--spacing-lg); padding: var(--spacing-md); border-radius: var(--radius-md); background: var(--wf-bg-hover); border: 1px solid var(--wf-border); color: var(--wf-text-secondary); }
.panel-actions { margin-top: var(--spacing-xl); display: flex; justify-content: flex-end; gap: var(--spacing-md); }
.btn-primary { background: var(--wf-accent); color: var(--wf-text-on-accent); border: 1px solid var(--wf-accent); }
@media (max-width: 980px) {
  .overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .config-layout { grid-template-columns: 1fr; }
  .config-nav { position: static; grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .overview-grid, .form-grid, .config-nav { grid-template-columns: 1fr; }
  .config-hero, .panel-header { flex-direction: column; }
  .toast-stack { right: 16px; top: 64px; }
}
</style>
