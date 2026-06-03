<template>
  <div class="template-detail-page">
    <header class="template-detail-hero">
      <div>
        <router-link class="back-link" to="/world-builder">返回世界构建</router-link>
        <p class="eyebrow">世界模板详情</p>
        <h1>{{ templateData?.name || '世界模板' }}</h1>
        <p class="hero-description">{{ templateData?.description || '查看模板定义的结构、规则说明和默认数据。' }}</p>
      </div>
      <span class="template-id-chip">{{ templateData?.id || templateId }}</span>
    </header>

    <div v-if="loading" class="state-card">正在加载模板详情...</div>
    <div v-else-if="error" class="state-card error">{{ error }}</div>

    <template v-else-if="templateData">
      <section class="detail-card section-card">
        <div class="card-head">
          <h2>基础定义</h2>
        </div>
        <dl class="meta-list">
          <div>
            <dt>模板 ID</dt>
            <dd>{{ templateData.id }}</dd>
          </div>
          <div>
            <dt>模板名称</dt>
            <dd>{{ templateData.name }}</dd>
          </div>
          <div>
            <dt>冲突提示</dt>
            <dd>{{ templateData.conflict_warning || '无' }}</dd>
          </div>
        </dl>
      </section>

      <section class="detail-card section-card">
        <div class="card-head">
          <h2>结构栏目</h2>
          <span>{{ detailSections.length }} 项</span>
        </div>
        <div v-if="detailSections.length" class="structure-list">
          <article v-for="section in detailSections" :key="section.id || section.name" class="structure-item">
            <div>
              <h3>{{ section.name || section.id }}</h3>
              <p>{{ section.description || '无说明' }}</p>
            </div>
            <code>{{ section.target || '无目标路径' }}</code>
          </article>
        </div>
        <p v-else class="empty-text">未定义结构栏目。</p>
      </section>

      <section class="detail-card section-card">
        <div class="card-head">
          <h2>设定集合</h2>
          <span>{{ settingCollections.length }} 项</span>
        </div>
        <div v-if="settingCollections.length" class="structure-list">
          <article v-for="collection in settingCollections" :key="collection.id || collection.name" class="structure-item">
            <div>
              <h3>{{ collection.name || collection.id }}</h3>
              <p>{{ collection.description || '无说明' }}</p>
              <div class="tag-row compact">
                <span v-if="collection.category" class="pill muted">{{ collection.category }}</span>
                <span v-for="route in collection.routes || []" :key="route" class="pill muted">{{ route }}</span>
              </div>
            </div>
            <code>{{ collection.id || '无集合 ID' }}</code>
          </article>
        </div>
        <p v-else class="empty-text">通用模板未启用额外设定集合。</p>
      </section>

      <section class="detail-grid">
        <article class="detail-card">
          <div class="card-head">
            <h2>提取重点</h2>
          </div>
          <ul v-if="focusPoints.length" class="text-list">
            <li v-for="point in focusPoints" :key="point">{{ point }}</li>
          </ul>
          <p v-else class="empty-text">未定义额外提取重点。</p>
        </article>

        <article class="detail-card">
          <div class="card-head">
            <h2>世界信息规则</h2>
          </div>
          <ul v-if="worldInfoGuide.length" class="text-list">
            <li v-for="item in worldInfoGuide" :key="item">{{ item }}</li>
          </ul>
          <p v-else class="empty-text">未定义世界信息规则。</p>
        </article>

        <article class="detail-card wide">
          <div class="card-head">
            <h2>设定数据规则</h2>
          </div>
          <ul v-if="settingsGuide.length" class="text-list">
            <li v-for="item in settingsGuide" :key="item">{{ item }}</li>
          </ul>
          <p v-else class="empty-text">未定义设定数据规则。</p>
        </article>
      </section>

      <section class="detail-card section-card">
        <div class="card-head">
          <h2>默认带有的数据</h2>
          <span>新世界初始数据结构</span>
        </div>
        <div class="default-data-grid">
          <article v-for="item in defaultDataSummary" :key="item.key" class="default-data-item">
            <span>{{ item.label }}</span>
            <strong>{{ item.summary }}</strong>
          </article>
        </div>
        <pre class="json-block">{{ formattedDefaultData }}</pre>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { worldApi } from '../api/world'

const props = defineProps({
  templateId: {
    type: String,
    default: 'generic',
  },
})

const DEFAULT_TEMPLATE_ID = 'generic'
const DND_TEMPLATE_ID = 'dnd-campaign'

const buildDefaultData = () => ({
  world_info: {
    name: '',
    description: '',
    era: '',
    anchor_time: '',
    writing_style: '',
    reference_text: '',
  },
  entities: [],
  events: [],
  settings: {
    items: [],
    mapData: {
      regionRelations: '',
      countryRelations: '',
      importantLocations: '',
      structuredMaps: [],
    },
    calendars: [],
  },
})

const buildDndTemplate = (template = {}) => ({
  id: template.id || DND_TEMPLATE_ID,
  name: template.name || 'DND 跑团世界模板',
  description: template.description || '面向 DND 跑团的世界模板，覆盖战役前提、桌面规则、方格地图、势力、NPC、反派威胁、冒险遭遇、宝物和玩家角色接入。',
  conflict_warning: template.conflict_warning || '该模板会把资料优先拆分为战役运营、规则资源和跑团地图字段。',
  focus_tags: template.focus_tags || ['战役总览', '桌面规则', '方格地图', '冒险遭遇', '玩家接入'],
  focus_points: template.focus_points || ['优先提取战役前提、起始等级、主要威胁、玩家角色钩子和 DND 方格战斗地图。'],
  detail_sections: template.detail_sections || [
    { id: 'campaign_overview', name: '战役总览', target: 'world_info.dnd_campaign', description: '战役前提、等级范围、主冲突和玩家目标。' },
    { id: 'table_rules', name: '桌面规则', target: 'settings.items[collectionId=dnd_table_rules]', description: '版本、资料书、升级、休息、死亡、复活、暗骰和安全工具。' },
    { id: 'maps', name: '地图与地点', target: 'settings.mapData.structuredMaps', description: '世界地图、区域地图、地牢地图和 DND 方格战斗地图。' },
    { id: 'encounters', name: '遭遇与怪物', target: 'settings.items[collectionId=dnd_encounters]', description: '战斗、陷阱、环境危险、怪物战术和胜败条件。' },
  ],
  setting_collections: template.setting_collections || [],
  world_info_guide: template.world_info_guide || [],
  settings_guide: template.settings_guide || [],
  default_data: template.default_data || buildDefaultData(),
})

const buildTemplate = (template = {}) => (template.id === DND_TEMPLATE_ID ? buildDndTemplate(template) : buildGenericTemplate(template))

const buildGenericTemplate = (template = {}) => ({
  id: template.id || DEFAULT_TEMPLATE_ID,
  name: template.name || '通用模板',
  description: template.description || '默认解析结构，按核心简介、关键事实、关系网络、阶段/演变和设定补充说明组织世界观内容。',
  conflict_warning: template.conflict_warning || '不同模板的结构栏目可能不一致。',
  focus_tags: template.focus_tags || ['核心简介', '关键事实', '关系网络', '阶段/演变', '设定补充说明'],
  focus_points: template.focus_points || [],
  detail_sections: template.detail_sections || [
    {
      id: 'core_intro',
      name: '核心简介',
      target: 'entities[].attributes.简介 / settings.items[].structuredDetail.intro',
      description: '对象的高密度概览，说明本质、身份、定位、用途或叙事作用。',
    },
    {
      id: 'key_facts',
      name: '关键事实',
      target: 'entities[].attributes / settings.items[].structuredDetail.facts',
      description: '可被反复引用的稳定事实，使用短字段承载身份、归属、能力、资源、规则边界等信息。',
    },
    {
      id: 'relationships',
      name: '关系网络',
      target: 'entities[].relationships / settings.items[].structuredDetail.relationships',
      description: '对象与人物、组织、地点、事件、规则之间的关联，保留关系类型、说明、时期和来源事件。',
    },
    {
      id: 'stages',
      name: '阶段/演变',
      target: 'entities[].stages / settings.items[].structuredDetail.stages',
      description: '对象在不同时间、版本、势力阶段或剧情阶段中的变化。',
    },
    {
      id: 'supplement',
      name: '设定补充说明',
      target: 'entities[].attributes.设定补充说明 / settings.items[].detailContent',
      description: '不适合放入短字段但仍有价值的背景、限制、解释、争议和人工补充说明。',
    },
  ],
  setting_collections: template.setting_collections || [],
  world_info_guide: template.world_info_guide || [
    '优先提取作品/世界名称、时代背景、主线时间锚点与整体世界描述。',
    '若文本同时包含多个时期，anchor_time 应优先落在主线剧情最常活动的时期。',
  ],
  settings_guide: template.settings_guide || [
    'settings.items 仅沉淀文本明确支撑的长期设定。',
    'mapData 聚焦区域关系、国家关系、重要地点；calendars 聚焦纪年或历法系统。',
  ],
  default_data: template.default_data || buildDefaultData(),
})

const loading = ref(false)
const error = ref('')
const templateData = ref(null)

const focusPoints = computed(() => templateData.value?.focus_points || [])
const detailSections = computed(() => templateData.value?.detail_sections || [])
const settingCollections = computed(() => templateData.value?.setting_collections || [])
const worldInfoGuide = computed(() => templateData.value?.world_info_guide || [])
const settingsGuide = computed(() => templateData.value?.settings_guide || [])
const defaultData = computed(() => templateData.value?.default_data || {})
const formattedDefaultData = computed(() => JSON.stringify(defaultData.value, null, 2))

const defaultDataSummary = computed(() => {
  const data = defaultData.value || {}
  const settings = data.settings && typeof data.settings === 'object' ? data.settings : {}
  const mapData = settings.mapData && typeof settings.mapData === 'object' ? settings.mapData : {}
  return [
    { key: 'world_info', label: '世界基础信息', summary: `${Object.keys(data.world_info || {}).length} 个字段` },
    { key: 'entities', label: '实体', summary: `${Array.isArray(data.entities) ? data.entities.length : 0} 条默认实体` },
    { key: 'events', label: '事件', summary: `${Array.isArray(data.events) ? data.events.length : 0} 条默认事件` },
    { key: 'settings', label: '设定条目', summary: `${Array.isArray(settings.items) ? settings.items.length : 0} 条默认设定` },
    { key: 'mapData', label: '地图数据', summary: `${Object.keys(mapData).length} 个字段` },
    { key: 'calendars', label: '历法', summary: `${Array.isArray(settings.calendars) ? settings.calendars.length : 0} 条默认历法` },
  ]
})

async function loadTemplate() {
  loading.value = true
  error.value = ''
  const targetTemplateId = props.templateId || DEFAULT_TEMPLATE_ID
  try {
    const response = await worldApi.getWorldTemplate(targetTemplateId)
    templateData.value = buildTemplate(response.template || {})
  } catch (err) {
    try {
      const response = await worldApi.listWorldTemplates()
      const templates = Array.isArray(response.templates) ? response.templates : []
      const matched = templates.find(template => template?.id === targetTemplateId) || templates.find(template => template?.id === DEFAULT_TEMPLATE_ID)
      templateData.value = buildTemplate(matched || { id: targetTemplateId })
    } catch (_) {
      templateData.value = buildTemplate({ id: targetTemplateId })
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadTemplate)
watch(() => props.templateId, loadTemplate)
</script>

<style scoped>
.template-detail-page {
  max-width: 1120px;
  margin: 0 auto;
  padding: var(--spacing-2xl) var(--spacing-lg) 80px;
}

.template-detail-hero {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-xl);
  align-items: flex-start;
  margin-bottom: var(--spacing-xl);
  padding-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--wf-border);
}

.back-link {
  display: inline-flex;
  align-items: center;
  margin-bottom: var(--spacing-sm);
  padding: 0;
  color: var(--wf-accent);
  background: transparent;
  border: 0;
  text-decoration: none;
  font-size: 0.92rem;
  font-weight: 600;
}

.back-link:hover {
  color: var(--wf-accent-hover);
}

.eyebrow {
  margin: 0 0 var(--spacing-xs);
  color: var(--wf-text-muted);
  font-family: var(--font-mono);
  font-size: 12px;
}

.template-detail-hero h1 {
  margin: var(--spacing-sm) 0;
  font-size: 2rem;
}

.hero-description {
  max-width: 760px;
  margin: 0;
  color: var(--wf-text-secondary);
  line-height: 1.7;
}

.template-id-chip {
  flex-shrink: 0;
  padding: 4px 10px;
  border-radius: var(--radius-full);
  border: 1px solid var(--wf-border-light);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-accent);
  font-family: var(--font-mono);
  font-size: 12px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.detail-card {
  padding: var(--spacing-lg);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-xl);
  background: var(--wf-bg-card);
  box-shadow: var(--shadow-sm);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  transition: all var(--transition-normal);
}

.detail-card:hover {
  border-color: var(--wf-border-light);
  background: rgba(255, 255, 255, 0.05);
  box-shadow: var(--shadow-md);
}

.detail-card.wide {
  grid-column: 1 / -1;
}

.section-card {
  margin-bottom: var(--spacing-lg);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.card-head h2 {
  margin: 0;
  color: var(--wf-text-primary);
  font-size: 1.15rem;
}

.card-head span {
  color: var(--wf-text-muted);
  font-family: var(--font-mono);
  font-size: 12px;
}

.meta-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: var(--spacing-md);
  margin: 0;
}

.meta-list div {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.meta-list dt {
  color: var(--wf-text-muted);
  font-size: 12px;
}

.meta-list dd {
  margin: 0;
  color: var(--wf-text-primary);
  line-height: 1.6;
  word-break: break-word;
}

.tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.tag-row.compact {
  margin-top: var(--spacing-sm);
}

.pill {
  display: inline-flex;
  align-items: center;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--radius-full);
  border: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.05);
  color: var(--wf-text-secondary);
  font-size: 12px;
  font-weight: 500;
}

.pill.muted {
  color: var(--wf-text-muted);
}

.structure-list {
  display: grid;
  gap: var(--spacing-md);
}

.structure-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(240px, 0.72fr);
  gap: var(--spacing-lg);
  padding: var(--spacing-md);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.03);
}

.structure-item h3 {
  margin: 0 0 6px;
  color: var(--wf-text-primary);
  font-size: 1rem;
}

.structure-item p {
  margin: 0;
  color: var(--wf-text-secondary);
  line-height: 1.65;
}

.structure-item code {
  align-self: start;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--wf-border);
  background: var(--wf-bg-input);
  color: var(--wf-text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
}

.text-list {
  margin: 0;
  padding-left: 1.1rem;
  color: var(--wf-text-secondary);
  line-height: 1.8;
}

.text-list li::marker {
  color: var(--wf-accent);
}

.empty-text {
  margin: 0;
  color: var(--wf-text-muted);
}

.default-data-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.default-data-item {
  display: grid;
  gap: 4px;
  padding: var(--spacing-md);
  border-radius: var(--radius-lg);
  border: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.04);
}

.default-data-item span {
  color: var(--wf-text-muted);
  font-size: 12px;
}

.default-data-item strong {
  color: var(--wf-text-primary);
  font-size: 0.95rem;
}

.json-block {
  max-height: 520px;
  overflow: auto;
  margin: 0;
  padding: var(--spacing-lg);
  border-radius: var(--radius-lg);
  border: 1px solid var(--wf-border);
  background: var(--wf-bg-input);
  color: var(--wf-text-secondary);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.65;
}

.state-card {
  padding: var(--spacing-xl);
  border-radius: var(--radius-xl);
  border: 1px solid var(--wf-border);
  background: var(--wf-bg-card);
  color: var(--wf-text-secondary);
}

.state-card.error {
  border-color: rgba(255, 71, 87, 0.28);
  background: rgba(255, 71, 87, 0.12);
  color: var(--wf-danger);
}

@media (max-width: 860px) {
  .template-detail-hero,
  .structure-item {
    display: grid;
    grid-template-columns: 1fr;
  }

  .detail-grid,
  .meta-list {
    grid-template-columns: 1fr;
  }
}
</style>
