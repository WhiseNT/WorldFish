<template>
  <section class="batch-editor">
    <div class="batch-header">
      <strong>批量编辑</strong>
      <span>已选 {{ selectedCount }} 个区域</span>
    </div>
    <div class="batch-grid">
      <select v-model="updates.terrain" class="field">
        <option value="">不修改地形</option>
        <option v-for="item in terrains" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <select v-model="updates.status" class="field">
        <option value="">不修改状态</option>
        <option v-for="item in statuses" :key="item.value" :value="item.value">{{ item.label }}</option>
      </select>
      <input v-model="updates.faction" class="field" placeholder="设置所属势力（留空不改）" />
      <input v-model="resourceText" class="field" placeholder="添加资源：铁矿, 水源" />
      <input v-model="tagText" class="field" placeholder="添加标签：边境, 战略区" />
      <input v-model="updates.color" class="field" placeholder="特殊颜色：#ffffaf" />
      <div class="clear-row">
        <label><input type="checkbox" v-model="updates.clear_faction" /> 清除势力</label>
        <label><input type="checkbox" v-model="updates.clear_resources" /> 清除资源</label>
        <label><input type="checkbox" v-model="updates.clear_tags" /> 清除标签</label>
      </div>
    </div>
    <button class="apply-btn" :disabled="selectedCount === 0 || saving" @click="apply">
      {{ saving ? '应用中...' : '应用到选中区域' }}
    </button>
  </section>
</template>

<script>
export default {
  name: 'MapBatchEditor',
  props: {
    selectedCount: { type: Number, default: 0 },
    saving: { type: Boolean, default: false },
  },
  emits: ['apply'],
  data() {
    return {
      resourceText: '',
      tagText: '',
      updates: {
        terrain: '',
        status: '',
        faction: '',
        clear_faction: false,
        clear_resources: false,
        clear_tags: false,
        color: '',
      },
      terrains: [
        ['unset', '未设置'], ['plain', '平原'], ['forest', '森林'], ['mountain', '山地'], ['desert', '沙漠'], ['snow', '雪原'],
        ['ocean', '海洋'], ['lake', '湖泊'], ['river', '河流'], ['swamp', '沼泽'], ['city', '城市'], ['ruins', '废墟'], ['special', '特殊区域'],
      ].map(([value, label]) => ({ value, label })),
      statuses: [
        ['normal', '正常'], ['war', '战争中'], ['occupied', '被占领'], ['disaster', '灾害中'], ['blocked', '封锁中'], ['abandoned', '废弃'], ['unknown', '未知'], ['special', '特殊状态'],
      ].map(([value, label]) => ({ value, label })),
    }
  },
  methods: {
    splitText(text) {
      return String(text || '').split(/[,，]/).map(item => item.trim()).filter(Boolean)
    },
    apply() {
      const updates = {}
      Object.entries(this.updates).forEach(([key, value]) => {
        if (typeof value === 'boolean' ? value : String(value || '').trim()) updates[key] = value
      })
      const resources = this.splitText(this.resourceText)
      const tags = this.splitText(this.tagText)
      if (resources.length) updates.resources = resources
      if (tags.length) updates.tags = tags
      this.$emit('apply', updates)
    },
  },
}
</script>

<style scoped>
.batch-editor { border: 1px solid var(--wf-border); border-radius: var(--radius-lg); background: var(--wf-bg-card); color: var(--wf-text-primary); padding: var(--spacing-md); }
.batch-header { display: flex; justify-content: space-between; color: var(--wf-text-primary); margin-bottom: var(--spacing-sm); }
.batch-header span { color: var(--wf-text-muted); font-size: 13px; }
.batch-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: var(--spacing-sm); }
.field { border: 1px solid var(--wf-border); border-radius: var(--radius-md); padding: var(--spacing-sm) var(--spacing-md); background: var(--wf-bg-input); color: var(--wf-text-primary); outline: none; }
.field::placeholder { color: var(--wf-text-muted); }
.field:focus { border-color: var(--wf-accent); box-shadow: 0 0 0 3px var(--wf-accent-muted); }
.field option { background: var(--wf-dropdown-panel); color: var(--wf-text-primary); }
.field option:checked,
.field option:hover,
.field option:focus { background: var(--wf-dropdown-option-active); }
.clear-row { grid-column: 1 / -1; display: flex; gap: var(--spacing-md); flex-wrap: wrap; color: var(--wf-text-secondary); font-size: 13px; }
.apply-btn { margin-top: var(--spacing-sm); border: 1px solid var(--wf-accent); border-radius: var(--radius-md); padding: var(--spacing-sm) var(--spacing-md); background: var(--wf-accent); color: var(--wf-text-on-accent); font-weight: 600; cursor: pointer; }
.apply-btn:disabled { opacity: .4; cursor: not-allowed; }
</style>
