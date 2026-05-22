<template>
  <div class="world-builder">
    <!-- 顶部导航栏 -->
    <header class="world-builder-header">
      <div class="header-content">
        <h1 class="world-builder-title">世界观构建</h1>
        <p class="world-builder-subtitle">创建和管理你的世界观设定，构建完整的虚拟世界</p>
      </div>

      <div class="builder-header-actions">
        <span v-if="saveStatus" class="save-status">{{ saveStatus }}</span>
        <span v-if="worldId" class="world-id-badge">{{ worldId }}</span>
        <span v-if="linkedProjectId" class="project-id-badge">{{ linkedProjectId }}</span>
        <button
          v-if="worldId"
          @click="deleteWorld()"
          :disabled="isSaving || isDeleting"
          class="btn btn-danger"
        >
          {{ isDeleting ? '删除中...' : '删除世界观' }}
        </button>
        <button
          @click="launchProjectFromWorld()"
          :disabled="isSaving || isProjectLaunching"
          class="btn btn-secondary"
        >
          {{ projectActionLabel }}
        </button>
        <button
          @click="saveWorld()"
          :disabled="isSaving || isProjectLaunching"
          class="btn btn-primary"
        >
          {{ isSaving ? '保存中...' : (worldId ? '保存世界观' : '创建世界观') }}
        </button>
      </div>
    </header>
    
    <!-- 标签页导航 -->
    <div class="tabs-container">
      <div class="tabs">
        <button 
          :class="{ active: activeTab === 'basic' }"
          @click="activeTab = 'basic'"
          class="tab-btn"
        >
          <span class="tab-icon">📋</span>
          <span class="tab-label">基本信息</span>
        </button>
        <button 
          :class="{ active: activeTab === 'entities' }"
          @click="activeTab = 'entities'"
          class="tab-btn"
        >
          <span class="tab-icon">🧬</span>
          <span class="tab-label">核心实体与事件</span>
        </button>
        <button 
          :class="{ active: activeTab === 'settings' }"
          @click="activeTab = 'settings'"
          class="tab-btn"
        >
          <span class="tab-icon">⚙️</span>
          <span class="tab-label">设定管理</span>
        </button>
        <button 
          :class="{ active: activeTab === 'evolutions' }"
          @click="activeTab = 'evolutions'"
          class="tab-btn"
        >
          <span class="tab-icon">🌀</span>
          <span class="tab-label">推演记录</span>
        </button>
        <button 
          :class="{ active: activeTab === 'timeline' }"
          @click="activeTab = 'timeline'"
          class="tab-btn"
        >
          <span class="tab-icon">⏰</span>
          <span class="tab-label">时间线</span>
        </button>
        <button 
          :class="{ active: activeTab === 'map' }"
          @click="activeTab = 'map'"
          class="tab-btn"
        >
          <span class="tab-icon">🗺️</span>
          <span class="tab-label">地图</span>
        </button>
      </div>
    </div>

    <!-- 标签页内容 -->
    <div class="tab-content">
      <!-- 基本信息 -->
      <div v-if="activeTab === 'basic'" class="tab-pane basic-info">
        <div class="form-section">
          <div class="section-header">
            <h2 class="section-title">世界观基本信息</h2>
            <p class="section-description">定义你的世界观核心设定</p>
          </div>
          <div class="form-grid">
            <div class="form-group">
              <label class="form-label">世界观名称</label>
              <input 
                type="text" 
                v-model="world.name" 
                placeholder="输入世界观名称"
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label class="form-label">时代背景</label>
              <input 
                type="text" 
                v-model="world.era" 
                placeholder="例如：中世纪、未来、异世界等"
                class="form-input"
              >
            </div>
            <div class="form-group">
              <label class="form-label">锚定时间</label>
              <input 
                type="text" 
                v-model="world.anchor_time" 
                placeholder="故事发生的核心时间"
                class="form-input"
              >
            </div>
            <div class="form-group form-group-full">
              <label class="form-label">世界观描述</label>
              <textarea 
                v-model="world.description" 
                placeholder="描述这个世界观的基本设定..."
                rows="4"
                class="form-textarea"
              ></textarea>
            </div>
          </div>

          <!-- 文风设定 -->
          <div class="form-section" style="margin-top: 24px;">
            <div class="section-header">
              <h2 class="section-title">文风设定</h2>
              <p class="section-description">设定推演叙事的文风，AI生成内容时将模仿此风格</p>
            </div>
            <div class="form-grid">
              <div class="form-group form-group-full">
                <label class="form-label">文风描述</label>
                <input
                  type="text"
                  v-model="world.writing_style"
                  placeholder="例如：冷峻克制的史诗风格、幽默风趣的网文风格..."
                  class="form-input"
                >
              </div>
              <div class="form-group form-group-full">
                <label class="form-label">参考文本（节选原著片段，用于模仿文风）</label>
                <textarea
                  v-model="world.reference_text"
                  placeholder="粘贴原著中的典型段落，AI将模仿其写作风格..."
                  rows="5"
                  class="form-textarea"
                ></textarea>
              </div>
            </div>
          </div>
        </div>

        <!-- AI世界观提取 -->
        <div class="ai-extract-section">
          <div class="section-header">
            <h2 class="section-title">AI世界观提取</h2>
            <p class="section-description">粘贴世界观描述文本或上传文件，AI将自动提取关键信息</p>
          </div>
          <div class="extract-toolbar">
            <div class="llm-status-chip" :class="{ 'is-ready': hasLlmConfig, 'is-missing': !hasLlmConfig }">
              <span class="llm-status-dot"></span>
              <span>{{ llmStatusText }}</span>
              <span v-if="llmConfigStatus.api_key_masked" class="llm-status-meta">{{ llmConfigStatus.api_key_masked }}</span>
            </div>
            <button class="btn btn-secondary" @click="openLlmConfigDialog">
              配置 LLM
            </button>
          </div>

          <!-- 文件上传区域 -->
          <div class="form-group form-group-full">
            <label class="form-label">上传文件让 AI 解读（支持 PDF、Markdown、TXT）</label>
            <div
              class="file-drop-zone"
              :class="{ 'file-drag-over': isDragOver }"
              @dragover.prevent="isDragOver = true"
              @dragleave.prevent="isDragOver = false"
              @drop.prevent="handleFileDrop"
            >
              <input
                ref="fileInput"
                type="file"
                multiple
                accept=".pdf,.md,.markdown,.txt,.json"
                class="file-input-hidden"
                @change="handleFileSelect"
              />
              <div class="file-drop-content">
                <span class="file-drop-icon">📄</span>
                <span>拖拽文件到此处或</span>
                <button type="button" class="btn btn-secondary file-browse-btn" @click="$refs.fileInput.click()">
                  选择文件
                </button>
                <span class="file-drop-hint">支持 PDF、Markdown、TXT 格式</span>
              </div>
            </div>
            <!-- 已选文件列表 -->
            <div v-if="selectedFiles.length > 0" class="selected-files">
              <div v-for="(file, index) in selectedFiles" :key="index" class="selected-file-item">
                <span class="file-name">{{ file.name }}</span>
                <span class="file-size">({{ formatFileSize(file.size) }})</span>
                <button class="file-remove-btn" @click="removeFile(index)">×</button>
              </div>
            </div>
          </div>

          <!-- JSON 直接导入 -->
          <div class="json-import-row">
            <input
              ref="jsonFileInput"
              type="file"
              accept=".json"
              class="file-input-hidden"
              @change="handleJsonImport"
            />
            <button type="button" class="btn btn-secondary json-import-btn" @click="$refs.jsonFileInput.click()">
              导入 JSON 世界观文件
            </button>
            <span class="json-import-hint">直接导入 JSON 格式的世界观数据，无需 AI 解读</span>
          </div>

          <div class="form-group form-group-full">
            <label class="form-label">或直接输入世界观文本</label>
            <textarea
              v-model="extractText"
              placeholder="粘贴世界观描述文本，AI将自动提取关键信息..."
              rows="6"
              class="form-textarea"
            ></textarea>
          </div>
          <button
            @click="extractWorldInfo"
            :disabled="isExtracting || (!extractText && selectedFiles.length === 0)"
            class="btn btn-primary extract-btn"
          >
            {{ isExtracting ? '提取中...' : '提取世界观信息' }}
          </button>

          <!-- 提取进度条 -->
          <div v-if="isExtracting && extractProgress.message" class="extract-progress">
            <div class="progress-bar-container">
              <div class="progress-bar-fill" :style="{ width: extractProgress.progress + '%' }"></div>
            </div>
            <div class="progress-info">
              <span class="progress-stage">{{ extractProgress.message }}</span>
              <span class="progress-pct">{{ extractProgress.progress }}%</span>
            </div>
          </div>

          <p v-if="extractError" class="extract-error">{{ extractError }}</p>

          <!-- 提取结果预览 -->
          <div v-if="extractedData" class="extract-preview">
            <div class="preview-header">
              <h3 class="preview-title">提取结果预览</h3>
              <span v-if="extractedData.rag_indexed" class="rag-index-badge">
                已索引 {{ extractedData.rag_document_count || 0 }} 条至 RAG 知识库
              </span>
            </div>
            <div class="preview-content">
              <pre class="preview-code">{{ JSON.stringify(extractedData, null, 2) }}</pre>
            </div>
            <button @click="applyExtractedData" class="btn btn-secondary apply-btn">
              合并提取的数据
            </button>
            <p class="preview-note">会保留当前已编辑内容，仅补充新增信息，并尽量合并重复实体、事件和设定。</p>
          </div>
        </div>

        <div v-if="showLlmConfigDialog" class="dialog">
          <div class="dialog-content llm-config-dialog">
            <div class="dialog-header">
              <h2 class="dialog-title">配置 LLM 提取服务</h2>
              <button class="close-btn" @click="closeLlmConfigDialog">×</button>
            </div>
            <div class="dialog-body">
              <div class="form-group">
                <label class="form-label">API Key</label>
                <input
                  type="password"
                  v-model="llmConfig.apiKey"
                  :placeholder="llmConfigStatus.api_key_configured ? '留空则保持当前已保存的 API Key' : '输入可用的 LLM API Key'"
                  class="form-input"
                >
                <span v-if="llmConfigStatus.api_key_configured" class="form-hint">
                  当前已保存：{{ llmConfigStatus.api_key_masked }}
                </span>
              </div>
              <div class="form-group">
                <label class="form-label">Base URL</label>
                <input
                  type="text"
                  v-model="llmConfig.baseUrl"
                  placeholder="例如：https://dashscope.aliyuncs.com/compatible-mode/v1"
                  class="form-input"
                >
              </div>
              <div class="form-group">
                <label class="form-label">Model Name</label>
                <input
                  type="text"
                  v-model="llmConfig.modelName"
                  placeholder="例如：qwen-plus / gpt-4o-mini"
                  class="form-input"
                >
              </div>
              <div class="config-feedback" :class="{ success: llmConfigFeedbackType === 'success', error: llmConfigFeedbackType === 'error' }" v-if="llmConfigFeedback">
                {{ llmConfigFeedback }}
              </div>
            </div>
            <div class="dialog-footer">
              <button class="btn btn-secondary" @click="closeLlmConfigDialog">关闭</button>
              <button class="btn btn-secondary" :disabled="isTestingLlmConfig" @click="testLlmConfigConnection">
                {{ isTestingLlmConfig ? '测试中...' : '测试连接' }}
              </button>
              <button class="btn btn-primary" :disabled="isSavingLlmConfig" @click="saveLlmConfig">
                {{ isSavingLlmConfig ? '保存中...' : '保存配置' }}
              </button>
            </div>
          </div>
        </div>

      </div>

      <div v-if="activeTab === 'entities'" class="tab-pane entity-hub-pane">
        <div class="form-section entity-hub-section">
          <div class="section-header">
            <h2 class="section-title">核心实体</h2>
            <p class="section-description">实体会自动映射到设定管理中的对应设定项，成长阶段也会随实体一起存储。</p>
          </div>
          <div class="overview-header collapsible-header" @click="showEntitiesExpanded = !showEntitiesExpanded">
            <span class="collapse-arrow">{{ showEntitiesExpanded ? '▼' : '▶' }}</span>
            <h3 class="overview-title">核心实体 ({{ entities.length }})</h3>
            <span class="enabled-count">已启用 {{ enabledEntityCount }}</span>
          </div>
          <div v-if="entities.length === 0" class="overview-empty">暂无实体数据，导入或提取世界观后自动填充</div>
          <div v-else-if="showEntitiesExpanded" class="entity-card-list entity-card-grid">
            <div
              v-for="d in entityItems"
              :key="d.id"
              v-memo="[d.id, d.enabled, d.bioExpanded]"
              class="entity-card entity-card-rich"
              :class="{ 'entity-disabled': !d.enabled }"
            >
              <div class="entity-card-header entity-card-header-rich">
                <label class="toggle-switch" @click.stop>
                  <input type="checkbox" :checked="d.enabled" @change="toggleEntityEnabled(d.entity)" />
                  <span class="toggle-slider"></span>
                </label>
                <div class="entity-card-main">
                  <span class="entity-card-name">{{ d.entity.name }}</span>
                  <span class="entity-card-type">{{ d.entity.type || '未分类' }}</span>
                </div>
                <button type="button" class="entity-setting-link" @click.stop="openLinkedSetting(d.entity)">
                  {{ d.hasSetting ? '查看对应设定' : '生成对应设定' }}
                </button>
              </div>

              <div v-if="d.simpleKeys.length > 0" class="entity-card-attrs">
                <span v-for="key in d.simpleKeys" :key="key" class="entity-attr-tag">
                  <span class="attr-key">{{ key }}</span>: <span class="attr-value">{{ d.simpleAttrs[key] }}</span>
                </span>
              </div>

              <div v-if="d.hasBio" class="entity-bio-block">
                <div class="entity-bio-header" @click="toggleBioExpanded(d.entity)">
                  <span class="entity-bio-title">简介</span>
                  <span class="entity-bio-toggle">{{ d.bioExpanded ? '收起' : '展开' }}</span>
                </div>
                <p v-if="d.bioExpanded" class="entity-bio-text">{{ d.bio }}</p>
                <p v-else class="entity-bio-preview">{{ d.bioPreview }}...</p>
              </div>

              <div v-if="d.powerChanges.length > 0" class="entity-nested-block">
                <div class="entity-nested-title">实力变化 ({{ d.powerChanges.length }})</div>
                <div class="entity-nested-list">
                  <div v-for="(item, i) in d.powerChanges" :key="'power-'+i" class="entity-nested-card">
                    <div class="entity-nested-card-header">
                      <span class="entity-nested-time">{{ item.时间节点 || '未知时间' }}</span>
                      <span class="entity-nested-change">{{ item.变化前 || '?' }} → {{ item.变化后 || '?' }}</span>
                    </div>
                    <div v-if="item.触发事件" class="entity-nested-cause">触发: {{ item.触发事件 }}</div>
                    <p v-if="item.描述" class="entity-nested-desc">{{ item.描述 }}</p>
                  </div>
                </div>
              </div>

              <div v-if="d.personalityChanges.length > 0" class="entity-nested-block">
                <div class="entity-nested-title">性格变化 ({{ d.personalityChanges.length }})</div>
                <div class="entity-nested-list">
                  <div v-for="(item, i) in d.personalityChanges" :key="'char-'+i" class="entity-nested-card">
                    <div class="entity-nested-card-header">
                      <span class="entity-nested-time">{{ item.时间节点 || '未知时间' }}</span>
                      <span class="entity-nested-change">{{ item.变化前 || '?' }} → {{ item.变化后 || '?' }}</span>
                    </div>
                    <div v-if="item.触发事件" class="entity-nested-cause">触发: {{ item.触发事件 }}</div>
                    <p v-if="item.描述" class="entity-nested-desc">{{ item.描述 }}</p>
                  </div>
                </div>
              </div>

              <div v-if="d.turningPoints.length > 0" class="entity-nested-block">
                <div class="entity-nested-title">关键转折 ({{ d.turningPoints.length }})</div>
                <div class="entity-nested-list">
                  <div v-for="(item, i) in d.turningPoints" :key="'turn-'+i" class="entity-nested-card">
                    <div class="entity-nested-card-header">
                      <span class="entity-nested-time">{{ item.时间节点 || '未知时间' }}</span>
                      <span class="entity-nested-event-name">{{ item.事件 || '' }}</span>
                    </div>
                    <p v-if="item.影响" class="entity-nested-desc">{{ item.影响 }}</p>
                  </div>
                </div>
              </div>

              <div v-if="d.hasStages" class="entity-stage-block">
                <div class="entity-stage-title">成长阶段 ({{ d.stages.length }})</div>
                <div class="entity-stage-list">
                  <div v-for="stage in d.stages" :key="stage.id || stage.name" class="entity-stage-card">
                    <div class="entity-stage-card-header">
                      <span class="entity-stage-name">{{ stage.name }}</span>
                      <span v-if="stage.era" class="entity-stage-era">{{ stage.era }}</span>
                    </div>
                    <p v-if="stage.description" class="entity-stage-description">{{ stage.description }}</p>
                    <div v-if="stage.attributes && Object.keys(stage.attributes).length > 0" class="entity-stage-attrs">
                      <span v-for="(value, key) in stage.attributes" :key="`${stage.id || stage.name}-${key}`" class="entity-stage-attr-tag">
                        <span class="attr-key">{{ key }}</span>: <span class="attr-value">{{ value }}</span>
                      </span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="entity-stage-empty">当前实体还没有显式成长阶段，后续推演或补充设定后会显示在这里。</div>
            </div>
          </div>
        </div>

        <div class="form-section entity-hub-section">
          <div class="section-header">
            <h2 class="section-title">关键事件</h2>
            <p class="section-description">事件中的关联实体可以直接跳转到它们在设定管理中的条目。</p>
          </div>
          <div class="overview-header collapsible-header" @click="showEventsExpanded = !showEventsExpanded">
            <span class="collapse-arrow">{{ showEventsExpanded ? '▼' : '▶' }}</span>
            <h3 class="overview-title">关键事件 ({{ events.length }})</h3>
            <span class="enabled-count">已启用 {{ enabledEventCount }}</span>
          </div>
          <div v-if="events.length === 0" class="overview-empty">暂无事件数据，导入或提取世界观后自动填充</div>
          <div v-else-if="showEventsExpanded" class="event-card-list event-card-stack">
            <div
              v-for="d in eventItems"
              :key="d.id"
              v-memo="[d.id, d.enabled]"
              class="event-card event-card-rich"
              :class="{ 'entity-disabled': !d.enabled }"
            >
              <div class="event-card-header">
                <label class="toggle-switch" @click.stop>
                  <input type="checkbox" :checked="d.enabled" @change="toggleEventEnabled(d.event)" />
                  <span class="toggle-slider"></span>
                </label>
                <span class="event-card-name">{{ d.event.name }}</span>
                <span v-if="d.event.date" class="event-card-date">{{ d.event.date }}</span>
              </div>
              <p v-if="d.event.description" class="event-card-desc">{{ d.event.description }}</p>
              <div v-if="d.event.entities && d.event.entities.length > 0" class="event-card-entities">
                <button
                  v-for="entityName in d.event.entities"
                  :key="entityName"
                  type="button"
                  class="event-entity-tag event-entity-link"
                  @click.stop="openEntitySettingByName(entityName)"
                >
                  {{ entityName }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 设定管理 -->
      <div v-if="activeTab === 'settings'" class="tab-pane settings-management">
        <div class="settings-layout">
          <!-- 左侧分类栏 -->
          <div class="settings-sidebar">
            <div class="sidebar-header">
              <h3 class="sidebar-title">设定集</h3>
            </div>
            <div class="category-list">
              <div class="tree-root">
                <div class="tree-item root-item">
                  <span class="item-name">设定集</span>
                </div>
                <div class="tree-children">
                  <div v-for="category in settingCategories" :key="category.id" class="tree-node">
                    <div class="tree-item category-item" :class="{ active: activeCategory === category.id }" @click="toggleCategory(category.id)">
                      <span class="expand-icon">{{ category.expanded ? '▼' : '▶' }}</span>
                      <span class="category-icon">{{ category.icon }}</span>
                      <span class="category-name">{{ category.name }}</span>
                    </div>
                    <div v-if="category.expanded" class="tree-children">
                      <div v-for="collection in getCollectionsByCategory(category.id)" :key="collection.id" class="tree-node">
                        <div class="tree-item collection-item" @click="toggleCollection(collection.id)">
                          <span class="expand-icon">{{ collection.expanded ? '▼' : '▶' }}</span>
                          <span class="collection-icon">📁</span>
                          <span class="collection-name">{{ collection.name }}</span>
                        </div>
                        <div v-if="collection.expanded" class="tree-children">
                          <div v-for="setting in getSettingsByCollection(collection.id)" :key="setting.id" class="tree-item setting-item">
                            <span class="setting-icon">📄</span>
                            <span class="setting-name">{{ setting.name }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- 右侧内容区 -->
          <div class="settings-content">
            <div class="content-header">
              <div class="header-search">
                <input type="text" placeholder="搜索设定标题..." class="search-input">
              </div>
              <div class="header-actions">
                <button class="btn btn-secondary my-proposals-btn">我的提案</button>
                <button class="btn btn-primary new-setting-btn" @click="openNewSettingDialog">+ 新建设定</button>
              </div>
            </div>
            
            <div class="settings-list">
              <div 
                v-for="setting in filteredSettings" 
                :key="setting.id"
                class="setting-card"
                @click="viewSettingDetail(setting)"
              >
                <div class="setting-header">
                  <h4 class="setting-title">{{ setting.name }}</h4>
                  <span :class="['setting-type-tag', setting.settingType]">
                    {{ setting.settingType === 'setting' ? '设定' : '设定集' }}
                  </span>
                </div>
                <p class="setting-description">{{ setting.description }}</p>
                <div class="setting-footer">
                  <div class="setting-meta">
                    <span class="meta-label">最近更新</span>
                    <span class="update-time">刚刚</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'evolutions'" class="tab-pane evolution-history-pane">
        <div class="form-section evolution-history-section">
          <div class="section-header">
            <h2 class="section-title">推演记录</h2>
            <p class="section-description">查看当前世界观下的每一次推演项目，并跳转到对应的推演记录页面。</p>
          </div>

          <div v-if="!worldId" class="overview-empty">请先保存世界观，然后再查看它的推演记录。</div>
          <div v-else-if="isLoadingEvolutionHistory" class="overview-empty">推演记录加载中...</div>
          <p v-else-if="evolutionHistoryError" class="extract-error">{{ evolutionHistoryError }}</p>
          <div v-else-if="evolutionHistory.length === 0" class="overview-empty">暂无推演记录，点击右上角“创建推演项目”开始第一次推演。</div>
          <div v-else class="evolution-history-list">
            <article v-for="record in evolutionHistory" :key="record.id" class="evolution-history-card">
              <div class="evolution-history-top">
                <div class="evolution-history-main">
                  <div class="evolution-history-type">{{ getEvolutionTypeLabel(record.evolution_type) }}</div>
                  <h3 class="evolution-history-title">{{ record.scenario || '未命名推演' }}</h3>
                </div>
                <span class="evolution-status-badge" :class="`is-${record.status}`">{{ getEvolutionStatusLabel(record.status) }}</span>
              </div>

              <div class="evolution-history-meta">
                <span>记录 ID: {{ record.id }}</span>
                <span>轮次: {{ (record.rounds || []).length }}</span>
                <span>更新时间: {{ formatDateTime(record.updated_at || record.created_at) }}</span>
              </div>

              <p class="evolution-history-description">{{ record.scenario }}</p>

              <div class="evolution-history-actions">
                <button type="button" class="btn btn-secondary" @click="openEvolutionRecord(record)">
                  查看推演记录
                </button>
              </div>
            </article>
          </div>
        </div>
      </div>

      <!-- 时间线 -->
      <div v-if="activeTab === 'timeline'" class="tab-pane timeline-section">
        <div class="timeline-header">
          <div class="header-info">
            <span class="timeline-eyebrow">Chronology Atlas</span>
            <h3 class="header-title">世界时间线</h3>
            <p class="header-description">保留时间线：{{ timelinePrimaryLabel }}，事件与实体阶段已按可定位年份挂接。</p>
          </div>
          <div class="header-actions">
            <div class="zoom-controls">
              <button class="btn btn-secondary zoom-btn" @click="zoomOut">
                <span>−</span>
              </button>
              <span class="zoom-level">{{ Math.round(zoomLevel * 100) }}%</span>
              <button class="btn btn-secondary zoom-btn" @click="zoomIn">
                <span>+</span>
              </button>
            </div>
            <button class="btn btn-secondary calendar-edit-btn" @click="openCalendarEdit">历法编辑</button>
          </div>
        </div>

        <div class="timeline-status-grid">
          <div class="timeline-status-card is-primary">
            <span class="status-label">主轴</span>
            <strong>{{ timelinePrimaryLabel }}</strong>
            <small>{{ timelineRangeLabels.start }} - {{ timelineRangeLabels.end }}</small>
          </div>
          <div class="timeline-status-card">
            <span class="status-label">历法</span>
            <strong>{{ timelineDiagnostics.usableCalendars }} / {{ timelineDiagnostics.totalCalendars }}</strong>
            <small>可定位 / 已提取</small>
          </div>
          <div class="timeline-status-card">
            <span class="status-label">事件锚点</span>
            <strong>{{ timelineDiagnostics.eventAnchors }}</strong>
            <small>显示 {{ timelineDiagnostics.visibleEvents }} 条</small>
          </div>
          <div class="timeline-status-card">
            <span class="status-label">实体阶段</span>
            <strong>{{ timelineDiagnostics.stageAnchors }}</strong>
            <small>显示 {{ timelineDiagnostics.visibleStages }} 条</small>
          </div>
        </div>

        <div class="timeline-insights">
          <div class="timeline-insight-card timeline-chronology-card">
            <div class="insight-header">
              <span class="insight-kicker">纪元 / 纪年骨架</span>
              <span class="insight-count">{{ timelineEraSummaries.length }} 纪元 · {{ timelineYearSummaries.length }} 纪年</span>
            </div>
            <div v-if="calendarSummaries.length > 0" class="chronology-columns">
              <div class="chronology-column">
                <div class="chronology-column-title">纪元</div>
                <button
                  v-for="calendar in timelineEraSummaries"
                  :key="calendar.id"
                  type="button"
                  class="calendar-summary-row is-era"
                  @click="showCalendarDetail(calendar)"
                >
                  <span class="summary-name">{{ calendar.name }}</span>
                  <span class="summary-meta">{{ calendar.timeRange || calendar.baseTime || '未定义区间' }}</span>
                </button>
                <div v-if="timelineEraSummaries.length === 0" class="timeline-empty-hint">没有可展示的纪元。</div>
              </div>
              <div class="chronology-column">
                <div class="chronology-column-title">纪年</div>
                <button
                  v-for="calendar in timelineYearSummaries"
                  :key="calendar.id"
                  type="button"
                  class="calendar-summary-row is-year"
                  @click="showCalendarDetail(calendar)"
                >
                  <span class="summary-name">{{ calendar.name }}</span>
                  <span class="summary-meta">{{ calendar.timeRange || calendar.baseTime || '未定义区间' }}</span>
                </button>
                <div v-if="timelineYearSummaries.length === 0" class="timeline-empty-hint">没有可展示的纪年。</div>
              </div>
            </div>
            <div v-else class="timeline-empty-hint">尚未定义历法体系，请先在“历法编辑”中创建至少一条历法。</div>
          </div>

          <div class="timeline-insight-card timeline-quality-card">
            <div class="insight-header">
              <span class="insight-kicker">数据诊断</span>
              <span class="insight-count">{{ timelineDiagnostics.noisyCalendars }} 项待清理</span>
            </div>
            <div v-if="timelineIssueCalendars.length > 0" class="timeline-issue-list">
              <div v-for="issue in timelineIssueCalendars" :key="issue.id" class="timeline-issue-row">
                <span class="issue-name">{{ issue.name }}</span>
                <span class="issue-reason">{{ issue.issue }}</span>
              </div>
            </div>
            <div v-else class="timeline-empty-hint">当前历法数据可以直接渲染。</div>
          </div>
        </div>
        
        <!-- 横向时间轴 -->
        <div class="timeline-container" ref="timelineContainer" @wheel="handleWheel" :style="{ height: timelineHeight }">
          <div class="timeline-canvas" ref="timelineCanvas" :style="timelineCanvasStyle">
            <div class="timeline-title">
              <span>世界基准时间轴</span>
            </div>
            <div class="timeline-axis">
              <div class="timeline-line"></div>
              <div
                v-for="tick in timelineTicks"
                :key="tick.label"
                class="timeline-tick"
                :style="{ left: tick.position + '%' }"
              >
                <span>{{ tick.label }}</span>
              </div>
              <div class="timeline-axis-range">
                <span class="axis-range-label">{{ timelineRangeLabels.start }}</span>
                <span class="axis-range-label">{{ timelineRangeLabels.end }}</span>
              </div>
            </div>

            <div class="timeline-lane-title" :style="{ top: timelineCalendarTop - 30 + 'px' }">纪元与纪年</div>
            <div class="timeline-band-layer" :style="{ top: timelineCalendarTop + 'px', height: timelineCalendarHeight + 'px' }">
              <div v-if="calendarTimelineItems.length === 0" class="timeline-empty-lane">暂无历法区间，点击“历法编辑”创建后会显示在这里。</div>
              <div 
                v-for="(calendar, index) in calendarTimelineItems" 
                :key="calendar.id"
                class="timeline-band calendar-band"
                :class="[`is-${calendar.kind}`, { 'is-low-confidence': calendar.issue }]"
                :style="getCalendarBandStyle(calendar, index)"
                @click="showCalendarDetail(calendar.source || calendar)"
              >
                <div class="band-name">{{ calendar.name }}</div>
                <div class="band-caption">{{ calendar.caption }}</div>
              </div>
            </div>

            <div class="timeline-lane-title" :style="{ top: timelineEventTop - 30 + 'px' }">关键事件</div>
            <div class="timeline-point-layer" :style="{ top: timelineEventTop + 'px', height: timelineEventHeight + 'px' }">
              <div v-if="timelineEventItems.length === 0" class="timeline-empty-lane">暂无可定位事件。</div>
              <button
                v-for="(event, index) in timelineEventItems"
                :key="event.id"
                type="button"
                class="timeline-point-event"
                :style="getTimelineEventStyle(event, index)"
                :title="`${event.label} · ${event.name}`"
                :aria-label="`${event.label} ${event.name}`"
                @click="selectEvent(event.source)"
              >
                <span class="event-dot"></span>
                <span class="event-popover">
                  <strong>{{ event.name }}</strong>
                  <small>{{ event.label }} · {{ event.entities.slice(0, 2).join(' / ') || event.dateText }}</small>
                </span>
              </button>
            </div>

            <div class="timeline-lane-title" :style="{ top: timelineStageTop - 30 + 'px' }">实体阶段</div>
            <div class="timeline-stage-layer" :style="{ top: timelineStageTop + 'px', height: timelineStageHeight + 'px' }">
              <div v-if="timelineStageItems.length === 0" class="timeline-empty-lane">暂无可定位实体阶段。</div>
              <div
                v-for="(stage, index) in timelineStageItems"
                :key="stage.id"
                class="timeline-stage-chip"
                :style="getTimelineStageStyle(stage, index)"
                :title="`${stage.label} · ${stage.entityName} · ${stage.name}`"
              >
                <span class="stage-pulse"></span>
                <span class="stage-name">{{ stage.entityName }} · {{ stage.name }}</span>
              </div>
            </div>

            <div 
              v-if="world.anchor_time"
              class="anchor-time-marker"
              :style="{ left: getAnchorTimePosition() + '%' }"
              @click="scrollToPosition(getAnchorTimePosition())"
            >
              <div class="anchor-label">锚定时间: {{ world.anchor_time }}</div>
            </div>
          </div>
        </div>

        <div class="timeline-context-grid">
          <section class="timeline-context-panel">
            <div class="context-panel-header">
              <span>事件锚点</span>
              <strong>{{ timelineDiagnostics.visibleEvents }}</strong>
            </div>
            <button
              v-for="event in timelineEventItems.slice(0, 12)"
              :key="`ctx-${event.id}`"
              type="button"
              class="context-event-row"
              @click="selectEvent(event.source)"
            >
              <span class="context-year">{{ event.label }}</span>
              <span class="context-title">{{ event.name }}</span>
              <span class="context-meta">{{ event.entities.slice(0, 3).join(' / ') || event.dateText }}</span>
            </button>
          </section>

          <section class="timeline-context-panel">
            <div class="context-panel-header">
              <span>实体阶段</span>
              <strong>{{ timelineDiagnostics.visibleStages }}</strong>
            </div>
            <div v-for="stage in timelineStageItems.slice(0, 12)" :key="`ctx-${stage.id}`" class="context-stage-row">
              <span class="context-year">{{ stage.label }}</span>
              <span class="context-title">{{ stage.entityName }}</span>
              <span class="context-meta">{{ stage.name }} · {{ stage.era }}</span>
            </div>
          </section>
        </div>
      </div>

      <!-- 地图 -->
      <div v-if="activeTab === 'map'" class="tab-pane map-section">
        <div class="section-header">
          <h3 class="section-title">世界地图</h3>
          <p class="section-description">定义世界地理和地区关系</p>
        </div>
        <div class="map-form">
          <div class="form-group">
            <label class="form-label">地区关系</label>
            <textarea 
              v-model="mapData.regionRelations" 
              placeholder="描述各个地区之间的关系，如地理、政治、经济等..."
              rows="4"
              class="form-textarea"
            ></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">国家地域关系</label>
            <textarea 
              v-model="mapData.countryRelations" 
              placeholder="描述国家之间的地域关系，如边界、领土、外交等..."
              rows="4"
              class="form-textarea"
            ></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">重要地理位置</label>
            <textarea 
              v-model="mapData.importantLocations" 
              placeholder="描述重要的地理位置，如城市、山脉、河流等..."
              rows="4"
              class="form-textarea"
            ></textarea>
          </div>
        </div>
      </div>

      <!-- 历法编辑窗口 -->
      <div v-if="showCalendarEdit" class="dialog">
        <div class="dialog-content calendar-edit-dialog">
          <div class="dialog-header">
            <h2 class="dialog-title">历法编辑</h2>
            <button class="close-btn" @click="cancelCalendarEdit">×</button>
          </div>
          
          <div class="calendar-edit-content">
            <div class="calendar-table-container">
              <table class="calendar-table">
                <thead>
                  <tr>
                    <th>历法</th>
                    <th>类型</th>
                    <th>基准时间</th>
                    <th>基准时间区间</th>
                    <th>单位</th>
                    <th>比例</th>
                    <th>月日制</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="calendar in editCalendars" :key="calendar.id">
                    <td>{{ calendar.name }}</td>
                    <td>
                      <span :class="['type-tag', calendar.type === '纪元' ? 'epoch' : 'year']">
                        {{ calendar.type }}
                      </span>
                    </td>
                    <td>{{ calendar.baseTime }}</td>
                    <td>{{ calendar.timeRange }}</td>
                    <td>{{ calendar.unit }}</td>
                    <td>{{ calendar.ratio }}</td>
                    <td>{{ calendar.calendarType }}</td>
                    <td class="action-buttons">
                      <button class="btn btn-secondary edit-btn" @click="editCalendar(calendar)">✏️</button>
                      <button class="btn btn-danger delete-btn" @click="deleteCalendar(calendar.id)">🗑️</button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            <div class="calendar-info">
              <h3 class="info-title">历法编辑说明</h3>
              <div class="info-section">
                <h4 class="info-subtitle">历法类型：</h4>
                <ul class="info-list">
                  <li>• 纪元：用于记录世界大事件的历法体系</li>
                  <li>• 纪年：用于记录政权或朝代的历法</li>
                </ul>
              </div>
              <div class="info-section">
                <h4 class="info-subtitle">时间单位：</h4>
                <ul class="info-list">
                  <li>• 可自定义时间单位名称和符号</li>
                  <li>• 比例系数表示该单位与基准年的关系</li>
                  <li>• 如：1纪元 = 2基准年，则比例系数为2</li>
                </ul>
              </div>
              <div class="info-section">
                <h4 class="info-subtitle">年份规则：</h4>
                <ul class="info-list">
                  <li>• 纪元历法之间不能重叠</li>
                  <li>• 纪元首尾相接不算重叠</li>
                  <li>• 仅第一个纪元可设置无开始时间</li>
                </ul>
              </div>
            </div>
          </div>
          
          <div class="dialog-footer">
            <button class="btn btn-secondary add-calendar-btn" @click="addCalendar">添加历法</button>
            <button class="btn btn-primary save-btn" @click="saveCalendars">保存</button>
            <button class="btn btn-secondary cancel-btn" @click="cancelCalendarEdit">取消</button>
          </div>
        </div>
      </div>
      
      <!-- 历法详情编辑窗口 -->
      <div v-if="showCalendarDetailEdit" class="dialog">
        <div class="dialog-content calendar-detail-dialog">
          <div class="dialog-header">
            <h2 class="dialog-title">编辑历法</h2>
            <button class="close-btn" @click="cancelCalendarDetailEdit">×</button>
          </div>
          
          <div class="calendar-detail-content">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">* 历法标题</label>
                <input type="text" v-model="currentCalendar.name" class="form-input">
              </div>
              <div class="form-group">
                <label class="form-label">* 历法类型</label>
                <select v-model="currentCalendar.type" class="form-select">
                  <option value="纪元">纪元</option>
                  <option value="纪年">纪年</option>
                </select>
              </div>
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">* 基准年份</label>
                <input type="text" v-model="currentCalendar.startYear" class="form-input">
              </div>
              <div class="form-group">
                <label class="form-label">结束年份</label>
                <div class="end-year-input">
                  <input type="text" v-model="currentCalendar.endYear" class="form-input" :disabled="currentCalendar.noEndTime">
                  <label class="checkbox-label">
                    <input type="checkbox" v-model="currentCalendar.noEndTime">
                    无结束时间
                  </label>
                </div>
              </div>
            </div>
            
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">* 时间单位名称</label>
                <input type="text" v-model="currentCalendar.unit" class="form-input">
              </div>
              <div class="form-group">
                <label class="form-label">月日制 / 附加规则</label>
                <input type="text" v-model="currentCalendar.calendarType" class="form-input" placeholder="未开启或自定义规则">
              </div>
              <div class="form-group">
                <label class="form-label">* 比例系数</label>
                <input type="text" v-model="currentCalendar.ratioValue" class="form-input">
              </div>
            </div>
            
            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" v-model="currentCalendar.customCalendar">
                自定义日月配置
              </label>
            </div>
            
            <div class="form-group">
              <label class="form-label">历法描述（可选）</label>
              <textarea v-model="currentCalendar.description" class="form-textarea" placeholder="输入历法的详细描述..." rows="4"></textarea>
            </div>
          </div>
          
          <div class="dialog-footer">
            <button class="btn btn-secondary cancel-btn" @click="cancelCalendarDetailEdit">取消</button>
            <button class="btn btn-primary save-btn" @click="saveCalendarDetail">保存</button>
          </div>
        </div>
      </div>
      
      <!-- 新建设定对话框 -->
      <div v-if="showNewSettingDialog" class="dialog">
        <div class="dialog-content new-setting-dialog">
          <div class="dialog-header">
            <h2 class="dialog-title">创建新设定提案</h2>
            <button class="close-btn" @click="closeNewSettingDialog">×</button>
          </div>
          
          <div class="new-setting-content">
            <!-- 标签页 -->
            <div class="setting-tabs">
              <button class="tab-btn active">基本信息</button>
              <button class="tab-btn">设定详情内容</button>
              <button class="tab-btn">设置</button>
            </div>
            
            <!-- 基本信息 -->
            <div class="setting-form">
              <div class="form-row">
                <div class="form-group required">
                  <label class="form-label">* 设定名称</label>
                  <input type="text" v-model="newSetting.name" class="form-input" placeholder="输入设定名称">
                </div>
                <div class="form-group">
                  <label class="form-label">类型</label>
                  <div class="type-selector">
                    <button 
                      :class="['type-btn', { active: newSetting.settingType === 'setting' }]"
                      @click="newSetting.settingType = 'setting'"
                    >
                      设定
                    </button>
                    <button 
                      :class="['type-btn', { active: newSetting.settingType === 'collection' }]"
                      @click="newSetting.settingType = 'collection'"
                    >
                      设定集
                    </button>
                  </div>
                </div>
                <div class="form-group">
                  <label class="form-label">设定列表</label>
                  <div class="type-selector">
                    <button 
                      :class="['type-btn', { active: newSetting.showInList }]"
                      @click="newSetting.showInList = true"
                    >
                      展示
                    </button>
                    <button 
                      :class="['type-btn', { active: !newSetting.showInList }]"
                      @click="newSetting.showInList = false"
                    >
                      不展示
                    </button>
                  </div>
                </div>
              </div>
              
              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">别名 (可选)</label>
                  <div class="alias-input">
                    <input 
                      type="text" 
                      v-model="newSetting.newAlias" 
                      class="form-input" 
                      placeholder="输入别名后按 Enter 添加"
                      @keyup.enter="addAlias"
                    >
                  </div>
                  <div class="alias-list" v-if="newSetting.aliases.length > 0">
                    <span v-for="(alias, index) in newSetting.aliases" :key="index" class="alias-tag">
                      {{ alias }}
                      <button class="remove-alias" @click="removeAlias(index)">×</button>
                    </span>
                  </div>
                </div>
                <div class="form-group" v-if="newSetting.settingType === 'setting'">
                  <label class="form-label">设定分类 (可选)</label>
                  <select v-model="newSetting.category" class="form-select">
                    <option value="">选择设定分类</option>
                    <option v-for="cat in settingCategories" :key="cat.id" :value="cat.id">
                      {{ cat.name }}
                    </option>
                  </select>
                </div>
              </div>
              
              <!-- 设定特有字段 -->
              <div class="form-group required" v-if="newSetting.settingType === 'setting'">
                <label class="form-label">* 关联设定集</label>
                <select v-model="newSetting.parentCollection" class="form-select">
                  <option value="">选择关联设定集</option>
                  <option v-for="collection in settingCollections" :key="collection.id" :value="collection.id">
                    {{ collection.name }}
                  </option>
                </select>
              </div>
              
              <!-- 设定集特有字段 -->
              <div class="form-group" v-if="newSetting.settingType === 'collection'">
                <label class="form-label">上级设定集 (可选)</label>
                <select v-model="newSetting.parentCollection" class="form-select">
                  <option value="">选择上级设定集（不选则作为根设定集）</option>
                  <option v-for="collection in settingCollections" :key="collection.id" :value="collection.id">
                    {{ collection.name }}
                  </option>
                </select>
              </div>
              
              <div class="form-group required">
                <label class="form-label">* 设定描述</label>
                <textarea 
                  v-model="newSetting.description" 
                  class="form-textarea" 
                  placeholder="请输入设定简短描述，会显示在设定列表卡片上"
                  rows="4"
                ></textarea>
                <div class="char-count">0 / 300</div>
              </div>
            </div>
          </div>
          
          <div class="dialog-footer">
            <button class="btn btn-secondary cancel-btn" @click="closeNewSettingDialog">取消</button>
            <button class="btn btn-secondary save-draft-btn">💾 保存提案</button>
            <button class="btn btn-primary submit-btn" @click="saveNewSetting">→ 提交提案</button>
          </div>
        </div>
      </div>
      
      <!-- 设定详情对话框 -->
      <div v-if="showSettingDetail" class="dialog">
        <div class="dialog-content setting-detail-dialog">
          <div class="dialog-header">
            <h2 class="dialog-title">{{ currentSetting.name }} - 详情</h2>
            <button class="close-btn" @click="closeSettingDetail">×</button>
          </div>
          
          <div class="setting-detail-content">
            <div class="detail-header">
              <div class="detail-info">
                <h3 class="detail-title">{{ currentSetting.name }}</h3>
                <div class="detail-meta">
                  <span :class="['setting-type-tag', currentSetting.settingType]">
                    {{ currentSetting.settingType === 'setting' ? '设定' : '设定集' }}
                  </span>
                  <span v-if="currentSetting.aliases && currentSetting.aliases.length > 0" class="aliases">
                    别名：{{ currentSetting.aliases.join(', ') }}
                  </span>
                </div>
              </div>
            </div>
            
            <div class="detail-body">
              <div v-if="currentSettingStructuredSections.length > 0" class="setting-structured-grid">
                <section
                  v-for="section in currentSettingStructuredSections"
                  :key="section.key"
                  class="setting-structured-section"
                  :class="{ 'is-wide': section.wide }"
                >
                  <div class="setting-structured-header">
                    <h4 class="setting-structured-title">{{ section.title }}</h4>
                    <span v-if="section.kind !== 'text'" class="setting-structured-count">{{ section.items.length }}</span>
                  </div>

                  <div v-if="section.kind === 'text'" class="setting-structured-text">{{ section.content }}</div>

                  <div v-else-if="section.kind === 'facts'" class="setting-facts-grid">
                    <div v-for="item in section.items" :key="`${section.key}-${item.label}`" class="setting-fact-item">
                      <span class="setting-fact-label">{{ item.label }}</span>
                      <span class="setting-fact-value">{{ item.value }}</span>
                    </div>
                  </div>

                  <div v-else class="setting-card-list">
                    <article v-for="item in section.items" :key="item.id || `${section.key}-${item.title}`" class="setting-structured-card">
                      <div class="setting-card-header">
                        <div>
                          <h5 class="setting-card-title">{{ item.title }}</h5>
                          <div v-if="item.subtitle" class="setting-card-subtitle">{{ item.subtitle }}</div>
                        </div>
                      </div>

                      <p v-if="item.description" class="setting-card-description">{{ item.description }}</p>

                      <div v-if="item.fields && item.fields.length > 0" class="setting-card-fields">
                        <div v-for="field in item.fields" :key="`${item.id || item.title}-${field.label}`" class="setting-card-field">
                          <span class="setting-card-field-label">{{ field.label }}</span>
                          <span class="setting-card-field-value">{{ field.value }}</span>
                        </div>
                      </div>
                    </article>
                  </div>
                </section>
              </div>

              <div class="form-group">
                <label class="form-label">{{ currentSettingDetailLabel }}</label>
                <p v-if="currentSettingStructuredSections.length > 0" class="setting-detail-hint">
                  上方分栏展示的是实体结构化内容；这里可补充额外说明、背景设定或人工修订文本。
                </p>
                <textarea 
                  v-model="currentSetting.detailContent" 
                  class="form-textarea detail-textarea" 
                  placeholder="输入详细内容..."
                  rows="10"
                ></textarea>
              </div>
            </div>
          </div>
          
          <div class="dialog-footer">
            <button class="btn btn-secondary cancel-btn" @click="closeSettingDetail">取消</button>
            <button class="btn btn-primary save-btn" @click="saveSettingDetail">保存</button>
          </div>
        </div>
      </div>
      
      <!-- 设定选择窗口 -->
      <div v-if="showSettingSelector" class="dialog">
        <div class="dialog-content setting-selector-dialog">
          <div class="dialog-header">
            <h2 class="dialog-title">选择设定</h2>
            <button class="close-btn" @click="closeSettingSelector">×</button>
          </div>
          
          <div class="setting-selector-content">
            <div class="setting-categories">
              <div 
                v-for="category in settingCategories" 
                :key="category.id"
                :class="['category-filter', { active: selectedCategoryFilter === category.id || selectedCategoryFilter === 'all' }]"
                @click="selectedCategoryFilter = selectedCategoryFilter === category.id ? 'all' : category.id"
              >
                {{ category.icon }} {{ category.name }}
              </div>
            </div>
            
            <div class="setting-list">
              <div 
                v-for="setting in filteredSettingsForSelection" 
                :key="setting.id"
                :class="['setting-item-checkbox', { selected: selectedSettings.includes(setting.id) }]"
                @click="toggleSettingSelection(setting.id)"
              >
                <input 
                  type="checkbox" 
                  :checked="selectedSettings.includes(setting.id)"
                  @click.stop="toggleSettingSelection(setting.id)"
                >
                <div class="setting-info">
                  <div class="setting-name">{{ setting.name }}</div>
                  <div class="setting-description">{{ setting.description }}</div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="dialog-footer">
            <button class="btn btn-secondary cancel-btn" @click="closeSettingSelector">取消</button>
            <button class="btn btn-primary save-btn" @click="confirmSettingSelection">确认选择</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { worldApi } from '../api/world'
import { projectApi } from '../api/project'
import { generateOntologyFromProject } from '../api/graph'
import service from '../api/index'

const SETTING_CATEGORY_OPTIONS = [
  { id: 'character', name: '角色', icon: '👤' },
  { id: 'item', name: '物品', icon: '📦' },
  { id: 'organization', name: '组织', icon: '🏢' },
  { id: 'geography', name: '地理', icon: '🌍' },
  { id: 'ability', name: '能力', icon: '⚡' },
  { id: 'other', name: '其他', icon: '📋' }
]

const createDefaultMapData = () => ({
  regionRelations: '',
  countryRelations: '',
  importantLocations: ''
})

const createDefaultSettingCategories = () => SETTING_CATEGORY_OPTIONS.map((category, index) => ({
  ...category,
  expanded: index === 0
}))

const createDefaultSettings = () => []

const createDefaultCalendars = () => []

const createLocalId = (prefix, index = 0) => `${prefix}_${Date.now()}_${index}_${Math.random().toString(36).slice(2, 8)}`

const normalizeEntityStage = (stage, index = 0, entityName = '') => {
  if (!stage || typeof stage !== 'object') {
    return null
  }

  const rawAttributes = stage.attributes && typeof stage.attributes === 'object'
    ? stage.attributes
    : (stage['属性'] && typeof stage['属性'] === 'object' ? stage['属性'] : {})

  const name = String(stage.name || stage['名称'] || stage.title || `${entityName || '实体'}阶段${index + 1}`).trim()
  if (!name) {
    return null
  }

  return {
    id: stage.id || createLocalId('stage', index),
    name,
    era: String(stage.era || stage['时期'] || stage.time || '').trim(),
    description: String(stage.description || stage['描述'] || '').trim(),
    attributes: { ...rawAttributes },
    setting_item_id: String(stage.setting_item_id || stage.settingId || stage.linked_setting_id || '').trim(),
    source: stage.source && typeof stage.source === 'object' ? { ...stage.source } : {},
  }
}

const normalizeEntityRelationship = (relationship) => {
  if (!relationship || typeof relationship !== 'object') {
    return null
  }

  const target = String(
    relationship.target || relationship.entity || relationship.name || relationship['对象'] || relationship['目标'] || ''
  ).trim()

  if (!target) {
    return null
  }

  return {
    target,
    type: String(relationship.type || relationship.relation || relationship.kind || relationship['关系类型'] || relationship['关系'] || '关联').trim() || '关联',
    description: String(relationship.description || relationship.detail || relationship.summary || relationship['说明'] || '').trim(),
    time_period: String(relationship.time_period || relationship.period || relationship['时期'] || relationship['时间'] || '').trim(),
    source_event: String(relationship.source_event || relationship.event || relationship['触发事件'] || '').trim(),
  }
}

const normalizeEntitiesForUi = (entities = []) => {
  if (!Array.isArray(entities)) {
    return []
  }

  return entities
    .filter(entity => entity && typeof entity === 'object')
    .map((entity, index) => {
      const rawAttributes = entity.attributes && typeof entity.attributes === 'object' ? { ...entity.attributes } : {}
      const rawStages = Array.isArray(entity.stages)
        ? entity.stages
        : (Array.isArray(rawAttributes.stages)
          ? rawAttributes.stages
          : (Array.isArray(rawAttributes['阶段']) ? rawAttributes['阶段'] : []))

      delete rawAttributes.stages
      delete rawAttributes['阶段']

      const normalizedStages = rawStages
        .map((stage, stageIndex) => normalizeEntityStage(stage, stageIndex, entity.name))
        .filter(Boolean)

      const normalizedEntity = {
        ...entity,
        id: entity.id || createLocalId('entity', index),
        name: String(entity.name || '').trim(),
        type: String(entity.type || '').trim(),
        aliases: normalizeAliases(entity.aliases || entity.alias || rawAttributes.aliases || rawAttributes['别名']),
        attributes: rawAttributes,
        stages: normalizedStages,
        relationships: (Array.isArray(entity.relationships) ? entity.relationships : Array.isArray(rawAttributes.relationships) ? rawAttributes.relationships : Array.isArray(rawAttributes['关系']) ? rawAttributes['关系'] : [])
          .map(normalizeEntityRelationship)
          .filter(Boolean),
        setting_item_id: String(entity.setting_item_id || entity.settingId || entity.linked_setting_id || '').trim(),
        evolution_refs: Array.isArray(entity.evolution_refs)
          ? entity.evolution_refs.map(ref => String(ref || '').trim()).filter(Boolean)
          : [],
      }

      return normalizedEntity
    })
    .filter(entity => entity.name)
}

const ENTITY_SPECIAL_ATTRIBUTE_KEYS = new Set(['简介', '实力变化', '性格变化', '关键转折'])

const hasStructuredDisplayValue = (value) => {
  if (Array.isArray(value)) {
    return value.some(item => hasStructuredDisplayValue(item))
  }

  if (value && typeof value === 'object') {
    return Object.values(value).some(item => hasStructuredDisplayValue(item))
  }

  return Boolean(String(value ?? '').trim())
}

const formatStructuredText = (value, options = {}) => {
  const { inline = false } = options

  if (!hasStructuredDisplayValue(value)) {
    return ''
  }

  if (Array.isArray(value)) {
    const normalizedItems = value
      .map(item => formatStructuredText(item, { inline: true }))
      .filter(Boolean)

    if (!normalizedItems.length) {
      return ''
    }

    return inline ? normalizedItems.join('；') : normalizedItems.map(item => `- ${item}`).join('\n')
  }

  if (value && typeof value === 'object') {
    const entries = Object.entries(value)
      .filter(([, nestedValue]) => hasStructuredDisplayValue(nestedValue))
      .map(([key, nestedValue]) => `${key}：${formatStructuredText(nestedValue, { inline: true })}`)
      .filter(Boolean)

    return inline ? entries.join('；') : entries.join('\n')
  }

  return String(value ?? '').trim()
}

const buildEntitySettingSummary = (entity) => {
  const attributes = entity.attributes || {}
  const introText = formatStructuredText(attributes['简介'])
  const attributeLines = Object.entries(attributes)
    .filter(([key, value]) => !ENTITY_SPECIAL_ATTRIBUTE_KEYS.has(key) && hasStructuredDisplayValue(value))
    .map(([key, value]) => `${key}：${formatStructuredText(value, { inline: true })}`)

  const stageLines = (entity.stages || [])
    .map(stage => {
      const stageDetailParts = []
      if (stage.era) stageDetailParts.push(stage.era)
      if (stage.description) stageDetailParts.push(stage.description)

      const stageAttributePreview = Object.entries(stage.attributes || {})
        .filter(([, value]) => hasStructuredDisplayValue(value))
        .slice(0, 2)
        .map(([key, value]) => `${key}：${formatStructuredText(value, { inline: true })}`)
        .join('；')

      if (stageAttributePreview) {
        stageDetailParts.push(stageAttributePreview)
      }

      const suffix = stageDetailParts.filter(Boolean).join('｜')
      return suffix ? `[${stage.name}] ${suffix}` : `[${stage.name}]`
    })
    .filter(Boolean)

  const relationshipLines = (entity.relationships || [])
    .map(relationship => {
      const target = String(relationship.target || '').trim()
      const relationType = String(relationship.type || '').trim()
      const description = String(relationship.description || '').trim()
      if (!target) {
        return ''
      }

      const summary = [target, relationType ? `（${relationType}）` : '', description ? `：${description}` : ''].join('')
      return summary.trim()
    })
    .filter(Boolean)

  const lines = [
    introText,
    relationshipLines.length ? `关系网络：\n${relationshipLines.map(line => `- ${line}`).join('\n')}` : '',
    stageLines.length ? `成长阶段：\n${stageLines.map(line => `- ${line}`).join('\n')}` : '',
    attributeLines.join('\n'),
  ].filter(Boolean)

  const previewText = introText.split('\n').find(Boolean) || relationshipLines[0] || stageLines[0] || attributeLines[0] || entity.type || '实体设定'
  return {
    description: previewText,
    detailContent: lines.join('\n') || entity.type || '实体设定',
  }
}

const buildStructuredFieldItems = (source, excludedKeys = []) => {
  if (!source || typeof source !== 'object' || Array.isArray(source)) {
    return []
  }

  const excluded = new Set(excludedKeys)
  return Object.entries(source)
    .filter(([key, value]) => !excluded.has(key) && hasStructuredDisplayValue(value))
    .map(([label, value]) => ({
      label,
      value: formatStructuredText(value, { inline: true }),
    }))
    .filter(field => field.value)
}

const buildEntityDetailSections = (entity) => {
  if (!entity || typeof entity !== 'object') {
    return []
  }

  const attributes = entity.attributes || {}
  const sections = []
  const handledAttributeKeys = new Set(['简介', '实力变化', '性格变化', '关键转折'])

  const introText = formatStructuredText(attributes['简介'])
  if (introText) {
    sections.push({
      key: 'intro',
      title: '核心简介',
      kind: 'text',
      wide: true,
      content: introText,
    })
  }

  const overviewItems = [
    { label: '实体类型', value: String(entity.type || '未分类').trim() || '未分类' },
  ]

  const aliases = normalizeAliases(entity.aliases)
  if (aliases.length > 0) {
    overviewItems.push({ label: '别名', value: aliases.join('、') })
  }

  Object.entries(attributes)
    .filter(([key, value]) => !handledAttributeKeys.has(key) && !Array.isArray(value) && !(value && typeof value === 'object') && hasStructuredDisplayValue(value))
    .forEach(([label, value]) => {
      overviewItems.push({ label, value: formatStructuredText(value, { inline: true }) })
      handledAttributeKeys.add(label)
    })

  if (overviewItems.length > 0) {
    sections.push({
      key: 'overview',
      title: '实体概览',
      kind: 'facts',
      items: overviewItems,
    })
  }

  if (Array.isArray(entity.relationships) && entity.relationships.length > 0) {
    sections.push({
      key: 'relationships',
      title: '关系网络',
      kind: 'cards',
      items: entity.relationships
        .filter(relationship => relationship && typeof relationship === 'object')
        .map((relationship, index) => ({
          id: `relationship_${index}`,
          title: String(relationship.target || '').trim() || `关系 ${index + 1}`,
          subtitle: String(relationship.type || '').trim(),
          description: String(relationship.description || '').trim(),
          fields: buildStructuredFieldItems(relationship, ['target', 'type', 'description']),
        }))
        .filter(item => item.title || item.description || item.fields.length > 0),
    })
  }

  if (Array.isArray(entity.stages) && entity.stages.length > 0) {
    sections.push({
      key: 'stages',
      title: '成长阶段',
      kind: 'cards',
      wide: true,
      items: entity.stages
        .filter(stage => stage && typeof stage === 'object')
        .map((stage, index) => ({
          id: stage.id || `stage_${index}`,
          title: String(stage.name || '').trim() || `阶段 ${index + 1}`,
          subtitle: String(stage.era || '').trim(),
          description: String(stage.description || '').trim(),
          fields: buildStructuredFieldItems(stage.attributes || {}),
        }))
        .filter(item => item.title || item.description || item.fields.length > 0),
    })
  }

  const specialArraySections = [
    {
      key: 'powerChanges',
      attrKey: '实力变化',
      title: '实力变化',
      wide: true,
      buildCard: (item, index) => ({
        id: `power_${index}`,
        title: [String(item['变化前'] || '').trim(), String(item['变化后'] || '').trim()].filter(Boolean).join(' -> ') || `实力变化 ${index + 1}`,
        subtitle: String(item['时间节点'] || '').trim(),
        description: String(item['描述'] || '').trim(),
        fields: buildStructuredFieldItems(item, ['变化前', '变化后', '时间节点', '描述']),
      }),
    },
    {
      key: 'personalityChanges',
      attrKey: '性格变化',
      title: '性格变化',
      wide: true,
      buildCard: (item, index) => ({
        id: `personality_${index}`,
        title: [String(item['变化前'] || '').trim(), String(item['变化后'] || '').trim()].filter(Boolean).join(' -> ') || `性格变化 ${index + 1}`,
        subtitle: String(item['时间节点'] || '').trim(),
        description: String(item['描述'] || '').trim(),
        fields: buildStructuredFieldItems(item, ['变化前', '变化后', '时间节点', '描述']),
      }),
    },
    {
      key: 'turningPoints',
      attrKey: '关键转折',
      title: '关键转折',
      wide: true,
      buildCard: (item, index) => ({
        id: `turning_${index}`,
        title: String(item['事件'] || item.name || '').trim() || `关键转折 ${index + 1}`,
        subtitle: String(item['时间节点'] || '').trim(),
        description: String(item['影响'] || item['描述'] || '').trim(),
        fields: buildStructuredFieldItems(item, ['事件', '时间节点', '影响', '描述']),
      }),
    },
  ]

  specialArraySections.forEach((sectionConfig) => {
    const sourceItems = Array.isArray(attributes[sectionConfig.attrKey]) ? attributes[sectionConfig.attrKey] : []
    if (!sourceItems.length) {
      return
    }

    sections.push({
      key: sectionConfig.key,
      title: sectionConfig.title,
      kind: 'cards',
      wide: sectionConfig.wide,
      items: sourceItems
        .filter(item => item && typeof item === 'object')
        .map(sectionConfig.buildCard)
        .filter(item => item.title || item.description || item.fields.length > 0),
    })
  })

  Object.entries(attributes)
    .filter(([key, value]) => !handledAttributeKeys.has(key) && (Array.isArray(value) || (value && typeof value === 'object')) && hasStructuredDisplayValue(value))
    .forEach(([key, value]) => {
      if (Array.isArray(value)) {
        sections.push({
          key: `extra_${key}`,
          title: key,
          kind: 'cards',
          wide: value.length > 2,
          items: value.map((item, index) => {
            if (item && typeof item === 'object') {
              return {
                id: `${key}_${index}`,
                title: String(item.name || item.title || item['名称'] || item['事件'] || '').trim() || `${key} ${index + 1}`,
                subtitle: String(item['时间节点'] || item.time || item.date || item.type || '').trim(),
                description: String(item.description || item['描述'] || item.detail || item['影响'] || '').trim(),
                fields: buildStructuredFieldItems(item, ['name', 'title', '名称', '事件', '时间节点', 'time', 'date', 'type', 'description', '描述', 'detail', '影响']),
              }
            }

            return {
              id: `${key}_${index}`,
              title: `${key} ${index + 1}`,
              subtitle: '',
              description: formatStructuredText(item),
              fields: [],
            }
          }).filter(item => item.title || item.description || item.fields.length > 0),
        })
        return
      }

      sections.push({
        key: `extra_${key}`,
        title: key,
        kind: 'facts',
        wide: true,
        items: buildStructuredFieldItems(value),
      })
    })

  return sections.filter(section => {
    if (section.kind === 'text') {
      return Boolean(section.content)
    }
    return Array.isArray(section.items) && section.items.length > 0
  })
}

const findSettingForEntityRecord = (settings = [], entity = {}) => {
  const entityId = String(entity.id || '').trim()
  const settingId = String(entity.setting_item_id || '').trim()
  return settings.find(setting => {
    if (!setting || typeof setting !== 'object') return false
    if (settingId && String(setting.id || '') === settingId) return true
    if (entityId && String(setting.linkedEntityId || '') === entityId) return true
    return String(setting.name || '').trim() === String(entity.name || '').trim()
  }) || null
}

const TIMELINE_BASE_WIDTH = 2600
const TIMELINE_LANE_ROW_HEIGHT = 52
const TIMELINE_EVENT_ROW_HEIGHT = 58
const TIMELINE_STAGE_ROW_HEIGHT = 38
const TIMELINE_EVENT_LIMIT = 96
const TIMELINE_STAGE_LIMIT = 56
const TIMELINE_ISSUE_LIMIT = 8

const POLITICAL_ENTITY_KEYWORDS = [
  'organization', 'nation', 'state', 'kingdom', 'empire', 'dynasty', 'faction', 'government', 'alliance', 'church', 'tribe',
  '组织', '国家', '政权', '王朝', '帝国', '联盟', '教会', '部族', '势力', '团体', '联邦', '共和国', '公司', '公会'
]

const POLITICAL_TIME_RANGE_KEYS = ['timerange', '存续时间', '存在时间', '存在区间', '在位时间', '统治时间']
const POLITICAL_START_KEYS = ['start', 'startyear', '开始时间', '起始时间', '成立时间', '建立时间', '建国时间', '创立时间', '即位时间']
const POLITICAL_END_KEYS = ['end', 'endyear', '结束时间', '终止时间', '灭亡时间', '解散时间', '覆灭时间', '退位时间']

const normalizeTimelineText = (value) => String(value || '')
  .replace(/[，,]/g, '')
  .replace(/\s+/g, ' ')
  .trim()

const normalizeCalendarRatio = (value) => {
  let text = String(value || '1').trim()
  text = text.replace(/^×\s*/i, '').replace(/^x\s*/i, '').trim()
  return `×${text || '1'}`
}

const extractTimelineYears = (value, options = {}) => {
  const text = normalizeTimelineText(value)
  if (!text) {
    return []
  }

  if (/\d+\s*世纪/i.test(text) && !/\d{3,6}\s*年/.test(text)) {
    return []
  }

  const anchorYear = Number.isFinite(options.anchorYear) ? options.anchorYear : null
  const years = []
  const seen = new Set()
  const addYear = (year) => {
    if (!Number.isFinite(year)) return
    if (seen.has(year)) return
    seen.add(year)
    years.push(year)
  }

  if (/(元年|建城|建立|登基|称帝|开始|始于)/.test(text) && !/\d{3,6}\s*年(?!\s*前)/.test(text)) {
    addYear(0)
  }

  const wanBefore = text.match(/(\d+(?:\.\d+)?)\s*万\s*年\s*前/)
  if (wanBefore && anchorYear !== null) {
    addYear(Math.round(anchorYear - Number.parseFloat(wanBefore[1]) * 10000))
  }

  const beforeMatches = Array.from(text.matchAll(/(\d{2,6})\s*年\s*前/g))
  beforeMatches.forEach((match) => {
    if (anchorYear !== null) {
      addYear(anchorYear - Number.parseInt(match[1], 10))
    }
  })

  const explicitMatches = Array.from(text.matchAll(/([-+]?\d{3,6})\s*年(?!\s*前)/g))
  explicitMatches.forEach((match) => {
    let year = Number.parseInt(match[1], 10)
    if (Number.isNaN(year)) return
    const prefix = text.slice(Math.max(0, match.index - 6), match.index)
    if (!match[1].startsWith('-') && /(公元前|bc|bce)/i.test(prefix)) {
      year = -Math.abs(year)
    }
    addYear(year)
  })

  const bareMatches = Array.from(text.matchAll(/[-+]?\d{3,6}/g))
  bareMatches.forEach((match) => {
    const index = match.index || 0
    const after = text.slice(index + match[0].length, index + match[0].length + 2)
    const before = text.slice(Math.max(0, index - 3), index)
    if (/[月日天周章卷部]/.test(after)) return
    if (/第\s*$/.test(before) && /纪/.test(after)) return
    let year = Number.parseInt(match[0], 10)
    if (Number.isNaN(year)) return
    if (!match[0].startsWith('-') && /(公元前|bc|bce)/i.test(text.slice(Math.max(0, index - 8), index))) {
      year = -Math.abs(year)
    }
    addYear(year)
  })

  return years
}

const parseTimelineYear = (value, options = {}) => {
  const text = String(value || '').trim()
  if (!text) {
    return null
  }

  const years = extractTimelineYears(text, options)
  return years.length ? years[0] : null
}

const formatTimelineYear = (value) => {
  if (!Number.isFinite(value)) {
    return '未知'
  }

  return value < 0 ? `前${Math.abs(value)}` : `${value}`
}

const parseTimelineRange = (value, options = {}) => {
  const text = String(value || '').trim()
  if (!text) {
    return null
  }

  const years = extractTimelineYears(text, options)
  if (!years.length) {
    return null
  }

  return {
    start: years[0],
    end: years.length > 1 ? years[1] : null,
    openEnded: /(至今|现在|当前|ongoing|present|无结束)/i.test(text) || years.length === 1,
  }
}

const inferCalendarTimelineType = (calendar = {}) => {
  const rawType = String(calendar.type || '').trim()
  const name = String(calendar.name || '').trim()
  const text = [name, calendar.timeRange, calendar.baseTime, calendar.description].map(item => String(item || '')).join(' ')

  if (/纪年/.test(rawType) || /(王历|王国历|通用历|标准纪年|建城|年数|历法|历$|公历|纪年)/.test(text)) {
    if (!/(第一纪|第二纪|第三纪|第四纪|第五纪|纪元|年代|时代)/.test(name)) {
      return '纪年'
    }
  }

  if (/(纪元|第一纪|第二纪|第三纪|第四纪|第五纪|年代|时代|大灾变|萌芽|初耀|双生|纷争|黑暗纪|灾难纪)/.test(text)) {
    return '纪元'
  }

  return rawType.includes('纪年') ? '纪年' : '纪元'
}

const assessCalendarTimelineIssue = (calendar = {}, years = []) => {
  const name = String(calendar.name || '').trim()
  const text = [name, calendar.timeRange, calendar.baseTime, calendar.description, calendar.unit].map(item => String(item || '')).join(' ')

  if (/^(未知|未明确|不明|无具体历法|未知历法)$/i.test(name)) {
    return '名称无法指向稳定历法'
  }

  if (/(周一到周日|月亮弥撒|红月周期|每周|每月|满月|节日|弥撒)/.test(text)) {
    return '更像周期或节日，不进入主时间轴'
  }

  if (!years.length) {
    return '缺少可定位年份'
  }

  if (/(未知|未明确|不明|推测|可推断|未提及具体)/.test(text)) {
    return '区间或来源低置信'
  }

  return ''
}

const buildCalendarTimelineItem = (calendar = {}, index = 0, anchorYear = null) => {
  const parsedRange = parseTimelineRange(calendar.timeRange, { anchorYear })
  const rangeYears = parsedRange ? [parsedRange.start, parsedRange.end].filter(Number.isFinite) : []
  const baseYear = parseTimelineYear(calendar.baseTime, { anchorYear })
  const years = [...extractTimelineYears(calendar.baseTime, { anchorYear }), ...rangeYears]
  const issue = assessCalendarTimelineIssue(calendar, years)

  if (issue === '更像周期或节日，不进入主时间轴' || !years.length) {
    return null
  }

  const start = Number.isFinite(baseYear) ? baseYear : parsedRange?.start
  if (!Number.isFinite(start)) {
    return null
  }

  let end = Number.isFinite(parsedRange?.end) ? parsedRange.end : null
  if (!Number.isFinite(end) && Number.isFinite(baseYear) && Number.isFinite(parsedRange?.start) && parsedRange.start !== baseYear) {
    end = parsedRange.start
  }
  if (!Number.isFinite(end) && parsedRange?.openEnded && Number.isFinite(anchorYear) && anchorYear > start) {
    end = anchorYear
  }
  if (!Number.isFinite(end)) {
    end = start + 1
  }
  if (end < start) {
    const swap = end
    end = start
    return {
      id: calendar.id || `calendar_${index}`,
      name: String(calendar.name || '未命名历法').trim(),
      caption: `${inferCalendarTimelineType(calendar)} · ${calendar.timeRange || calendar.baseTime || '未定义区间'}`,
      start: swap,
      end,
      kind: inferCalendarTimelineType(calendar) === '纪年' ? 'year' : 'era',
      issue,
      source: calendar,
    }
  }

  return {
    id: calendar.id || `calendar_${index}`,
    name: String(calendar.name || '未命名历法').trim(),
    caption: `${inferCalendarTimelineType(calendar)} · ${calendar.timeRange || calendar.baseTime || '未定义区间'}`,
    start,
    end,
    kind: inferCalendarTimelineType(calendar) === '纪年' ? 'year' : 'era',
    issue,
    source: calendar,
  }
}

const getTimelineEventDateText = (event = {}) => {
  const estimated = String(event.estimated_date || '').trim()
  const date = String(event.date || '').trim()
  if (estimated && !/^(未知|unknown)$/i.test(estimated)) return estimated
  return date
}

const buildTimelineEventItem = (event = {}, index = 0, anchorYear = null) => {
  const dateText = getTimelineEventDateText(event)
  const year = parseTimelineYear(dateText, { anchorYear })
  if (!Number.isFinite(year)) {
    return null
  }

  const entities = Array.isArray(event.entities) ? event.entities.map(item => String(item || '').trim()).filter(Boolean) : []
  return {
    id: event.id || `event_${index}_${String(event.name || '').slice(0, 12)}`,
    name: String(event.name || '未命名事件').trim(),
    year,
    label: `${formatTimelineYear(year)}年`,
    dateText,
    description: String(event.description || '').trim(),
    entities,
    weight: entities.length + (String(event.date || '').trim() ? 3 : 0) + (String(event.description || '').length > 40 ? 1 : 0),
    source: event,
  }
}

const buildTimelineStageItem = (entity = {}, stage = {}, index = 0, anchorYear = null) => {
  const era = String(stage.era || '').trim()
  const year = parseTimelineYear(era, { anchorYear })
  if (!Number.isFinite(year)) {
    return null
  }

  return {
    id: stage.id || `stage_${entity.id || entity.name || index}_${index}`,
    entityName: String(entity.name || '未命名实体').trim(),
    entityType: String(entity.type || '实体').trim(),
    name: String(stage.name || '阶段').trim(),
    year,
    label: `${formatTimelineYear(year)}年`,
    era,
    description: String(stage.description || '').trim(),
    weight: String(stage.description || '').length + (entity.type === '人物' ? 12 : 0),
    source: { entity, stage },
  }
}

const getAttributeValueByKeys = (attributes, keys) => {
  if (!attributes || typeof attributes !== 'object') {
    return ''
  }

  for (const [rawKey, rawValue] of Object.entries(attributes)) {
    const normalizedKey = String(rawKey || '').trim().toLowerCase()
    if (!normalizedKey) {
      continue
    }
    if (keys.some(key => normalizedKey === key || normalizedKey.includes(key))) {
      return String(rawValue || '').trim()
    }
  }

  return ''
}

const isPoliticalEntity = (entity) => {
  const typeText = String(entity?.type || '').trim().toLowerCase()
  const nameText = String(entity?.name || '').trim().toLowerCase()
  return POLITICAL_ENTITY_KEYWORDS.some(keyword => typeText.includes(keyword) || nameText.includes(keyword))
}

const buildPoliticalEntitySpan = (entity, index) => {
  if (!entity || !isPoliticalEntity(entity)) {
    return null
  }

  const attributes = entity.attributes && typeof entity.attributes === 'object' ? entity.attributes : {}
  const rangeValue = getAttributeValueByKeys(attributes, POLITICAL_TIME_RANGE_KEYS)
  const parsedRange = parseTimelineRange(rangeValue)
  const startValue = getAttributeValueByKeys(attributes, POLITICAL_START_KEYS)
  const endValue = getAttributeValueByKeys(attributes, POLITICAL_END_KEYS)

  const start = parsedRange?.start ?? parseTimelineYear(startValue)
  const end = parsedRange?.end ?? parseTimelineYear(endValue)
  const resolvedStart = Number.isFinite(start) ? start : end

  if (!Number.isFinite(resolvedStart)) {
    return null
  }

  return {
    id: entity.id || `political_entity_${index}`,
    name: String(entity.name || '未命名政治实体').trim(),
    type: String(entity.type || '政治实体').trim(),
    description: rangeValue || [startValue, endValue].filter(Boolean).join(' ~ '),
    start: resolvedStart,
    end: Number.isFinite(end) ? end : Infinity,
    openEnded: !Number.isFinite(end),
  }
}

const normalizeSettingCategory = (value) => {
  const text = String(value || '').trim().toLowerCase()
  if (!text) {
    return 'other'
  }

  if (text.includes('char') || text.includes('人物') || text.includes('角色') || text.includes('种族')) return 'character'
  if (text.includes('item') || text.includes('物品') || text.includes('道具') || text.includes('科技') || text.includes('装备')) return 'item'
  if (text.includes('orga') || text.includes('组织') || text.includes('势力') || text.includes('国家') || text.includes('政权')) return 'organization'
  if (text.includes('geo') || text.includes('地理') || text.includes('地点') || text.includes('区域') || text.includes('城市')) return 'geography'
  if (text.includes('ability') || text.includes('能力') || text.includes('魔法') || text.includes('规则') || text.includes('体系')) return 'ability'
  return 'other'
}

const normalizeAliases = (aliases) => {
  if (Array.isArray(aliases)) {
    return aliases.map(alias => String(alias || '').trim()).filter(Boolean)
  }
  if (typeof aliases === 'string') {
    return aliases
      .split(/[、,，/|]/)
      .map(alias => alias.trim())
      .filter(Boolean)
  }
  return []
}

const getCategoryMeta = (categoryId) => SETTING_CATEGORY_OPTIONS.find(category => category.id === categoryId) || SETTING_CATEGORY_OPTIONS[SETTING_CATEGORY_OPTIONS.length - 1]

const normalizeSettingsForUi = (settings = []) => {
  const normalizedCollections = []
  const normalizedItems = []
  const collectionsByCategory = new Map()

  settings.forEach((setting, index) => {
    if (!setting || typeof setting !== 'object') {
      return
    }

    const category = normalizeSettingCategory(setting.category)
    const settingType = setting.settingType === 'collection' ? 'collection' : 'setting'
    const normalizedSetting = {
      ...setting,
      id: setting.id || createLocalId(settingType, index),
      category,
      settingType,
      name: String(setting.name || '').trim(),
      collectionId: setting.collectionId || setting.parentCollection || '',
      description: String(setting.description || setting.detailContent || '').trim(),
      aliases: normalizeAliases(setting.aliases),
      detailContent: String(setting.detailContent || setting.description || '').trim(),
      linkedEntityId: String(setting.linkedEntityId || setting.entityId || '').trim(),
      sourceType: String(setting.sourceType || '').trim(),
      autoGenerated: Boolean(setting.autoGenerated),
    }

    if (!normalizedSetting.name) {
      return
    }

    if (settingType === 'collection') {
      normalizedSetting.expanded = setting.expanded !== false
      normalizedCollections.push(normalizedSetting)
      collectionsByCategory.set(category, normalizedSetting)
    } else {
      normalizedItems.push(normalizedSetting)
    }
  })

  normalizedItems.forEach((setting, index) => {
    if (!setting.collectionId) {
      let collection = collectionsByCategory.get(setting.category)
      if (!collection) {
        const categoryMeta = getCategoryMeta(setting.category)
        collection = {
          id: createLocalId(`collection_${setting.category}`, index),
          name: `${categoryMeta.name}设定集`,
          settingType: 'collection',
          category: setting.category,
          expanded: true,
          description: `${categoryMeta.name}相关设定`,
          aliases: [],
          detailContent: `${categoryMeta.name}相关设定`,
        }
        collectionsByCategory.set(setting.category, collection)
        normalizedCollections.push(collection)
      }
      setting.collectionId = collection.id
    }
  })

  return [...normalizedCollections, ...normalizedItems]
}

const normalizeCalendarsForUi = (calendars = []) => calendars
  .filter(calendar => calendar && typeof calendar === 'object')
  .map((calendar, index) => {
    const startYear = String(calendar.baseTime || calendar.startYear || '').trim()
    const endYear = String(calendar.endYear || '').trim()
    const rawRange = String(calendar.timeRange || '').trim()
    const timeRange = rawRange || (startYear ? `${startYear} ~ ${endYear || '无'}` : '')
    const normalizedCalendar = {
      ...calendar,
      id: calendar.id || createLocalId('calendar', index),
      name: String(calendar.name || '').trim(),
      rawType: String(calendar.type || '').trim(),
      baseTime: startYear,
      timeRange,
      unit: String(calendar.unit || '年').trim() || '年',
      ratio: normalizeCalendarRatio(calendar.ratio),
      calendarType: String(calendar.calendarType || '未开启').trim() || '未开启',
      description: String(calendar.description || '').trim(),
    }

    return {
      ...normalizedCalendar,
      type: inferCalendarTimelineType(normalizedCalendar),
    }
  })
  .filter(calendar => calendar.name)

const mergeMultilineText = (...values) => {
  const lines = []
  values.forEach(value => {
    String(value || '')
      .split(/\n+/)
      .map(line => line.trim())
      .filter(Boolean)
      .forEach(line => {
        if (!lines.includes(line)) {
          lines.push(line)
        }
      })
  })
  return lines.join('\n')
}

const mergeTextValue = (currentValue, incomingValue) => {
  const currentText = String(currentValue || '').trim()
  const incomingText = String(incomingValue || '').trim()

  if (!incomingText) {
    return currentText
  }

  if (!currentText) {
    return incomingText
  }

  if (currentText === incomingText) {
    return currentText
  }

  if (currentText.includes(incomingText)) {
    return currentText
  }

  if (incomingText.includes(currentText)) {
    return incomingText
  }

  return mergeMultilineText(currentText, incomingText)
}

const preferIncomingText = (currentValue, incomingValue) => {
  const currentText = String(currentValue || '').trim()
  const incomingText = String(incomingValue || '').trim()

  if (!incomingText) {
    return currentText
  }

  if (!currentText) {
    return incomingText
  }

  const placeholderPattern = /^(未命名|未定义|未知|暂无|待定|无|none|null|unknown)$/i
  if (placeholderPattern.test(currentText)) {
    return incomingText
  }

  return currentText
}

const isMeaningfulEventTime = (value) => {
  const text = String(value || '').trim().toLowerCase()
  return Boolean(text) && !['unknown', '未知', '未定义', 'none', 'null'].includes(text)
}

const mergeArrayValues = (currentValues = [], incomingValues = []) => {
  const merged = []
  const seen = new Set()

  ;[...currentValues, ...incomingValues].forEach((value) => {
    if (value == null) {
      return
    }
    const key = typeof value === 'object' ? JSON.stringify(value) : String(value)
    if (seen.has(key)) {
      return
    }
    seen.add(key)
    merged.push(value)
  })

  return merged
}

const mergePlainObjectValues = (currentValue = {}, incomingValue = {}) => {
  if (!currentValue || typeof currentValue !== 'object' || Array.isArray(currentValue)) {
    return incomingValue && typeof incomingValue === 'object' && !Array.isArray(incomingValue) ? { ...incomingValue } : {}
  }

  if (!incomingValue || typeof incomingValue !== 'object' || Array.isArray(incomingValue)) {
    return { ...currentValue }
  }

  const merged = { ...currentValue }
  Object.entries(incomingValue).forEach(([key, value]) => {
    const existingValue = merged[key]

    if (Array.isArray(existingValue) && Array.isArray(value)) {
      merged[key] = mergeArrayValues(existingValue, value)
      return
    }

    if (
      existingValue && typeof existingValue === 'object' && !Array.isArray(existingValue)
      && value && typeof value === 'object' && !Array.isArray(value)
    ) {
      merged[key] = mergePlainObjectValues(existingValue, value)
      return
    }

    if (value == null || String(value).trim() === '') {
      return
    }

    if (existingValue == null || String(existingValue).trim() === '') {
      merged[key] = value
      return
    }

    merged[key] = mergeTextValue(existingValue, value)
  })

  return merged
}

const mergeStageRecords = (currentStages = [], incomingStages = []) => {
  const mergedByKey = new Map()

  ;[...currentStages, ...incomingStages].forEach((stage, index) => {
    if (!stage || typeof stage !== 'object' || !String(stage.name || '').trim()) {
      return
    }

    const nameKey = String(stage.name || '').trim().toLowerCase()
    const eraKey = String(stage.era || '').trim().toLowerCase()
    const key = `${nameKey}|${eraKey}`
    const existing = mergedByKey.get(key)

    if (!existing) {
      mergedByKey.set(key, {
        ...stage,
        id: stage.id || createLocalId('stage', index),
        name: String(stage.name || '').trim(),
        era: String(stage.era || '').trim(),
        description: String(stage.description || '').trim(),
        attributes: mergePlainObjectValues({}, stage.attributes),
        setting_item_id: String(stage.setting_item_id || '').trim(),
        source: mergePlainObjectValues({}, stage.source),
      })
      return
    }

    mergedByKey.set(key, {
      ...existing,
      ...stage,
      id: existing.id || stage.id || createLocalId('stage', index),
      name: preferIncomingText(existing.name, stage.name),
      era: preferIncomingText(existing.era, stage.era),
      description: mergeTextValue(existing.description, stage.description),
      attributes: mergePlainObjectValues(existing.attributes, stage.attributes),
      setting_item_id: String(existing.setting_item_id || stage.setting_item_id || '').trim(),
      source: mergePlainObjectValues(existing.source, stage.source),
    })
  })

  return Array.from(mergedByKey.values())
}

const mergeEntityRecords = (currentEntities = [], incomingEntities = []) => {
  const mergedByKey = new Map()

  const getEntityKeys = (entity) => {
    const idKey = String(entity.id || '').trim()
    const nameKey = String(entity.name || '').trim().toLowerCase()
    const typeKey = String(entity.type || '').trim().toLowerCase()
    const keys = []
    if (idKey) {
      keys.push(`id:${idKey}`)
    }
    if (nameKey) {
      keys.push(`name:${nameKey}|type:${typeKey}`)
      keys.push(`name:${nameKey}`)
    }
    normalizeAliases(entity.aliases).forEach((alias) => {
      const aliasKey = String(alias || '').trim().toLowerCase()
      if (aliasKey) {
        keys.push(`alias:${aliasKey}|type:${typeKey}`)
        keys.push(`alias:${aliasKey}`)
      }
    })
    return keys
  }

  const putEntity = (entity, index) => {
    if (!entity || typeof entity !== 'object' || !String(entity.name || '').trim()) {
      return
    }

    const normalizedEntity = normalizeEntitiesForUi([entity])[0]
    if (!normalizedEntity) {
      return
    }

    const keys = getEntityKeys(normalizedEntity)
    const existingKey = keys.find(key => mergedByKey.has(key))
    const existing = existingKey ? mergedByKey.get(existingKey) : null

    if (!existing) {
      const createdEntity = {
        ...normalizedEntity,
        id: normalizedEntity.id || createLocalId('entity', index),
        name: String(normalizedEntity.name || '').trim(),
        type: String(normalizedEntity.type || '').trim(),
        aliases: normalizeAliases(normalizedEntity.aliases),
        attributes: mergePlainObjectValues({}, normalizedEntity.attributes),
        stages: mergeStageRecords([], normalizedEntity.stages),
        relationships: mergeArrayValues([], normalizedEntity.relationships),
        evolution_refs: mergeArrayValues([], normalizedEntity.evolution_refs),
        setting_item_id: String(normalizedEntity.setting_item_id || '').trim(),
      }

      keys.forEach(key => mergedByKey.set(key, createdEntity))
      return
    }

    const mergedEntity = {
      ...existing,
      ...normalizedEntity,
      id: existing.id || normalizedEntity.id || createLocalId('entity', index),
      name: preferIncomingText(existing.name, normalizedEntity.name),
      type: preferIncomingText(existing.type, normalizedEntity.type),
      aliases: mergeArrayValues(normalizeAliases(existing.aliases), normalizeAliases(normalizedEntity.aliases)),
      attributes: mergePlainObjectValues(existing.attributes, normalizedEntity.attributes),
      stages: mergeStageRecords(existing.stages, normalizedEntity.stages),
      relationships: mergeArrayValues(existing.relationships, normalizedEntity.relationships),
      evolution_refs: mergeArrayValues(existing.evolution_refs, normalizedEntity.evolution_refs),
      setting_item_id: String(existing.setting_item_id || normalizedEntity.setting_item_id || '').trim(),
    }

    keys.forEach(key => mergedByKey.set(key, mergedEntity))
  }

  currentEntities.forEach(putEntity)
  incomingEntities.forEach((entity, index) => putEntity(entity, currentEntities.length + index))

  const uniqueEntities = []
  const seenIds = new Set()
  mergedByKey.forEach((entity) => {
    const idKey = String(entity.id || entity.name || '').trim().toLowerCase()
    if (!idKey || seenIds.has(idKey)) {
      return
    }
    seenIds.add(idKey)
    uniqueEntities.push(entity)
  })

  return normalizeEntitiesForUi(uniqueEntities)
}

const mergeEventRecords = (currentEvents = [], incomingEvents = []) => {
  const mergedByKey = new Map()

  const getEventKeys = (event) => {
    const idKey = String(event.id || '').trim()
    const nameKey = String(event.name || '').trim().toLowerCase()
    const dateKey = String(event.date || '').trim().toLowerCase()
    const keys = []
    if (idKey) {
      keys.push(`id:${idKey}`)
    }
    if (nameKey) {
      keys.push(`name:${nameKey}|date:${dateKey}`)
      keys.push(`name:${nameKey}`)
    }
    return keys
  }

  const putEvent = (event, index) => {
    if (!event || typeof event !== 'object' || !String(event.name || '').trim()) {
      return
    }

    const normalizedEvent = {
      ...event,
      id: event.id || createLocalId('event', index),
      name: String(event.name || '').trim(),
      description: String(event.description || '').trim(),
      date: String(event.date || '').trim(),
      entities: Array.isArray(event.entities) ? event.entities.map(name => String(name || '').trim()).filter(Boolean) : [],
    }

    const keys = getEventKeys(normalizedEvent)
    const existingKey = keys.find(key => mergedByKey.has(key))
    const existing = existingKey ? mergedByKey.get(existingKey) : null

    if (!existing) {
      const createdEvent = {
        ...normalizedEvent,
        entities: mergeArrayValues([], normalizedEvent.entities),
      }

      keys.forEach(key => mergedByKey.set(key, createdEvent))
      return
    }

    const mergedEvent = {
      ...existing,
      ...normalizedEvent,
      id: existing.id || normalizedEvent.id || createLocalId('event', index),
      name: preferIncomingText(existing.name, normalizedEvent.name),
      description: mergeTextValue(existing.description, normalizedEvent.description),
      date: preferIncomingText(existing.date, normalizedEvent.date),
      time_type: isMeaningfulEventTime(existing.time_type) && !isMeaningfulEventTime(normalizedEvent.time_type)
        ? existing.time_type
        : (normalizedEvent.time_type || existing.time_type || 'unknown'),
      estimated_date: isMeaningfulEventTime(existing.estimated_date) && !isMeaningfulEventTime(normalizedEvent.estimated_date)
        ? existing.estimated_date
        : (normalizedEvent.estimated_date || existing.estimated_date || '未知'),
      entities: mergeArrayValues(existing.entities, normalizedEvent.entities),
    }

    keys.forEach(key => mergedByKey.set(key, mergedEvent))
  }

  currentEvents.forEach(putEvent)
  incomingEvents.forEach((event, index) => putEvent(event, currentEvents.length + index))

  const uniqueEvents = []
  const seenIds = new Set()
  mergedByKey.forEach((event) => {
    const idKey = String(event.id || event.name || '').trim().toLowerCase()
    if (!idKey || seenIds.has(idKey)) {
      return
    }
    seenIds.add(idKey)
    uniqueEvents.push(event)
  })

  return uniqueEvents
}

// 实体类型 → 设定分类映射
const ENTITY_TYPE_TO_SETTING_CATEGORY = {
  '人物': 'character', '角色': 'character', 'person': 'character', 'character': 'character',
  '种族': 'character', '生物': 'character',
  '国家': 'organization', '政权': 'organization', '组织': 'organization', '势力': 'organization',
  'nation': 'organization', 'organization': 'organization', 'faction': 'organization',
  '团体': 'organization', '教会': 'organization', '公司': 'organization', '公会': 'organization',
  '地点': 'geography', '位置': 'geography', '城市': 'geography', 'location': 'geography',
  'geography': 'geography', 'place': 'geography', '区域': 'geography',
  '物品': 'item', '道具': 'item', '装备': 'item', '武器': 'item', 'item': 'item',
  '能力': 'ability', '魔法': 'ability', '技能': 'ability', '体系': 'ability', 'ability': 'ability',
}

const entitiesToSettingsItems = (entities) => {
  if (!Array.isArray(entities)) return []
  return normalizeEntitiesForUi(entities)
    .filter(entity => entity && typeof entity === 'object' && String(entity.name || '').trim())
    .map(entity => {
      const name = String(entity.name || '').trim()
      const entityType = String(entity.type || '').trim()
      const category = ENTITY_TYPE_TO_SETTING_CATEGORY[entityType] || normalizeSettingCategory(entityType)

      const summary = buildEntitySettingSummary(entity)

      return {
        id: entity.setting_item_id || `setting_${entity.id}`,
        name,
        settingType: 'setting',
        category,
        description: summary.description || entityType,
        aliases: normalizeAliases(entity.aliases),
        detailContent: summary.detailContent || summary.description || entityType,
        linkedEntityId: entity.id,
        sourceType: 'entity',
        autoGenerated: true,
      }
    })
}

const normalizeExtractedSettings = (settings) => {
  const normalized = {
    items: createDefaultSettings(),
    mapData: createDefaultMapData(),
    calendars: createDefaultCalendars(),
  }

  if (!settings || typeof settings !== 'object') {
    return normalized
  }

  const _normalizeMapField = (value) => {
    if (Array.isArray(value)) {
      return value.map(item => {
        if (typeof item === 'object' && item !== null) {
          // {name, description} 结构 → "name: description"
          const label = String(item.name || item.title || '').trim()
          const desc = String(item.description || item.detail || '').trim()
          return label && desc ? `${label}：${desc}` : (label || desc)
        }
        return String(item || '').trim()
      }).filter(Boolean).join('\n')
    }
    if (typeof value === 'object' && value !== null) {
      // 对象值 → key-value 换行展开
      return Object.entries(value)
        .filter(([, v]) => v != null && String(v).trim())
        .map(([k, v]) => `${k}: ${String(v).trim()}`)
        .join('\n')
    }
    return String(value || '').trim()
  }

  const rawMapData = settings.mapData && typeof settings.mapData === 'object' ? settings.mapData : {}
  normalized.mapData = {
    regionRelations: _normalizeMapField(rawMapData.regionRelations || rawMapData['区域关系']),
    countryRelations: _normalizeMapField(rawMapData.countryRelations || rawMapData['国家关系'] || rawMapData['政区关系']),
    importantLocations: _normalizeMapField(rawMapData.importantLocations || rawMapData['重要地点'] || rawMapData['地理环境']),
  }

  const extractedItems = Array.isArray(settings.items) ? settings.items : []
  const fallbackItems = !Array.isArray(settings.items)
    ? Object.entries(settings)
      .filter(([key, value]) => !['items', 'mapData', 'calendars'].includes(key) && String(value || '').trim())
      .map(([key, value]) => ({
        name: key,
        settingType: 'setting',
        category: normalizeSettingCategory(key),
        description: String(value).trim(),
        aliases: [],
        detailContent: String(value).trim(),
      }))
    : []

  normalized.items = normalizeSettingsForUi([...extractedItems, ...fallbackItems])
  normalized.calendars = normalizeCalendarsForUi(Array.isArray(settings.calendars) ? settings.calendars : [])

  return normalized
}

const mergeSettingsByKey = (currentSettings = [], incomingSettings = []) => {
  const mergedByKey = new Map()

  ;[...currentSettings, ...incomingSettings].forEach((setting, index) => {
    if (!setting || typeof setting !== 'object' || !String(setting.name || '').trim()) {
      return
    }

    const category = normalizeSettingCategory(setting.category)
    const settingType = setting.settingType === 'collection' ? 'collection' : 'setting'
    const linkedEntityId = String(setting.linkedEntityId || setting.entityId || '').trim()
    const key = linkedEntityId
      ? `entity:${linkedEntityId}`
      : `${settingType}:${category}:${String(setting.name).trim().toLowerCase()}`
    const existing = mergedByKey.get(key)

    if (!existing) {
      mergedByKey.set(key, {
        ...setting,
        id: setting.id || createLocalId(settingType, index),
        category,
        settingType,
        aliases: normalizeAliases(setting.aliases),
        description: String(setting.description || setting.detailContent || '').trim(),
        detailContent: String(setting.detailContent || setting.description || '').trim(),
        linkedEntityId,
        sourceType: String(setting.sourceType || '').trim(),
        autoGenerated: Boolean(setting.autoGenerated),
      })
      return
    }

    mergedByKey.set(key, {
      ...existing,
      ...setting,
      id: existing.id || setting.id || createLocalId(settingType, index),
      category,
      settingType,
      collectionId: existing.collectionId || setting.collectionId,
      aliases: Array.from(new Set([...normalizeAliases(existing.aliases), ...normalizeAliases(setting.aliases)])),
      description: String(setting.description || existing.description || setting.detailContent || '').trim(),
      detailContent: String(setting.detailContent || existing.detailContent || setting.description || existing.description || '').trim(),
      linkedEntityId: linkedEntityId || existing.linkedEntityId || '',
      sourceType: String(setting.sourceType || existing.sourceType || '').trim(),
      autoGenerated: Boolean(setting.autoGenerated || existing.autoGenerated),
    })
  })

  return normalizeSettingsForUi(Array.from(mergedByKey.values()))
}

const syncEntitiesWithSettings = (entities = [], settings = []) => {
  const normalizedEntities = normalizeEntitiesForUi(entities)
  const normalizedSettings = normalizeSettingsForUi(settings).map(setting => ({ ...setting }))

  const hydratedEntities = normalizedEntities.map(entity => {
    const matchedSetting = findSettingForEntityRecord(normalizedSettings, entity)
    if (matchedSetting) {
      matchedSetting.linkedEntityId = matchedSetting.linkedEntityId || entity.id
      return {
        ...entity,
        setting_item_id: matchedSetting.id,
      }
    }
    return entity
  })

  const mergedSettings = mergeSettingsByKey(normalizedSettings, entitiesToSettingsItems(hydratedEntities))

  const syncedEntities = hydratedEntities.map(entity => {
    const matchedSetting = findSettingForEntityRecord(mergedSettings, entity)
    return matchedSetting
      ? {
          ...entity,
          setting_item_id: matchedSetting.id,
        }
      : entity
  })

  return {
    entities: syncedEntities,
    settings: mergedSettings,
  }
}

const mergeCalendarsByName = (currentCalendars = [], incomingCalendars = []) => {
  const mergedByName = new Map()

  ;[...currentCalendars, ...incomingCalendars].forEach((calendar, index) => {
    if (!calendar || typeof calendar !== 'object' || !String(calendar.name || '').trim()) {
      return
    }

    const key = String(calendar.name).trim().toLowerCase()
    const existing = mergedByName.get(key)
    const normalizedCalendar = normalizeCalendarsForUi([calendar])[0]
    if (!normalizedCalendar) {
      return
    }

    if (!existing) {
      mergedByName.set(key, normalizedCalendar)
      return
    }

    mergedByName.set(key, {
      ...existing,
      ...normalizedCalendar,
      id: existing.id || normalizedCalendar.id || createLocalId('calendar', index),
      description: normalizedCalendar.description || existing.description,
    })
  })

  return Array.from(mergedByName.values())
}

export default {
  name: 'WorldBuilderView',
  data() {
    return {
      worldId: '',
      linkedProjectId: '',
      linkedProjectStatus: '',
      isSaving: false,
      isDeleting: false,
      isProjectLaunching: false,
      isSavingLlmConfig: false,
      isTestingLlmConfig: false,
      saveStatus: '',
      extractError: '',
      showLlmConfigDialog: false,
      llmConfigFeedback: '',
      llmConfigFeedbackType: 'success',
      llmConfigStatus: {
        api_key_configured: false,
        api_key_masked: '',
        base_url: '',
        model_name: ''
      },
      llmConfig: {
        apiKey: '',
        baseUrl: '',
        modelName: ''
      },
      activeTab: 'basic',
      world: {
        name: '',
        description: '',
        era: '',
        anchor_time: '',
        writing_style: '',
        reference_text: ''
      },
      extractText: '',
      isExtracting: false,
      extractProgress: { stage: '', progress: 0, message: '' },
      extractPollTimer: null,
      extractedData: null,
      selectedFiles: [],
      isDragOver: false,
      entities: [],
      events: [],
      evolutionHistory: [],
      isLoadingEvolutionHistory: false,
      evolutionHistoryError: '',
      showEntitiesExpanded: true,
      showEventsExpanded: true,
      expandedBios: {},
      entityItems: [],
      eventItems: [],
      disabledEntityIds: new Set(),
      disabledEventIds: new Set(),
      showAddEntityDialog: false,
      showAddEventDialog: false,
      showEditEventDialog: false,
      newEntity: {
        name: '',
        type: '',
        customType: '',
        attributes: []
      },
      newEvent: {
        name: '',
        description: '',
        date: '',
        selectedSettings: []
      },
      mapData: createDefaultMapData(),
      // 时间线交互状态
      zoomLevel: 1,
      selectedEvent: null,
      timelineContainer: null,
      timelineCanvas: null,
      // 设定管理
      activeCategory: 'character',
      settingCategories: createDefaultSettingCategories(),
      settings: createDefaultSettings(),
      showNewSettingDialog: false,
      newSetting: {
        name: '',
        settingType: 'setting',
        showInList: true,
        category: '',
        aliases: [],
        parentCollection: '',
        description: '',
        newAlias: ''
      },
      currentSetting: null,
      showSettingDetail: false,
      showSettingSelector: false,
      selectedSettings: [],
      selectedCategoryFilter: 'all',
      showCalendarEdit: false,
      showCalendarDetailEdit: false,
      currentCalendar: null,
      calendars: createDefaultCalendars(),
      editCalendars: []
    }
  },
  computed: {
    // ====== 实体/事件 — 数据缓存 + v-memo 避免重复渲染 ======
    enabledEntityCount() {
      let count = 0
      for (const e of this.entities) {
        if (!this.disabledEntityIds.has(e.id || e.name)) count++
      }
      return count
    },
    enabledEventCount() {
      let count = 0
      for (const ev of this.events) {
        if (!this.disabledEventIds.has(ev.id || ev.name)) count++
      }
      return count
    },
    timelineCanvasStyle() {
      return {
        width: `${Math.max(1320, TIMELINE_BASE_WIDTH * this.zoomLevel)}px`,
        minHeight: this.timelineHeight,
      }
    },
    calendarSummaries() {
      return [...this.calendars].sort((a, b) => {
        const anchorYear = parseTimelineYear(this.world.anchor_time)
        const aStart = parseTimelineYear(a.baseTime || a.timeRange?.split(' ~ ')[0], { anchorYear }) ?? 0
        const bStart = parseTimelineYear(b.baseTime || b.timeRange?.split(' ~ ')[0], { anchorYear }) ?? 0
        return aStart - bStart
      })
    },
    timelineEraSummaries() {
      return this.calendarSummaries
        .filter(calendar => inferCalendarTimelineType(calendar) === '纪元')
        .slice(0, 8)
    },
    timelineYearSummaries() {
      return this.calendarSummaries
        .filter(calendar => inferCalendarTimelineType(calendar) === '纪年')
        .slice(0, 8)
    },
    calendarTimelineItems() {
      const anchorYear = parseTimelineYear(this.world.anchor_time)
      return this.calendars
        .map((calendar, index) => buildCalendarTimelineItem(calendar, index, anchorYear))
        .filter(Boolean)
        .sort((a, b) => a.start - b.start || a.end - b.end)
        .slice(0, 48)
    },
    calendarTimelineLayout() {
      return this.calculateSpanLayout(this.calendarTimelineItems)
    },
    timelineEventAnchors() {
      const anchorYear = parseTimelineYear(this.world.anchor_time)
      return (this.events || [])
        .map((event, index) => buildTimelineEventItem(event, index, anchorYear))
        .filter(Boolean)
    },
    timelineEventItems() {
      const groupedByYear = new Map()
      this.timelineEventAnchors.forEach(event => {
        const bucket = groupedByYear.get(event.year) || []
        bucket.push(event)
        groupedByYear.set(event.year, bucket)
      })

      const selected = []
      Array.from(groupedByYear.keys()).sort((a, b) => a - b).forEach(year => {
        const events = groupedByYear.get(year)
          .sort((a, b) => b.weight - a.weight || a.name.localeCompare(b.name, 'zh-Hans-CN'))
          .slice(0, 8)
        selected.push(...events)
      })

      return selected
        .sort((a, b) => a.year - b.year || b.weight - a.weight)
        .slice(0, TIMELINE_EVENT_LIMIT)
    },
    timelineEventLayout() {
      return this.calculatePointLayout(this.timelineEventItems, 5, 4)
    },
    timelineStageAnchors() {
      const anchorYear = parseTimelineYear(this.world.anchor_time)
      const stages = []
      ;(this.entities || []).forEach((entity) => {
        ;(entity.stages || []).forEach((stage, index) => {
          const item = buildTimelineStageItem(entity, stage, index, anchorYear)
          if (item) stages.push(item)
        })
      })
      return stages
    },
    timelineStageItems() {
      return [...this.timelineStageAnchors]
        .sort((a, b) => a.year - b.year || b.weight - a.weight)
        .slice(0, TIMELINE_STAGE_LIMIT)
    },
    timelineStageLayout() {
      return this.calculatePointLayout(this.timelineStageItems, 6, 3)
    },
    timelineIssueCalendars() {
      const anchorYear = parseTimelineYear(this.world.anchor_time)
      return this.calendars
        .map((calendar, index) => {
          const years = [
            ...extractTimelineYears(calendar.baseTime, { anchorYear }),
            ...extractTimelineYears(calendar.timeRange, { anchorYear }),
          ]
          const issue = assessCalendarTimelineIssue(calendar, years)
          return issue ? {
            id: calendar.id || `issue_${index}`,
            name: calendar.name || '未命名历法',
            issue,
          } : null
        })
        .filter(Boolean)
        .slice(0, TIMELINE_ISSUE_LIMIT)
    },
    timelineDiagnostics() {
      return {
        totalCalendars: this.calendars.length,
        usableCalendars: this.calendarTimelineItems.length,
        eventAnchors: this.timelineEventAnchors.length,
        visibleEvents: this.timelineEventItems.length,
        stageAnchors: this.timelineStageAnchors.length,
        visibleStages: this.timelineStageItems.length,
        noisyCalendars: this.timelineIssueCalendars.length,
      }
    },
    timelinePrimaryLabel() {
      const primary = this.calendarTimelineItems.find(item => item.kind === 'era') || this.calendarTimelineItems[0]
      if (primary) return primary.name
      return this.world.anchor_time || '未锚定'
    },
    timelineTicks() {
      const { min, max } = this.getTimeRange()
      const totalRange = Math.max(max - min, 1)
      return Array.from({ length: 6 }).map((_, index) => {
        const year = Math.round(min + (totalRange * index) / 5)
        return {
          label: `${formatTimelineYear(year)}年`,
          position: ((year - min) / totalRange) * 100,
        }
      })
    },
    timelineRangeLabels() {
      const { min, max } = this.getTimeRange()
      return {
        start: `${formatTimelineYear(min)}年`,
        end: `${formatTimelineYear(max)}年`,
      }
    },
    timelineCalendarTop() {
      return 126
    },
    timelineCalendarHeight() {
      return Math.max(this.getLayoutRowCount(this.calendarTimelineLayout), 1) * TIMELINE_LANE_ROW_HEIGHT + 8
    },
    timelineEventTop() {
      return this.timelineCalendarTop + this.timelineCalendarHeight + 72
    },
    timelineEventHeight() {
      return Math.max(this.getLayoutRowCount(this.timelineEventLayout), 1) * TIMELINE_EVENT_ROW_HEIGHT + 16
    },
    timelineStageTop() {
      return this.timelineEventTop + this.timelineEventHeight + 70
    },
    timelineStageHeight() {
      return Math.max(this.getLayoutRowCount(this.timelineStageLayout), 1) * TIMELINE_STAGE_ROW_HEIGHT + 16
    },
    filteredSettings() {
      return this.settings.filter(setting => setting.category === this.activeCategory)
    },
    settingCollections() {
      return this.settings.filter(setting => setting.settingType === 'collection')
    },
    filteredSettingsForSelection() {
      return this.settings.filter(setting => {
        // 只包含设定，不包含设定集
        if (setting.settingType !== 'setting') return false
        // 根据分类过滤
        if (this.selectedCategoryFilter !== 'all' && setting.category !== this.selectedCategoryFilter) return false
        return true
      })
    },
    currentSettingLinkedEntity() {
      if (!this.currentSetting) {
        return null
      }

      const linkedEntityId = String(this.currentSetting.linkedEntityId || '').trim()
      const currentSettingName = String(this.currentSetting.name || '').trim()

      return this.entities.find((entity) => {
        if (!entity || typeof entity !== 'object') {
          return false
        }

        const entityId = String(entity.id || '').trim()
        if (linkedEntityId && entityId === linkedEntityId) {
          return true
        }

        return currentSettingName && String(entity.name || '').trim() === currentSettingName
      }) || null
    },
    currentSettingStructuredSections() {
      if (!this.currentSettingLinkedEntity) {
        return []
      }

      return buildEntityDetailSections(this.currentSettingLinkedEntity)
    },
    currentSettingDetailLabel() {
      return this.currentSettingLinkedEntity ? '设定补充说明' : '详细内容'
    },
    hasRunnableProject() {
      return ['ontology_generated', 'graph_building', 'graph_completed'].includes(this.linkedProjectStatus)
    },
    hasLlmConfig() {
      return !!this.llmConfigStatus.api_key_configured
    },
    llmStatusText() {
      if (!this.hasLlmConfig) {
        return 'LLM 未配置，世界观提取不可用'
      }
      return `LLM 已配置，当前模型：${this.llmConfigStatus.model_name || '未指定'}`
    },
    projectActionLabel() {
      if (this.isProjectLaunching) {
        return '项目初始化中...'
      }
      if (this.hasRunnableProject) {
        return '打开关联项目'
      }
      if (this.linkedProjectId) {
        return '继续初始化项目'
      }
      return '创建推演项目'
    },
    // 计算时间线容器的高度，确保容纳语义时间带与事件层
    timelineHeight() {
      const totalHeight = this.timelineStageTop + this.timelineStageHeight + 86
      return Math.max(totalHeight, 520) + 'px'
    }
  },
  watch: {
    entities: {
      handler() { this._chunkBuildEntityItems() },
    },
    events: {
      handler() { this._chunkBuildEventItems() },
    },
    activeTab(newTab) {
      if (newTab === 'timeline') {
        this.$nextTick(() => {
          this.syncTimelineRefs()
          this.updateTimelineZoom()
        })
      }
      if (newTab === 'entities') {
        this.entityItems = []
        this.eventItems = []
        this.$nextTick(() => {
          this._chunkBuildEntityItems()
          this._chunkBuildEventItems()
        })
      }
    }
  },
  methods: {
    _chunkBuildEntityItems() {
      // 非阻塞分帧构建，每帧处理 12 个实体
      const entities = this.entities
      if (!entities.length) return

      // 一次性构建 entity→setting 映射（避免 computed 重复计算）
      const settingMap = {}
      const s = this.settings || []
      for (const entity of entities) {
        settingMap[entity.id || entity.name] = findSettingForEntityRecord(s, entity)
      }

      const CHUNK = 12
      let cursor = 0
      const result = []

      const processChunk = () => {
        const end = Math.min(cursor + CHUNK, entities.length)
        for (let i = cursor; i < end; i++) {
          const entity = entities[i]
          const attrs = entity.attributes || {}
          const id = entity.id || entity.name
          const simpleAttrs = {}
          const skip = ['简介', '实力变化', '性格变化', '关键转折', '阶段']
          for (const [k, v] of Object.entries(attrs)) {
            if (skip.includes(k)) continue
            if (Array.isArray(v)) continue
            if (typeof v === 'object' && v !== null) {
              simpleAttrs[k] = JSON.stringify(v, null, 1).slice(0, 200)
            } else if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') {
              simpleAttrs[k] = v
            }
          }
          const bio = attrs['简介'] || ''
          result.push({
            entity, id,
            simpleAttrs, simpleKeys: Object.keys(simpleAttrs),
            bio, hasBio: !!bio,
            bioExpanded: !!this.expandedBios[id],
            bioPreview: bio.slice(0, 120),
            powerChanges: Array.isArray(attrs['实力变化']) ? attrs['实力变化'] : [],
            personalityChanges: Array.isArray(attrs['性格变化']) ? attrs['性格变化'] : [],
            turningPoints: Array.isArray(attrs['关键转折']) ? attrs['关键转折'] : [],
            stages: Array.isArray(entity.stages) ? entity.stages : [],
            hasStages: (Array.isArray(entity.stages) ? entity.stages : []).length > 0,
            hasSetting: !!settingMap[id],
            enabled: !this.disabledEntityIds.has(id),
          })
        }
        cursor = end
        if (cursor < entities.length) {
          requestAnimationFrame(processChunk)
        } else {
          this.entityItems = result  // 全部完成，一次性提交，无闪烁
        }
      }
      requestAnimationFrame(processChunk)
    },
    _chunkBuildEventItems() {
      const events = this.events
      if (!events.length) return
      const CHUNK = 20
      let cursor = 0
      const result = []

      const processChunk = () => {
        const end = Math.min(cursor + CHUNK, events.length)
        for (let i = cursor; i < end; i++) {
          const ev = events[i]
          result.push({
            event: ev,
            id: ev.id || ev.name,
            enabled: !this.disabledEventIds.has(ev.id || ev.name),
          })
        }
        cursor = end
        if (cursor < events.length) {
          requestAnimationFrame(processChunk)
        } else {
          this.eventItems = result
        }
      }
      requestAnimationFrame(processChunk)
    },
    _rebuildEntityItems() {
      this._chunkBuildEntityItems()
    },
    _rebuildEventItems() {
      this._chunkBuildEventItems()
    },

    syncEntitySettingLinks() {
      const synced = syncEntitiesWithSettings(this.entities, this.settings)
      this.entities = synced.entities
      this.settings = synced.settings
      return synced
    },
    findSettingForEntity(entity) {
      return findSettingForEntityRecord(this.settings, entity)
    },
    openLinkedSetting(entity) {
      this.syncEntitySettingLinks()
      const setting = this.findSettingForEntity(entity)
      if (!setting) {
        alert('当前实体还没有对应的设定项，请先保存世界观或补充设定。')
        return
      }

      this.activeTab = 'settings'
      this.activeCategory = setting.category || 'other'
      this.viewSettingDetail(setting)
    },
    openEntitySettingByName(entityName) {
      const entity = this.entities.find(item => item.name === entityName)
      if (entity) {
        this.openLinkedSetting(entity)
      }
    },
    async loadEvolutionHistory(worldId = this.worldId) {
      if (!worldId) {
        this.evolutionHistory = []
        this.evolutionHistoryError = ''
        return
      }

      this.isLoadingEvolutionHistory = true
      this.evolutionHistoryError = ''
      try {
        const response = await service.get(`/api/evolution/world/${worldId}`)
        this.evolutionHistory = Array.isArray(response.evolutions) ? response.evolutions : []
      } catch (error) {
        console.error('加载推演记录失败:', error)
        this.evolutionHistory = []
        this.evolutionHistoryError = error.message || '加载推演记录失败'
      } finally {
        this.isLoadingEvolutionHistory = false
      }
    },
    openEvolutionRecord(record) {
      if (!record?.id) {
        return
      }
      this.$router.push({
        name: 'SimulationEvolution',
        params: { id: record.id }
      })
    },
    getEvolutionStatusLabel(status) {
      const labels = {
        created: '已创建',
        running: '进行中',
        completed: '已完成',
        failed: '失败',
      }
      return labels[status] || status || '未知'
    },
    getEvolutionTypeLabel(type) {
      const labels = {
        forward: '向后推演',
        branch: '分支推演',
      }
      return labels[type] || '推演'
    },
    formatDateTime(value) {
      if (!value) {
        return '未知时间'
      }

      const date = new Date(value)
      if (Number.isNaN(date.getTime())) {
        return String(value)
      }

      return new Intl.DateTimeFormat('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      }).format(date)
    },
    buildWorldPayload() {
      this.syncEntitySettingLinks()
      return {
        world_info: { ...this.world },
        settings: {
          items: this.settings,
          mapData: this.mapData,
          calendars: this.calendars
        },
        entities: this.entities,
        events: this.events,
        writing_style: this.world.writing_style || '',
        reference_text: this.world.reference_text || ''
      }
    },
    buildProjectPayload() {
      return {
        name: this.world.name || '未命名世界观项目',
        description: this.world.description || '',
        world_id: this.worldId,
        simulation_requirement: this.buildSimulationRequirement(),
        settings: {
          source_type: 'world_builder',
          source_world_id: this.worldId,
        }
      }
    },
    buildSimulationRequirement() {
      const worldName = this.world.name || '未命名世界观'
      const eraText = this.world.era ? `时代背景为${this.world.era}。` : ''
      const anchorText = this.world.anchor_time ? `关键锚点时间是${this.world.anchor_time}。` : ''

      return [
        `请基于世界观《${worldName}》构建用于世界观推演的知识图谱本体。`,
        '需要覆盖核心实体、组织、地点、关键事件、时间线与重要设定之间的关系，支持后续环境搭建、社会模拟与报告生成。',
        eraText,
        anchorText,
      ].filter(Boolean).join(' ')
    },
    buildLlmConfigPayload() {
      const payload = {
        base_url: (this.llmConfig.baseUrl || '').trim(),
        model_name: (this.llmConfig.modelName || '').trim()
      }

      if ((this.llmConfig.apiKey || '').trim()) {
        payload.api_key = this.llmConfig.apiKey.trim()
      }

      return payload
    },
    openLlmConfigDialog() {
      this.llmConfig = {
        apiKey: '',
        baseUrl: this.llmConfigStatus.base_url || 'https://api.openai.com/v1',
        modelName: this.llmConfigStatus.model_name || ''
      }
      this.llmConfigFeedback = ''
      this.llmConfigFeedbackType = 'success'
      this.showLlmConfigDialog = true
    },
    closeLlmConfigDialog() {
      this.showLlmConfigDialog = false
    },
    async loadLlmConfigStatus() {
      try {
        const response = await worldApi.getLlmConfig()
        this.llmConfigStatus = response.config || this.llmConfigStatus
        if (!this.llmConfig.baseUrl) {
          this.llmConfig.baseUrl = this.llmConfigStatus.base_url || 'https://api.openai.com/v1'
        }
        if (!this.llmConfig.modelName) {
          this.llmConfig.modelName = this.llmConfigStatus.model_name || ''
        }
      } catch (error) {
        console.error('加载 LLM 配置失败:', error)
      }
    },
    async saveLlmConfig() {
      this.isSavingLlmConfig = true
      this.llmConfigFeedback = ''

      try {
        const payload = this.buildLlmConfigPayload()
        const response = await worldApi.saveLlmConfig(payload)
        this.llmConfigStatus = response.config || this.llmConfigStatus
        this.llmConfig.apiKey = ''
        this.llmConfig.baseUrl = this.llmConfigStatus.base_url || this.llmConfig.baseUrl
        this.llmConfig.modelName = this.llmConfigStatus.model_name || this.llmConfig.modelName
        this.llmConfigFeedback = response.message || 'LLM 配置已保存'
        this.llmConfigFeedbackType = 'success'
      } catch (error) {
        console.error('保存 LLM 配置失败:', error)
        this.llmConfigFeedback = error.message || '保存配置失败'
        this.llmConfigFeedbackType = 'error'
      } finally {
        this.isSavingLlmConfig = false
      }
    },
    async testLlmConfigConnection() {
      this.isTestingLlmConfig = true
      this.llmConfigFeedback = ''

      try {
        const payload = this.buildLlmConfigPayload()
        const response = await worldApi.testLlmConfig(payload)
        this.llmConfigFeedback = response.message || 'LLM 连接测试成功'
        this.llmConfigFeedbackType = 'success'
        if (response.config) {
          this.llmConfigStatus = {
            ...this.llmConfigStatus,
            ...response.config
          }
        }
      } catch (error) {
        console.error('测试 LLM 配置失败:', error)
        this.llmConfigFeedback = error.message || 'LLM 连接测试失败'
        this.llmConfigFeedbackType = 'error'
      } finally {
        this.isTestingLlmConfig = false
      }
    },
    applyStoredWorld(world) {
      if (!world) {
        return
      }

      this.worldId = world.id || ''
      this.world = {
        name: world.name || '',
        description: world.description || '',
        era: world.era || '',
        anchor_time: world.anchor_time || '',
        writing_style: world.writing_style || '',
        reference_text: world.reference_text || ''
      }
      const normalizedEntities = normalizeEntitiesForUi(Array.isArray(world.entities) ? world.entities : [])
      this.entities = normalizedEntities
      this.events = Array.isArray(world.events) ? world.events : []

      const normalizedSettings = normalizeExtractedSettings(world.settings || {})
      // 从实体创建设定项，合并到 settings 中
      let mergedSettings = normalizedSettings.items
      if (normalizedEntities.length > 0) {
        const entitySettings = entitiesToSettingsItems(normalizedEntities)
        if (entitySettings.length > 0) {
          mergedSettings = mergeSettingsByKey(mergedSettings, entitySettings)
        }
      }
      const synced = syncEntitiesWithSettings(normalizedEntities, mergedSettings)
      this.entities = synced.entities
      this.settings = synced.settings
      this.mapData = { ...createDefaultMapData(), ...normalizedSettings.mapData }
      this.calendars = normalizedSettings.calendars
    },
    syncRouteWorldId() {
      if (!this.worldId || !this.$router || !this.$route) {
        return
      }

      this.$router.replace({
        query: {
          ...this.$route.query,
          worldId: this.worldId
        }
      })
    },
    async loadWorld(worldId) {
      if (!worldId) {
        return
      }

      try {
        const response = await worldApi.getWorld(worldId)
        this.applyStoredWorld(response.world)
        await this.loadLinkedProject(worldId)
        await this.loadEvolutionHistory(worldId)
        this.saveStatus = '已加载世界观'
      } catch (error) {
        console.error('加载世界观失败:', error)
        this.saveStatus = '加载失败'
      }
    },
    async loadLinkedProject(worldId = this.worldId) {
      this.linkedProjectId = ''
      this.linkedProjectStatus = ''

      if (!worldId) {
        return
      }

      try {
        const response = await projectApi.getProjects({ world_id: worldId, limit: 1 })
        const linkedProject = Array.isArray(response.projects) ? response.projects[0] : null

        if (linkedProject) {
          this.linkedProjectId = linkedProject.project_id || linkedProject.id || ''
          this.linkedProjectStatus = linkedProject.status || ''
        }
      } catch (error) {
        console.error('加载关联项目失败:', error)
      }
    },
    isEntityEnabled(entity) {
      const id = entity.id || entity.name
      return !this.disabledEntityIds.has(id)
    },
    toggleEntityEnabled(entity) {
      const id = entity.id || entity.name
      if (this.disabledEntityIds.has(id)) {
        this.disabledEntityIds.delete(id)
      } else {
        this.disabledEntityIds.add(id)
      }
      this.disabledEntityIds = new Set(this.disabledEntityIds)
      // Update cached items directly
      const item = this.entityItems.find(d => d.id === id)
      if (item) item.enabled = !this.disabledEntityIds.has(id)
    },
    isEventEnabled(event) {
      const id = event.id || event.name
      return !this.disabledEventIds.has(id)
    },
    toggleEventEnabled(event) {
      const id = event.id || event.name
      if (this.disabledEventIds.has(id)) {
        this.disabledEventIds.delete(id)
      } else {
        this.disabledEventIds.add(id)
      }
      this.disabledEventIds = new Set(this.disabledEventIds)
      const item = this.eventItems.find(d => d.id === id)
      if (item) item.enabled = !this.disabledEventIds.has(id)
    },
    // 实体属性渲染辅助方法
    isSimpleValue(val) {
      return typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean'
    },
    getSimpleAttrs(attrs) {
      const result = {}
      const skipKeys = ['简介', '实力变化', '性格变化', '关键转折', '阶段']
      for (const [key, val] of Object.entries(attrs || {})) {
        if (skipKeys.includes(key)) continue
        if (this.isSimpleValue(val)) {
          result[key] = val
        } else if (Array.isArray(val)) {
          continue
        } else if (typeof val === 'object' && val !== null) {
          // 嵌套对象：JSON 序列化，限制长度
          result[key] = JSON.stringify(val, null, 1).slice(0, 200)
        }
      }
      return result
    },
    getLongTextAttr(attrs) {
      if (!attrs) return ''
      return attrs['简介'] || ''
    },
    getArrayAttr(attrs, key) {
      if (!attrs) return []
      const val = attrs[key]
      return Array.isArray(val) ? val : []
    },
    getEntityCardId(entity) {
      return entity.id || entity.name || ''
    },
    isBioExpanded(entity) {
      const id = this.getEntityCardId(entity)
      return !!this.expandedBios[id]
    },
    toggleBioExpanded(entity) {
      const id = this.getEntityCardId(entity)
      this.$set(this.expandedBios, id, !this.expandedBios[id])
      const item = this.entityItems.find(d => d.id === id)
      if (item) item.bioExpanded = !!this.expandedBios[id]
    },
    async deleteWorld() {
      if (!this.worldId) return
      if (!confirm(`确定要删除世界观 "${this.world.name}" 吗？此操作不可恢复。`)) return

      this.isDeleting = true
      try {
        await worldApi.deleteWorld(this.worldId)
        // Navigate back to home
        this.$router.push({ name: 'Home' })
      } catch (e) {
        alert('删除失败: ' + (e.response?.data?.message || e.message || '未知错误'))
      } finally {
        this.isDeleting = false
      }
    },
    async ensureWorldId() {
      // 轻量确保 worldId 存在 — 仅 create + update，不加载 project/evolution
      if (this.worldId) return true
      try {
        const payload = this.buildWorldPayload()
        const createResponse = await worldApi.createWorld({
          ...this.world,
          settings: payload.settings
        })
        this.worldId = createResponse.world_id
        this.syncRouteWorldId()
        await worldApi.updateWorld(this.worldId, payload)
        this.saveStatus = '已保存'
        return true
      } catch (e) {
        console.warn('ensureWorldId 失败，RAG 索引将被跳过:', e)
        return false
      }
    },

    async saveWorld(options = {}) {
      const { silent = false, successMessage } = options
      this.isSaving = true

      try {
        const payload = this.buildWorldPayload()
        if (!this.worldId) {
          const createResponse = await worldApi.createWorld({
            ...this.world,
            settings: payload.settings
          })
          this.worldId = createResponse.world_id
          this.syncRouteWorldId()
        }

        const response = await worldApi.updateWorld(this.worldId, payload)
        this.applyStoredWorld(response.world)
        this.syncRouteWorldId()
        await this.loadLinkedProject(this.worldId)
        await this.loadEvolutionHistory(this.worldId)
        this.saveStatus = successMessage || '已保存'

        if (!silent) {
          alert(successMessage || '世界观保存成功！')
        }
      } catch (error) {
        console.error('保存世界观失败:', error)
        this.saveStatus = '保存失败'
        if (!silent) {
          alert('保存失败，请重试')
        }
      } finally {
        this.isSaving = false
      }
    },
    async launchProjectFromWorld() {
      if (this.isProjectLaunching) return
      this.isProjectLaunching = true
      this.saveStatus = '正在准备推演...'

      try {
        if (!this.worldId) {
          await this.saveWorld({ silent: true, successMessage: '世界观已保存' })
        }
        if (!this.worldId) {
          throw new Error('请先保存当前世界观')
        }

        this.saveStatus = '推演已就绪'
        this.$router.push({
          name: 'SimulationSetup',
          query: { worldId: this.worldId }
        })
      } catch (error) {
        console.error('启动推演失败:', error)
        this.saveStatus = '启动失败'
        alert('启动推演失败: ' + (error.message || ''))
      } finally {
        this.isProjectLaunching = false
      }
    },

    async extractWorldInfo() {
      const hasText = this.extractText.trim()
      const hasFiles = this.selectedFiles.length > 0
      if (!hasText && !hasFiles) return

      if (!this.hasLlmConfig) {
        this.extractError = '请先配置可用的 LLM API Key、Base URL 和 Model。'
        this.openLlmConfigDialog()
        return
      }

      this.isExtracting = true
      this.extractError = ''
      this.extractedData = null
      this.extractProgress = { stage: 'starting', progress: 0, message: '正在提交提取任务...' }
      try {
        // 如果没有 worldId，先轻量创建以便 RAG 自动索引
        const hasWorldId = await this.ensureWorldId()
        if (!hasWorldId && !this.worldId) {
          console.warn('世界观创建失败，提取将跳过 RAG 索引')
        }

        // 1. 提交提取任务（附带 worldId 用于自动 RAG 索引）
        let initResponse
        if (hasFiles) {
          const formData = new FormData()
          this.selectedFiles.forEach(file => {
            formData.append('files', file)
          })
          if (hasText) {
            formData.append('text', this.extractText)
          }
          initResponse = await worldApi.extractWorldFromFile(formData, this.worldId)
        } else {
          initResponse = await worldApi.extractWorld(this.extractText, this.worldId)
        }

        const taskId = initResponse.task_id
        if (!taskId) {
          // 可能是直接 JSON 数据返回
          this.extractedData = initResponse.extracted_data
          this.isExtracting = false
          return
        }

        // 2. 轮询进度（无超时限制，直到后端完成）
        const pollInterval = 1500

        const pollProgress = async () => {
          try {
            const progResp = await worldApi.getExtractProgress(taskId)
            this.extractProgress = {
              stage: progResp.stage || '',
              progress: progResp.progress || 0,
              message: progResp.message || '',
            }
            if (progResp.done) {
              if (progResp.extracted_data) {
                this.extractedData = progResp.extracted_data
              }
              if (progResp.error) {
                this.extractError = progResp.error
              }
              this.isExtracting = false
              return
            }
          } catch (e) {
            console.warn('进度轮询失败:', e)
          }
          if (this.isExtracting) {
            this.extractPollTimer = setTimeout(pollProgress, pollInterval)
          }
        }

        await pollProgress()
      } catch (error) {
        console.error('提取失败:', error)
        const serverMsg = error.response?.data?.message
        this.extractError = serverMsg || error.message || '提取失败，请重试'
        if (/api key|api_key|invalid_api_key|llm/i.test(this.extractError)) {
          this.openLlmConfigDialog()
        }
        this.isExtracting = false
      }
    },
    handleFileDrop(e) {
      this.isDragOver = false
      const files = e.dataTransfer?.files
      if (files) {
        this.addFiles(files)
      }
    },
    handleFileSelect(e) {
      const files = e.target?.files
      if (files) {
        this.addFiles(files)
      }
      // 重置 input 值以允许重新选择相同文件
      const input = this.$refs.fileInput
      if (input) {
        input.value = ''
      }
    },
    addFiles(fileList) {
      const textExts = ['pdf', 'md', 'markdown', 'txt']
      for (const file of fileList) {
        const ext = file.name.split('.').pop()?.toLowerCase()
        if (ext === 'json') {
          // JSON 文件走直接导入路径
          this.importJsonFile(file)
        } else if (textExts.includes(ext)) {
          // 文本文件走 LLM 提取
          if (!this.selectedFiles.some(f => f.name === file.name && f.size === file.size)) {
            this.selectedFiles.push(file)
          }
        }
      }
    },
    async importJsonFile(file) {
      try {
        const text = await file.text()
        const data = JSON.parse(text)
        if (!data || typeof data !== 'object') {
          this.extractError = 'JSON 文件内容无效'
          return
        }
        // 兼容已保存世界观格式
        if (!data.world_info && (data.name || data.description)) {
          data.world_info = {
            name: data.name || '',
            description: data.description || '',
            era: data.era || '',
            anchor_time: data.anchor_time || ''
          }
        }
        if (!data.entities && Array.isArray(data.entity_list)) {
          data.entities = data.entity_list
        }
        if (!data.events && Array.isArray(data.event_list)) {
          data.events = data.event_list
        }

        const hasWorldInfo = data.world_info && typeof data.world_info === 'object'
        const hasEntities = Array.isArray(data.entities)
        const hasEvents = Array.isArray(data.events)
        const hasSettings = data.settings && typeof data.settings === 'object'

        if (!hasWorldInfo && !hasEntities && !hasEvents && !hasSettings) {
          this.extractError = 'JSON 文件缺少有效的世界观数据'
          return
        }

        this.extractedData = data
        this.extractError = ''
      } catch (err) {
        console.error('JSON 导入失败:', err)
        this.extractError = 'JSON 解析失败: ' + (err.message || '格式错误')
      }
    },
    removeFile(index) {
      this.selectedFiles.splice(index, 1)
    },
    formatFileSize(bytes) {
      if (bytes < 1024) return bytes + ' B'
      if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
      return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
    },
    async handleJsonImport(e) {
      const file = e.target?.files?.[0]
      if (!file) return

      try {
        const text = await file.text()
        const data = JSON.parse(text)

        if (!data || typeof data !== 'object') {
          this.extractError = 'JSON 文件内容无效'
          return
        }

        // 兼容两种格式：提取结果格式 和 已保存世界观格式
        if (!data.world_info && (data.name || data.description)) {
          data.world_info = {
            name: data.name || '',
            description: data.description || '',
            era: data.era || '',
            anchor_time: data.anchor_time || ''
          }
        }
        if (!data.entities && Array.isArray(data.entity_list)) {
          data.entities = data.entity_list
        }
        if (!data.events && Array.isArray(data.event_list)) {
          data.events = data.event_list
        }

        const hasWorldInfo = data.world_info && typeof data.world_info === 'object'
        const hasEntities = Array.isArray(data.entities)
        const hasEvents = Array.isArray(data.events)
        const hasSettings = data.settings && typeof data.settings === 'object'

        if (!hasWorldInfo && !hasEntities && !hasEvents && !hasSettings) {
          this.extractError = 'JSON 文件缺少有效的世界观数据（需要 world_info / entities / events / settings 中至少一项）'
          return
        }

        this.extractedData = data
        this.extractError = ''
      } catch (err) {
        console.error('JSON 导入失败:', err)
        this.extractError = 'JSON 解析失败: ' + (err.message || '格式错误')
      } finally {
        const input = this.$refs.jsonFileInput
        if (input) {
          input.value = ''
        }
      }
    },
    async applyExtractedData() {
      if (this.extractedData) {
        // 将提取的数据应用到世界观
        const extractedWorldInfo = this.extractedData.world_info || {}
        const extractedWritingStyle = this.extractedData.writing_style || extractedWorldInfo.writing_style || ''
        const extractedReferenceText = this.extractedData.reference_text || extractedWorldInfo.reference_text || ''

        this.world = {
          ...this.world,
          name: preferIncomingText(this.world.name, extractedWorldInfo.name),
          description: mergeTextValue(this.world.description, extractedWorldInfo.description),
          era: preferIncomingText(this.world.era, extractedWorldInfo.era),
          anchor_time: preferIncomingText(this.world.anchor_time, extractedWorldInfo.anchor_time),
          writing_style: mergeTextValue(this.world.writing_style, extractedWritingStyle),
          reference_text: mergeTextValue(this.world.reference_text, extractedReferenceText),
        }

        if (this.extractedData.entities) {
          this.entities = mergeEntityRecords(this.entities, this.extractedData.entities)
          const entitySettings = entitiesToSettingsItems(this.entities)
          if (entitySettings.length > 0) {
            this.settings = mergeSettingsByKey(this.settings, entitySettings)
          }
        }
        if (this.extractedData.events) {
          this.events = mergeEventRecords(this.events, this.extractedData.events)
        }
        if (this.extractedData.settings) {
          const normalizedSettings = normalizeExtractedSettings(this.extractedData.settings)
          this.settings = mergeSettingsByKey(this.settings, normalizedSettings.items)
          this.mapData = {
            regionRelations: mergeMultilineText(this.mapData.regionRelations, normalizedSettings.mapData.regionRelations),
            countryRelations: mergeMultilineText(this.mapData.countryRelations, normalizedSettings.mapData.countryRelations),
            importantLocations: mergeMultilineText(this.mapData.importantLocations, normalizedSettings.mapData.importantLocations),
          }
          this.calendars = mergeCalendarsByName(this.calendars, normalizedSettings.calendars)
        }

        this.syncEntitySettingLinks()
        
        this.extractedData = null
        this.extractText = ''
        this.selectedFiles = []
        await this.saveWorld({ silent: false, successMessage: 'AI 提取结果已保存到世界观！' })
      }
    },
    addAttribute() {
      this.newEntity.attributes.push({ key: '', value: '' })
    },
    removeAttribute(index) {
      this.newEntity.attributes.splice(index, 1)
    },
    addEntity() {
      // 处理自定义类型
      let entityType = this.newEntity.type
      if (entityType === '自定义' && this.newEntity.customType) {
        entityType = this.newEntity.customType
      }
      
      // 转换属性数组为对象
      const attributes = {}
      this.newEntity.attributes.forEach(attr => {
        if (attr.key) {
          attributes[attr.key] = attr.value
        }
      })
      
      this.entities.push({
        id: Date.now() + Math.random(),
        name: this.newEntity.name,
        type: entityType,
        attributes: attributes,
        stages: [],
        setting_item_id: '',
        evolution_refs: [],
      })
      this.syncEntitySettingLinks()
      this.showAddEntityDialog = false
      this.newEntity = {
        name: '',
        type: '',
        customType: '',
        attributes: []
      }
    },
    deleteEntity(id) {
      this.entities = this.entities.filter(entity => entity.id !== id)
    },
    
    // 设定管理方法
    searchSettings() {
      console.log('搜索设定')
    },
    openNewSettingDialog() {
      this.newSetting = {
        name: '',
        settingType: 'setting',
        showInList: true,
        category: this.activeCategory,
        aliases: [],
        parentCollection: '',
        description: '',
        newAlias: ''
      }
      this.showNewSettingDialog = true
    },
    closeNewSettingDialog() {
      this.showNewSettingDialog = false
    },
    addAlias() {
      if (this.newSetting.newAlias.trim()) {
        this.newSetting.aliases.push(this.newSetting.newAlias.trim())
        this.newSetting.newAlias = ''
      }
    },
    removeAlias(index) {
      this.newSetting.aliases.splice(index, 1)
    },
    saveNewSetting() {
      const setting = {
        id: Date.now(),
        name: this.newSetting.name,
        settingType: this.newSetting.settingType,
        category: this.newSetting.category,
        collectionId: this.newSetting.parentCollection,
        description: this.newSetting.description,
        aliases: [...this.newSetting.aliases],
        showInList: this.newSetting.showInList,
        detailContent: ''
      }
      this.settings.push(setting)
      this.syncEntitySettingLinks()
      this.showNewSettingDialog = false
      alert('设定创建成功！')
    },
    
    // 展开/折叠分类
    toggleCategory(categoryId) {
      const category = this.settingCategories.find(cat => cat.id === categoryId)
      if (category) {
        const isActiveCategory = this.activeCategory === categoryId
        this.activeCategory = categoryId
        category.expanded = isActiveCategory ? !category.expanded : true
      }
    },
    toggleCollection(collectionId) {
      const collection = this.settings.find(setting => setting.id === collectionId && setting.settingType === 'collection')
      if (collection) {
        collection.expanded = !collection.expanded
      }
    },
    
    // 查看设定详情
    viewSettingDetail(setting) {
      this.currentSetting = JSON.parse(JSON.stringify(setting))
      this.showSettingDetail = true
    },
    
    // 关闭设定详情
    closeSettingDetail() {
      this.showSettingDetail = false
      this.currentSetting = null
    },
    
    // 保存设定详情
    saveSettingDetail() {
      const index = this.settings.findIndex(setting => setting.id === this.currentSetting.id)
      if (index !== -1) {
        this.settings[index] = JSON.parse(JSON.stringify(this.currentSetting))
      }
      this.syncEntitySettingLinks()
      this.showSettingDetail = false
      this.currentSetting = null
      alert('设定详情保存成功！')
    },
    
    // 根据分类获取设定集
    getCollectionsByCategory(categoryId) {
      return this.settings.filter(setting => setting.settingType === 'collection' && setting.category === categoryId)
    },
    
    // 根据设定集获取设定
    getSettingsByCollection(collectionId) {
      return this.settings.filter(setting => setting.settingType === 'setting' && setting.collectionId == collectionId)
    },
    addEvent() {
      const entities = this.newEvent.selectedSettings.map(settingId => {
        const setting = this.settings.find(s => s.id === settingId)
        return setting ? setting.name : ''
      }).filter(Boolean)
      
      this.events.push({
        id: Date.now() + Math.random(),
        name: this.newEvent.name,
        description: this.newEvent.description,
        date: this.newEvent.date,
        entities: entities
      })
      this.showAddEventDialog = false
      this.newEvent = {
        name: '',
        description: '',
        date: '',
        selectedSettings: []
      }
    },
    
    // 切换设定的选择状态
    toggleSetting(settingId) {
      const index = this.newEvent.selectedSettings.indexOf(settingId)
      if (index > -1) {
        this.newEvent.selectedSettings.splice(index, 1)
      } else {
        this.newEvent.selectedSettings.push(settingId)
      }
    },
    
    // 打开设定选择窗口
    openSettingSelector() {
      this.showSettingSelector = true
      this.selectedCategoryFilter = 'all'
    },
    
    // 关闭设定选择窗口
    closeSettingSelector() {
      this.showSettingSelector = false
    },
    
    // 切换设定选择状态
    toggleSettingSelection(settingId) {
      const index = this.selectedSettings.indexOf(settingId)
      if (index > -1) {
        this.selectedSettings.splice(index, 1)
      } else {
        this.selectedSettings.push(settingId)
      }
    },
    
    // 确认设定选择
    confirmSettingSelection() {
      // 这里可以根据需要处理选择的设定
      console.log('Selected settings:', this.selectedSettings)
      // 例如，将选择的设定应用到当前事件
      this.newEvent.selectedSettings = [...this.selectedSettings]
      this.showSettingSelector = false
    },
    
    // 移除已选择的设定
    removeSelectedSetting(settingId) {
      const index = this.newEvent.selectedSettings.indexOf(settingId)
      if (index > -1) {
        this.newEvent.selectedSettings.splice(index, 1)
      }
    },
    deleteEvent(id) {
      this.events = this.events.filter(event => event.id !== id)
    },
    
    // 更新事件
    updateEvent() {
      const entities = this.newEvent.selectedSettings.map(settingId => {
        const setting = this.settings.find(s => s.id === settingId)
        return setting ? setting.name : ''
      }).filter(Boolean)
      
      const index = this.events.findIndex(event => event.id === this.selectedEvent.id)
      if (index !== -1) {
        this.events[index] = {
          ...this.events[index],
          name: this.newEvent.name,
          description: this.newEvent.description,
          date: this.newEvent.date,
          entities: entities
        }
        this.showEditEventDialog = false
        this.selectedEvent = null
        alert('事件更新成功！')
      }
    },
    // 打开历法编辑窗口
    openCalendarEdit() {
      // 复制历法数据到编辑数组
      this.editCalendars = JSON.parse(JSON.stringify(this.calendars))
      this.showCalendarEdit = true
    },
    
    // 添加新历法
    addCalendar() {
      const newCalendar = {
        id: Date.now(),
        name: '',
        type: '纪元',
        baseTime: '',
        timeRange: '',
        unit: '年',
        ratio: '×1',
        calendarType: '未开启',
        description: ''
      }
      this.editCalendars.push(newCalendar)
      this.currentCalendar = {
        ...JSON.parse(JSON.stringify(newCalendar)),
        startYear: '',
        endYear: '',
        noEndTime: false,
        ratioValue: '1',
        customCalendar: false,
      }
      this.showCalendarDetailEdit = true
    },
    
    // 删除历法
    deleteCalendar(calendarId) {
      this.editCalendars = this.editCalendars.filter(calendar => calendar.id !== calendarId)
    },
    
    // 保存历法
    saveCalendars() {
      // 保存编辑后的历法数据
      this.calendars = JSON.parse(JSON.stringify(this.editCalendars))
      console.log('保存历法:', this.calendars)
      // 这里可以调用API保存历法数据
      alert('历法保存成功！')
      this.showCalendarEdit = false
    },
    
    // 取消编辑
    cancelCalendarEdit() {
      // 清空编辑数组，不保存任何更改
      this.editCalendars = []
      this.showCalendarEdit = false
    },
    
    // 编辑历法
    editCalendar(calendar) {
      // 复制历法数据到当前编辑对象
      this.currentCalendar = JSON.parse(JSON.stringify(calendar))
      // 解析时间范围
      if (calendar.timeRange) {
        const timeRange = calendar.timeRange.split(' ~ ')
        this.currentCalendar.startYear = timeRange[0] || calendar.baseTime || ''
        this.currentCalendar.noEndTime = timeRange[1] === '无'
        this.currentCalendar.endYear = this.currentCalendar.noEndTime ? '' : (timeRange[1] || '')
      } else {
        this.currentCalendar.startYear = calendar.baseTime || ''
        this.currentCalendar.endYear = ''
        this.currentCalendar.noEndTime = false
      }
      // 解析比例系数
      if (calendar.ratio) {
        this.currentCalendar.ratioValue = calendar.ratio.replace('×', '')
      } else {
        this.currentCalendar.ratioValue = '1'
      }
      this.currentCalendar.customCalendar = String(calendar.calendarType || '').trim() && calendar.calendarType !== '未开启'
      // 打开编辑窗口
      this.showCalendarDetailEdit = true
    },
    
    // 保存历法详情
    saveCalendarDetail() {
      const startYear = String(this.currentCalendar.startYear || '').trim()
      const endYear = String(this.currentCalendar.endYear || '').trim()
      const ratioValue = String(this.currentCalendar.ratioValue || '1').trim() || '1'
      const savedCalendar = {
        id: this.currentCalendar.id,
        name: String(this.currentCalendar.name || '').trim() || '未命名历法',
        type: String(this.currentCalendar.type || '纪元').trim() || '纪元',
        baseTime: startYear,
        timeRange: startYear
          ? `${startYear} ~ ${this.currentCalendar.noEndTime ? '无' : (endYear || startYear)}`
          : '',
        unit: String(this.currentCalendar.unit || '年').trim() || '年',
        ratio: `×${ratioValue.replace(/^×/, '')}`,
        calendarType: String(this.currentCalendar.calendarType || '未开启').trim() || '未开启',
        description: String(this.currentCalendar.description || '').trim(),
      }

      const index = this.editCalendars.findIndex(c => c.id === savedCalendar.id)
      if (index !== -1) {
        this.editCalendars.splice(index, 1, savedCalendar)
      } else {
        this.editCalendars.push(savedCalendar)
      }
      // 关闭编辑窗口
      this.showCalendarDetailEdit = false
      this.currentCalendar = null
    },
    
    // 取消编辑历法详情
    cancelCalendarDetailEdit() {
      // 清空当前编辑对象
      this.currentCalendar = null
      this.showCalendarDetailEdit = false
    },
    calculateSpanLayout(items) {
      const layout = new Map()
      const rowEnds = []

      ;[...items]
        .sort((a, b) => a.start - b.start)
        .forEach(item => {
          const start = Number.isFinite(item.start) ? item.start : 0
          const end = Number.isFinite(item.end) ? item.end : Infinity
          let row = 0

          while (row < rowEnds.length && rowEnds[row] > start) {
            row += 1
          }

          rowEnds[row] = end
          layout.set(item.id, { row, start, end })
        })

      return layout
    },

    calculatePointLayout(items, proximity = 4, maxRows = 4) {
      const layout = new Map()
      const rowPositions = Array.from({ length: maxRows }, () => -Infinity)
      const { min: minTime, max: maxTime } = this.getTimeRange()
      const totalRange = Math.max(maxTime - minTime, 1)

      ;[...items]
        .sort((a, b) => (a.year || 0) - (b.year || 0))
        .forEach(item => {
          const year = Number.isFinite(item.year) ? item.year : minTime
          const position = ((year - minTime) / totalRange) * 100
          let row = rowPositions.findIndex(lastPosition => Math.abs(position - lastPosition) >= proximity)
          if (row < 0) {
            row = rowPositions.indexOf(Math.min(...rowPositions))
          }
          rowPositions[row] = position
          layout.set(item.id, { row, position, year })
        })

      return layout
    },

    getLayoutRowCount(layout) {
      if (!layout || layout.size === 0) {
        return 0
      }

      return Math.max(...Array.from(layout.values()).map(item => item.row)) + 1
    },

    getTimelineBandStyle(item, layout, index, topOffset, paletteSet) {
      const layoutInfo = layout.get(item.id)
      if (!layoutInfo) {
        return {}
      }

      const { min: minTime, max: maxTime } = this.getTimeRange()
      const totalRange = Math.max(maxTime - minTime, 1)
      const left = ((layoutInfo.start - minTime) / totalRange) * 100
      const effectiveEnd = layoutInfo.end === Infinity ? maxTime : layoutInfo.end
      const width = Math.max((((effectiveEnd - layoutInfo.start) / totalRange) * 100), 8)
      const top = layoutInfo.row * TIMELINE_LANE_ROW_HEIGHT
      const palettes = paletteSet === 'political'
        ? [
            ['rgba(15, 118, 110, 0.16)', '#0f766e', '#115e59'],
            ['rgba(8, 145, 178, 0.16)', '#0891b2', '#0e7490'],
            ['rgba(21, 94, 117, 0.16)', '#155e75', '#164e63'],
            ['rgba(14, 116, 144, 0.16)', '#0e7490', '#155e75']
          ]
        : [
            ['rgba(59, 130, 246, 0.16)', '#3b82f6', '#1d4ed8'],
            ['rgba(168, 85, 247, 0.16)', '#a855f7', '#7e22ce'],
            ['rgba(245, 158, 11, 0.16)', '#f59e0b', '#b45309'],
            ['rgba(236, 72, 153, 0.16)', '#ec4899', '#be185d']
          ]
      const [background, borderColor, textColor] = palettes[index % palettes.length]

      return {
        position: 'absolute',
        left: `${left}%`,
        width: `${Math.min(width, 100 - left)}%`,
        top: `${top}px`,
        height: '38px',
        background,
        borderColor,
        color: textColor,
      }
    },

    getCalendarBandStyle(calendar, index) {
      return this.getTimelineBandStyle(calendar, this.calendarTimelineLayout, index, this.timelineCalendarTop, 'epoch')
    },

    getTimelineEventStyle(event, index) {
      const layoutInfo = this.timelineEventLayout.get(event.id)
      if (!layoutInfo) {
        return {}
      }

      return {
        position: 'absolute',
        left: `${Math.max(1, Math.min(99, layoutInfo.position))}%`,
        top: `${layoutInfo.row * TIMELINE_EVENT_ROW_HEIGHT}px`,
        '--event-accent-index': index % 4,
      }
    },

    getTimelineStageStyle(stage, index) {
      const layoutInfo = this.timelineStageLayout.get(stage.id)
      if (!layoutInfo) {
        return {}
      }

      return {
        position: 'absolute',
        left: `${Math.max(1, Math.min(99, layoutInfo.position))}%`,
        top: `${layoutInfo.row * TIMELINE_STAGE_ROW_HEIGHT}px`,
        '--stage-accent-index': index % 4,
      }
    },
    
    // 获取所有纪年的时间范围
    getTimeRange() {
      let minTime = Infinity
      let maxTime = -Infinity

      const registerYear = (year) => {
        if (!Number.isFinite(year)) {
          return
        }

        minTime = Math.min(minTime, year)
        maxTime = Math.max(maxTime, year)
      }

      const anchorYear = parseTimelineYear(this.world.anchor_time)

      this.calendarTimelineItems.forEach(calendar => {
        const start = calendar.start
        const end = calendar.end

        registerYear(start)
        registerYear(end)
      })

      this.timelineEventItems.forEach(event => registerYear(event.year))
      this.timelineStageItems.forEach(stage => registerYear(stage.year))
      registerYear(anchorYear)

      if (!Number.isFinite(minTime) || !Number.isFinite(maxTime)) {
        return { min: -10000, max: 26000 }
      }

      if (minTime === maxTime) {
        return {
          min: minTime - 1000,
          max: maxTime + 1000
        }
      }

      const padding = Math.max(100, Math.round((maxTime - minTime) * 0.1))

      return {
        min: minTime - padding,
        max: maxTime + padding
      }
    },
    
    // 获取事件在时间轴上的位置
    getEventPosition(date) {
      const year = parseTimelineYear(date)
      if (!Number.isFinite(year)) return 50

      const { min: minTime, max: maxTime } = this.getTimeRange()
      const totalRange = maxTime - minTime
      
      // 确保年份在范围内
      const clampedYear = Math.max(minTime, Math.min(maxTime, year))
      const position = ((clampedYear - minTime) / totalRange) * 100
      return position
    },
    
    // 获取锚定时间的位置
    getAnchorTimePosition() {
      if (!this.world.anchor_time) return 50 // 默认中间位置

      const year = parseTimelineYear(this.world.anchor_time)
      if (!Number.isFinite(year)) return 50

      const { min: minTime, max: maxTime } = this.getTimeRange()
      const totalRange = maxTime - minTime
      
      // 确保年份在范围内
      const clampedYear = Math.max(minTime, Math.min(maxTime, year))
      const position = ((clampedYear - minTime) / totalRange) * 100
      return position
    },
    
    // 缩放功能
    zoomIn() {
      if (this.zoomLevel < 3) {
        this.zoomLevel += 0.25
        this.updateTimelineZoom()
      }
    },
    
    zoomOut() {
      if (this.zoomLevel > 0.5) {
        this.zoomLevel -= 0.25
        this.updateTimelineZoom()
      }
    },
    
    updateTimelineZoom() {
      this.$nextTick(() => {
        this.syncTimelineRefs()
      })
    },

    syncTimelineRefs() {
      this.timelineContainer = this.$refs.timelineContainer || null
      this.timelineCanvas = this.$refs.timelineCanvas || null
    },
    
    // 获取缩放后的位置
    getScaledPosition(position) {
      return position * this.zoomLevel
    },
    
    // 滚动到指定位置
    scrollToPosition(position) {
      this.syncTimelineRefs()

      if (this.timelineContainer && this.timelineCanvas) {
        const canvasWidth = this.timelineCanvas.scrollWidth
        const scrollPosition = (position / 100) * canvasWidth - this.timelineContainer.clientWidth / 2
        const maxScrollLeft = Math.max(0, canvasWidth - this.timelineContainer.clientWidth)
        this.timelineContainer.scrollTo({
          left: Math.max(0, Math.min(scrollPosition, maxScrollLeft)),
          behavior: 'smooth'
        })
      }
    },
    
    // 处理鼠标滚轮事件
    handleWheel(event) {
      event.preventDefault()
      if (event.deltaY > 0) {
        this.zoomOut()
      } else {
        this.zoomIn()
      }
    },
    
    // 选择事件
    selectEvent(event) {
      this.selectedEvent = event
      // 滚动到事件位置
      const position = this.getEventPosition(event.date)
      this.scrollToPosition(position)
    },
    
    // 编辑事件
    editEvent(event) {
      this.newEvent = {
        name: event.name,
        description: event.description,
        date: event.date,
        selectedSettings: event.entities.map(entityName => {
          const setting = this.settings.find(s => s.name === entityName)
          return setting ? setting.id : ''
        }).filter(Boolean)
      }
      this.showEditEventDialog = true
    },
    
    // 显示历法详情
    showCalendarDetail(calendar) {
      alert(`历法: ${calendar.name}\n类型: ${calendar.type}\n时间范围: ${calendar.timeRange}\n单位: ${calendar.unit}\n比例: ${calendar.ratio}`)
    },
    
  }
  ,
  mounted() {
    this.syncTimelineRefs()
    this.updateTimelineZoom()
    this.loadLlmConfigStatus()

    const worldId = this.$route?.query?.worldId
    if (worldId) {
      this.loadWorld(worldId)
    }
  }
}
</script>

<style scoped>
/* =========== Layout Core =========== */
.world-builder {
  padding: var(--spacing-xl);
  max-width: 1440px;
  margin: 0 auto;
  min-height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  background: var(--neutral-gray-50);
}

.world-builder-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--neutral-gray-200);
  padding-bottom: var(--spacing-md);
}

.builder-header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.save-status {
  font-size: 0.85rem;
  color: var(--wf-text-muted);
}

.world-id-badge {
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: var(--neutral-gray-100);
  color: var(--wf-text-secondary);
  font-size: 0.8rem;
  font-family: var(--font-mono);
}

.project-id-badge {
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  background: rgba(14, 165, 233, 0.12);
  color: var(--primary-blue);
  font-size: 0.8rem;
  font-family: var(--font-mono);
}

.world-builder-title {
  font-size: 2rem;
  font-weight: 700;
  color: var(--wf-text-primary);
}

.world-builder-subtitle {
  color: var(--wf-text-muted);
  margin-top: var(--spacing-xs);
}

/* =========== Tabs Navigation =========== */
.tabs-container {
  margin-bottom: var(--spacing-lg);
  border-bottom: 1px solid var(--neutral-gray-200);
}

.tabs {
  display: flex;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.tab-btn {
  padding: var(--spacing-sm) var(--spacing-lg);
  border: none;
  background: none;
  cursor: pointer;
  font-size: 1rem;
  font-weight: 500;
  color: var(--wf-text-muted);
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  transition: all var(--transition-fast);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.tab-btn:hover {
  color: var(--primary-blue);
  background: var(--neutral-gray-100);
  border-radius: var(--radius-sm) var(--radius-sm) 0 0;
}

.tab-btn.active {
  color: var(--primary-blue);
  border-bottom-color: var(--primary-blue);
}

.tab-content {
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* =========== Forms & Grids =========== */
.form-section {
  background: var(--wf-bg-card);
  padding: var(--spacing-xl);
  border-radius: var(--radius-md);
  box-shadow: none;
  margin-bottom: var(--spacing-lg);
}

.section-header {
  margin-bottom: var(--spacing-lg);
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--wf-text-primary);
}

.section-description {
  color: var(--wf-text-muted);
  font-size: 0.9rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: var(--spacing-lg);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.form-group-full {
  grid-column: 1 / -1;
}

.form-label {
  font-weight: 500;
  color: var(--wf-text-secondary);
  font-size: 0.9rem;
}

.form-input, .form-textarea, .form-select {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--neutral-gray-300);
  border-radius: var(--radius-sm);
  font-family: inherit;
  font-size: 1rem;
  transition: border-color var(--transition-fast);
  background: var(--wf-bg-card);
  color: var(--wf-text-primary);
}

.form-input:focus, .form-textarea:focus, .form-select:focus {
  outline: none;
  border-color: var(--primary-blue);
  box-shadow: 0 0 0 2px var(--primary-blue-light);
}

/* =========== Buttons =========== */
.btn {
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-sm);
}

.btn-primary { 
  background: var(--primary-blue); 
  color: white; 
}
.btn-primary:hover:not(:disabled) { 
  background: var(--primary-blue-dark); 
}

.btn-secondary { 
  background: var(--neutral-gray-100); 
  color: var(--wf-text-primary); 
  border-color: var(--neutral-gray-300);
}
.btn-secondary:hover:not(:disabled) { 
  background: var(--neutral-gray-200); 
}

.btn-danger { 
  background: #ef4444; 
  color: white; 
}
.btn-danger:hover:not(:disabled) { 
  background: #dc2626; 
}

.btn:disabled { 
  opacity: 0.6; 
  cursor: not-allowed; 
}

/* =========== Settings Management =========== */
.settings-layout {
  display: flex;
  gap: var(--spacing-lg);
  min-height: 600px;
  align-items: flex-start;
}

.settings-sidebar {
  width: 280px;
  min-width: 280px;
  background: var(--wf-bg-card);
  border-radius: var(--radius-md);
  box-shadow: none;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 200px);
  overflow-y: auto;
}

.sidebar-header {
  padding: var(--spacing-md) var(--spacing-lg);
  border-bottom: 1px solid var(--neutral-gray-200);
  background: var(--neutral-gray-50);
  position: sticky;
  top: 0;
  z-index: 10;
}

.category-list {
  padding: var(--spacing-sm);
}

.tree-root {
  display: flex;
  flex-direction: column;
}

.tree-node {
  display: flex;
  flex-direction: column;
  position: relative;
}

.tree-item {
  display: flex;
  align-items: center;
  padding: var(--spacing-sm);
  cursor: pointer;
  border-radius: var(--radius-sm);
  margin-bottom: 2px;
  color: var(--wf-text-secondary);
  transition: background var(--transition-fast);
  position: relative;
  z-index: 1;
}

.tree-item:hover {
  background: var(--neutral-gray-100);
}

.category-item.active {
  background: var(--primary-blue-light);
  color: var(--primary-blue-dark);
  font-weight: 500;
}

.root-item {
  font-weight: 600;
  margin-bottom: var(--spacing-sm);
}

.tree-children {
  display: flex;
  flex-direction: column;
  padding-left: 20px;
  position: relative;
}

.tree-children::before {
  content: '';
  position: absolute;
  left: 10px;
  top: 0;
  bottom: 0;
  width: 1px;
  background: var(--neutral-gray-300);
}

.tree-node::before {
  content: '';
  position: absolute;
  left: 10px;
  top: 20px;
  width: 10px;
  height: 1px;
  background: var(--neutral-gray-300);
}

.expand-icon {
  width: 20px;
  text-align: center;
  color: var(--neutral-gray-400);
  font-size: 0.8rem;
  z-index: 2;
}

.category-icon, .collection-icon, .setting-icon {
  margin-right: var(--spacing-sm);
  z-index: 2;
}

.item-name, .category-name, .collection-name, .setting-name {
  z-index: 2;
}

.settings-content {
  flex: 1;
  background: var(--wf-bg-card);
  padding: var(--spacing-xl);
  border-radius: var(--radius-md);
  box-shadow: none;
  min-height: 100%;
}

.header-search { flex: 1; margin-right: var(--spacing-lg); }
.search-input { width: 100%; max-width: 400px; padding: var(--spacing-sm) var(--spacing-md); border: 1px solid var(--neutral-gray-300); border-radius: var(--radius-sm); }

.content-header { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  margin-bottom: var(--spacing-lg); 
}

.settings-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-lg);
}

.setting-card {
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  cursor: pointer;
  background: var(--wf-bg-card);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  display: flex;
  flex-direction: column;
}

.setting-card:hover { 
  transform: translateY(-2px); 
  box-shadow: var(--shadow-md); 
  border-color: var(--primary-blue-light);
}

.setting-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: var(--spacing-sm); }
.setting-title { font-weight: 600; color: var(--wf-text-primary); }
.setting-type-tag { padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; background: var(--neutral-gray-100); color: var(--wf-text-secondary); }
.setting-type-tag.setting { background: #e0f2fe; color: #0284c7; }

.setting-description {
  color: var(--wf-text-muted);
  font-size: 0.85rem;
  margin-bottom: var(--spacing-md);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  flex: 1;
}

.setting-footer {
  border-top: 1px solid var(--neutral-gray-100);
  padding-top: var(--spacing-sm);
  margin-top: auto;
}

.setting-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: var(--neutral-gray-400);
}

/* =========== Timeline =========== */
.timeline-section {
  background: var(--wf-bg-card);
  padding: var(--spacing-xl);
  border-radius: var(--radius-md);
  box-shadow: none;
}

.timeline-header { 
  display: flex; 
  justify-content: space-between; 
  align-items: center;
  margin-bottom: var(--spacing-lg); 
}

.header-info .header-title { 
  font-size: 1.5rem; 
  font-weight: 600; 
  color: var(--wf-text-primary); 
  margin-bottom: var(--spacing-xs);
}

.header-info .header-description { 
  color: var(--wf-text-muted); 
  font-size: 0.9rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.zoom-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  background: var(--neutral-gray-100);
  padding: 4px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--wf-border);
}

.zoom-btn {
  width: 32px;
  height: 32px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  font-weight: bold;
}

.zoom-level {
  font-size: 0.85rem;
  color: var(--wf-text-secondary);
  min-width: 50px;
  text-align: center;
}

.timeline-insights {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.timeline-insight-card {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.98));
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: var(--radius-lg);
  padding: var(--spacing-lg);
  box-shadow: none;
}

.insight-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.insight-kicker {
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--primary-blue);
}

.insight-count {
  font-size: 0.8rem;
  color: var(--wf-text-muted);
}

.calendar-summary-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--spacing-md);
}

.calendar-summary-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  width: 100%;
  text-align: left;
  border: 1px solid rgba(59, 130, 246, 0.16);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  background: rgba(239, 246, 255, 0.86);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.calendar-summary-card:hover {
  transform: translateY(-2px);
  border-color: rgba(59, 130, 246, 0.36);
  box-shadow: 0 10px 24px rgba(59, 130, 246, 0.12);
}

.summary-name {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--wf-text-primary);
}

.summary-meta {
  font-size: 0.78rem;
  color: var(--wf-text-secondary);
  line-height: 1.5;
}

.era-summary-text {
  margin: 0 0 10px;
  color: var(--wf-text-primary);
  font-size: 0.95rem;
  line-height: 1.7;
}

.era-summary-subtext,
.timeline-empty-hint {
  margin: 0;
  font-size: 0.82rem;
  line-height: 1.6;
  color: var(--wf-text-muted);
}

.timeline-container {
  position: relative;
  min-height: 500px;
  background: var(--wf-bg-card);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
  overflow-x: auto;
  overflow-y: auto;
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-md);
  box-shadow: none;
  width: 100%;
  min-width: 1000px;
}

.timeline-canvas {
  position: relative;
  min-width: 100%;
  min-height: 500px;
}

.timeline-title {
  position: absolute;
  top: 10px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 14px;
  font-weight: 600;
  color: var(--wf-text-secondary);
  z-index: 2;
}

/* 时间轴样式 */
.timeline-axis { 
  position: absolute; 
  top: 50px; 
  left: 0; 
  width: 100%; 
  z-index: 1;
}

.timeline-line { 
  height: 4px; 
  background: var(--primary-blue); 
  width: 100%; 
  position: absolute; 
  border-radius: 2px;
}

.timeline-axis-range {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
}

.axis-range-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--wf-text-muted);
}

.timeline-lane-title {
  position: absolute;
  left: 0;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--wf-text-muted);
}

.timeline-band-layer {
  position: absolute;
  left: 0;
  right: 0;
}

.timeline-empty-lane {
  display: flex;
  align-items: center;
  height: 100%;
  padding: 0 14px;
  border: 1px dashed rgba(148, 163, 184, 0.4);
  border-radius: var(--radius-md);
  background: rgba(248, 250, 252, 0.8);
  color: var(--wf-text-muted);
  font-size: 0.82rem;
}

.timeline-band {
  position: absolute;
  min-width: 90px;
  border-radius: 999px;
  padding: 8px 14px;
  border: 1px solid;
  box-sizing: border-box;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
  cursor: default;
}

.band-name {
  font-size: 0.84rem;
  font-weight: 700;
  line-height: 1.3;
}

.band-caption {
  font-size: 0.72rem;
  opacity: 0.82;
  margin-top: 2px;
  line-height: 1.4;
}

/* 锚定时间标记 */
.anchor-time-marker {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(to bottom, #ef4444, #dc2626);
  z-index: 10;
  border-radius: 2px;
  box-shadow: 0 0 8px rgba(239, 68, 68, 0.3);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.7; }
  100% { opacity: 1; }
}

.anchor-label { 
  position: absolute; 
  background: linear-gradient(135deg, #ef4444, #dc2626); 
  color: white; 
  padding: 6px 12px; 
  border-radius: 6px; 
  font-size: 0.75rem; 
  font-weight: 500;
  top: 10px; 
  right: 10px; 
  white-space: nowrap; 
  box-shadow: 0 2px 8px rgba(239, 68, 68, 0.3);
  transform: translateY(-50%);
  transition: all 0.3s ease;
}

.anchor-label::after {
  content: '';
  position: absolute;
  left: -8px;
  top: 50%;
  transform: translateY(-50%);
  border-width: 6px;
  border-style: solid;
  border-color: transparent #ef4444 transparent transparent;
}

.anchor-label:hover {
  transform: translateY(-50%) scale(1.05);
  box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);
}

/* 事件层 */
.event-layers { 
  position: absolute; 
  left: 0; 
  right: 0; 
  width: 100%; 
  z-index: 5;
}

.timeline-event {
  position: absolute;
  background: var(--wf-bg-card);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  font-size: 0.85rem;
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  transform: translateX(-50%);
  min-width: 140px;
  text-align: center;
  border-left: 4px solid var(--primary-blue);
  transition: all 0.3s ease;
  z-index: 5;
}

.timeline-event:hover {
  transform: translateX(-50%) translateY(-4px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
  z-index: 10 !important;
}

.timeline-event::before {
  content: '';
  position: absolute;
  bottom: -8px;
  left: 50%;
  transform: translateX(-50%);
  border-width: 8px 8px 0;
  border-style: solid;
  border-color: white transparent transparent;
  transition: all 0.3s ease;
}

.timeline-event:hover::before {
  border-color: white transparent transparent;
}

.event-title { 
  font-weight: 600; 
  color: var(--wf-text-primary); 
  margin-bottom: 4px; 
  line-height: 1.3;
}

.event-date { 
  color: var(--primary-blue); 
  font-size: 0.75rem; 
  font-weight: 500;
}

/* 事件列表 */
.timeline-events .events-header { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  margin-bottom: var(--spacing-md); 
  padding-bottom: var(--spacing-sm);
  border-bottom: 2px solid var(--neutral-gray-100);
}

.timeline-events .header-title { 
  font-size: 1.25rem; 
  font-weight: 600;
  color: var(--wf-text-primary);
}

.event-list { 
  display: grid; 
  gap: var(--spacing-md); 
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); 
}

.event-card { 
  background: var(--wf-bg-card); 
  padding: var(--spacing-lg); 
  border-radius: var(--radius-lg); 
  border: 1px solid var(--wf-border); 
  position: relative; 
  box-shadow: none;
  transition: all 0.3s ease;
  overflow: hidden;
}

.event-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--primary-blue-light);
}

.event-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: var(--primary-blue);
}

.event-card-title { 
  font-size: 1.1rem; 
  color: var(--wf-text-primary); 
  margin-bottom: var(--spacing-xs); 
  font-weight: 600;
  padding-left: var(--spacing-sm);
}

.event-card-description { 
  color: var(--wf-text-secondary); 
  font-size: 0.9rem; 
  margin-bottom: var(--spacing-md); 
  line-height: 1.5; 
  padding-left: var(--spacing-sm);
}

.event-card-meta { 
  display: flex; 
  flex-direction: column; 
  gap: 6px; 
  font-size: 0.8rem; 
  color: var(--wf-text-muted); 
  background: var(--neutral-gray-50); 
  padding: var(--spacing-sm); 
  border-radius: var(--radius-sm); 
  margin-bottom: var(--spacing-lg); 
  padding-left: var(--spacing-sm);
}

.event-card .event-card-actions {
  display: flex;
  gap: var(--spacing-sm);
  justify-content: flex-end;
  margin-top: var(--spacing-md);
}

.event-card .edit-btn, .event-card .delete-btn {
  transition: all 0.3s ease;
  font-size: 0.8rem;
  padding: 4px 12px;
}

.event-card .edit-btn:hover, .event-card .delete-btn:hover {
  transform: scale(1.05);
}

.event-card.active {
  border-color: var(--primary-blue);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.2);
}

.event-card.active::before {
  background: var(--primary-blue);
  width: 6px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .timeline-insights {
    grid-template-columns: 1fr;
  }

  .calendar-summary-list {
    grid-template-columns: 1fr;
  }

  .timeline-container {
    min-height: 350px;
    padding: var(--spacing-md);
  }
  
  .timeline-header {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-md);
  }
  
  .event-list {
    grid-template-columns: 1fr;
  }
  
  .timeline-event {
    min-width: 120px;
    padding: 8px 12px;
  }

  .timeline-band {
    min-width: 74px;
    padding: 7px 10px;
  }
}

@media (max-width: 480px) {
  .timeline-container {
    min-height: 300px;
  }
  
  .timeline-section {
    padding: var(--spacing-md);
  }

  .timeline-title {
    left: 0;
    transform: none;
  }

  .timeline-axis-range {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .event-card {
    padding: var(--spacing-md);
  }
}

/* Timeline redesign: dark atlas surface */
.timeline-section {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.045), rgba(255, 255, 255, 0.02)),
    var(--wf-bg-surface);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
  padding: 28px;
  overflow: hidden;
}

.timeline-section .timeline-header {
  align-items: flex-start;
  margin-bottom: 22px;
}

.timeline-eyebrow {
  display: inline-block;
  margin-bottom: 4px;
  color: var(--wf-accent);
  font-family: var(--font-mono);
  font-size: 0.76rem;
  letter-spacing: 0;
}

.timeline-section .header-info .header-title {
  margin: 0;
  font-size: 1.8rem;
  line-height: 1.05;
  color: var(--wf-text-primary);
}

.timeline-section .header-info .header-description {
  margin-top: 10px;
  color: var(--wf-text-secondary);
  max-width: 720px;
}

.timeline-section .zoom-controls {
  height: 40px;
  background: rgba(0, 0, 0, 0.24);
  border: 1px solid var(--wf-border-light);
  border-radius: var(--radius-md);
  padding: 4px;
}

.timeline-section .zoom-btn {
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  color: var(--wf-text-primary);
}

.timeline-section .zoom-level {
  color: var(--wf-text-secondary);
  font-family: var(--font-mono);
}

.timeline-status-grid {
  display: grid;
  grid-template-columns: minmax(260px, 1.35fr) repeat(3, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.timeline-status-card {
  min-height: 86px;
  padding: 14px 16px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid var(--wf-border);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.timeline-status-card.is-primary {
  background: linear-gradient(135deg, rgba(255, 255, 175, 0.12), rgba(255, 255, 255, 0.035));
  border-color: rgba(255, 255, 175, 0.28);
}

.status-label {
  color: var(--wf-text-muted);
  font-size: 0.75rem;
}

.timeline-status-card strong {
  margin-top: 4px;
  color: var(--wf-text-primary);
  font-size: 1.12rem;
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-status-card small {
  color: var(--wf-text-secondary);
  font-size: 0.76rem;
}

.timeline-insights {
  grid-template-columns: minmax(0, 1.35fr) minmax(300px, 0.65fr);
  gap: 14px;
}

.timeline-insight-card {
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
  padding: 16px;
}

.insight-kicker {
  color: var(--wf-accent);
  letter-spacing: 0;
}

.insight-count {
  color: var(--wf-text-secondary);
}

.chronology-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.chronology-column {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.chronology-column-title {
  color: var(--wf-text-muted);
  font-size: 0.78rem;
}

.calendar-summary-row {
  width: 100%;
  min-height: 48px;
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: rgba(0, 0, 0, 0.22);
  border: 1px solid var(--wf-border);
  color: var(--wf-text-primary);
  text-align: left;
}

.calendar-summary-row:hover {
  background: rgba(255, 255, 255, 0.06);
  border-color: rgba(255, 255, 175, 0.32);
}

.calendar-summary-row .summary-name,
.calendar-summary-row .summary-meta {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.calendar-summary-row .summary-name {
  font-size: 0.9rem;
  color: var(--wf-text-primary);
}

.calendar-summary-row .summary-meta {
  font-size: 0.78rem;
  color: var(--wf-text-secondary);
}

.timeline-issue-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.timeline-issue-row {
  display: grid;
  grid-template-columns: minmax(90px, 0.45fr) minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  padding: 9px 10px;
  border-radius: var(--radius-sm);
  background: rgba(255, 71, 87, 0.06);
  border: 1px solid rgba(255, 71, 87, 0.14);
}

.issue-name,
.issue-reason {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.8rem;
}

.issue-name {
  color: var(--wf-text-primary);
}

.issue-reason {
  color: var(--wf-text-secondary);
}

.timeline-container {
  min-width: 0;
  min-height: 520px;
  padding: 0;
  border-radius: var(--radius-lg);
  background: #0b0b0d;
  border: 1px solid var(--wf-border-light);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.025);
  overflow: auto;
}

.timeline-canvas {
  min-height: 520px;
  border-radius: var(--radius-lg);
  background:
    linear-gradient(90deg, rgba(255,255,255,0.045) 1px, transparent 1px) 0 0 / 160px 100%,
    linear-gradient(180deg, rgba(255,255,255,0.035) 1px, transparent 1px) 0 0 / 100% 52px,
    radial-gradient(circle at 20% 0%, rgba(255,255,175,0.06), transparent 28%),
    #0b0b0d;
}

.timeline-title {
  top: 20px;
  left: 24px;
  transform: none;
  color: var(--wf-text-secondary);
  font-size: 0.82rem;
  font-family: var(--font-mono);
  font-weight: 500;
}

.timeline-axis {
  top: 78px;
  left: 24px;
  right: 24px;
  width: auto;
}

.timeline-line {
  height: 2px;
  background: linear-gradient(90deg, rgba(255,255,175,0.18), var(--wf-accent), rgba(255,255,175,0.18));
  box-shadow: 0 0 18px rgba(255, 255, 175, 0.14);
}

.timeline-tick {
  position: absolute;
  top: -8px;
  transform: translateX(-50%);
  color: var(--wf-text-muted);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  white-space: nowrap;
  pointer-events: none;
}

.timeline-tick::before {
  content: '';
  display: block;
  width: 1px;
  height: 16px;
  margin: 0 auto 12px;
  background: rgba(255, 255, 255, 0.16);
}

.timeline-axis-range {
  margin-top: 30px;
}

.axis-range-label {
  color: var(--wf-text-muted);
  font-family: var(--font-mono);
  font-weight: 500;
}

.timeline-lane-title {
  left: 24px;
  color: var(--wf-text-secondary);
  font-size: 0.75rem;
  letter-spacing: 0;
  text-transform: none;
}

.timeline-band-layer,
.timeline-point-layer,
.timeline-stage-layer {
  position: absolute;
  left: 24px;
  right: 24px;
}

.timeline-empty-lane {
  min-height: 44px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.03);
  border: 1px dashed var(--wf-border-light);
  color: var(--wf-text-muted);
}

.timeline-band {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 160px;
  padding: 6px 12px;
  border-radius: var(--radius-md);
  color: var(--wf-text-primary) !important;
  background: rgba(255, 255, 255, 0.055);
  backdrop-filter: blur(10px);
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.22);
  overflow: hidden;
  cursor: pointer;
}

.timeline-band.is-year {
  border-style: dashed;
}

.timeline-band.is-low-confidence {
  opacity: 0.58;
}

.band-name,
.band-caption {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.band-name {
  font-size: 0.82rem;
}

.band-caption {
  font-size: 0.7rem;
  color: var(--wf-text-secondary);
}

.timeline-point-event {
  width: 18px;
  height: 18px;
  padding: 0;
  border: 0;
  border-radius: 999px;
  background: transparent;
  transform: translateX(-50%);
  z-index: 6;
}

.timeline-point-event:hover {
  transform: translateX(-50%) translateY(-2px);
  z-index: 18;
}

.event-dot {
  display: block;
  width: 12px;
  height: 12px;
  margin: 3px;
  border-radius: 999px;
  background: var(--wf-accent);
  border: 2px solid #0b0b0d;
  box-shadow: 0 0 0 1px rgba(255, 255, 175, 0.45), 0 0 18px rgba(255, 255, 175, 0.22);
}

.event-popover {
  position: absolute;
  left: 50%;
  bottom: 24px;
  min-width: 210px;
  max-width: 270px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: rgba(17, 17, 19, 0.96);
  border: 1px solid var(--wf-border-light);
  box-shadow: var(--shadow-lg);
  color: var(--wf-text-primary);
  text-align: left;
  opacity: 0;
  pointer-events: none;
  transform: translate(-50%, 6px);
  transition: opacity var(--transition-fast), transform var(--transition-fast);
}

.timeline-point-event:hover .event-popover {
  opacity: 1;
  transform: translate(-50%, 0);
}

.event-popover strong,
.event-popover small {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.event-popover strong {
  font-size: 0.86rem;
}

.event-popover small {
  margin-top: 3px;
  color: var(--wf-text-secondary);
  font-size: 0.72rem;
}

.timeline-stage-chip {
  height: 26px;
  max-width: 190px;
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 4px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid var(--wf-border);
  color: var(--wf-text-secondary);
  transform: translateX(-50%);
  overflow: hidden;
  z-index: 5;
}

.timeline-stage-chip:hover {
  color: var(--wf-text-primary);
  border-color: rgba(255, 255, 175, 0.26);
  background: rgba(255, 255, 255, 0.07);
  z-index: 12;
}

.stage-pulse {
  flex: 0 0 auto;
  width: 7px;
  height: 7px;
  border-radius: 999px;
  background: #7dd3fc;
  box-shadow: 0 0 12px rgba(125, 211, 252, 0.34);
}

.stage-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.74rem;
}

.anchor-time-marker {
  top: 18px;
  bottom: 18px;
  width: 2px;
  background: linear-gradient(180deg, rgba(255,71,87,0), var(--wf-danger), rgba(255,71,87,0));
  box-shadow: 0 0 18px rgba(255, 71, 87, 0.26);
  animation: none;
}

.anchor-label {
  top: 0;
  left: 10px;
  right: auto;
  max-width: 340px;
  overflow: hidden;
  text-overflow: ellipsis;
  background: rgba(255, 71, 87, 0.18);
  border: 1px solid rgba(255, 71, 87, 0.42);
  color: #ffd8dd;
  border-radius: var(--radius-sm);
  box-shadow: none;
  transform: none;
}

.anchor-label::after {
  display: none;
}

.timeline-context-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.timeline-context-panel {
  min-width: 0;
  padding: 14px;
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.035);
  border: 1px solid var(--wf-border);
}

.context-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  color: var(--wf-text-secondary);
}

.context-panel-header strong {
  color: var(--wf-accent);
  font-family: var(--font-mono);
}

.context-event-row,
.context-stage-row {
  width: 100%;
  min-height: 42px;
  display: grid;
  grid-template-columns: 78px minmax(0, 0.75fr) minmax(0, 1fr);
  gap: 10px;
  align-items: center;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: transparent;
  border: 1px solid transparent;
  color: var(--wf-text-primary);
  text-align: left;
}

.context-event-row:hover {
  background: rgba(255, 255, 255, 0.055);
  border-color: var(--wf-border-light);
}

.context-year {
  color: var(--wf-accent);
  font-family: var(--font-mono);
  font-size: 0.74rem;
}

.context-title,
.context-meta {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.context-title {
  color: var(--wf-text-primary);
  font-size: 0.86rem;
}

.context-meta {
  color: var(--wf-text-secondary);
  font-size: 0.76rem;
}

@media (max-width: 980px) {
  .timeline-status-grid,
  .timeline-insights,
  .timeline-context-grid {
    grid-template-columns: 1fr;
  }

  .chronology-columns {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .timeline-section {
    padding: 18px;
  }

  .timeline-section .timeline-header {
    flex-direction: column;
    gap: 14px;
  }

  .calendar-summary-row,
  .context-event-row,
  .context-stage-row {
    grid-template-columns: 1fr;
  }
}

/* =========== Dialog & Modals =========== */
.dialog { 
  position: fixed; 
  inset: 0; 
  background: rgba(0,0,0,0.6); 
  backdrop-filter: blur(2px);
  display: flex; 
  align-items: center; 
  justify-content: center; 
  z-index: 1000; 
}

.dialog-content { 
  background: var(--wf-bg-card); 
  border-radius: var(--radius-md); 
  width: 600px; 
  max-width: 90vw; 
  max-height: 90vh; 
  display: flex; 
  flex-direction: column; 
  box-shadow: var(--shadow-xl); 
  animation: modalIn 0.2s ease-out;
}

@keyframes modalIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.setting-selector-dialog { width: 800px; }

.dialog-header { 
  padding: var(--spacing-lg); 
  border-bottom: 1px solid var(--neutral-gray-100); 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  background: var(--neutral-gray-50);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

.dialog-title { font-size: 1.25rem; font-weight: 600; color: var(--wf-text-primary); margin: 0; }

.dialog-body { padding: var(--spacing-lg); overflow-y: auto; }
.dialog-body.split-layout { display: flex; gap: var(--spacing-xl); padding: 0; }
.detail-sidebar { width: 280px; padding: var(--spacing-lg); border-right: 1px solid var(--neutral-gray-200); background: var(--neutral-gray-50); }
.detail-body { flex: 1; padding: var(--spacing-lg); }

.setting-structured-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.setting-structured-section {
  border: 1px solid var(--neutral-gray-200);
  border-radius: var(--radius-md);
  background: var(--neutral-gray-50);
  padding: var(--spacing-md);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.setting-structured-section.is-wide {
  grid-column: 1 / -1;
}

.setting-structured-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
}

.setting-structured-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: var(--wf-text-primary);
}

.setting-structured-count {
  min-width: 28px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(14, 165, 233, 0.12);
  color: var(--primary-blue);
  font-size: 0.78rem;
  text-align: center;
}

.setting-structured-text {
  white-space: pre-line;
  line-height: 1.7;
  color: var(--wf-text-secondary);
}

.setting-facts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--spacing-sm);
}

.setting-fact-item {
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: var(--wf-bg-card);
  border: 1px solid var(--neutral-gray-200);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.setting-fact-label {
  font-size: 0.78rem;
  color: var(--wf-text-muted);
}

.setting-fact-value {
  color: var(--wf-text-primary);
  white-space: pre-line;
  word-break: break-word;
}

.setting-card-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--spacing-sm);
}

.setting-structured-card {
  padding: 12px;
  border-radius: var(--radius-sm);
  background: var(--wf-bg-card);
  border: 1px solid var(--neutral-gray-200);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.setting-card-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--wf-text-primary);
}

.setting-card-subtitle {
  font-size: 0.8rem;
  color: var(--primary-blue);
  margin-top: 2px;
}

.setting-card-description {
  margin: 0;
  color: var(--wf-text-secondary);
  line-height: 1.6;
  white-space: pre-line;
}

.setting-card-fields {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 4px;
}

.setting-card-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.setting-card-field-label {
  font-size: 0.76rem;
  color: var(--wf-text-muted);
}

.setting-card-field-value {
  color: var(--wf-text-primary);
  white-space: pre-line;
  word-break: break-word;
}

.setting-detail-hint {
  margin: 0 0 var(--spacing-sm);
  font-size: 0.84rem;
  color: var(--wf-text-muted);
}

.dialog-footer { 
  padding: var(--spacing-md) var(--spacing-lg); 
  border-top: 1px solid var(--neutral-gray-100); 
  display: flex; 
  justify-content: flex-end; 
  gap: var(--spacing-sm); 
  background: var(--neutral-gray-50);
  border-radius: 0 0 var(--radius-md) var(--radius-md);
}

.close-btn { background: none; border: none; font-size: 1.5rem; line-height: 1; cursor: pointer; color: var(--neutral-gray-400); padding: 0 4px; }
.close-btn:hover { color: var(--wf-text-primary); }

/* =========== AI Extraction =========== */
.ai-extract-section { margin-top: var(--spacing-lg); background: var(--wf-bg-surface); border: 1px solid var(--wf-border); padding: var(--spacing-xl); border-radius: var(--radius-md); }
.extract-toolbar { display: flex; align-items: center; justify-content: space-between; gap: var(--spacing-md); flex-wrap: wrap; margin-bottom: var(--spacing-md); }
.llm-status-chip { display: inline-flex; align-items: center; gap: var(--spacing-sm); padding: 8px 12px; border-radius: 999px; font-size: 0.9rem; background: var(--wf-bg-card); border: 1px solid var(--wf-border); color: var(--wf-text-secondary); }
.llm-status-chip.is-ready { border-color: #86efac; background: rgba(0, 212, 170, 0.1); color: var(--wf-success); }
.llm-status-chip.is-missing { border-color: #fca5a5; background: rgba(255, 71, 87, 0.1); color: var(--wf-danger); }
.llm-status-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; }
.llm-status-meta { font-family: var(--font-mono); font-size: 0.8rem; opacity: 0.85; }
.extract-btn { background: var(--wf-accent); color: #0f172a; margin-top: var(--spacing-md); }
.extract-error { margin-top: var(--spacing-sm); color: var(--wf-danger); font-size: 0.9rem; }

/* Extraction Progress Bar */
.extract-progress { margin-top: var(--spacing-md); }
.progress-bar-container {
  width: 100%; height: 8px;
  background: var(--wf-bg-hover, #2a2a35);
  border-radius: 4px; overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--wf-accent, #3b82f6), #6366f1);
  border-radius: 4px; transition: width 0.3s ease;
}
.progress-info { display: flex; justify-content: space-between; align-items: center; margin-top: 6px; }
.progress-stage { font-size: 0.85rem; color: var(--wf-text-secondary); }
.progress-pct { font-size: 0.8rem; color: var(--wf-text-muted); font-weight: 600; }

/* 文件上传区域 */
.file-drop-zone {
  border: 2px dashed var(--neutral-gray-300);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
  text-align: center;
  transition: border-color 0.2s, background-color 0.2s;
  cursor: pointer;
}
.file-drop-zone:hover,
.file-drop-zone.file-drag-over {
  border-color: #0284c7;
  background-color: rgba(2, 132, 199, 0.05);
}
.file-drop-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--wf-text-muted);
  font-size: 0.9rem;
}
.file-drop-icon {
  font-size: 2rem;
}
.file-drop-hint {
  font-size: 0.8rem;
  color: var(--neutral-gray-400);
}
.file-input-hidden {
  display: none;
}
.file-browse-btn {
  padding: 4px 12px;
  font-size: 0.85rem;
}
.selected-files {
  margin-top: var(--spacing-sm);
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}
.selected-file-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--neutral-gray-100);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-sm);
  padding: 4px 8px;
  font-size: 0.85rem;
}
.file-name {
  color: var(--wf-text-secondary);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-size {
  color: var(--neutral-gray-400);
}
.file-remove-btn {
  border: none;
  background: none;
  color: var(--neutral-gray-400);
  cursor: pointer;
  font-size: 1.1rem;
  line-height: 1;
  padding: 0 2px;
}
.file-remove-btn:hover {
  color: var(--wf-danger);
}

/* JSON 导入 */
.json-import-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
  padding: var(--spacing-sm) 0;
  border-top: 1px dashed var(--neutral-gray-200);
}
.json-import-btn {
  padding: 4px 14px;
  font-size: 0.85rem;
  white-space: nowrap;
}
.json-import-hint {
  font-size: 0.8rem;
  color: var(--neutral-gray-400);
}

/* 实体与事件概览 */
.entity-event-overview {
  margin-top: var(--spacing-lg);
}
.overview-section {
  margin-bottom: var(--spacing-md);
}
.overview-header {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}
.overview-header.collapsible-header {
  cursor: pointer;
  user-select: none;
}
.overview-header.collapsible-header:hover {
  opacity: 0.8;
}
.collapse-arrow {
  font-size: 0.75rem;
  color: var(--wf-text-secondary);
  width: 16px;
  text-align: center;
  flex-shrink: 0;
}
.enabled-count {
  font-size: 0.75rem;
  color: var(--neutral-gray-500);
  margin-left: auto;
}
.overview-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--wf-text-secondary);
}
.overview-empty {
  color: var(--neutral-gray-400);
  font-size: 0.85rem;
  font-style: italic;
  padding: var(--spacing-md);
  text-align: center;
}
.entity-card-list, .event-card-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}
.entity-card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: var(--spacing-md);
}
.entity-card {
  content-visibility: auto;
  contain-intrinsic-size: auto 200px;
  background: var(--wf-bg-card);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  min-width: 240px;
  flex: 1 1 auto;
  max-width: 360px;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast), border-color var(--transition-fast), opacity 0.2s;
}
.entity-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--primary-blue-light);
}
.entity-card.entity-disabled {
  opacity: 0.45;
}
.entity-card.entity-disabled:hover {
  transform: none;
  box-shadow: none;
  border-color: var(--wf-border);
}
.entity-card-rich {
  max-width: none;
  min-width: 0;
  padding: var(--spacing-md);
  background: var(--wf-bg-card);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  color: var(--wf-text-primary);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast), border-color var(--transition-fast);
}
.entity-card-rich:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--primary-blue-light);
}

/* Skeleton loading */
.entity-card-skeleton,
.event-card-skeleton {
  min-height: 120px;
  pointer-events: none;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}
@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 0.7; }
}
.skeleton-line {
  height: 14px;
  border-radius: 4px;
  background: rgba(255,255,255,0.06);
  margin-bottom: 8px;
}
.skeleton-name { width: 60%; height: 16px; }
.skeleton-type { width: 35%; }
.skeleton-date { width: 40%; height: 12px; }
.skeleton-tag { display: inline-block; height: 20px; border-radius: 10px; margin-right: 8px; }
.w-60 { width: 60px; }
.w-40 { width: 40px; }

.entity-card-header {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}
.entity-card-header-rich {
  align-items: flex-start;
}
.entity-card-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  flex: 1;
}
.entity-setting-link {
  border: 1px solid var(--wf-border-light);
  background: var(--wf-bg-hover);
  color: var(--wf-text-secondary);
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: var(--radius-full);
  padding: 4px 12px;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
  flex-shrink: 0;
}
.entity-setting-link:hover {
  background: rgba(2, 132, 199, 0.12);
  border-color: rgba(2, 132, 199, 0.25);
  color: #38bdf8;
}

/* 加载更多按钮 */
.entity-load-more {
  grid-column: 1 / -1;
  text-align: center;
  padding: var(--spacing-md);
}
.entity-load-more .btn {
  min-width: 240px;
}

/* Toggle Switch */
.toggle-switch {
  position: relative;
  display: inline-block;
  width: 32px;
  height: 18px;
  flex-shrink: 0;
}
.toggle-switch input {
  opacity: 0;
  width: 0;
  height: 0;
}
.toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #ccc;
  transition: 0.2s;
  border-radius: 18px;
}
.toggle-slider:before {
  position: absolute;
  content: "";
  height: 14px;
  width: 14px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: 0.2s;
  border-radius: 50%;
}
.toggle-switch input:checked + .toggle-slider {
  background-color: var(--wf-accent, #3b82f6);
}
.toggle-switch input:checked + .toggle-slider:before {
  transform: translateX(14px);
}
.entity-card-name {
  font-weight: 600;
  color: var(--wf-text-primary);
  font-size: 0.95rem;
}
.entity-card-type {
  font-size: 0.72rem;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.08);
  border-radius: 4px;
  padding: 2px 10px;
  white-space: nowrap;
  border: 1px solid rgba(56, 189, 248, 0.15);
  font-weight: 500;
}
.entity-card-attrs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: var(--spacing-sm);
}
.entity-attr-tag {
  font-size: 0.72rem;
  color: var(--wf-text-secondary);
  background: var(--wf-bg-hover);
  border: 1px solid var(--wf-border-light);
  border-radius: 4px;
  padding: 2px 10px;
}
/* 简介/长文本 */
.entity-bio-block {
  margin-top: var(--spacing-sm);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.entity-bio-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: var(--wf-bg-hover);
  cursor: pointer;
  user-select: none;
}
.entity-bio-header:hover {
  background: rgba(56, 189, 248, 0.08);
}
.entity-bio-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: var(--wf-text-primary);
}
.entity-bio-toggle {
  font-size: 0.7rem;
  color: #38bdf8;
}
.entity-bio-text {
  margin: 0;
  padding: var(--spacing-sm);
  font-size: 0.8rem;
  line-height: 1.65;
  color: var(--wf-text-secondary);
  white-space: pre-wrap;
}
.entity-bio-preview {
  margin: 0;
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: 0.75rem;
  color: var(--wf-text-muted);
}

/* 嵌套数组块（实力变化/性格变化/关键转折） */
.entity-nested-block {
  margin-top: var(--spacing-sm);
  border-top: 1px solid var(--wf-border);
  padding-top: var(--spacing-sm);
}
.entity-nested-title {
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  color: var(--wf-text-muted);
  text-transform: uppercase;
  margin-bottom: var(--spacing-xs);
}
.entity-nested-list {
  display: grid;
  gap: 6px;
}
.entity-nested-card {
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  background: var(--wf-bg-hover);
  border: 1px solid var(--wf-border);
}
.entity-nested-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-sm);
}
.entity-nested-time {
  font-size: 0.7rem;
  color: var(--wf-accent);
  white-space: nowrap;
}
.entity-nested-change {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--wf-text-primary);
}
.entity-nested-event-name {
  font-size: 0.72rem;
  font-weight: 500;
  color: var(--wf-text-primary);
}
.entity-nested-cause {
  margin-top: 2px;
  font-size: 0.68rem;
  color: #2dd4bf;
}
.entity-nested-desc {
  margin: 4px 0 0;
  font-size: 0.72rem;
  color: var(--wf-text-secondary);
  line-height: 1.5;
}

.entity-stage-block {
}
.entity-stage-title {
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.03em;
  color: var(--wf-text-muted);
  margin-bottom: var(--spacing-sm);
  text-transform: uppercase;
}
.entity-stage-list {
  display: grid;
  gap: var(--spacing-sm);
}
.entity-stage-card {
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  background: var(--wf-bg-hover);
  border: 1px solid var(--wf-border);
}
.entity-stage-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: 4px;
}
.entity-stage-name {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--wf-text-primary);
}
.entity-stage-era {
  font-size: 0.7rem;
  color: #2dd4bf;
  background: rgba(45, 212, 191, 0.1);
  border-radius: 4px;
  padding: 1px 8px;
  font-weight: 500;
}
.entity-stage-description {
  margin: 0 0 var(--spacing-sm);
  font-size: 0.8rem;
  line-height: 1.6;
  color: var(--wf-text-secondary);
}
.entity-stage-attrs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.entity-stage-attr-tag {
  font-size: 0.7rem;
  color: var(--wf-text-muted);
  background: var(--wf-bg-card);
  border: 1px solid var(--wf-border);
  border-radius: 4px;
  padding: 2px 8px;
}
.entity-stage-empty {
  margin-top: var(--spacing-md);
  font-size: 0.8rem;
  color: var(--wf-text-muted);
  padding: var(--spacing-sm) var(--spacing-md);
  border-radius: var(--radius-sm);
  background: var(--wf-bg-hover);
  border: 1px dashed var(--wf-border);
}
.attr-key { font-weight: 500; }
.attr-value { color: var(--wf-text-muted); }

.event-card {
  content-visibility: auto;
  contain-intrinsic-size: auto 80px;
  background: var(--wf-bg-card);
  border: 1px solid var(--wf-border);
  border-left: 3px solid var(--primary-blue-light, #38bdf8);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  flex: 1 1 100%;
  max-width: 100%;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast), border-color var(--transition-fast), opacity 0.2s;
}
.event-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-color: var(--primary-blue-light, #38bdf8);
}
.event-card.entity-disabled {
  opacity: 0.45;
}
.event-card.entity-disabled:hover {
  transform: none;
  box-shadow: none;
  border-color: var(--wf-border);
}
.event-card-header {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}
.event-card-name {
  font-weight: 600;
  color: var(--wf-text-primary);
  font-size: 0.95rem;
}
.event-card-date {
  font-size: 0.75rem;
  color: #38bdf8;
  white-space: nowrap;
  font-weight: 500;
}
.event-card-desc {
  font-size: 0.85rem;
  color: var(--wf-text-secondary);
  margin: var(--spacing-sm) 0;
  line-height: 1.5;
}
.event-card-entities {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: var(--spacing-sm);
}
.event-card-stack {
  display: grid;
  gap: var(--spacing-md);
}
.event-card-rich {
  max-width: none;
}
.event-entity-tag {
  font-size: 0.72rem;
  color: #38bdf8;
  background: rgba(56, 189, 248, 0.08);
  border: 1px solid rgba(56, 189, 248, 0.15);
  border-radius: 4px;
  padding: 2px 10px;
  white-space: nowrap;
  font-weight: 500;
}
.event-entity-link {
  border: 1px solid rgba(56, 189, 248, 0.15);
  cursor: pointer;
  font-weight: 500;
  transition: all var(--transition-fast);
}
.event-entity-link:hover {
  background: rgba(56, 189, 248, 0.15);
  border-color: rgba(56, 189, 248, 0.3);
  color: #7dd3fc;
}

.evolution-history-list {
  display: grid;
  gap: var(--spacing-md);
}

.evolution-history-card {
  padding: var(--spacing-lg);
  border-radius: var(--radius-lg);
  background: linear-gradient(145deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.92));
  border: 1px solid rgba(148, 163, 184, 0.14);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.18);
}

.evolution-history-top {
  display: flex;
  justify-content: space-between;
  gap: var(--spacing-md);
  align-items: flex-start;
  margin-bottom: var(--spacing-sm);
}

.evolution-history-main {
  min-width: 0;
}

.evolution-history-type {
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(250, 204, 21, 0.95);
  margin-bottom: 6px;
}

.evolution-history-title {
  margin: 0;
  font-size: 1.04rem;
  font-weight: 700;
  color: rgba(248, 250, 252, 0.98);
}

.evolution-history-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 0.78rem;
  color: rgba(226, 232, 240, 0.74);
  margin-bottom: var(--spacing-sm);
}

.evolution-history-description {
  margin: 0 0 var(--spacing-md);
  font-size: 0.88rem;
  line-height: 1.7;
  color: rgba(226, 232, 240, 0.92);
}

.evolution-history-actions {
  display: flex;
  justify-content: flex-end;
}

.evolution-status-badge {
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.evolution-status-badge.is-running {
  background: rgba(59, 130, 246, 0.16);
  color: #93c5fd;
}

.evolution-status-badge.is-completed {
  background: rgba(34, 197, 94, 0.16);
  color: #86efac;
}

.evolution-status-badge.is-failed {
  background: rgba(239, 68, 68, 0.16);
  color: #fca5a5;
}

.evolution-status-badge.is-created {
  background: rgba(250, 204, 21, 0.16);
  color: #fde68a;
}

.extract-preview { background: var(--wf-bg-card); border: 1px solid var(--wf-border); border-radius: var(--radius-md); padding: var(--spacing-lg); margin-top: var(--spacing-md); box-shadow: none; }
.preview-header { margin-bottom: var(--spacing-sm); border-bottom: 1px solid var(--neutral-gray-100); padding-bottom: var(--spacing-sm); }
.preview-title { font-size: 1rem; font-weight: 600; color: var(--wf-text-secondary); }
.rag-index-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: var(--radius-full);
  font-size: 0.8rem;
  color: var(--wf-success);
  background: rgba(0, 212, 170, 0.1);
  border: 1px solid rgba(0, 212, 170, 0.25);
  margin-left: var(--spacing-sm);
}

.preview-code { 
  background: var(--neutral-gray-900); 
  color: var(--neutral-gray-100); 
  padding: var(--spacing-md); 
  border-radius: var(--radius-sm); 
  overflow-x: auto; 
  white-space: pre-wrap; 
  font-family: var(--font-mono); 
  font-size: 0.85rem; 
  line-height: 1.6;
  margin-bottom: var(--spacing-md); 
  max-height: 300px;
  overflow-y: auto;
}

.llm-config-dialog { width: 680px; }
.form-hint { font-size: 0.85rem; color: var(--wf-text-muted); }
.config-feedback { margin-top: var(--spacing-md); padding: var(--spacing-sm) var(--spacing-md); border-radius: var(--radius-sm); font-size: 0.9rem; }
.config-feedback.success { background: #ecfdf5; border: 1px solid #86efac; color: var(--wf-success); }
.config-feedback.error { background: rgba(255, 71, 87, 0.1); border: 1px solid #fca5a5; color: var(--wf-danger); }

</style>

