<template>
  <aside class="cell-panel">
    <div v-if="!cell" class="empty-panel">选择一个区域单元后，可在这里编辑地形、势力、资源、颜色和区域绑定。</div>
    <template v-else>
      <div class="panel-header">
        <div>
          <h3>{{ draft.name || `区域 ${cell.q},${cell.r}` }}</h3>
          <p>{{ cell.id }}</p>
        </div>
        <span class="coord">行{{ cell.r }} / 列{{ cell.q }}</span>
      </div>

      <label>区域名称</label>
      <input v-model="draft.name" class="field" placeholder="例如：北境山口" />

      <label>简短描述</label>
      <textarea v-model="draft.description" class="field" rows="3" placeholder="从故事视角描述这片区域"></textarea>

      <div class="two-col">
        <div>
          <label>地形</label>
          <select v-model="draft.terrain" class="field">
            <option v-for="item in terrainOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
        <div>
          <label>状态</label>
          <select v-model="draft.status" class="field">
            <option v-for="item in statusOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>
      </div>

      <label>所属势力</label>
      <input v-model="draft.faction" class="field" placeholder="例如：北方王国" />

      <label>资源标签（逗号分隔）</label>
      <input v-model="resourceText" class="field" placeholder="铁矿, 水源, 魔法晶脉" />

      <label>重要地点（逗号分隔）</label>
      <input v-model="locationText" class="field" placeholder="城市、山脉、港口等" />

      <label>特殊颜色</label>
      <div class="color-row">
        <input v-model="draft.color" class="field color-text" placeholder="例如：#ffffaf 或 rgba(...)" />
        <input v-model="draft.color" type="color" class="color-picker" />
        <button class="clear-color" type="button" @click="draft.color = ''">清除</button>
      </div>

      <label>绑定区域地图</label>
      <div class="bind-row">
        <select v-model="draft.linked_map_id" class="field">
          <option value="">不绑定</option>
          <option v-for="map in linkableMaps" :key="map.id" :value="map.id">{{ map.name }}</option>
        </select>
        <button class="jump-btn" type="button" :disabled="!draft.linked_map_id" @click="$emit('jump-map', draft.linked_map_id)">跳转</button>
      </div>

      <label>备注</label>
      <textarea v-model="draft.notes" class="field" rows="2"></textarea>

      <p class="auto-save-hint">修改会立即应用到地图；点击页面顶部“保存世界观”后持久化。</p>
    </template>
  </aside>
</template>

<script>
const terrainOptions = [
  ['unset', '未设置'], ['plain', '平原'], ['forest', '森林'], ['mountain', '山地'], ['desert', '沙漠'],
  ['snow', '雪原'], ['ocean', '海洋'], ['lake', '湖泊'], ['river', '河流'], ['swamp', '沼泽'],
  ['city', '城市'], ['ruins', '废墟'], ['special', '特殊区域'],
].map(([value, label]) => ({ value, label }))

const statusOptions = [
  ['normal', '正常'], ['war', '战争中'], ['occupied', '被占领'], ['disaster', '灾害中'],
  ['blocked', '封锁中'], ['abandoned', '废弃'], ['unknown', '未知'], ['special', '特殊状态'],
].map(([value, label]) => ({ value, label }))

export default {
  name: 'MapCellPanel',
  props: {
    cell: { type: Object, default: null },
    maps: { type: Array, default: () => [] },
    currentMapId: { type: String, default: '' },
    saving: { type: Boolean, default: false },
  },
  emits: ['save', 'jump-map'],
  data() {
    return {
      terrainOptions,
      statusOptions,
      draft: {},
      resourceText: '',
      locationText: '',
      isHydratingDraft: false,
    }
  },
  computed: {
    linkableMaps() {
      return (this.maps || []).filter(map => map.id !== this.currentMapId)
    },
  },
  watch: {
    cell: {
      immediate: true,
      deep: true,
      handler(cell) {
        this.isHydratingDraft = true
        this.draft = cell ? JSON.parse(JSON.stringify(cell)) : {}
        this.resourceText = (this.draft.resources || []).join(', ')
        this.locationText = (this.draft.locations || []).join(', ')
        this.$nextTick(() => { this.isHydratingDraft = false })
      },
    },
    draft: {
      deep: true,
      handler() {
        if (!this.isHydratingDraft) this.save()
      },
    },
    resourceText() {
      if (!this.isHydratingDraft) this.save()
    },
    locationText() {
      if (!this.isHydratingDraft) this.save()
    },
  },
  methods: {
    splitText(text) {
      return String(text || '').split(/[,，]/).map(item => item.trim()).filter(Boolean)
    },
    save() {
      this.$emit('save', {
        ...this.draft,
        resources: this.splitText(this.resourceText),
        locations: this.splitText(this.locationText),
      })
    },
  },
}
</script>

<style scoped>
.cell-panel { border: 1px solid var(--wf-border); border-radius: var(--radius-lg); background: var(--wf-bg-card); color: var(--wf-text-primary); padding: var(--spacing-lg); min-width: 320px; max-height: 720px; overflow: auto; }
.empty-panel { color: var(--wf-text-secondary); line-height: 1.7; }
.panel-header { display: flex; justify-content: space-between; gap: var(--spacing-md); margin-bottom: var(--spacing-md); }
.panel-header h3 { margin: 0; font-size: 18px; color: var(--wf-text-primary); }
.panel-header p { margin: 4px 0 0; color: var(--wf-text-muted); font-size: 12px; }
.coord { background: var(--wf-accent-muted); color: var(--wf-accent); border: 1px solid rgba(255,255,175,0.15); padding: 5px 8px; border-radius: var(--radius-full); height: fit-content; font-size: 12px; }
label { display: block; margin: 10px 0 6px; color: var(--wf-text-secondary); font-size: 13px; font-weight: 600; }
.field { width: 100%; box-sizing: border-box; border: 1px solid var(--wf-border); border-radius: var(--radius-md); padding: var(--spacing-sm) var(--spacing-md); font-size: 14px; background: var(--wf-bg-input); color: var(--wf-text-primary); outline: none; }
.field::placeholder { color: var(--wf-text-muted); }
.field:focus { border-color: var(--wf-accent); box-shadow: 0 0 0 3px var(--wf-accent-muted); }
.field option { background: var(--wf-dropdown-panel); color: var(--wf-text-primary); }
.field option:checked,
.field option:hover,
.field option:focus { background: var(--wf-dropdown-option-active); }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: var(--spacing-sm); }
.color-row, .bind-row { display: flex; gap: var(--spacing-sm); align-items: center; }
.color-text { flex: 1; }
.color-picker { width: 44px; height: 38px; padding: 3px; }
.clear-color, .jump-btn { border: 1px solid var(--wf-border-light); border-radius: var(--radius-md); background: transparent; color: var(--wf-accent); padding: var(--spacing-sm) var(--spacing-md); cursor: pointer; white-space: nowrap; }
.jump-btn:disabled { opacity: .4; cursor: not-allowed; }
.bind-row .field { flex: 1; }
.auto-save-hint { margin-top: var(--spacing-md); color: var(--wf-text-muted); font-size: 12px; line-height: 1.5; }
</style>
