<template>
  <div class="world-builder">
    <Teleport v-if="showCollabWidget" to="#wf-navbar-below-right">
      <div class="collab-status-card active">
        <span>协作已连接</span>
        <button type="button" class="inline-sync-btn" @click="openCollabRoom">打开房间</button>
      </div>
    </Teleport>
    <!-- 顶部导航栏 -->
    <header class="world-builder-header">
      <div class="header-content">
        <h1 class="world-builder-title">世界观构建</h1>
        <p class="world-builder-subtitle">创建和管理你的世界观设定，构建完整的虚拟世界</p>
      </div>

      <div class="builder-header-side">
        <div class="builder-header-actions">
          <div class="history-actions" aria-label="编辑历史操作">
            <button
              type="button"
              class="btn btn-secondary history-btn"
              :disabled="!canUndo"
              :title="undoButtonTitle"
              aria-label="撤回"
              @click="undoWorldChange"
            >
              <SvgIcon name="undo" :size="17" :stroke-width="2.2" />
            </button>
            <button
              type="button"
              class="btn btn-secondary history-btn"
              :disabled="!canRedo"
              :title="redoButtonTitle"
              aria-label="重做"
              @click="redoWorldChange"
            >
              <SvgIcon name="redo" :size="17" :stroke-width="2.2" />
            </button>
          </div>
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
        </div>
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
          <SvgIcon class="tab-icon" name="list" :size="16" />
          <span class="tab-label">基本信息</span>
        </button>
        <button 
          :class="{ active: activeTab === 'entities' }"
          @click="activeTab = 'entities'"
          class="tab-btn"
        >
          <SvgIcon class="tab-icon" name="dna" :size="16" />
          <span class="tab-label">核心实体与事件</span>
        </button>
        <button 
          :class="{ active: activeTab === 'settings' }"
          @click="activeTab = 'settings'"
          class="tab-btn"
        >
          <SvgIcon class="tab-icon" name="settings" :size="16" />
          <span class="tab-label">设定管理</span>
        </button>
        <button 
          :class="{ active: activeTab === 'evolutions' }"
          @click="activeTab = 'evolutions'"
          class="tab-btn"
        >
          <SvgIcon class="tab-icon" name="swirl" :size="16" />
          <span class="tab-label">推演记录</span>
        </button>
        <button 
          :class="{ active: activeTab === 'timeline' }"
          @click="activeTab = 'timeline'"
          class="tab-btn"
        >
          <SvgIcon class="tab-icon" name="clock" :size="16" />
          <span class="tab-label">时间线</span>
        </button>
        <button 
          :class="{ active: activeTab === 'map' }"
          @click="activeTab = 'map'"
          class="tab-btn"
        >
          <SvgIcon class="tab-icon" name="map" :size="16" />
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
            <p class="section-description">上传文件、输入文本，或直接扫描当前世界观已索引的知识库内容</p>
          </div>
          <div class="extract-toolbar">
            <div class="llm-status-chip" :class="{ 'is-ready': hasLlmConfig, 'is-missing': !hasLlmConfig }">
              <span class="llm-status-dot"></span>
              <span>{{ llmStatusText }}</span>
            </div>
            <button class="btn btn-secondary" @click="goToLlmConfig">
              配置 LLM
            </button>
          </div>

          <div class="form-section extraction-template-section">
            <div class="section-header compact-header">
              <h3 class="section-title small-title">世界模板</h3>
            </div>
            <div class="template-candidate-bar">
              <span class="template-candidate-label">候选模板</span>
              <div class="template-candidate-row">
                <button
                  v-for="template in templateCandidates"
                  :key="template.id"
                  type="button"
                  class="template-candidate-btn"
                  :class="{ active: template.id === selectedTemplateId }"
                  @click="selectedTemplateId = template.id"
                >
                  <span class="template-candidate-name">{{ template.name }}</span>
                  <span v-if="template.id === worldTemplateDefaultId" class="template-candidate-badge">默认</span>
                </button>
              </div>
            </div>
            <div class="single-template-panel card">
              <div class="single-template-main">
                <div class="single-template-title-row">
                  <strong class="single-template-title">{{ selectedWorldTemplate?.name || '通用模板' }}</strong>
                  <span class="template-badge">默认模板</span>
                </div>
                <p class="single-template-description">{{ templateSelectionNotice }}</p>
                <div v-if="selectedTemplateSectionNames.length > 0" class="template-tag-row">
                  <span v-for="section in selectedTemplateSectionNames" :key="`section-${section}`" class="template-tag">{{ section }}</span>
                </div>
              </div>
              <router-link
                class="template-detail-link"
                :to="{ name: 'WorldTemplateDetail', params: { templateId: selectedWorldTemplate?.id || worldTemplateDefaultId } }"
              >
                查看详情
              </router-link>
            </div>
          </div>

          <div class="form-section extraction-source-section">
            <div class="section-header compact-header">
              <h3 class="section-title small-title">扫描来源</h3>
              <span class="llm-status-chip">同一界面支持输入与知识库联合扫描</span>
            </div>
            <div class="type-selector">
              <button type="button" class="type-btn" :class="{ active: extractScanSource === 'input' }" @click="extractScanSource = 'input'; extractError = ''">
                上传/输入文本
                <span>保持当前行为，上传文件或直接粘贴文本后进行扫描</span>
              </button>
              <button type="button" class="type-btn" :class="{ active: extractScanSource === 'rag' }" @click="extractScanSource = 'rag'; extractError = ''">
                已有 RAG 知识库
                <span>不上传新内容，直接扫描当前世界观已索引的知识库</span>
              </button>
              <button type="button" class="type-btn" :class="{ active: extractScanSource === 'input_and_rag' }" @click="extractScanSource = 'input_and_rag'; extractError = ''">
                上传/输入 + 知识库
                <span>把新上传/输入内容与已有知识库一起扫描，只索引新内容</span>
              </button>
            </div>
            <p class="extract-source-note" :class="{ 'is-warning': extractUsesRagSource && !worldId }">{{ extractSourceNotice }}</p>
            <div class="extract-guidance">
              <p class="extract-guidance-item">文风分析已暂停以节省 token。</p>
              <p class="extract-guidance-item">人物简介会限长，但阶段成长、实力变化、性格变化、关键转折会完整保留。</p>
            </div>
          </div>

          <!-- 文件上传区域 -->
          <div v-if="extractNeedsManualInput" class="form-group form-group-full">
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
                <span class="file-drop-icon"><SvgIcon name="file" :size="38" :stroke-width="1.6" /></span>
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
                <button class="file-remove-btn" @click="removeFile(index)" title="移除文件"><SvgIcon name="close" :size="13" /></button>
              </div>
            </div>
          </div>
          <div v-else class="extract-source-note">
            当前模式将直接扫描当前世界观绑定的 RAG 知识库内容，不需要上传文件或填写文本。
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

          <div class="form-section extraction-mode-section">
            <div class="section-header compact-header">
              <h3 class="section-title small-title">扫描模式</h3>
              <span class="llm-status-chip">统一 RAG 向量索引</span>
            </div>
            <div class="type-selector">
              <button type="button" class="type-btn" :class="{ active: extractionMode === 'fast' }" @click="extractionMode = 'fast'">
                快速扫描
                <span>大块并行，适合快速生成世界观草稿</span>
              </button>
              <button type="button" class="type-btn" :class="{ active: extractionMode === 'deep' }" @click="extractionMode = 'deep'">
                深度扫描
                <span>线性滚动，保留摘要与实体快照</span>
              </button>
            </div>
          </div>

          <div v-if="extractNeedsManualInput" class="form-group form-group-full">
            <label class="form-label">或直接输入世界观文本</label>
            <textarea
              v-model="extractText"
              placeholder="粘贴世界观描述文本，AI将自动提取关键信息..."
              rows="6"
              class="form-textarea"
            ></textarea>
          </div>
          <div class="extract-action-row">
            <button
              @click="extractWorldInfo(false)"
              :disabled="!canExtractWorld"
              class="btn btn-primary extract-btn"
            >
              {{ isExtracting ? '提取中...' : '提取世界观信息' }}
            </button>
            <button
              @click="extractWorldInfo(true)"
              :disabled="!canExtractWorld"
              class="btn btn-primary extract-btn"
            >
              重新完整扫描
            </button>
            <button
              v-if="extractTaskId && !showExtractScanModal"
              type="button"
              @click="openExtractScanPanel()"
              class="btn btn-secondary extract-btn"
            >
              打开扫描窗口
            </button>
          </div>

          <!-- 提取进度条 -->
          <div v-if="(isExtracting || isScanCompleted) && extractProgress.message" class="extract-progress">
            <div class="progress-bar-container">
              <div class="progress-bar-fill" :style="{ width: extractProgress.progress + '%' }"></div>
            </div>
            <div class="progress-info">
              <span class="progress-stage">{{ extractProgress.message }}</span>
              <span class="progress-pct">{{ extractProgress.progress }}%</span>
            </div>
            <div v-if="scanCompletionText" class="scan-complete-banner">{{ scanCompletionText }}</div>
            <div v-if="scanEstimateText" class="cache-progress-note">
              {{ scanEstimateText }}<span v-if="scanEstimateSourceText">（{{ scanEstimateSourceText }}）</span>
            </div>
            <div v-if="cacheProgressText" class="cache-progress-note">{{ cacheProgressText }}</div>
            <div v-if="extractProgress.ragProgress" class="rag-sub-progress">
              <div class="rag-sub-header">
                <span>RAG 向量索引</span>
                <span>{{ extractProgress.ragProgress.progress || 0 }}%</span>
              </div>
              <div class="progress-bar-container sub-progress-bar">
                <div class="progress-bar-fill rag-progress-fill" :style="{ width: (extractProgress.ragProgress.progress || 0) + '%' }"></div>
              </div>
              <p class="rag-sub-message">{{ extractProgress.ragProgress.message }}</p>
              <p v-if="ragDocumentText" class="rag-sub-message">{{ ragDocumentText }}</p>
            </div>
            <div v-if="extractionMode === 'deep' && deepStateText" class="cache-progress-note">{{ deepStateText }}</div>
            <div v-if="scanActivityText" class="cache-progress-note scan-live-note"><span class="scan-live-dot"></span>{{ scanActivityText }}</div>
            <div v-if="canPauseExtract || canCancelExtract" class="extract-inline-actions">
              <button v-if="canPauseExtract" type="button" class="btn btn-secondary" :disabled="isPausingExtract || isCancellingExtract" @click="pauseExtraction">
                {{ isPausingExtract ? '暂停中...' : '暂停' }}
              </button>
              <button v-if="canCancelExtract" type="button" class="btn btn-secondary" :disabled="isCancellingExtract" @click="cancelExtraction">
                {{ isCancellingExtract ? '正在中止...' : '强制中止' }}
              </button>
            </div>
          </div>

          <p v-if="extractError" class="extract-error">{{ extractError }}</p>

          <div v-if="showExtractScanModal" class="deep-scan-overlay">
            <div class="deep-scan-modal">
              <div class="deep-scan-top">
                <div class="deep-scan-title-row">
                  <h3>{{ scanModalTitle }}</h3>
                  <div class="scan-title-actions">
                    <span>{{ extractProgress.progress || 0 }}%</span>
                    <button type="button" class="scan-close-btn" @click="closeExtractScanPanel" title="关闭扫描窗口"><SvgIcon name="close" :size="14" /></button>
                  </div>
                </div>
                <div class="progress-bar-container deep-main-bar">
                  <div class="progress-bar-fill" :style="{ width: (extractProgress.progress || 0) + '%' }"></div>
                </div>
                <div v-if="scanCompletionText" class="scan-complete-banner">{{ scanCompletionText }}</div>
                <div v-if="scanEstimateText" class="deep-scan-meta">
                  {{ scanEstimateText }}<span v-if="scanEstimateSourceText">（{{ scanEstimateSourceText }}）</span>
                </div>
                <div class="deep-scan-meta">已处理: {{ deepProcessedText }} / {{ extractProgress.detail?.total_chars_label || '未知总量' }}</div>
                <div v-if="scanActivityText" class="deep-scan-meta scan-live-note"><span class="scan-live-dot"></span>{{ scanActivityText }}</div>
              </div>

              <div class="deep-scan-section">
                <div class="deep-row">
                  <span class="deep-label">当前状态</span>
                  <strong>{{ extractProgress.message || scanStatusLabel }}</strong>
                </div>
                <div class="deep-row">
                  <span class="deep-label">当前阅读</span>
                  <strong>{{ deepCurrentTitle }}</strong>
                </div>
                <div v-if="scanHeartbeatText" class="deep-row">
                  <span class="deep-label">活跃心跳</span>
                  <strong>{{ scanHeartbeatText }}</strong>
                </div>
                <div class="deep-row stacked">
                  <span class="deep-label">块进度</span>
                  <div class="progress-bar-container deep-chunk-bar">
                    <div class="progress-bar-fill" :style="{ width: scanChunkProgress + '%' }"></div>
                  </div>
                  <span>{{ scanChunkProgress }}%</span>
                </div>
                <div class="deep-scan-meta">{{ scanChunkText }}</div>
              </div>

              <div v-if="extractProgress.ragProgress" class="deep-scan-section">
                <h4>RAG 向量索引</h4>
                <div class="progress-bar-container deep-chunk-bar">
                  <div class="progress-bar-fill rag-progress-fill" :style="{ width: (extractProgress.ragProgress.progress || 0) + '%' }"></div>
                </div>
                <p class="deep-empty">{{ extractProgress.ragProgress.message }}</p>
              </div>

              <div class="deep-scan-section">
                <h4>
                  <SvgIcon :name="extractionMode === 'deep' ? 'book' : 'box'" :size="16" />
                  {{ extractionMode === 'deep' ? '实时发现实体' : '快速扫描进度' }}
                </h4>
                <ul v-if="deepDiscoveries.length" class="deep-discovery-list">
                  <li v-for="(item, index) in deepDiscoveries" :key="index">{{ item }}</li>
                </ul>
                <p v-else class="deep-empty">{{ scanDiscoveryFallback }}</p>
              </div>

              <div class="deep-scan-section">
                <h4>
                  <SvgIcon name="brain" :size="16" />
                  {{ extractionMode === 'deep' ? '模型思考摘要' : '扫描摘要' }}
                </h4>
                <p class="deep-summary">{{ deepThinkingSummary }}</p>
              </div>

              <div class="deep-scan-footer">
                <div class="deep-stats-row">
                  <span v-for="item in deepKnowledgeStats" :key="item.label">{{ item.label }}({{ item.count }})</span>
                </div>
                <div class="deep-actions-row">
                  <button v-if="canPauseExtract" type="button" class="btn btn-secondary" :disabled="isPausingExtract || isCancellingExtract" @click="pauseExtraction">
                    {{ isPausingExtract ? '暂停中...' : '暂停' }}
                  </button>
                  <button v-if="canResumeExtract" type="button" class="btn btn-secondary" :disabled="isResumingExtract" @click="resumeExtraction">
                    {{ isResumingExtract ? '继续中...' : '继续' }}
                  </button>
                  <button v-if="canCancelExtract" type="button" class="btn btn-secondary" :disabled="isCancellingExtract" @click="cancelExtraction">
                    {{ isCancellingExtract ? '正在中止...' : '强制中止当前扫描' }}
                  </button>
                  <button v-if="canDeleteExtract" type="button" class="btn btn-danger" :disabled="isDeletingExtractTask" @click="deleteExtractionTask">
                    {{ isDeletingExtractTask ? '删除中...' : '删除扫描' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div v-if="extractedData && !showExtractResultDialog" class="extract-result-reminder">
            <span>已有未应用的扫描结果：{{ extractedResultSummaryText }}</span>
            <button type="button" class="btn btn-secondary" @click="openExtractResultDialog(false)">查看结果并选择是否应用</button>
          </div>
        </div>

        <div v-if="showExtractResultDialog && extractedData" class="dialog extract-result-dialog-overlay">
          <div class="dialog-content extract-result-dialog">
            <div class="dialog-header">
              <div>
                <h2 class="dialog-title">扫描解析已完成</h2>
                <p class="dialog-subtitle">请检查解析结果，并选择是否合并到当前世界观。</p>
              </div>
              <button class="close-btn" @click="dismissExtractResultDialog" title="稍后处理"><SvgIcon name="close" :size="16" /></button>
            </div>
            <div class="dialog-body">
              <div class="extract-result-summary-grid">
                <div>
                  <span>实体</span>
                  <strong>{{ extractedResultSummary.entities }}</strong>
                </div>
                <div>
                  <span>事件</span>
                  <strong>{{ extractedResultSummary.events }}</strong>
                </div>
                <div>
                  <span>设定</span>
                  <strong>{{ extractedResultSummary.settings }}</strong>
                </div>
                <div>
                  <span>扫描模式</span>
                  <strong>{{ extractionMode === 'deep' ? '深度扫描' : '快速扫描' }}</strong>
                </div>
              </div>
              <div v-if="extractedData.rag_indexed" class="rag-index-badge result-rag-badge">
                已索引 {{ extractedData.rag_document_count || 0 }} 条至 RAG 知识库
              </div>
              <div v-if="hasExtractionFailures" class="extract-warning">
                有 {{ extractionDiagnostics.failed_chunks.length }} / {{ extractionDiagnostics.total_chunks }} 个章节组解析失败，当前结果可能不完整。可以暂不应用，调整后重新扫描。
              </div>
              <div class="preview-content">
                <pre class="preview-code result-preview-code">{{ JSON.stringify(extractedData, null, 2) }}</pre>
              </div>
              <p class="preview-note">应用会保留当前已编辑内容，仅补充新增信息，并尽量合并重复实体、事件和设定。</p>
            </div>
            <div class="dialog-actions extract-result-actions">
              <button type="button" class="btn btn-secondary" @click="dismissExtractResultDialog">暂不应用</button>
              <button type="button" class="btn btn-danger" @click="discardExtractedData">不应用并丢弃</button>
              <button type="button" class="btn btn-primary" @click="applyExtractedData">应用到世界观</button>
            </div>
          </div>
        </div>

        <div v-if="showLlmConfigDialog" class="dialog">
          <div class="dialog-content llm-config-dialog">
            <div class="dialog-header">
              <h2 class="dialog-title">配置 LLM 提取服务</h2>
              <button class="close-btn" @click="closeLlmConfigDialog" title="关闭"><SvgIcon name="close" :size="16" /></button>
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
            <SvgIcon class="collapse-arrow" :name="showEntitiesExpanded ? 'chevron-down' : 'chevron-right'" :size="14" />
            <h3 class="overview-title">核心实体 ({{ entities.length }})</h3>
            <span class="enabled-count">已启用 {{ enabledEntityCount }}</span>
            <div class="entity-layout-control" @click.stop>
              <span class="entity-layout-control-label">按行对齐</span>
              <label class="toggle-switch entity-layout-toggle">
                <input type="checkbox" :checked="entityCardRowAligned" @change="toggleEntityCardRowAlignment" />
                <span class="toggle-slider"></span>
              </label>
            </div>
          </div>
          <div v-if="entities.length === 0" class="overview-empty">暂无实体数据，导入或提取世界观后自动填充</div>
          <div
            v-else-if="showEntitiesExpanded"
            class="entity-card-list entity-card-grid"
            :class="{ 'entity-card-grid-row-aligned': entityCardRowAligned }"
          >
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
                <div class="entity-card-actions">
                  <button type="button" class="entity-setting-link" @click.stop="openLinkedSetting(d.entity)">
                    {{ d.hasSetting ? '查看对应设定' : '生成对应设定' }}
                  </button>
                  <button type="button" class="entity-delete-link" @click.stop="deleteEntity(d.entity.id)">
                    删除实体
                  </button>
                </div>
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
            <SvgIcon class="collapse-arrow" :name="showEventsExpanded ? 'chevron-down' : 'chevron-right'" :size="14" />
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
                    <div class="tree-item category-item" :class="{ expanded: category.expanded }" @click="toggleCategory(category.id)">
                      <SvgIcon class="expand-icon" :name="category.expanded ? 'chevron-down' : 'chevron-right'" :size="13" />
                      <SvgIcon class="category-icon" :name="category.icon" :size="15" />
                      <span class="category-name">{{ category.name }}</span>
                    </div>
                    <div v-if="category.expanded" class="tree-children">
                      <div v-for="collection in getCollectionsByCategory(category.id)" :key="collection.id" class="tree-node">
                        <div
                          class="tree-item collection-item"
                          :class="{ active: activeSettingCollection && activeSettingCollection.id === collection.id }"
                          @click="openSettingCollection(collection)"
                        >
                          <button
                            type="button"
                            class="tree-expand-button"
                            @click.stop="toggleCollectionExpand(collection.id)"
                            :title="collection.expanded ? '折叠设定集' : '展开设定集'"
                          >
                            <SvgIcon class="expand-icon" :name="collection.expanded ? 'chevron-down' : 'chevron-right'" :size="13" />
                          </button>
                          <button
                            type="button"
                            class="tree-item-main collection-item-main"
                            @click.stop="openSettingCollection(collection)"
                          >
                            <SvgIcon class="collection-icon" name="folder" :size="15" />
                            <span class="collection-name">{{ collection.name }}</span>
                          </button>
                        </div>
                        <div v-if="collection.expanded" class="tree-children">
                          <div
                            v-for="setting in getSettingsByCollection(collection.id)"
                            :key="setting.id"
                            class="tree-item setting-item"
                            :class="{ active: activeSidebarSettingId === setting.id || currentSetting?.id === setting.id }"
                            @click="openSidebarSetting(setting)"
                          >
                            <SvgIcon class="setting-icon" name="file" :size="14" />
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
                <input
                  type="text"
                  v-model="settingsSearchQuery"
                  placeholder="搜索设定标题、描述、别名或详细内容..."
                  class="search-input"
                >
              </div>
              <div class="header-actions">
                <button class="btn btn-primary new-setting-btn" @click="openNewSettingDialog"><SvgIcon name="plus" :size="15" /> 新建设定</button>
              </div>
            </div>

            <div v-if="activeSettingCollection" class="settings-filter-bar">
              <span class="settings-filter-chip">当前设定集：{{ activeSettingCollection.name }}</span>
              <button type="button" class="settings-filter-clear" @click="clearActiveCollectionFilter">显示当前分类全部设定</button>
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
                <span>轮次: {{ (record.rounds || []).length }} / {{ getEvolutionTotalRounds(record) }}</span>
                <span v-if="isEvolutionActive(record)">进度: {{ getEvolutionProgress(record) }}%</span>
                <span>更新时间: {{ formatDateTime(record.updated_at || record.created_at) }}</span>
              </div>
              <div v-if="isEvolutionActive(record)" class="evolution-history-progress">
                <div class="evolution-history-progress-fill" :style="{ width: getEvolutionProgress(record) + '%' }"></div>
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
      <div v-if="activeTab === 'timeline'" class="tab-pane timeline-section timeline-workspace">
        <div class="timeline-hero-panel">
          <div class="timeline-hero-copy">
            <span class="timeline-eyebrow">Chronology Workspace</span>
            <h3 class="header-title">世界时间线</h3>
            <p class="header-description">
              用故事线、历法和诊断三种视图理解世界历史。旧版历法、事件日期、实体阶段会自动兼容并转换为可读时间点。
            </p>
          </div>
          <div class="timeline-actions">
            <div class="timeline-view-tabs" role="tablist" aria-label="时间线视图">
              <button type="button" :class="{ active: timelineViewMode === 'story' }" @click="timelineViewMode = 'story'"><SvgIcon name="timeline-node" :size="14" />故事线</button>
              <button type="button" :class="{ active: timelineViewMode === 'calendar' }" @click="timelineViewMode = 'calendar'"><SvgIcon name="clock" :size="14" />历法</button>
              <button type="button" :class="{ active: timelineViewMode === 'diagnostics' }" @click="timelineViewMode = 'diagnostics'"><SvgIcon name="info" :size="14" />诊断</button>
            </div>
            <button class="btn btn-secondary calendar-edit-btn" @click="openCalendarEdit">
              <SvgIcon name="clock" :size="15" />
              历法编辑
            </button>
          </div>
        </div>

        <div class="timeline-overview-grid">
          <div class="timeline-overview-card is-primary">
            <span>覆盖范围</span>
            <strong>{{ timelineOverviewStats.range }}</strong>
            <small>按可解析数据自动推断</small>
          </div>
          <div class="timeline-overview-card">
            <span>故事事件</span>
            <strong>{{ timelineOverviewStats.events }}</strong>
            <small>{{ timelineOverviewStats.totalEvents }} 条原始事件</small>
          </div>
          <div class="timeline-overview-card">
            <span>实体阶段</span>
            <strong>{{ timelineOverviewStats.stages }}</strong>
            <small>{{ timelineOverviewStats.totalStages }} 个原始阶段</small>
          </div>
          <div class="timeline-overview-card" :class="{ 'has-warning': timelineOverviewStats.unresolved > 0 }">
            <span>待修复</span>
            <strong>{{ timelineOverviewStats.unresolved }}</strong>
            <small>无法定位或低置信数据</small>
          </div>
        </div>

        <div class="timeline-filter-row">
          <div class="timeline-search-box">
            <SvgIcon name="search" :size="16" />
            <input v-model="timelineSearchQuery" placeholder="搜索事件、实体、历法或描述..." />
          </div>
          <div class="timeline-filter-chips">
            <button type="button" :class="{ active: timelineTypeFilter === 'all' }" @click="timelineTypeFilter = 'all'"><SvgIcon name="grid" :size="13" />全部</button>
            <button type="button" :class="{ active: timelineTypeFilter === 'event' }" @click="timelineTypeFilter = 'event'"><SvgIcon name="bolt" :size="13" />事件</button>
            <button type="button" :class="{ active: timelineTypeFilter === 'stage' }" @click="timelineTypeFilter = 'stage'"><SvgIcon name="user" :size="13" />阶段</button>
            <button type="button" :class="{ active: timelineTypeFilter === 'calendar' }" @click="timelineTypeFilter = 'calendar'"><SvgIcon name="clock" :size="13" />历法</button>
          </div>
        </div>

        <div class="timeline-workspace-layout">
          <main class="timeline-main-panel">
            <section v-if="timelineViewMode === 'story'" class="timeline-story-view">
              <div v-if="chronologyGroups.length === 0" class="timeline-empty-state">
                <SvgIcon name="clock" :size="38" />
                <h4>暂无可定位时间点</h4>
                <p>请为事件填写明确年份，或在实体阶段中填写时期。无法解析的数据会出现在“诊断”视图。</p>
              </div>
              <article v-for="group in chronologyGroups" :key="group.key" class="chronology-group">
                <div class="chronology-year-rail">
                  <span class="chronology-year">{{ group.label }}</span>
                  <span class="chronology-count">{{ group.items.length }} 项</span>
                </div>
                <div class="chronology-card-stack">
                  <button
                    v-for="item in group.items"
                    :key="item.id"
                    type="button"
                    class="chronology-card"
                    :class="[`is-${item.type}`, { selected: selectedTimelineItemId === item.id, 'is-low-confidence': item.confidence === 'low' }]"
                    @click="selectTimelineItem(item)"
                  >
                    <span class="chronology-hover-card">
                      <strong>{{ item.title }}</strong>
                      <small>{{ item.subtitle || getTimelineItemTypeLabel(item.type) }}</small>
                      <em>{{ item.description || item.rawText || item.label }}</em>
                    </span>
                    <span class="chronology-card-icon"><SvgIcon :name="getTimelineItemIcon(item.type)" :size="17" /></span>
                    <span class="chronology-card-body">
                      <span class="chronology-card-kicker">{{ getTimelineItemTypeLabel(item.type) }} · {{ item.label }}</span>
                      <strong>{{ item.title }}</strong>
                      <small>{{ item.subtitle }}</small>
                    </span>
                    <span class="chronology-confidence" :class="`is-${item.confidence}`">{{ getTimelineConfidenceLabel(item.confidence) }}</span>
                  </button>
                </div>
              </article>
            </section>

            <section v-else-if="timelineViewMode === 'calendar'" class="timeline-calendar-view">
              <div class="calendar-graphic-panel">
                <div class="calendar-graphic-header">
                  <div>
                    <strong>纪元 / 纪年图形轴</strong>
                    <p>滚轮移动时间轴，按住 Ctrl + 滚轮缩放。开始/结束时间均按纯数字年份渲染。</p>
                  </div>
                  <span class="calendar-axis-meter">
                    <SvgIcon name="timeline-node" :size="14" />
                    {{ chronologyCalendarItems.length }} 条历法 · {{ Math.round(calendarGraphicZoom * 100) }}%
                  </span>
                </div>
                <div v-if="chronologyCalendarItems.length === 0" class="timeline-empty-state compact">
                  <SvgIcon name="clock" :size="34" />
                  <h4>暂无可图形化渲染的历法</h4>
                  <p>请在“历法编辑”里补充名称、基准时间或时间范围。</p>
                </div>
                <div
                  v-else
                  class="calendar-graphic-stage"
                  :style="{ height: calendarGraphicHeight + 'px' }"
                  @wheel="handleCalendarGraphicWheel"
                  tabindex="0"
                  aria-label="纪元和纪年图形时间轴，滚轮平移，按住 Ctrl 滚轮缩放"
                >
                  <div class="calendar-graphic-axis">
                    <div class="calendar-axis-line"></div>

                    <span
                      v-for="tick in calendarGraphicTicks"
                      :key="`calendar-tick-${tick.label}`"
                      class="calendar-axis-tick"
                      :style="{ left: getCalendarGraphicPosition(tick.year) + '%' }"
                    >{{ tick.label }}</span>
                  </div>
                  <div
                    v-for="row in calendarGraphicRows"
                    :key="row.id"
                    class="calendar-graphic-row"
                    :style="{ top: row.top + 'px' }"
                  >
                    <button
                      v-for="segment in row.items"
                      :key="`graphic-${segment.item.id}`"
                      type="button"
                      class="calendar-graphic-band"
                      :class="getCalendarGraphicBandClass(segment)"
                      :style="getCalendarGraphicBandStyle(segment)"
                      @click="selectTimelineItem(segment.item)"
                    >
                      <span class="calendar-band-title">{{ segment.item.title }}</span>
                      <span class="calendar-band-range">{{ segment.item.label }}</span>
                      <span class="calendar-band-duration">{{ segment.durationLabel }}</span>
                      <span class="calendar-band-hover-card">
                        <strong>{{ segment.item.title }}</strong>
                        <small>{{ segment.item.label }} · {{ segment.durationLabel }}</small>
                        <em>{{ segment.item.subtitle }}</em>
                        <em v-if="segment.item.description">{{ segment.item.description }}</em>
                      </span>
                    </button>
                  </div>
                </div>
              </div>

              <div class="calendar-view-columns">
                <div class="calendar-view-column">
                  <div class="calendar-view-title">纪元</div>
                  <button
                    v-for="item in chronologyCalendarItems.filter(calendar => calendar.kind === 'era')"
                    :key="item.id"
                    type="button"
                    class="calendar-line-card"
                    :class="{ selected: selectedTimelineItemId === item.id }"
                    @click="selectTimelineItem(item)"
                  >
                    <span class="calendar-line-name">{{ item.title }}</span>
                    <span class="calendar-line-range">{{ item.label }} · {{ item.subtitle }}</span>
                  </button>
                  <div v-if="chronologyCalendarItems.filter(calendar => calendar.kind === 'era').length === 0" class="timeline-empty-hint">暂无纪元。</div>
                </div>
                <div class="calendar-view-column">
                  <div class="calendar-view-title">纪年</div>
                  <button
                    v-for="item in chronologyCalendarItems.filter(calendar => calendar.kind === 'year')"
                    :key="item.id"
                    type="button"
                    class="calendar-line-card"
                    :class="{ selected: selectedTimelineItemId === item.id }"
                    @click="selectTimelineItem(item)"
                  >
                    <span class="calendar-line-name">{{ item.title }}</span>
                    <span class="calendar-line-range">{{ item.label }} · {{ item.subtitle }}</span>
                  </button>
                  <div v-if="chronologyCalendarItems.filter(calendar => calendar.kind === 'year').length === 0" class="timeline-empty-hint">暂无纪年。</div>
                </div>
              </div>
            </section>

            <section v-else class="timeline-diagnostics-view">
              <div class="diagnostics-header-card">
                <SvgIcon name="info" :size="20" />
                <div>
                  <strong>时间解析诊断</strong>
                  <p>这些条目不会丢失，只是暂时无法放到故事线中。补充明确年份或历法基准后会自动进入时间线。</p>
                </div>
              </div>
              <div v-if="timelineUnresolvedItems.length === 0" class="timeline-empty-state compact">
                <SvgIcon name="check" :size="34" />
                <h4>没有需要修复的时间数据</h4>
                <p>当前事件、阶段和历法都可以被新版时间线识别。</p>
              </div>
              <button
                v-for="item in timelineUnresolvedItems"
                :key="item.id"
                type="button"
                class="diagnostic-row"
                :class="`is-${item.type}`"
                @click="selectTimelineItem(item)"
              >
                <span class="diagnostic-icon"><SvgIcon :name="getTimelineItemIcon(item.type)" :size="16" /></span>
                <span class="diagnostic-main">
                  <strong>{{ item.title }}</strong>
                  <small>{{ item.reason }}</small>
                </span>
                <span class="diagnostic-raw">{{ item.rawText || '无时间文本' }}</span>
              </button>
            </section>
          </main>

        </div>
      </div>

      <!-- 地图 -->
      <div v-if="activeTab === 'map'" class="tab-pane map-section">
        <div class="section-header">
          <h3 class="section-title">世界观结构化地图</h3>
          <p class="section-description">用区域单元承载地形、势力、资源、事件和世界观实体位置。</p>
        </div>

        <WorldMapEditor
          :world-id="worldId"
          :initial-maps="mapData.structuredMaps || []"
          :entities="entities"
          :events="events"
          @need-world-id="ensureWorldId"
          @maps-change="updateStructuredMaps"
        />

        <details class="legacy-map-details">
          <summary>旧版地图概述文本</summary>
          <div class="map-form legacy-map-form">
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
        </details>
      </div>

      <!-- 历法编辑窗口 -->
      <div v-if="showCalendarEdit" class="dialog">
        <div class="dialog-content calendar-edit-dialog">
          <div class="dialog-header">
            <h2 class="dialog-title">历法编辑</h2>
            <button class="close-btn" @click="cancelCalendarEdit" title="关闭"><SvgIcon name="close" :size="16" /></button>
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
                      <button class="btn btn-secondary edit-btn icon-only" @click="editCalendar(calendar)" title="编辑历法"><SvgIcon name="edit" :size="14" /></button>
                      <button class="btn btn-danger delete-btn icon-only" @click="deleteCalendar(calendar.id)" title="删除历法"><SvgIcon name="trash" :size="14" /></button>
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
                  <li><SvgIcon name="timeline-node" :size="13" /> 纪元：用于记录世界大事件的历法体系</li>
                  <li><SvgIcon name="timeline-node" :size="13" /> 纪年：用于记录政权或朝代的历法</li>
                </ul>
              </div>
              <div class="info-section">
                <h4 class="info-subtitle">时间单位：</h4>
                <ul class="info-list">
                  <li><SvgIcon name="timeline-node" :size="13" /> 可自定义时间单位名称和符号</li>
                  <li><SvgIcon name="timeline-node" :size="13" /> 比例系数表示该单位与基准年的关系</li>
                  <li><SvgIcon name="timeline-node" :size="13" /> 如：1纪元 = 2基准年，则比例系数为2</li>
                </ul>
              </div>
              <div class="info-section">
                <h4 class="info-subtitle">年份规则：</h4>
                <ul class="info-list">
                  <li><SvgIcon name="timeline-node" :size="13" /> 纪元历法之间不能重叠</li>
                  <li><SvgIcon name="timeline-node" :size="13" /> 纪元首尾相接不算重叠</li>
                  <li><SvgIcon name="timeline-node" :size="13" /> 仅第一个纪元可设置无开始时间</li>
                  <li><SvgIcon name="timeline-node" :size="13" /> 仅最后一个纪元可设置无结束时间</li>
                  <li><SvgIcon name="timeline-node" :size="13" /> 所有纪年历法可设置无结束时间</li>
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
            <button class="close-btn" @click="cancelCalendarDetailEdit" title="关闭"><SvgIcon name="close" :size="16" /></button>
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
              <label class="form-label">* 开始时间</label>
              <input type="number" step="1" v-model.number="currentCalendar.startYear" class="form-input" placeholder="仅输入数字，如：0">
            </div>
              <div class="form-group">
                <label class="form-label">结束年份</label>
                <div class="end-year-input">
                  <input type="number" step="1" v-model.number="currentCalendar.endYear" class="form-input" placeholder="仅输入数字" :disabled="currentCalendar.noEndTime">
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
                <label class="form-label">客观基准时间</label>
                <input type="text" v-model="currentCalendar.absoluteBaseTime" class="form-input" placeholder="如：公元2000年">
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
            <button class="close-btn" @click="closeNewSettingDialog" title="关闭"><SvgIcon name="close" :size="16" /></button>
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
                      <button class="remove-alias" @click="removeAlias(index)" title="移除别名"><SvgIcon name="close" :size="13" /></button>
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
                    <option value="">自动归入当前分类通用设定集</option>
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
            <button class="btn btn-secondary save-draft-btn"><SvgIcon name="save" :size="15" /> 保存提案</button>
            <button class="btn btn-primary submit-btn" @click="saveNewSetting"><SvgIcon name="arrow-right" :size="15" /> 提交提案</button>
          </div>
        </div>
      </div>
      
      <!-- 设定详情对话框 -->
      <div v-if="showSettingDetail && currentSetting" class="dialog">
        <div class="dialog-content setting-detail-dialog setting-detail-workbench">
          <div class="dialog-header setting-detail-topbar">
            <div>
              <span class="detail-eyebrow">SETTING WORKBENCH</span>
              <h2 class="dialog-title">{{ currentSetting.name }} - 详情编辑</h2>
            </div>
            <button class="close-btn" @click="closeSettingDetail" title="关闭"><SvgIcon name="close" :size="16" /></button>
          </div>
          
          <div class="setting-detail-content setting-detail-editor">
            <aside class="setting-detail-profile">
              <div class="detail-profile-card">
                <div class="detail-avatar">{{ currentSettingInitial }}</div>
                <div class="detail-info">
                  <input
                    v-model="currentSetting.name"
                    class="detail-title-input"
                    placeholder="设定名称"
                  >
                  <textarea
                    v-model="currentSetting.description"
                    class="detail-description-input"
                    placeholder="卡片摘要 / 一句话简介"
                    rows="6"
                  ></textarea>
                </div>
              </div>

              <div class="detail-meta-grid">
                <label class="detail-meta-field">
                  <span>类型</span>
                  <select v-model="currentSetting.settingType" class="form-select">
                    <option value="setting">设定</option>
                    <option value="collection">设定集</option>
                  </select>
                </label>
                <label class="detail-meta-field">
                  <span>分类</span>
                  <select v-model="currentSetting.category" class="form-select" @change="assignCurrentSettingDefaultCollection">
                    <option v-for="category in settingCategories" :key="category.id" :value="category.id">
                      {{ category.name }}
                    </option>
                  </select>
                </label>
                <label class="detail-meta-field detail-meta-field-wide">
                  <span>所属设定集</span>
                  <select v-model="currentSetting.collectionId" class="form-select">
                    <option value="">自动归入当前分类通用设定集</option>
                    <option
                      v-for="collection in settingCollections"
                      :key="collection.id"
                      :value="collection.id"
                      :disabled="collection.id === currentSetting.id"
                    >
                      {{ collection.name }}
                    </option>
                  </select>
                </label>
              </div>

              <div class="detail-alias-editor">
                <div class="detail-panel-heading">
                  <strong>别名</strong>
                  <span>{{ currentSetting.aliases?.length || 0 }}</span>
                </div>
                <div class="alias-chips editable-aliases">
                  <span v-for="(alias, index) in currentSetting.aliases" :key="`${alias}-${index}`" class="alias-chip">
                    {{ alias }}
                    <button type="button" @click="removeCurrentSettingAlias(index)">×</button>
                  </span>
                  <span v-if="!currentSetting.aliases || currentSetting.aliases.length === 0" class="empty-inline-hint">暂无别名</span>
                </div>
                <div class="alias-input-row">
                  <input
                    v-model="currentSettingNewAlias"
                    class="form-input"
                    placeholder="新增别名"
                    @keyup.enter="addCurrentSettingAlias"
                  >
                  <button type="button" class="btn btn-secondary" @click="addCurrentSettingAlias">添加</button>
                </div>
              </div>

              <div v-if="currentSettingLinkedEntity" class="linked-entity-panel">
                <div class="detail-panel-heading">
                  <strong>关联实体</strong>
                  <span>{{ currentSettingLinkedEntity.type || '未分类' }}</span>
                </div>
                <p>{{ currentSettingLinkedEntity.name }}</p>
                <button type="button" class="btn btn-secondary" @click="refreshCurrentSettingFromEntity">
                  从实体同步结构化内容
                </button>
              </div>
            </aside>
            
            <main class="setting-detail-main">
              <section class="detail-editor-section is-wide">
                <div class="detail-panel-heading">
                  <strong>核心简介</strong>
                  <span>INTRO</span>
                </div>
                <textarea
                  v-model="currentSetting.structuredDetail.intro"
                  class="form-textarea structured-intro-textarea"
                  placeholder="概括这个设定的本质、背景、用途或叙事定位..."
                  rows="8"
                ></textarea>
              </section>

              <section class="detail-editor-section">
                <div class="detail-panel-heading">
                  <strong>关键事实</strong>
                  <button type="button" class="inline-add-btn" @click="addSettingFact">+ 字段</button>
                </div>
                <div class="structured-field-list">
                  <div
                    v-for="(field, index) in currentSetting.structuredDetail.facts"
                    :key="field.id"
                    class="structured-field-row"
                  >
                    <input v-model="field.label" class="form-input" placeholder="字段名">
                    <input v-model="field.value" class="form-input" placeholder="字段内容">
                    <button type="button" class="icon-remove-btn" @click="removeSettingFact(index)">×</button>
                  </div>
                  <div v-if="!currentSetting.structuredDetail.facts.length" class="empty-structured-state">
                    暂无关键事实，可添加如身份、阵营、能力、地点等字段。
                  </div>
                </div>
              </section>

              <section class="detail-editor-section">
                <div class="detail-panel-heading">
                  <strong>关系网络</strong>
                  <button type="button" class="inline-add-btn" @click="addSettingRelationship">+ 关系</button>
                </div>
                <div class="structured-card-editor-list">
                  <article
                    v-for="(relationship, index) in currentSetting.structuredDetail.relationships"
                    :key="relationship.id"
                    class="structured-card-editor"
                  >
                    <div class="structured-card-editor-header">
                      <input v-model="relationship.target" class="form-input" placeholder="关联对象">
                      <input v-model="relationship.type" class="form-input" placeholder="关系类型">
                      <button type="button" class="icon-remove-btn" @click="removeSettingRelationship(index)">×</button>
                    </div>
                    <textarea v-model="relationship.description" class="form-textarea structured-description-textarea" placeholder="关系描述" rows="5"></textarea>
                    <div class="structured-card-editor-grid">
                      <input v-model="relationship.time_period" class="form-input" placeholder="时期 / 时间段">
                      <input v-model="relationship.source_event" class="form-input" placeholder="来源事件">
                    </div>
                  </article>
                  <div v-if="!currentSetting.structuredDetail.relationships.length" class="empty-structured-state">
                    暂无关系记录，可添加关联人物、组织、地点或事件。
                  </div>
                </div>
              </section>

              <section class="detail-editor-section is-wide">
                <div class="detail-panel-heading">
                  <strong>阶段 / 演变</strong>
                  <button type="button" class="inline-add-btn" @click="addSettingStage">+ 阶段</button>
                </div>
                <div class="structured-card-editor-list">
                  <article
                    v-for="(stage, stageIndex) in currentSetting.structuredDetail.stages"
                    :key="stage.id"
                    class="structured-card-editor stage-editor-card"
                  >
                    <div class="structured-card-editor-header">
                      <input v-model="stage.name" class="form-input" placeholder="阶段名称">
                      <input v-model="stage.era" class="form-input" placeholder="时期">
                      <button type="button" class="icon-remove-btn" @click="removeSettingStage(stageIndex)">×</button>
                    </div>
                    <textarea v-model="stage.description" class="form-textarea structured-description-textarea" placeholder="阶段描述" rows="5"></textarea>
                    <div class="detail-panel-heading compact-heading">
                      <strong>阶段字段</strong>
                      <button type="button" class="inline-add-btn" @click="addSettingStageField(stageIndex)">+ 字段</button>
                    </div>
                    <div class="structured-field-list compact-field-list">
                      <div v-for="(field, fieldIndex) in stage.fields" :key="field.id" class="structured-field-row">
                        <input v-model="field.label" class="form-input" placeholder="字段名">
                        <input v-model="field.value" class="form-input" placeholder="字段内容">
                        <button type="button" class="icon-remove-btn" @click="removeSettingStageField(stageIndex, fieldIndex)">×</button>
                      </div>
                    </div>
                  </article>
                  <div v-if="!currentSetting.structuredDetail.stages.length" class="empty-structured-state">
                    暂无阶段记录，可添加成长阶段、历史时期或版本演变。
                  </div>
                </div>
              </section>

              <section class="detail-editor-section is-wide">
                <div class="detail-panel-heading">
                  <strong>{{ currentSettingDetailLabel }}</strong>
                  <span>FREEFORM</span>
                </div>
                <p class="setting-detail-hint">
                  结构化内容会用于详情分栏与后续保存；这里保留自由文本，适合补充背景设定、人工修订和未归类说明。
                </p>
                <textarea 
                  v-model="currentSetting.detailContent" 
                  class="form-textarea detail-textarea" 
                  placeholder="输入详细内容..."
                  rows="12"
                ></textarea>
              </section>
            </main>
          </div>
          
          <div class="dialog-footer">
            <button
              v-if="currentSetting && currentSetting.settingType === 'setting'"
              class="btn btn-danger delete-btn"
              @click="deleteCurrentSetting"
            >
              删除设定
            </button>
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
            <button class="close-btn" @click="closeSettingSelector" title="关闭"><SvgIcon name="close" :size="16" /></button>
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
import { collabApi } from '../api/collab'
import { generateOntologyFromProject } from '../api/graph'
import service from '../api/index'
import WorldMapEditor from '../components/map/WorldMapEditor.vue'
import SvgIcon from '../components/ui/SvgIcon.vue'
import { ensureCollabIdentity } from '../utils/collabIdentity.js'
import {
  readEntityCardRowLayoutPreference,
  writeEntityCardRowLayoutPreference,
} from '../utils/entityCardLayoutPreference.js'

const LAST_EXTRACT_TASK_KEY = 'worldfish:lastExtractTaskId'
const EXTRACT_TASK_DELETED_EVENT = 'worldfish:extract-task-deleted'
const EXTRACT_TASK_SYNC_EVENT = 'worldfish:extract-task-sync'
const WORLD_UPDATED_EVENT = 'worldfish:world-updated'
const CLIENT_ID_KEY = 'worldfish:clientId'
const EDIT_HISTORY_LIMIT = 80
const EDIT_HISTORY_CAPTURE_DELAY = 350
const DEFAULT_WORLD_TEMPLATE_ID = 'generic'
const DND_WORLD_TEMPLATE_ID = 'dnd-campaign'
const CACHE_TTL_MS = 60000

let cachedWorldTemplates = null
let cachedWorldTemplatesAt = 0
let cachedLlmConfig = null
let cachedLlmConfigAt = 0
let cachedExtractSelectedFiles = []

const DEFAULT_TEMPLATE_DETAIL_SECTIONS = [
  {
    id: 'core_intro',
    name: '核心简介',
    target: 'entities[].attributes.简介 / settings.items[].structuredDetail.intro',
    description: '对象的高密度概览。',
  },
  {
    id: 'key_facts',
    name: '关键事实',
    target: 'entities[].attributes / settings.items[].structuredDetail.facts',
    description: '可复用的稳定事实字段。',
  },
  {
    id: 'relationships',
    name: '关系网络',
    target: 'entities[].relationships / settings.items[].structuredDetail.relationships',
    description: '对象之间的关系、时期与来源事件。',
  },
  {
    id: 'stages',
    name: '阶段/演变',
    target: 'entities[].stages / settings.items[].structuredDetail.stages',
    description: '对象在不同阶段中的变化。',
  },
  {
    id: 'supplement',
    name: '设定补充说明',
    target: 'entities[].attributes.设定补充说明 / settings.items[].detailContent',
    description: '无法短字段化的背景、限制与补充说明。',
  },
]

const cloneEditableState = (value) => JSON.parse(JSON.stringify(value ?? null))

const buildFallbackWorldTemplates = () => ([
  {
    id: DEFAULT_WORLD_TEMPLATE_ID,
    name: '通用模板',
    description: '默认解析结构，按核心简介、关键事实、关系网络、阶段/演变和设定补充说明组织世界观内容。',
    conflict_warning: '不同模板的结构栏目可能不一致。',
    focus_tags: DEFAULT_TEMPLATE_DETAIL_SECTIONS.map(section => section.name),
    focus_points: [],
    detail_sections: DEFAULT_TEMPLATE_DETAIL_SECTIONS,
    setting_collections: [],
    world_info_guide: [],
    settings_guide: [],
  },
  {
    id: DND_WORLD_TEMPLATE_ID,
    name: 'DND 跑团世界模板',
    description: '面向 DND 跑团的世界模板，覆盖战役前提、桌面规则、方格地图、势力、神祇位面、NPC、反派威胁、冒险遭遇、宝物和玩家角色接入。',
    conflict_warning: '该模板会把资料优先拆分为战役运营、规则资源和跑团地图字段。',
    focus_tags: ['战役总览', '桌面规则', '方格地图', '势力与神祇', '冒险遭遇', '宝物据点', '玩家接入'],
    focus_points: ['优先提取战役前提、起始等级、主要威胁、玩家角色钩子和 DND 方格战斗地图。'],
    detail_sections: [
      { id: 'campaign_overview', name: '战役总览', target: 'world_info.dnd_campaign', description: '战役前提、等级范围、主冲突和玩家目标。' },
      { id: 'table_rules', name: '桌面规则', target: 'settings.items[collectionId=dnd_table_rules]', description: '版本、资料书、升级、休息、死亡、复活、暗骰和安全工具。' },
      { id: 'maps', name: '地图与地点', target: 'settings.mapData.structuredMaps', description: '世界地图、区域地图、地牢地图和 DND 方格战斗地图。' },
      { id: 'encounters', name: '遭遇与怪物', target: 'settings.items[collectionId=dnd_encounters]', description: '战斗、陷阱、环境危险、怪物战术和胜败条件。' },
    ],
    setting_collections: [],
    world_info_guide: [],
    settings_guide: [],
  },
])

const SETTING_CATEGORY_OPTIONS = [
      { id: 'character', name: '角色', icon: 'user' },
      { id: 'item', name: '物品', icon: 'box' },
      { id: 'organization', name: '组织', icon: 'building' },
      { id: 'geography', name: '地理', icon: 'world' },
      { id: 'ability', name: '能力', icon: 'bolt' },
      { id: 'other', name: '其他', icon: 'list' }
]

const createDefaultMapData = () => ({
  regionRelations: '',
  countryRelations: '',
  importantLocations: '',
  structuredMaps: []
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
    .filter(entity => entity.name && !isFragmentEntityName(entity.name, entity.type, entity.attributes?.['简介']))
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
const TIMELINE_FOCUS_WINDOWS = [50, 100, 300, 1000, 3000]
const TIMELINE_FOCUS_MIN_ITEMS = 2
const TIMELINE_FOCUS_VISUAL_RATIO = 0.72
const TIMELINE_CONTEXT_POINT_SPAN = 20

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

const normalizeCalendarNumber = (value, fallback = 0) => {
  if (typeof value === 'number' && Number.isFinite(value)) return value
  const text = String(value ?? '').trim()
  if (/^[-+]?\d+(?:\.\d+)?$/.test(text)) return Number(text)
  const parsed = parseTimelineYear(text)
  return Number.isFinite(parsed) ? parsed : fallback
}

const normalizeCalendarRatio = (value) => {
  let text = String(value || '1').trim()
  text = text.replace(/^×\s*/i, '').replace(/^x\s*/i, '').trim()
  return `×${text || '1'}`
}

const parseCalendarRatioNumber = (value) => {
  const text = String(value || '1').trim().replace(/^×\s*/i, '').replace(/^x\s*/i, '').trim()
  const parsed = Number.parseFloat(text)
  return Number.isFinite(parsed) && parsed !== 0 ? parsed : 1
}

const normalizeCalendarName = (value) => String(value || '')
  .replace(/[\s·•・_\-—]+/g, '')
  .replace(/纪元$/g, '纪')
  .replace(/历法$/g, '历')
  .trim()
  .toLowerCase()

const parseAbsoluteYearFromText = (value) => {
  const text = normalizeTimelineText(value)
  if (!text) return null
  const explicit = text.match(/(?:公元|ad|ce)\s*([-+]?\d{1,6})\s*年?/i)
  if (explicit) return Number.parseInt(explicit[1], 10)
  const bc = text.match(/(?:公元前|bc|bce)\s*(\d{1,6})\s*年?/i)
  if (bc) return -Math.abs(Number.parseInt(bc[1], 10))
  const bare = text.match(/^([-+]?\d{1,6})\s*年?$/)
  if (bare) return Number.parseInt(bare[1], 10)
  return null
}

const parseLocalYearForCalendar = (value, calendarName = '') => {
  const text = normalizeTimelineText(value)
  if (!text) return null
  const names = [calendarName, calendarName.replace(/纪元$/, '纪'), calendarName.replace(/纪$/, '纪元')]
    .filter(Boolean)
    .map(name => name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  if (names.length) {
    const re = new RegExp(`(?:${names.join('|')})\\s*(前)?\\s*([-+]?\\d{1,6}|元)\\s*年?`, 'i')
    const match = text.match(re)
    if (match) {
      const raw = match[2] === '元' ? 0 : Number.parseInt(match[2], 10)
      return match[1] ? -Math.abs(raw) : raw
    }
  }
  const generic = text.match(/(?:第)?\s*(前)?\s*([-+]?\d{1,6}|元)\s*年/)
  if (generic && !/(公元|ad|ce|bc|bce)/i.test(text)) {
    const raw = generic[2] === '元' ? 0 : Number.parseInt(generic[2], 10)
    return generic[1] ? -Math.abs(raw) : raw
  }
  return null
}

const parseCalendarEquation = (value, calendarName = '') => {
  const text = normalizeTimelineText(value)
  if (!text) return null
  const local = parseLocalYearForCalendar(text, calendarName)
  const absolute = parseAbsoluteYearFromText(text)
  if (Number.isFinite(local) && Number.isFinite(absolute)) {
    return { localYear: local, absoluteYear: absolute }
  }
  return null
}

const buildCalendarReferenceIndex = (calendars = []) => {
  const references = []
  ;(calendars || []).forEach((calendar, index) => {
    const name = String(calendar?.name || '').trim()
    if (!name) return
    const textSources = [calendar.absoluteBaseTime, calendar.baseTime, calendar.timeRange, calendar.description].filter(Boolean)
    const equation = textSources.map(source => parseCalendarEquation(source, name)).find(Boolean)
    const explicitAbsolute = parseAbsoluteYearFromText(calendar.absoluteBaseTime)
    const baseAbsolute = Number.isFinite(explicitAbsolute) ? explicitAbsolute : equation?.absoluteYear
    const localFromBase = parseLocalYearForCalendar(calendar.baseTime, name)
    const localBaseYear = Number.isFinite(Number(calendar.localBaseYear))
      ? Number(calendar.localBaseYear)
      : (Number.isFinite(equation?.localYear) ? equation.localYear : (Number.isFinite(localFromBase) ? localFromBase : 0))
    const aliases = [name, name.replace(/纪元$/, '纪'), name.replace(/纪$/, '纪元')]
      .filter(Boolean)
      .map(normalizeCalendarName)
    references.push({
      id: calendar.id || `calendar_ref_${index}`,
      name,
      aliases: Array.from(new Set(aliases)),
      localBaseYear,
      absoluteBaseYear: Number.isFinite(baseAbsolute) ? baseAbsolute : null,
      ratio: parseCalendarRatioNumber(calendar.ratio),
      confidence: Number.isFinite(baseAbsolute) ? 'high' : 'low',
      source: calendar,
    })
  })
  references.push({
    id: 'gregorian',
    name: '公元',
    aliases: ['公元', 'ad', 'ce', 'gregorian'].map(normalizeCalendarName),
    localBaseYear: 0,
    absoluteBaseYear: 0,
    ratio: 1,
    confidence: 'high',
    source: null,
  })
  return references
}

const resolveTimelineExpression = (value, options = {}) => {
  const text = normalizeTimelineText(value)
  if (!text) return null
  const calendarRefs = options.calendarRefs || []
  const anchorYear = Number.isFinite(options.anchorYear) ? options.anchorYear : null

  const absolute = parseAbsoluteYearFromText(text)
  if (Number.isFinite(absolute) && /(公元|ad|ce|bc|bce)/i.test(text)) {
    return { year: absolute, absoluteYear: absolute, localYear: absolute, calendarName: '公元', label: text, rawDateText: text, confidence: 'high' }
  }

  const matchedRef = calendarRefs.find(ref => ref.aliases.some(alias => alias && normalizeCalendarName(text).includes(alias)))
  if (matchedRef) {
    const localYear = parseLocalYearForCalendar(text, matchedRef.name)
    if (Number.isFinite(localYear) && Number.isFinite(matchedRef.absoluteBaseYear)) {
      const year = matchedRef.absoluteBaseYear + (localYear - matchedRef.localBaseYear) * matchedRef.ratio
      return {
        year,
        absoluteYear: year,
        localYear,
        calendarName: matchedRef.name,
        label: `${text} / 公元${Math.round(year)}年`,
        rawDateText: text,
        confidence: matchedRef.confidence,
      }
    }
    if (Number.isFinite(localYear)) {
      return { year: null, absoluteYear: null, localYear, calendarName: matchedRef.name, label: text, rawDateText: text, confidence: 'low' }
    }
  }

  if (Number.isFinite(absolute)) {
    return { year: absolute, absoluteYear: absolute, localYear: absolute, calendarName: '客观年', label: text, rawDateText: text, confidence: 'medium' }
  }

  const years = extractTimelineYears(text, { anchorYear })
  if (years.length) {
    return { year: years[0], absoluteYear: years[0], localYear: years[0], calendarName: '', label: text, rawDateText: text, confidence: 'medium' }
  }
  return null
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
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value
  }
  const text = String(value ?? '').trim()
  if (!text) {
    return null
  }
  if (/^[-+]?\d+(?:\.\d+)?$/.test(text)) {
    return Number(text)
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

const buildCalendarTimelineItem = (calendar = {}, index = 0, timelineContext = {}) => {
  const calendarRefs = timelineContext.calendarRefs || []
  const anchorYear = Number.isFinite(timelineContext.anchorYear) ? timelineContext.anchorYear : null
  const ownRef = calendarRefs.find(ref => String(ref.source?.id || '') === String(calendar.id || '') || ref.name === calendar.name)
  const startResolved = resolveTimelineExpression(calendar.baseTime || calendar.timeRange, { calendarRefs, anchorYear })
  const parsedRange = parseTimelineRange(calendar.timeRange, { anchorYear })
  const rangeEndText = String(calendar.timeRange || '').split(/\s*~\s*/)[1] || ''
  const endResolved = resolveTimelineExpression(rangeEndText, { calendarRefs, anchorYear })
  const issue = assessCalendarTimelineIssue(calendar, [startResolved?.year, endResolved?.year].filter(Number.isFinite))

  if (issue === '更像周期或节日，不进入主时间轴') {
    return null
  }

  const start = Number.isFinite(startResolved?.year)
    ? startResolved.year
    : (Number.isFinite(ownRef?.absoluteBaseYear) ? ownRef.absoluteBaseYear : null)
  if (!Number.isFinite(start)) {
    return null
  }

  let end = Number.isFinite(endResolved?.year) ? endResolved.year : null
  if (!Number.isFinite(end) && Number.isFinite(parsedRange?.end)) {
    end = parsedRange.end
  }
  const isOpenEnded = Boolean(parsedRange?.openEnded || calendar.noEndTime || /^\s*(无|至今|现在|ongoing|present)\s*$/i.test(rangeEndText))
  if (!Number.isFinite(end) && isOpenEnded && Number.isFinite(anchorYear) && anchorYear > start) {
    end = anchorYear
  }
  if (!Number.isFinite(end)) {
    end = isOpenEnded ? start : start + 1
  }

  const rangeStart = Math.min(start, end)
  const rangeEnd = Math.max(start, end)
  return {
    id: calendar.id || `calendar_${index}`,
    name: String(calendar.name || '未命名历法').trim(),
    caption: `${inferCalendarTimelineType(calendar)} · ${calendar.timeRange || calendar.baseTime || '未定义区间'}${ownRef?.confidence === 'low' ? ' · 未换算' : ''}`,
    start: rangeStart,
    end: rangeEnd,
    openEnded: isOpenEnded,
    kind: inferCalendarTimelineType(calendar) === '纪年' ? 'year' : 'era',
    issue: ownRef?.confidence === 'low' ? '缺少客观基准年' : issue,
    confidence: ownRef?.confidence || startResolved?.confidence || 'medium',
    source: calendar,
  }
}

const getTimelineEventDateText = (event = {}) => {
  const estimated = String(event.estimated_date || '').trim()
  const date = String(event.date || '').trim()
  if (estimated && !/^(未知|unknown)$/i.test(estimated)) return estimated
  return date
}

const buildTimelineEventItem = (event = {}, index = 0, timelineContext = {}) => {
  const dateText = getTimelineEventDateText(event)
  const resolved = resolveTimelineExpression(dateText, timelineContext)
  if (!Number.isFinite(resolved?.year)) {
    return null
  }

  const entities = Array.isArray(event.entities) ? event.entities.map(item => String(item || '').trim()).filter(Boolean) : []
  const year = resolved.year
  return {
    id: event.id || `event_${index}_${String(event.name || '').slice(0, 12)}`,
    name: String(event.name || '未命名事件').trim(),
    year,
    localYear: resolved.localYear,
    calendarName: resolved.calendarName,
    label: resolved.label || `${formatTimelineYear(year)}年`,
    dateText: resolved.label || dateText,
    rawDateText: dateText,
    description: String(event.description || '').trim(),
    entities,
    confidence: resolved.confidence,
    weight: entities.length + (String(event.date || '').trim() ? 3 : 0) + (String(event.description || '').length > 40 ? 1 : 0),
    source: event,
  }
}

const buildTimelineStageItem = (entity = {}, stage = {}, index = 0, timelineContext = {}) => {
  const era = String(stage.era || '').trim()
  const resolved = resolveTimelineExpression(era, timelineContext)
  if (!Number.isFinite(resolved?.year)) {
    return null
  }

  return {
    id: stage.id || `stage_${entity.id || entity.name || index}_${index}`,
    entityName: String(entity.name || '未命名实体').trim(),
    entityType: String(entity.type || '实体').trim(),
    name: String(stage.name || '阶段').trim(),
    year: resolved.year,
    localYear: resolved.localYear,
    calendarName: resolved.calendarName,
    label: resolved.label || `${formatTimelineYear(resolved.year)}年`,
    era,
    description: String(stage.description || '').trim(),
    confidence: resolved.confidence,
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

const createSettingDetailField = (label = '', value = '', index = 0) => ({
  id: createLocalId('setting_field', index),
  label: String(label || '').trim(),
  value: String(value || '').trim(),
})

const normalizeSettingDetailFields = (fields = []) => {
  if (!fields) {
    return []
  }

  if (Array.isArray(fields)) {
    return fields
      .map((field, index) => {
        if (field && typeof field === 'object') {
          return {
            id: field.id || createLocalId('setting_field', index),
            label: String(field.label || field.key || field.name || '').trim(),
            value: formatStructuredText(field.value ?? field.content ?? field.description ?? '', { inline: true }),
          }
        }
        const text = String(field || '').trim()
        return text ? createSettingDetailField(`字段 ${index + 1}`, text, index) : null
      })
      .filter(field => field && (field.label || field.value))
  }

  if (fields && typeof fields === 'object') {
    return Object.entries(fields)
      .filter(([, value]) => hasStructuredDisplayValue(value))
      .map(([label, value], index) => createSettingDetailField(label, formatStructuredText(value, { inline: true }), index))
  }

  return []
}

const createEmptySettingStructuredDetail = (intro = '') => ({
  intro: String(intro || '').trim(),
  facts: [],
  relationships: [],
  stages: [],
})

const normalizeSettingStructuredDetail = (detail = {}, fallbackIntro = '') => {
  const source = detail && typeof detail === 'object' && !Array.isArray(detail) ? detail : {}
  return {
    intro: String(source.intro || source.summary || fallbackIntro || '').trim(),
    facts: normalizeSettingDetailFields(source.facts || source.overview || source.attributes),
    relationships: Array.isArray(source.relationships)
      ? source.relationships.map((relationship, index) => ({
          id: relationship?.id || createLocalId('setting_relation', index),
          target: String(relationship?.target || relationship?.name || '').trim(),
          type: String(relationship?.type || relationship?.relation || '关联').trim() || '关联',
          description: String(relationship?.description || relationship?.detail || '').trim(),
          time_period: String(relationship?.time_period || relationship?.period || '').trim(),
          source_event: String(relationship?.source_event || relationship?.event || '').trim(),
        })).filter(item => item.target || item.description)
      : [],
    stages: Array.isArray(source.stages)
      ? source.stages.map((stage, index) => ({
          id: stage?.id || createLocalId('setting_stage', index),
          name: String(stage?.name || stage?.title || `阶段 ${index + 1}`).trim(),
          era: String(stage?.era || stage?.time || '').trim(),
          description: String(stage?.description || stage?.detail || '').trim(),
          fields: normalizeSettingDetailFields(stage?.fields || stage?.attributes),
        })).filter(item => item.name || item.description || item.fields.length > 0)
      : [],
  }
}

const createSettingStructuredDetailFromEntity = (entity, fallbackIntro = '') => {
  if (!entity || typeof entity !== 'object') {
    return createEmptySettingStructuredDetail(fallbackIntro)
  }

  const attributes = entity.attributes || {}
  const intro = formatStructuredText(attributes['简介']) || fallbackIntro
  const aliases = normalizeAliases(entity.aliases)
  const facts = [
    createSettingDetailField('实体类型', String(entity.type || '未分类').trim() || '未分类'),
    ...(aliases.length ? [createSettingDetailField('别名', aliases.join('、'))] : []),
    ...buildStructuredFieldItems(attributes, ['简介', '实力变化', '性格变化', '关键转折'])
      .map((field, index) => createSettingDetailField(field.label, field.value, index + 2)),
  ]

  return {
    intro,
    facts,
    relationships: (Array.isArray(entity.relationships) ? entity.relationships : [])
      .map((relationship, index) => ({
        id: relationship.id || createLocalId('setting_relation', index),
        target: String(relationship.target || '').trim(),
        type: String(relationship.type || '关联').trim() || '关联',
        description: String(relationship.description || '').trim(),
        time_period: String(relationship.time_period || '').trim(),
        source_event: String(relationship.source_event || '').trim(),
      }))
      .filter(item => item.target || item.description),
    stages: (Array.isArray(entity.stages) ? entity.stages : [])
      .map((stage, index) => ({
        id: stage.id || createLocalId('setting_stage', index),
        name: String(stage.name || `阶段 ${index + 1}`).trim(),
        era: String(stage.era || '').trim(),
        description: String(stage.description || '').trim(),
        fields: buildStructuredFieldItems(stage.attributes || {}).map((field, fieldIndex) => createSettingDetailField(field.label, field.value, fieldIndex)),
      }))
      .filter(item => item.name || item.description || item.fields.length > 0),
  }
}

const getCategoryMeta = (categoryId) => SETTING_CATEGORY_OPTIONS.find(category => category.id === categoryId) || SETTING_CATEGORY_OPTIONS[SETTING_CATEGORY_OPTIONS.length - 1]

const getDefaultCollectionIdForCategory = (categoryId) => `default_collection_${normalizeSettingCategory(categoryId)}`

const createDefaultCollectionForCategory = (categoryId) => {
  const category = normalizeSettingCategory(categoryId)
  const categoryMeta = getCategoryMeta(category)
  return {
    id: getDefaultCollectionIdForCategory(category),
    name: `${categoryMeta.name}设定集`,
    settingType: 'collection',
    category,
    expanded: true,
    description: `${categoryMeta.name}相关通用设定`,
    aliases: [],
    detailContent: `${categoryMeta.name}相关通用设定`,
    structuredDetail: createEmptySettingStructuredDetail(`${categoryMeta.name}相关通用设定`),
    autoGenerated: true,
    sourceType: 'default_collection',
  }
}

const FRAGMENT_ENTITY_NAMES = new Set([
  '的', '地', '得', '了', '着', '过', '和', '与', '及', '或', '在', '从', '向', '把', '被', '对', '为', '以', '于',
  '心地', '冷酷', '残酷', '尊敬', '尊敬的', '可敬', '可敬的', '人类应该', '人类是',
  '这', '那', '这个', '那个', '一种', '某种', '东西', '事情', '方面', '时候', '地方', '问题'
])

const normalizeIdentityKey = (value) => String(value || '')
  .trim()
  .toLowerCase()
  .replace(/[\s\-—_·•・()（）\[\]{}《》<>『』"'`]+/g, '')

const isFragmentEntityName = (name, type = '', detail = '') => {
  const text = String(name || '').trim()
  const key = normalizeIdentityKey(text)
  const entityType = String(type || '').trim()
  const detailText = String(detail || '').trim()
  if (!key) return true
  if (FRAGMENT_ENTITY_NAMES.has(key)) return true
  if (/^[的地得了着过和与及或在从向把被对于以之其]$/.test(text)) return true
  if (/^[，。！？、；：,.!?;:'"“”‘’（）()\[\]{}<>《》\s]+$/.test(text)) return true
  if (/^[一二三四五六七八九十百千万\d]+$/.test(text)) return true
  if (/^(说|说道|写道|认为|觉得|表示|指出|开始|继续|突然|然后)$/.test(text)) return true
  if (lenientShortFragment(key, entityType, detailText)) return true
  return false
}

const lenientShortFragment = (key, entityType, detailText) => {
  if (key.length > 2) return false
  if (!['', '其他', '地点', '人物', '物品', '能力', 'geography', 'other'].includes(entityType)) return false
  if (key.length === 1) return true
  return /[说道认为表示指出]\s*[：:]|[，。！？；]/.test(detailText)
}

const normalizeSettingsForUi = (settings = []) => {
  const normalizedCollections = []
  const normalizedItems = []
  const collectionsByCategory = new Map()
  const collectionIds = new Set()

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
      structuredDetail: normalizeSettingStructuredDetail(setting.structuredDetail, String(setting.detailContent || setting.description || '').trim()),
      linkedEntityId: String(setting.linkedEntityId || setting.entityId || '').trim(),
      sourceType: String(setting.sourceType || '').trim(),
      autoGenerated: Boolean(setting.autoGenerated),
    }

    if (!normalizedSetting.name) {
      return
    }

    if (settingType === 'setting' && isFragmentEntityName(normalizedSetting.name, normalizedSetting.category, `${normalizedSetting.description}\n${normalizedSetting.detailContent}`)) {
      return
    }

    if (settingType === 'collection') {
      normalizedSetting.expanded = setting.expanded !== false
      normalizedCollections.push(normalizedSetting)
      collectionsByCategory.set(category, normalizedSetting)
      collectionIds.add(String(normalizedSetting.id || '').trim())
    } else {
      normalizedItems.push(normalizedSetting)
    }
  })

  normalizedItems.forEach((setting) => {
    const currentCollectionId = String(setting.collectionId || '').trim()
    if (currentCollectionId && collectionIds.has(currentCollectionId)) {
      return
    }

    let collection = collectionsByCategory.get(setting.category)
    if (!collection) {
      collection = createDefaultCollectionForCategory(setting.category)
      collectionsByCategory.set(setting.category, collection)
      normalizedCollections.push(collection)
      collectionIds.add(String(collection.id || '').trim())
    }
    setting.collectionId = collection.id
  })

  return [...normalizedCollections, ...normalizedItems]
}

const normalizeCalendarsForUi = (calendars = []) => calendars
  .filter(calendar => calendar && typeof calendar === 'object')
  .map((calendar, index) => {
    const startYearValue = normalizeCalendarNumber(calendar.startYear ?? calendar.baseTime, 0)
    const endYearValue = calendar.noEndTime ? '' : normalizeCalendarNumber(calendar.endYear, startYearValue + 1)
    const startYear = Number.isFinite(startYearValue) ? startYearValue : 0
    const endYear = endYearValue === '' ? '' : (Number.isFinite(endYearValue) ? endYearValue : startYear + 1)
    const rawRange = String(calendar.timeRange || '').trim()
    const timeRange = `${startYear} ~ ${endYear === '' ? '无' : endYear}`
    const normalizedCalendar = {
      ...calendar,
      id: calendar.id || createLocalId('calendar', index),
      name: String(calendar.name || '').trim(),
      rawType: String(calendar.type || '').trim(),
      startYear,
      endYear,
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
    const estimatedDateKey = String(event.estimated_date || '').trim().toLowerCase()
    const entityKey = Array.isArray(event.entities)
      ? event.entities.map(name => String(name || '').trim().toLowerCase()).filter(Boolean).sort().join('|')
      : ''
    const keys = []
    if (idKey) {
      keys.push(`id:${idKey}`)
    }
    if (nameKey && dateKey) {
      keys.push(`name:${nameKey}|date:${dateKey}`)
    }
    if (nameKey && isMeaningfulEventTime(estimatedDateKey)) {
      keys.push(`name:${nameKey}|estimated:${estimatedDateKey}`)
    }
    if (nameKey && entityKey) {
      keys.push(`name:${nameKey}|entities:${entityKey}`)
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
const SETTING_CATEGORY_TO_ENTITY_TYPE = {
  character: '人物',
  organization: '组织',
  geography: '地点',
  item: '物品',
  ability: '能力',
  other: '其他',
}
const ENTITY_BACKED_SETTING_CATEGORIES = new Set(['character', 'organization', 'geography', 'item', 'ability'])

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
        structuredDetail: createSettingStructuredDetailFromEntity(entity, summary.description || summary.detailContent || ''),
        linkedEntityId: entity.id,
        sourceType: 'entity',
        autoGenerated: true,
      }
    })
}

const settingStructuredDetailToEntityPayload = (setting) => {
  const detail = normalizeSettingStructuredDetail(setting.structuredDetail, setting.description || setting.detailContent)
  const attributes = {}
  const intro = mergeMultilineText(setting.description, detail.intro, setting.detailContent)
  if (intro) attributes['简介'] = intro

  ;(detail.facts || []).forEach((fact) => {
    const label = String(fact?.label || '').trim()
    if (label && fact?.value != null && String(fact.value).trim()) {
      attributes[label] = fact.value
    }
  })

  const relationships = (detail.relationships || [])
    .filter(item => item && String(item.target || '').trim())
    .map(item => ({
      target: String(item.target || '').trim(),
      type: String(item.type || '关联').trim() || '关联',
      description: String(item.description || '').trim(),
      time_period: String(item.time_period || '').trim(),
      source_event: String(item.source_event || '').trim(),
    }))

  const stages = (detail.stages || [])
    .filter(stage => stage && String(stage.name || '').trim())
    .map((stage, index) => ({
      id: stage.id || createLocalId('stage', index),
      name: String(stage.name || '').trim(),
      era: String(stage.era || '').trim(),
      description: String(stage.description || '').trim(),
      attributes: (stage.fields || []).reduce((acc, field) => {
        const label = String(field?.label || '').trim()
        if (label && field?.value != null && String(field.value).trim()) {
          acc[label] = field.value
        }
        return acc
      }, {}),
      setting_item_id: String(setting.id || '').trim(),
    }))

  return { attributes, relationships, stages }
}

const settingsToEntityItems = (settings) => {
  if (!Array.isArray(settings)) return []
  return normalizeSettingsForUi(settings)
    .filter(setting => setting && setting.settingType === 'setting')
    .filter(setting => ENTITY_BACKED_SETTING_CATEGORIES.has(normalizeSettingCategory(setting.category)))
    .filter(setting => String(setting.name || '').trim())
    .map((setting, index) => {
      const category = normalizeSettingCategory(setting.category)
      const entityPayload = settingStructuredDetailToEntityPayload(setting)
      return {
        id: String(setting.linkedEntityId || '').trim() || `entity_${setting.id || index}`,
        name: String(setting.name || '').trim(),
        type: SETTING_CATEGORY_TO_ENTITY_TYPE[category] || '其他',
        aliases: normalizeAliases(setting.aliases),
        attributes: entityPayload.attributes,
        stages: entityPayload.stages,
        relationships: entityPayload.relationships,
        setting_item_id: String(setting.id || '').trim(),
        evolution_refs: [],
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
    structuredMaps: Array.isArray(rawMapData.structuredMaps) ? rawMapData.structuredMaps : [],
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
        structuredDetail: createEmptySettingStructuredDetail(String(value).trim()),
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
        structuredDetail: normalizeSettingStructuredDetail(setting.structuredDetail, String(setting.detailContent || setting.description || '').trim()),
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
      structuredDetail: normalizeSettingStructuredDetail(setting.structuredDetail || existing.structuredDetail, String(setting.detailContent || existing.detailContent || setting.description || existing.description || '').trim()),
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

  const entitiesFromSettings = settingsToEntityItems(normalizedSettings)
  const mergedEntities = mergeEntityRecords(normalizedEntities, entitiesFromSettings)

  const hydratedEntities = mergedEntities.map(entity => {
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
    if (!matchedSetting) return entity

    matchedSetting.linkedEntityId = matchedSetting.linkedEntityId || entity.id
    const mirroredEntity = settingsToEntityItems([matchedSetting])[0]
    if (!mirroredEntity) {
      return {
        ...entity,
        setting_item_id: matchedSetting.id,
      }
    }

    return {
      ...entity,
      id: entity.id || mirroredEntity.id,
      name: String(matchedSetting.name || mirroredEntity.name || entity.name || '').trim(),
      type: String(mirroredEntity.type || entity.type || '').trim(),
      aliases: mergeArrayValues(normalizeAliases(entity.aliases), normalizeAliases(mirroredEntity.aliases)),
      attributes: mergePlainObjectValues({}, mirroredEntity.attributes),
      stages: mergeStageRecords([], mirroredEntity.stages),
      relationships: mergeArrayValues([], mirroredEntity.relationships),
      setting_item_id: matchedSetting.id,
      evolution_refs: mergeArrayValues(entity.evolution_refs || [], mirroredEntity.evolution_refs || []),
    }
  })

  return {
    entities: normalizeEntitiesForUi(syncedEntities),
    settings: normalizeSettingsForUi(mergedSettings),
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
  components: { WorldMapEditor, SvgIcon },
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
      autoSaveTimer: null,
      autoSaveSignature: '',
      autoSaveLastSavedAt: 0,
      isApplyingStoredWorld: false,
      isApplyingHistory: false,
      pendingAutoSave: false,
      undoStack: [],
      redoStack: [],
      editHistoryCurrentSignature: '',
      editHistoryCurrentSnapshot: null,
      editHistoryTimer: null,
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
      worldTemplates: buildFallbackWorldTemplates(),
      worldTemplateDefaultId: DEFAULT_WORLD_TEMPLATE_ID,
      selectedTemplateId: DEFAULT_WORLD_TEMPLATE_ID,
      savedWorldTemplateId: DEFAULT_WORLD_TEMPLATE_ID,
      savedWorldTemplateName: '通用模板',
      worldTemplateLoadError: '',
      extractText: '',
      extractScanSource: 'input',
      extractionMode: 'fast',
      isExtracting: false,
      extractProgress: { stage: '', progress: 0, message: '', detail: {}, ragProgress: null, updatedAt: '', startedAt: '', running: false },
      extractPollTimer: null,
      extractPollingTaskId: '',
      extractUiTickTimer: null,
      extractUiTick: 0,
      extractTaskId: '',
      isCancellingExtract: false,
      isPausingExtract: false,
      isResumingExtract: false,
      isDeletingExtractTask: false,
      showExtractScanPanel: false,
      extractPanelDismissed: false,
      showExtractResultDialog: false,
      extractResultDialogDismissed: false,
      extractedData: null,
      selectedFiles: [...cachedExtractSelectedFiles],
      isDragOver: false,
      entities: [],
      events: [],
      evolutionHistory: [],
      isLoadingEvolutionHistory: false,
      evolutionHistoryError: '',
      evolutionHistoryPollTimer: null,
      showEntitiesExpanded: true,
      showEventsExpanded: true,
      entityCardRowAligned: false,
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
      timelineViewMode: 'calendar',
      selectedTimelineItemId: '',
      timelineSearchQuery: '',
      timelineTypeFilter: 'all',
      calendarGraphicZoom: 1,
      calendarGraphicCenter: 0,
      // 设定管理
      activeCategory: 'character',
      activeCollectionId: '',
      activeCollectionSnapshot: null,
      settingsSearchQuery: '',
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
      currentSettingNewAlias: '',
      activeSidebarSettingId: '',
      showSettingDetail: false,
      showSettingSelector: false,
      selectedSettings: [],
      selectedCategoryFilter: 'all',
      agentWorldRefreshTimer: null,
      showCalendarEdit: false,
      showCalendarDetailEdit: false,
      currentCalendar: null,
      calendars: createDefaultCalendars(),
      editCalendars: [],
      collabClientId: '',
      collabRoom: null,
      collabMembers: [],
      collabEvents: [],
      collabLatestSeq: 0,
      collabStatus: '协作未连接',
      collabPollTimer: null,
      collabHeartbeatTimer: null,
      isCollabWidgetActive: false,
      hasRemoteWorldUpdate: false,
      remoteWorldEvent: null,
      lastPublishedWorldSignature: ''
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
    calendarRefs() {
      return buildCalendarReferenceIndex(this.calendars)
    },
    timelineContext() {
      const anchorResolved = resolveTimelineExpression(this.world.anchor_time, { calendarRefs: this.calendarRefs })
      return {
        calendarRefs: this.calendarRefs,
        anchorYear: Number.isFinite(anchorResolved?.year) ? anchorResolved.year : null,
      }
    },
    calendarSummaries() {
      return [...this.calendars].sort((a, b) => {
        const aStart = resolveTimelineExpression(a.baseTime || a.timeRange?.split(' ~ ')[0], this.timelineContext)?.year ?? 0
        const bStart = resolveTimelineExpression(b.baseTime || b.timeRange?.split(' ~ ')[0], this.timelineContext)?.year ?? 0
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
      return this.calendars
        .map((calendar, index) => buildCalendarTimelineItem(calendar, index, this.timelineContext))
        .filter(Boolean)
        .sort((a, b) => a.start - b.start || a.end - b.end)
        .slice(0, 48)
    },
    calendarGraphicRange() {
      const years = []
      this.chronologyCalendarItems.forEach(item => {
        if (Number.isFinite(item.start)) years.push(item.start)
        if (Number.isFinite(item.end) && !item.openEnded) years.push(item.end)
      })
      if (!years.length) return { min: -50, max: 50, span: 100, fullMin: -50, fullMax: 50, fullSpan: 100 }
      let min = Math.min(...years)
      let max = Math.max(...years)
      if (min === max) {
        min -= 50
        max += 50
      }
      const baseSpan = Math.max(max - min, 1)
      const padding = Math.max(baseSpan * 0.18, 80)
      min -= padding
      max += padding
      const fullSpan = Math.max(max - min, 1)
      const zoom = Math.max(0.4, Math.min(8, this.calendarGraphicZoom || 1))
      const visibleSpan = Math.max(1, fullSpan / zoom)
      const center = Number.isFinite(this.calendarGraphicCenter) && this.calendarGraphicCenter !== 0
        ? this.calendarGraphicCenter
        : (min + max) / 2
      const rangeMin = center - visibleSpan / 2
      const rangeMax = center + visibleSpan / 2
      return { min: rangeMin, max: rangeMax, span: visibleSpan, fullMin: min, fullMax: max, fullSpan }
    },
    calendarGraphicRangeLabels() {
      return {
        start: `${formatTimelineYear(Math.round(this.calendarGraphicRange.min))}年`,
        end: `${formatTimelineYear(Math.round(this.calendarGraphicRange.max))}年`,
      }
    },
    calendarGraphicTicks() {
      const range = this.calendarGraphicRange
      const roughStep = range.span / 5
      const magnitude = Math.pow(10, Math.floor(Math.log10(Math.max(roughStep, 1))))
      const normalized = roughStep / magnitude
      const step = (normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10) * magnitude
      const first = Math.ceil(range.min / step) * step
      const ticks = []
      for (let year = first; year <= range.max + step * 0.1; year += step) {
        const rounded = Math.round(year)
        ticks.push({ year: rounded, label: `${formatTimelineYear(rounded)}年`, position: this.getCalendarGraphicPosition(rounded) })
      }
      return ticks.filter(tick => tick.position >= -2 && tick.position <= 102).slice(0, 12)
    },
    visibleCalendarGraphicItems() {
      const range = this.calendarGraphicRange
      return this.chronologyCalendarItems.filter(item => {
        const start = Number.isFinite(item.start) ? item.start : item.year
        const end = item.openEnded ? range.max : (Number.isFinite(item.end) ? item.end : start)
        return end >= range.min && start <= range.max
      })
    },
    calendarGraphicRows() {
      const rowHeight = 68
      const topOffset = 84
      const tolerance = 0.0001
      const rows = []
      const items = [...this.visibleCalendarGraphicItems]
        .sort((a, b) => this.getTimelineTypeOrder(a.kind === 'era' ? 'calendar' : 'stage') - this.getTimelineTypeOrder(b.kind === 'era' ? 'calendar' : 'stage') || a.start - b.start || a.end - b.end)

      items.forEach((item) => {
        const start = Number.isFinite(item.start) ? item.start : item.year
        const end = item.openEnded ? this.calendarGraphicRange.max : (Number.isFinite(item.end) ? item.end : start + 1)
        const clampedStart = Math.max(start, this.calendarGraphicRange.min)
        const clampedEnd = Math.min(end, this.calendarGraphicRange.max)
        const rawLeft = this.getCalendarGraphicPosition(start)
        const rawRight = this.getCalendarGraphicPosition(end)
        const left = this.getCalendarGraphicPosition(clampedStart)
        const right = this.getCalendarGraphicPosition(clampedEnd)
        const visibleLeft = Math.max(0, Math.min(100, Math.min(left, right)))
        const visibleRight = Math.max(0, Math.min(100, Math.max(left, right)))
        const duration = Math.max(0, Math.round(end - start))
        const segment = {
          item,
          start,
          end,
          left: visibleLeft,
          width: Math.max(0, visibleRight - visibleLeft),
          rawLeft,
          rawRight,
          clippedStart: rawLeft < 0,
          clippedEnd: rawRight > 100,
          duration,
          durationLabel: item.openEnded ? '持续至未来' : (duration > 0 ? `持续 ${duration} 年` : '瞬时节点'),
          connectedPrev: false,
          connectedNext: false,
        }

        let row = rows.find(candidate => {
          if (candidate.kind !== item.kind) return false
          return start + tolerance >= candidate.lastEnd
        })

        if (!row) {
          row = { id: `calendar-row-${rows.length}`, kind: item.kind, top: topOffset + rows.length * rowHeight, lastEnd: -Infinity, items: [] }
          rows.push(row)
        }

        const prev = row.items[row.items.length - 1]
        if (prev && Math.abs(prev.end - start) <= tolerance) {
          prev.connectedNext = true
          segment.connectedPrev = true
        }
        row.items.push(segment)
        row.lastEnd = Math.max(row.lastEnd, end)
      })

      return rows
    },
    calendarGraphicHeight() {
      return Math.max(this.calendarGraphicRows.length, 1) * 68 + 134
    },
    chronologyCalendarItems() {
      return this.calendarTimelineItems.map((calendar) => ({
        id: `calendar:${calendar.id}`,
        type: 'calendar',
        kind: calendar.kind,
        year: calendar.start,
        start: calendar.start,
        end: calendar.end,
        openEnded: Boolean(calendar.openEnded),
        label: calendar.openEnded ? `${formatTimelineYear(Math.round(calendar.start))}年 - 至今` : `${formatTimelineYear(Math.round(calendar.start))}年 - ${formatTimelineYear(Math.round(calendar.end))}年`,
        durationLabel: calendar.openEnded ? '持续至未来' : `持续 ${Math.max(0, Math.round(calendar.end - calendar.start))} 年`,
        title: calendar.name,
        subtitle: calendar.caption,
        description: calendar.source?.description || calendar.caption || '',
        confidence: calendar.confidence || (calendar.issue ? 'low' : 'medium'),
        reason: calendar.issue || '',
        source: calendar.source || calendar,
        rawText: calendar.source?.timeRange || calendar.source?.baseTime || calendar.caption,
        meta: [
          { label: '类型', value: calendar.kind === 'era' ? '纪元' : '纪年' },
          { label: '原始区间', value: calendar.source?.timeRange || '未填写' },
          { label: '基准时间', value: calendar.source?.baseTime || '未填写' },
          { label: '单位 / 比例', value: `${calendar.source?.unit || '年'} / ${calendar.source?.ratio || '×1'}` },
        ],
      }))
    },
    calendarTimelineLayout() {
      return this.calculateSpanLayout(this.calendarTimelineItems)
    },
    timelineEventAnchors() {
      return (this.events || [])
        .map((event, index) => buildTimelineEventItem(event, index, this.timelineContext))
        .filter(Boolean)
    },
    chronologyEventItems() {
      return this.timelineEventAnchors.map(event => ({
        id: `event:${event.id}`,
        type: 'event',
        year: event.year,
        label: event.label,
        title: event.name,
        subtitle: event.entities.length ? `关联：${event.entities.slice(0, 3).join(' / ')}` : (event.rawDateText || '未关联实体'),
        description: event.description,
        confidence: event.confidence || 'medium',
        source: event.source,
        rawText: event.rawDateText,
        meta: [
          { label: '来源字段', value: event.rawDateText || 'date / estimated_date' },
          { label: '关联实体', value: event.entities.join('、') || '无' },
          { label: '换算历法', value: event.calendarName || '未指定' },
        ],
      }))
    },
    timelineEventItems() {
      const groupedByYear = new Map()
      this.timelineEventAnchors.filter(event => this.isInsideFocusWindow(event.year, 1.25)).forEach(event => {
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
      return this.calculatePointLayout(this.timelineEventItems, 4.2, 12)
    },
    timelineDensityItems() {
      const items = []
      this.timelineEventAnchors.forEach(event => {
        const keywordBoost = /(开始|开端|序章|觉醒|穿越|危机爆发|主角|故事开始|战争|登场|关键转折)/.test(`${event.name} ${event.description} ${event.rawDateText}`) ? 4 : 0
        items.push({ year: event.year, weight: 8 + event.weight + keywordBoost, label: event.name, type: 'event' })
      })
      this.timelineStageAnchors.forEach(stage => {
        const protagonistBoost = /(主角|主人公|男主|女主)/.test(`${stage.entityName} ${stage.entityType}`) ? 3 : 0
        items.push({ year: stage.year, weight: 4 + protagonistBoost, label: `${stage.entityName} · ${stage.name}`, type: 'stage' })
      })
      this.calendarTimelineItems.forEach(calendar => {
        items.push({ year: calendar.start, weight: 1.2, label: calendar.name, type: 'calendar' })
        items.push({ year: calendar.end, weight: 0.8, label: calendar.name, type: 'calendar' })
      })
      return items.filter(item => Number.isFinite(item.year))
    },
    timelineFocusWindow() {
      const items = this.timelineDensityItems
      if (!items.length) return null
      if (items.length === 1) {
        const year = items[0].year
        return { min: year - 100, max: year + 100, center: year, score: items[0].weight, items, reason: 'single' }
      }

      let best = null
      const centers = items.map(item => item.year)
      centers.forEach(center => {
        TIMELINE_FOCUS_WINDOWS.forEach(size => {
          const half = size / 2
          const inside = items.filter(item => item.year >= center - half && item.year <= center + half)
          if (inside.length < TIMELINE_FOCUS_MIN_ITEMS) return
          const score = inside.reduce((sum, item) => sum + item.weight, 0) / Math.log10(size + 10)
          const eventCount = inside.filter(item => item.type === 'event').length
          const candidate = { min: center - half, max: center + half, center, score, items: inside, eventCount, reason: 'density' }
          if (!best || candidate.score > best.score || (candidate.score === best.score && candidate.eventCount > best.eventCount)) {
            best = candidate
          }
        })
      })

      if (best) return best
      const years = items.map(item => item.year).sort((a, b) => a - b)
      const center = years[Math.floor(years.length / 2)]
      return { min: center - 500, max: center + 500, center, score: 0, items, reason: 'median' }
    },
    isInsideFocusWindow() {
      return (year, multiplier = 1) => {
        const focus = this.timelineFocusWindow
        if (!focus || !Number.isFinite(year)) return true
        const center = focus.center
        const half = Math.max((focus.max - focus.min) / 2, 1) * multiplier
        return year >= center - half && year <= center + half
      }
    },
    timelineStageAnchors() {
      const stages = []
      ;(this.entities || []).forEach((entity) => {
        ;(entity.stages || []).forEach((stage, index) => {
          const item = buildTimelineStageItem(entity, stage, index, this.timelineContext)
          if (item) stages.push(item)
        })
      })
      return stages
    },
    chronologyStageItems() {
      return this.timelineStageAnchors.map(stage => ({
        id: `stage:${stage.id}`,
        type: 'stage',
        year: stage.year,
        label: stage.label,
        title: `${stage.entityName} · ${stage.name}`,
        subtitle: `${stage.entityType || '实体'}阶段`,
        description: stage.description,
        confidence: stage.confidence || 'medium',
        source: stage.source,
        rawText: stage.era,
        meta: [
          { label: '实体', value: stage.entityName },
          { label: '阶段', value: stage.name },
          { label: '原始时期', value: stage.era || '未填写' },
          { label: '换算历法', value: stage.calendarName || '未指定' },
        ],
      }))
    },
    timelineStageItems() {
      return [...this.timelineStageAnchors]
        .filter(stage => this.isInsideFocusWindow(stage.year, 1.25))
        .sort((a, b) => a.year - b.year || b.weight - a.weight)
        .slice(0, TIMELINE_STAGE_LIMIT)
    },
    timelineStageLayout() {
      return this.calculatePointLayout(this.timelineStageItems, 4.8, 8)
    },
    chronologyItems() {
      return [
        ...this.chronologyEventItems,
        ...this.chronologyStageItems,
        ...this.chronologyCalendarItems,
      ].filter(item => Number.isFinite(item.year))
        .sort((a, b) => a.year - b.year || this.getTimelineTypeOrder(a.type) - this.getTimelineTypeOrder(b.type) || a.title.localeCompare(b.title, 'zh-Hans-CN'))
    },
    filteredChronologyItems() {
      const query = String(this.timelineSearchQuery || '').trim().toLowerCase()
      return this.chronologyItems.filter(item => {
        if (this.timelineTypeFilter !== 'all' && item.type !== this.timelineTypeFilter) return false
        if (!query) return true
        const haystack = [
          item.title,
          item.subtitle,
          item.description,
          item.label,
          item.rawText,
          ...(item.meta || []).map(meta => `${meta.label} ${meta.value}`),
        ].join('\n').toLowerCase()
        return haystack.includes(query)
      })
    },
    chronologyGroups() {
      const groups = []
      const byYear = new Map()
      this.filteredChronologyItems.forEach(item => {
        const year = Math.round(item.year)
        if (!byYear.has(year)) {
          byYear.set(year, {
            key: `year:${year}`,
            year,
            label: `${formatTimelineYear(year)}年`,
            items: [],
          })
        }
        byYear.get(year).items.push(item)
      })
      Array.from(byYear.values()).sort((a, b) => a.year - b.year).forEach(group => {
        group.items.sort((a, b) => this.getTimelineTypeOrder(a.type) - this.getTimelineTypeOrder(b.type) || a.title.localeCompare(b.title, 'zh-Hans-CN'))
        groups.push(group)
      })
      return groups
    },
    timelineSelectedItem() {
      if (!this.selectedTimelineItemId) return null
      return [...this.chronologyItems, ...this.timelineUnresolvedItems].find(item => item.id === this.selectedTimelineItemId) || null
    },
    timelineIssueCalendars() {
      return this.calendars
        .map((calendar, index) => {
          const ref = this.calendarRefs.find(item => String(item.source?.id || '') === String(calendar.id || '') || item.name === calendar.name)
          const resolved = resolveTimelineExpression(calendar.baseTime || calendar.timeRange, this.timelineContext)
          const issue = ref?.confidence === 'low' ? '缺少客观基准年，无法安全换算到主时间轴' : assessCalendarTimelineIssue(calendar, [resolved?.year].filter(Number.isFinite))
          return issue ? {
            id: calendar.id || `issue_${index}`,
            name: calendar.name || '未命名历法',
            issue,
          } : null
        })
        .filter(Boolean)
        .slice(0, TIMELINE_ISSUE_LIMIT)
    },
    timelineUnresolvedItems() {
      const items = []
      ;(this.events || []).forEach((event, index) => {
        const rawText = getTimelineEventDateText(event)
        const resolved = resolveTimelineExpression(rawText, this.timelineContext)
        if (!Number.isFinite(resolved?.year)) {
          items.push({
            id: `unresolved-event:${event.id || index}`,
            type: 'event',
            title: event.name || '未命名事件',
            subtitle: '事件时间无法定位',
            description: event.description || '',
            rawText,
            confidence: 'low',
            reason: rawText ? '无法从事件时间中解析出年份或可换算历法。' : '事件没有填写 date 或 estimated_date。',
            source: event,
            meta: [
              { label: '原始时间', value: rawText || '未填写' },
              { label: '关联实体', value: (event.entities || []).join('、') || '无' },
            ],
          })
        }
      })
      ;(this.entities || []).forEach((entity) => {
        ;(entity.stages || []).forEach((stage, index) => {
          const rawText = String(stage?.era || '').trim()
          const resolved = resolveTimelineExpression(rawText, this.timelineContext)
          if (!Number.isFinite(resolved?.year)) {
            items.push({
              id: `unresolved-stage:${entity.id || entity.name}:${stage.id || index}`,
              type: 'stage',
              title: `${entity.name || '未命名实体'} · ${stage.name || '阶段'}`,
              subtitle: '实体阶段无法定位',
              description: stage.description || '',
              rawText,
              confidence: 'low',
              reason: rawText ? '无法从阶段时期中解析出年份或可换算历法。' : '阶段没有填写 era / 时期。',
              source: { entity, stage },
              meta: [
                { label: '实体', value: entity.name || '未命名实体' },
                { label: '原始时期', value: rawText || '未填写' },
              ],
            })
          }
        })
      })
      this.timelineIssueCalendars.forEach(issue => {
        const calendar = this.calendars.find(item => String(item.id || '') === String(issue.id || '')) || issue
        items.push({
          id: `unresolved-calendar:${issue.id}`,
          type: 'calendar',
          title: issue.name || '未命名历法',
          subtitle: '历法数据需要补充',
          description: calendar.description || '',
          rawText: calendar.timeRange || calendar.baseTime || '',
          confidence: 'low',
          reason: issue.issue,
          source: calendar,
          meta: [
            { label: '时间范围', value: calendar.timeRange || '未填写' },
            { label: '基准时间', value: calendar.baseTime || '未填写' },
          ],
        })
      })
      return items
    },
    timelineBackgroundItems() {
      const items = []
      this.timelineEventAnchors.forEach(event => {
        if (!this.isInsideFocusWindow(event.year, 1.25)) items.push({ type: 'event', year: event.year, label: event.name })
      })
      this.timelineStageAnchors.forEach(stage => {
        if (!this.isInsideFocusWindow(stage.year, 1.25)) items.push({ type: 'stage', year: stage.year, label: `${stage.entityName} · ${stage.name}` })
      })
      this.calendarTimelineItems.forEach(calendar => {
        if (!this.isInsideFocusWindow(calendar.start, 1.5) && !this.isInsideFocusWindow(calendar.end, 1.5)) items.push({ type: 'calendar', year: calendar.start, label: calendar.name })
      })
      return items
    },
    timelineOverviewStats() {
      const years = this.chronologyItems.map(item => item.year).filter(Number.isFinite)
      const min = years.length ? Math.min(...years) : null
      const max = years.length ? Math.max(...years) : null
      const totalStages = (this.entities || []).reduce((sum, entity) => sum + ((entity.stages || []).length), 0)
      return {
        range: Number.isFinite(min) && Number.isFinite(max)
          ? `${formatTimelineYear(Math.round(min))}年 - ${formatTimelineYear(Math.round(max))}年`
          : '未定位',
        events: this.chronologyEventItems.length,
        totalEvents: (this.events || []).length,
        stages: this.chronologyStageItems.length,
        totalStages,
        calendars: this.chronologyCalendarItems.length,
        unresolved: this.timelineUnresolvedItems.length,
      }
    },
    timelineDiagnostics() {
      return {
        totalCalendars: this.calendars.length,
        usableCalendars: this.calendarTimelineItems.length,
        eventAnchors: this.timelineEventAnchors.length,
        visibleEvents: this.timelineEventItems.length,
        stageAnchors: this.timelineStageAnchors.length,
        visibleStages: this.timelineStageItems.length,
        backgroundItems: this.timelineBackgroundItems.length,
        noisyCalendars: this.timelineIssueCalendars.length,
      }
    },
    timelineAnchor() {
      const focus = this.timelineFocusWindow
      const explicit = resolveTimelineExpression(this.world.anchor_time, this.timelineContext)
      if (Number.isFinite(explicit?.year) && (!focus || this.isInsideFocusWindow(explicit.year, 1))) {
        return { year: explicit.year, label: explicit.label || this.world.anchor_time, source: 'manual' }
      }
      const focusItems = (focus?.items || []).filter(item => item.type === 'event' || item.type === 'stage')
      const bestFocusItem = [...focusItems].sort((a, b) => b.weight - a.weight)[0]
      if (bestFocusItem) return { year: bestFocusItem.year, label: bestFocusItem.label, source: 'density' }
      if (focus) return { year: focus.center, label: `密集主轴 ${formatTimelineYear(Math.round(focus.center))}年附近`, source: 'density' }
      const years = this.timelineEventAnchors.map(event => event.year).filter(Number.isFinite).sort((a, b) => a - b)
      if (years.length) return { year: years[Math.floor(years.length / 2)], label: '事件中位时间', source: 'median' }
      return null
    },
    timelinePrimaryLabel() {
      if (this.timelineAnchor) return this.timelineAnchor.label || `${formatTimelineYear(this.timelineAnchor.year)}年`
      const primary = this.calendarTimelineItems.find(item => item.kind === 'era') || this.calendarTimelineItems[0]
      if (primary) return primary.name
      return this.world.anchor_time || '未锚定'
    },
    timelineFocusLabel() {
      const focus = this.timelineFocusWindow
      if (!focus) return this.timelinePrimaryLabel
      return `${formatTimelineYear(Math.round(focus.min))}年 - ${formatTimelineYear(Math.round(focus.max))}年 · ${focus.items.length} 个密集节点`
    },
    timelineScaleSegments() {
      const focus = this.timelineFocusWindow
      const contextYears = this.timelineBackgroundItems
        .map(item => item.year)
        .filter(Number.isFinite)
      const focusMin = focus?.min ?? this.getTimeRange().min
      const focusMax = focus?.max ?? this.getTimeRange().max
      const focusRange = Math.max(focusMax - focusMin, 1)
      const contextSpans = contextYears
        .filter(year => year < focusMin || year > focusMax)
        .sort((a, b) => a - b)
        .map(year => ({
          type: 'context',
          start: year - TIMELINE_CONTEXT_POINT_SPAN / 2,
          end: year + TIMELINE_CONTEXT_POINT_SPAN / 2,
          center: year,
        }))

      const raw = [...contextSpans, { type: 'focus', start: focusMin, end: focusMax, center: (focusMin + focusMax) / 2 }]
        .sort((a, b) => a.start - b.start)
      const segments = []
      raw.forEach((segment, index) => {
        const prev = raw[index - 1]
        if (prev && segment.start > prev.end) {
          const gapSize = segment.start - prev.end
          segments.push({
            type: gapSize > focusRange * 3 ? 'gap' : 'space',
            start: prev.end,
            end: segment.start,
            compressed: gapSize > focusRange * 3,
          })
        }
        segments.push(segment)
      })

      const contextCount = segments.filter(item => item.type === 'context').length
      const gapCount = segments.filter(item => item.compressed).length
      const reserved = focus ? TIMELINE_FOCUS_VISUAL_RATIO : 1
      const remaining = Math.max(0.12, 1 - reserved)
      const unit = contextCount + gapCount || 1
      let cursor = 0
      return segments.map(segment => {
        let visualSpan
        if (segment.type === 'focus') visualSpan = reserved
        else if (segment.compressed) visualSpan = remaining * 0.55 / unit
        else visualSpan = remaining * 0.9 / unit
        visualSpan = Math.max(segment.type === 'focus' ? 0.45 : 0.035, visualSpan)
        const result = { ...segment, visualStart: cursor, visualEnd: cursor + visualSpan }
        cursor += visualSpan
        return result
      }).map(segment => ({
        ...segment,
        visualStart: segment.visualStart / Math.max(cursor, 1),
        visualEnd: segment.visualEnd / Math.max(cursor, 1),
      }))
    },
    timelineCompressedGaps() {
      return this.timelineScaleSegments
        .filter(segment => segment.compressed)
        .map(segment => ({
          position: ((segment.visualStart + segment.visualEnd) / 2) * 100,
          label: `压缩 ${formatTimelineYear(Math.round(segment.start))}年-${formatTimelineYear(Math.round(segment.end))}年`,
        }))
    },
    timelineTicks() {
      const focus = this.timelineFocusWindow
      const focusTicks = focus
        ? Array.from({ length: 5 }).map((_, index) => Math.round(focus.min + ((focus.max - focus.min) * index) / 4))
        : []
      const contextTicks = this.timelineScaleSegments
        .filter(segment => segment.type === 'context')
        .map(segment => Math.round(segment.center))
      return [...contextTicks, ...focusTicks]
        .filter((year, index, arr) => Number.isFinite(year) && arr.indexOf(year) === index)
        .map(year => ({
          label: `${formatTimelineYear(year)}年`,
          position: this.getTimelinePosition(year),
        }))
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
    activeSettingCollection() {
      if (this.activeCollectionId) {
        const collection = this.settings.find(setting => setting.settingType === 'collection' && setting.id === this.activeCollectionId)
        if (collection) {
          return collection
        }
      }

      return this.findCollectionBySnapshot(this.activeCollectionSnapshot)
    },
    filteredSettings() {
      const query = String(this.settingsSearchQuery || '').trim().toLowerCase()
      const activeCollection = this.activeSettingCollection

      return this.settings.filter(setting => {
        if (setting.settingType !== 'setting') return false
        if (activeCollection && setting.collectionId !== activeCollection.id) return false
        if (!activeCollection && !query && setting.category !== this.activeCategory) return false
        if (!query) return true

        const searchableText = [
          setting.name,
          setting.description,
          setting.detailContent,
          setting.category,
          ...(Array.isArray(setting.aliases) ? setting.aliases : []),
        ].map(value => String(value || '').toLowerCase()).join('\n')

        return searchableText.includes(query)
      })
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
      return this.findEntityForSetting(this.currentSetting)
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
    currentSettingInitial() {
      const name = String(this.currentSetting?.name || '').trim()
      return name ? name.slice(0, 1).toUpperCase() : '设'
    },
    hasRunnableProject() {
      return ['ontology_generated', 'graph_building', 'graph_completed'].includes(this.linkedProjectStatus)
    },
    hasLlmConfig() {
      return !!this.llmConfigStatus.api_key_configured
    },
    embeddingStatus() {
      return this.llmConfigStatus.embedding || {}
    },
    hasEmbeddingConfig() {
      return !!this.embeddingStatus.available
    },
    extractRequiresEmbedding() {
      return this.extractScanSource === 'input' || this.extractScanSource === 'input_and_rag' || this.extractScanSource === 'rag'
    },
    llmStatusText() {
      if (!this.hasLlmConfig) return 'LLM 未连接'
      return this.hasEmbeddingConfig ? 'LLM / Embedding 已连接' : 'LLM 已连接，Embedding 未配置'
    },
    projectActionLabel() {
      if (this.isProjectLaunching) {
        return this.linkedProjectId ? '正在打开项目...' : '正在创建项目...'
      }
      if (this.linkedProjectId) {
        return '打开推演项目'
      }
      return '创建推演项目'
    },
    showCollabWidget() {
      return this.isCollabWidgetActive && Boolean(this.collabRoom) && this.$route?.name === 'WorldBuilder'
    },

    templateCandidates() {
      return Array.isArray(this.worldTemplates) ? this.worldTemplates : []
    },
    selectedWorldTemplate() {
      return this.templateCandidates.find(template => template.id === this.selectedTemplateId) || this.templateCandidates[0] || null
    },
    savedWorldTemplate() {
      return this.worldTemplates.find(template => template.id === this.savedWorldTemplateId) || this.selectedWorldTemplate || null
    },
    worldHasStructuredContent() {
      if ((this.world.description || '').trim()) return true
      if ((this.world.era || '').trim()) return true
      if ((this.world.anchor_time || '').trim()) return true
      if ((this.world.reference_text || '').trim()) return true
      if (Array.isArray(this.entities) && this.entities.length > 0) return true
      if (Array.isArray(this.events) && this.events.length > 0) return true
      if (Array.isArray(this.settings) && this.settings.some(item => item && String(item.name || '').trim() && !item.autoGenerated)) return true
      if (Array.isArray(this.calendars) && this.calendars.length > 0) return true
      if ((this.mapData.regionRelations || '').trim()) return true
      if ((this.mapData.countryRelations || '').trim()) return true
      if ((this.mapData.importantLocations || '').trim()) return true
      if (Array.isArray(this.mapData.structuredMaps) && this.mapData.structuredMaps.length > 0) return true
      return false
    },
    templateSwitchHasConflict() {
      return this.worldHasStructuredContent && this.selectedTemplateId !== this.savedWorldTemplateId
    },
    templateSelectionNotice() {
      if (this.worldTemplateLoadError) {
        return this.worldTemplateLoadError
      }
      return this.selectedWorldTemplate?.description || '默认解析结构，按核心简介、关键事实、关系网络、阶段/演变和设定补充说明组织世界观内容。'
    },
    selectedTemplateSectionNames() {
      const template = this.selectedWorldTemplate
      if (!template || !Array.isArray(template.detail_sections)) {
        return []
      }
      return template.detail_sections
        .map(section => String(section?.name || '').trim())
        .filter(Boolean)
    },
    extractionDiagnostics() {
      return this.extractedData?.extraction_diagnostics || {}
    },
    extractedResultSummary() {
      const data = this.extractedData || {}
      const settings = data.settings || {}
      return {
        entities: Array.isArray(data.entities) ? data.entities.length : 0,
        events: Array.isArray(data.events) ? data.events.length : 0,
        settings: Array.isArray(settings.items) ? settings.items.length : 0,
      }
    },
    extractedResultSummaryText() {
      const summary = this.extractedResultSummary
      return `${summary.entities} 个实体、${summary.events} 个事件${summary.settings ? `、${summary.settings} 条设定` : ''}`
    },
    extractUsesRagSource() {
      return this.extractScanSource === 'rag' || this.extractScanSource === 'input_and_rag'
    },
    extractNeedsManualInput() {
      return this.extractScanSource !== 'rag'
    },
    canExtractWorld() {
      if (this.isExtracting) return false
      if (this.extractRequiresEmbedding && !this.hasEmbeddingConfig) return false
      if (this.extractUsesRagSource && !this.worldId) return false
      if (!this.extractNeedsManualInput) return !!this.worldId
      return !!this.extractText.trim() || this.selectedFiles.length > 0
    },
    extractSourceNotice() {
      if (this.extractRequiresEmbedding && !this.hasEmbeddingConfig) {
        return '请先配置 Embedding 模型，或在 LLM 配置页选择本地 Embedding 模型后再开始扫描。'
      }
      if (this.extractScanSource === 'rag') {
        return this.worldId
          ? '当前模式会直接扫描当前世界观已索引的知识库内容，不会重复写回知识库。'
          : '请先创建或保存世界观，因为知识库是按世界观绑定的。'
      }
      if (this.extractScanSource === 'input_and_rag') {
        return this.worldId
          ? '将把新上传或输入的内容与当前世界观知识库一起扫描；只有新内容会写入知识库。'
          : '请先创建或保存世界观，因为知识库是按世界观绑定的。'
      }
      return '当前模式会扫描新上传或输入的内容，并可继续将新内容并行写入当前世界观知识库。'
    },
    hasExtractionFailures() {
      return Array.isArray(this.extractionDiagnostics.failed_chunks) && this.extractionDiagnostics.failed_chunks.length > 0
    },
    cacheProgressText() {
      const detail = this.extractProgress.detail || {}
      const total = detail.total_chunks || this.extractedData?.extraction_diagnostics?.total_chunks || 0
      if (!total) return ''
      const completed = Number(detail.completed_chunks ?? this.extractedData?.completed_chunks ?? 0)
      const failed = Number(detail.failed_chunks ?? this.extractedData?.failed_chunks ?? 0)
      const processed = Number(detail.processed_chunks ?? (completed + failed))
      const resumed = detail.resumed_from_cache ? '已从缓存恢复，' : ''
      return `${resumed}已处理 ${processed}/${total} 块（成功 ${completed}${failed ? `，失败 ${failed}` : ''}）${failed ? '，可再次点击解析继续' : ''}`
    },
    ragDocumentText() {
      const detail = this.extractProgress.ragProgress?.detail || {}
      const count = detail.total_chunks || detail.processed_chunks || this.extractedData?.rag_added_count || 0
      const docs = this.extractedData?.rag_document_count
      if (!count && !docs) return ''
      return `文本块 ${count || 0}${docs ? `，知识库文档 ${docs}` : ''}`
    },
    deepStateText() {
      const state = this.extractProgress.detail?.deep_state || this.extractedData?.deep_state
      if (!state) return ''
      const stats = state.snapshot_stats || {}
      const summary = state.rolling_summary_preview ? `摘要：${state.rolling_summary_preview}` : ''
      return `深度状态：实体快照 ${stats.entity_count || state.confirmed_entity_count || 0}，省略 ${stats.snapshot_omitted_count || 0}${summary ? `；${summary}` : ''}`
    },
    showExtractScanModal() {
      return this.showExtractScanPanel && !this.extractPanelDismissed && Boolean(this.extractTaskId)
    },
    showDeepScanModal() {
      return this.showExtractScanModal && this.extractionMode === 'deep'
    },
    extractStatus() {
      return this.extractProgress.status || this.extractProgress.stage || ''
    },
    scanStatusLabel() {
      return {
        running: '运行中',
        starting: '启动中',
        preparing: '准备中',
        chunking: '切分中',
        indexing: '索引中',
        extracting: '解析中',
        pause_requested: '正在暂停',
        paused: '已暂停',
        cancel_requested: '正在强制中止',
        cancelled: '已强制中止',
        stale: '意外中断，可继续',
        done: '已完成',
        completed: '已完成',
        error: '失败',
        failed: '失败',
      }[this.extractStatus] || '准备中'
    },
    scanModalTitle() {
      if (this.isScanCompleted) return this.extractionMode === 'deep' ? '深度扫描已完成' : '快速扫描已完成'
      if (this.isCancellingExtract || this.extractStatus === 'cancel_requested') return '正在强制中止...'
      if (this.extractStatus === 'paused') return '扫描已暂停'
      if (this.extractStatus === 'cancelled') return '扫描已强制中止'
      if (this.extractStatus === 'stale') return '扫描意外中断'
      return this.extractionMode === 'deep' ? '深度扫描中...' : '快速扫描中...'
    },
    deepState() {
      return this.extractProgress.detail?.deep_state || this.extractedData?.deep_state || {}
    },
    deepProcessedText() {
      const detail = this.extractProgress.detail || {}
      return detail.processed_chars_label || `${detail.processed_chars || 0}字`
    },
    scanEstimatedChars() {
      return Number(this.extractProgress.estimatedTextChars || this.extractProgress.detail?.estimated_text_chars || this.extractProgress.detail?.total_chars || 0)
    },
    scanEstimateText() {
      if (!this.scanEstimatedChars) return ''
      const label = this.extractProgress.estimatedTextCharsLabel || this.extractProgress.detail?.estimated_text_chars_label || this.formatScanCharCount(this.scanEstimatedChars)
      return `预估总文本：${label}`
    },
    scanEstimateBreakdown() {
      return Array.isArray(this.extractProgress.textEstimateBreakdown) ? this.extractProgress.textEstimateBreakdown : []
    },
    scanEstimateSourceText() {
      if (!this.scanEstimateBreakdown.length) return ''
      return this.scanEstimateBreakdown
        .slice(0, 4)
        .map(item => `${item.name || '文本'} ${item.chars_label || this.formatScanCharCount(item.chars || 0)}`)
        .join('；')
    },
    isScanCompleted() {
      return ['completed', 'done'].includes(this.extractStatus)
    },
    scanCompletionText() {
      if (!this.isScanCompleted) return ''
      const settings = this.extractedData?.settings || {}
      const settingCount = Array.isArray(settings.items) ? settings.items.length : 0
      const entityCount = Array.isArray(this.extractedData?.entities) ? this.extractedData.entities.length : 0
      const eventCount = Array.isArray(this.extractedData?.events) ? this.extractedData.events.length : 0
      return `扫描已完成：提取到 ${entityCount} 个实体、${eventCount} 个事件${settingCount ? `、${settingCount} 条设定` : ''}。`
    },
    scanProcessedChunks() {
      const detail = this.extractProgress.detail || {}
      const completed = Number(detail.completed_chunks || 0)
      const failed = Number(detail.failed_chunks || 0)
      return Number(detail.processed_chunks ?? (completed + failed)) || 0
    },
    scanRuntimeText() {
      this.extractUiTick
      const elapsed = Number(this.deepState.current_chunk_elapsed_seconds || 0)
      const startedAt = this.deepState.current_chunk_started_at
      const seconds = elapsed || this.secondsSince(startedAt)
      return seconds ? this.formatScanDuration(seconds) : ''
    },
    scanHeartbeatText() {
      this.extractUiTick
      const heartbeatAt = this.deepState.current_chunk_heartbeat_at || this.extractProgress.updatedAt
      const seconds = this.secondsSince(heartbeatAt)
      if (!heartbeatAt) return ''
      return seconds <= 1 ? '刚刚' : `${seconds}秒前`
    },
    scanActivityText() {
      this.extractUiTick
      if (!this.extractTaskId) return ''
      const active = ['running', 'extracting', 'preparing', 'chunking', 'indexing', 'starting', 'pause_requested', 'cancel_requested'].includes(this.extractStatus)
        || (this.isExtracting && !this.extractProgress.done)
        || this.extractProgress.running
      if (!active) return ''
      const parts = []
      if (this.scanRuntimeText) parts.push(`当前块已运行 ${this.scanRuntimeText}`)
      if (this.scanHeartbeatText) parts.push(`最近心跳 ${this.scanHeartbeatText}`)
      return parts.length ? `扫描仍在运行：${parts.join('，')}` : '扫描仍在运行，正在等待最新进度...'
    },
    deepCurrentTitle() {
      return this.deepState.current_chunk_title || '准备读取文本块...'
    },
    deepChunkProgress() {
      const value = Number(this.deepState.current_chunk_progress || 0)
      return Math.max(0, Math.min(100, Math.round(value)))
    },
    scanChunkProgress() {
      const detail = this.extractProgress.detail || {}
      const total = Number(detail.total_chunks || 0)
      if (!total) return this.deepChunkProgress
      return Math.max(0, Math.min(100, Math.round((this.scanProcessedChunks / total) * 100)))
    },
    scanChunkText() {
      const detail = this.extractProgress.detail || {}
      const completed = Number(detail.completed_chunks || 0)
      const total = Number(detail.total_chunks || 0)
      const failed = Number(detail.failed_chunks || 0)
      const processed = this.scanProcessedChunks
      return `已处理 ${processed}/${total || '?'} 块，成功 ${completed}${failed ? `，失败 ${failed}` : ''}`
    },
    deepDiscoveries() {
      return Array.isArray(this.deepState.discoveries) ? this.deepState.discoveries : []
    },
    scanDiscoveryFallback() {
      if (this.extractionMode === 'deep') return '正在阅读文本，等待模型返回结构化发现...'
      return `${this.scanChunkText}，快速扫描正在并行提取实体、事件与设定。`
    },
    deepThinkingSummary() {
      return this.deepState.rolling_summary_preview || '模型正在建立上下文，完成当前块后会显示阶段性摘要。'
    },
    deepKnowledgeStats() {
      const stats = this.deepState.knowledge_stats || {}
      return ['人物', '物品', '势力', '地点', '事件'].map(label => ({ label, count: stats[label] || 0 }))
    },
    canPauseExtract() {
      return ['running', 'extracting', 'preparing', 'chunking', 'indexing', 'starting'].includes(this.extractStatus)
    },
    canResumeExtract() {
      return ['paused', 'stale', 'cancelled'].includes(this.extractStatus)
    },
    canCancelExtract() {
      return ['running', 'extracting', 'preparing', 'chunking', 'indexing', 'starting', 'pause_requested', 'paused', 'stale'].includes(this.extractStatus)
    },
    canDeleteExtract() {
      return ['paused', 'stale', 'cancelled', 'failed', 'error', 'completed', 'done'].includes(this.extractStatus)
        || (this.extractProgress.done && ['pause_requested', 'cancel_requested'].includes(this.extractStatus))
    },
    canUndo() {
      return this.undoStack.length > 0
    },
    canRedo() {
      return this.redoStack.length > 0
    },
    undoButtonTitle() {
      return this.canUndo ? `撤回上一步（Ctrl+Z）· 还有 ${this.undoStack.length} 步` : '暂无可撤回的修改'
    },
    redoButtonTitle() {
      return this.canRedo ? `重做下一步（Ctrl+Y）· 还有 ${this.redoStack.length} 步` : '暂无可重做的修改'
    },
    collabOnlineCount() {
      return this.collabMembers.filter(member => member.online).length
    },
    // 根据时间线内容计算高度，确保所有卡片都在可视区域内
    timelineHeight() {
      const totalHeight = this.timelineStageTop + this.timelineStageHeight + 86
      return Math.max(totalHeight, 520) + 'px'
    }
  },
  watch: {
    '$route.query.extractTaskId': {
      async handler(taskId) {
        if (!taskId) return
        if (taskId === this.extractTaskId) {
          if (this.$route?.query?.showExtractPanel === '1') {
            this.openExtractScanPanel({ syncRoute: false })
          }
          return
        }
        await this.restoreExtractTaskFromRoute()
      }
    },
    '$route.query.showExtractPanel'(value) {
      if (value === '1' && this.$route?.query?.extractTaskId === this.extractTaskId) {
        this.openExtractScanPanel({ syncRoute: false })
      }
    },
    world: {
      deep: true,
      handler() { this.handleEditableStateChanged() },
    },
    mapData: {
      deep: true,
      handler() { this.handleEditableStateChanged() },
    },
    settings: {
      deep: true,
      handler() { this.handleEditableStateChanged() },
    },
    calendars: {
      deep: true,
      handler() { this.handleEditableStateChanged() },
    },
    entities: {
      deep: true,
      handler() {
        this._chunkBuildEntityItems()
        this.handleEditableStateChanged()
      },
    },
    events: {
      deep: true,
      handler() {
        this._chunkBuildEventItems()
        this.handleEditableStateChanged()
      },
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
    syncSelectedFilesCache() {
      cachedExtractSelectedFiles = Array.isArray(this.selectedFiles) ? [...this.selectedFiles] : []
    },
    clearSelectedFilesCache() {
      cachedExtractSelectedFiles = []
      this.selectedFiles = []
    },
    createEditSnapshot() {
      return cloneEditableState({
        world: this.world,
        selectedTemplateId: this.selectedTemplateId,
        mapData: this.mapData,
        settings: this.settings,
        calendars: this.calendars,
        entities: this.entities,
        events: this.events,
      })
    },
    getEditSnapshotSignature(snapshot = this.createEditSnapshot()) {
      try {
        return JSON.stringify(snapshot)
      } catch (error) {
        console.warn('生成编辑历史签名失败:', error)
        return `${Date.now()}`
      }
    },
    resetEditHistory(snapshot = this.createEditSnapshot()) {
      if (this.editHistoryTimer) {
        clearTimeout(this.editHistoryTimer)
        this.editHistoryTimer = null
      }
      this.undoStack = []
      this.redoStack = []
      this.editHistoryCurrentSnapshot = cloneEditableState(snapshot)
      this.editHistoryCurrentSignature = this.getEditSnapshotSignature(snapshot)
    },
    handleEditableStateChanged() {
      if (this.isApplyingStoredWorld || this.isApplyingHistory) return
      this.scheduleEditHistoryCapture()
      this.scheduleAutoSave()
    },
    scheduleEditHistoryCapture() {
      if (!this.editHistoryCurrentSignature) {
        this.resetEditHistory()
        return
      }
      if (this.editHistoryTimer) {
        clearTimeout(this.editHistoryTimer)
      }
      this.editHistoryTimer = window.setTimeout(() => {
        this.editHistoryTimer = null
        this.captureEditHistoryChange()
      }, EDIT_HISTORY_CAPTURE_DELAY)
    },
    captureEditHistoryChange() {
      if (this.isApplyingStoredWorld || this.isApplyingHistory) return false
      const snapshot = this.createEditSnapshot()
      const signature = this.getEditSnapshotSignature(snapshot)
      if (!this.editHistoryCurrentSignature || !this.editHistoryCurrentSnapshot) {
        this.editHistoryCurrentSnapshot = cloneEditableState(snapshot)
        this.editHistoryCurrentSignature = signature
        return false
      }
      if (signature === this.editHistoryCurrentSignature) return false

      this.undoStack = [...this.undoStack.slice(-(EDIT_HISTORY_LIMIT - 1)), cloneEditableState(this.editHistoryCurrentSnapshot)]
      this.redoStack = []
      this.editHistoryCurrentSnapshot = cloneEditableState(snapshot)
      this.editHistoryCurrentSignature = signature
      return true
    },
    flushEditHistoryCapture() {
      if (this.editHistoryTimer) {
        clearTimeout(this.editHistoryTimer)
        this.editHistoryTimer = null
      }
      this.captureEditHistoryChange()
    },
    applyEditSnapshot(snapshot) {
      if (!snapshot) return
      this.isApplyingHistory = true
      try {
        this.world = cloneEditableState(snapshot.world || {})
        this.selectedTemplateId = this.resolveKnownTemplateId(snapshot.selectedTemplateId || this.selectedTemplateId)
        this.mapData = { ...createDefaultMapData(), ...cloneEditableState(snapshot.mapData || {}) }
        this.settings = cloneEditableState(snapshot.settings || [])
        this.calendars = cloneEditableState(snapshot.calendars || [])
        this.entities = cloneEditableState(snapshot.entities || [])
        this.events = cloneEditableState(snapshot.events || [])
        this.syncOpenSettingReference()
        const appliedSnapshot = this.createEditSnapshot()
        this.editHistoryCurrentSnapshot = cloneEditableState(appliedSnapshot)
        this.editHistoryCurrentSignature = this.getEditSnapshotSignature(appliedSnapshot)
      } finally {
        this.$nextTick(() => {
          this.isApplyingHistory = false
          this._chunkBuildEntityItems()
          this._chunkBuildEventItems()
          this.scheduleAutoSave(800)
        })
      }
    },
    syncOpenSettingReference() {
      if (!this.currentSetting?.id) return
      this.currentSetting = this.settings.find(setting => setting.id === this.currentSetting.id) || this.currentSetting
    },
    undoWorldChange() {
      this.flushEditHistoryCapture()
      if (!this.canUndo) return
      const currentSnapshot = this.createEditSnapshot()
      const previousSnapshot = this.undoStack[this.undoStack.length - 1]
      this.undoStack = this.undoStack.slice(0, -1)
      this.redoStack = [...this.redoStack.slice(-(EDIT_HISTORY_LIMIT - 1)), currentSnapshot]
      this.applyEditSnapshot(previousSnapshot)
      this.saveStatus = '已撤回上一步修改'
    },
    redoWorldChange() {
      this.flushEditHistoryCapture()
      if (!this.canRedo) return
      const currentSnapshot = this.createEditSnapshot()
      const nextSnapshot = this.redoStack[this.redoStack.length - 1]
      this.redoStack = this.redoStack.slice(0, -1)
      this.undoStack = [...this.undoStack.slice(-(EDIT_HISTORY_LIMIT - 1)), currentSnapshot]
      this.applyEditSnapshot(nextSnapshot)
      this.saveStatus = '已重做下一步修改'
    },
    handleEditHistoryShortcut(event) {
      const key = String(event.key || '').toLowerCase()
      const modifierPressed = event.ctrlKey || event.metaKey
      if (!modifierPressed || event.altKey) return

      if (key === 'z' && event.shiftKey) {
        if (!this.canRedo) return
        event.preventDefault()
        this.redoWorldChange()
        return
      }

      if (key === 'z') {
        if (!this.canUndo) return
        event.preventDefault()
        this.undoWorldChange()
        return
      }

      if (key === 'y') {
        if (!this.canRedo) return
        event.preventDefault()
        this.redoWorldChange()
      }
    },
    getTimelineTypeOrder(type) {
      return { calendar: 0, event: 1, stage: 2 }[type] ?? 9
    },
    selectTimelineItem(item) {
      if (!item) return
      this.selectedTimelineItemId = item.id
    },
    getTimelineItemIcon(type) {
      return { event: 'bolt', stage: 'user', calendar: 'clock' }[type] || 'info'
    },
    getTimelineItemTypeLabel(type) {
      return { event: '事件', stage: '实体阶段', calendar: '历法' }[type] || '条目'
    },
    getTimelineConfidenceLabel(confidence) {
      return { high: '高置信', medium: '已解析', low: '待确认' }[confidence] || '已解析'
    },
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
      this.openSidebarSetting(setting)
    },
    openEntitySettingByName(entityName) {
      const entity = this.entities.find(item => item.name === entityName)
      if (entity) {
        this.openLinkedSetting(entity)
      }
    },
    async loadEvolutionHistory(worldId = this.worldId, options = {}) {
      const { silent = false } = options
      if (!worldId) {
        this.evolutionHistory = []
        this.evolutionHistoryError = ''
        this.stopEvolutionHistoryPolling()
        return
      }

      if (!silent) {
        this.isLoadingEvolutionHistory = true
      }
      this.evolutionHistoryError = ''
      try {
        const response = await service.get(`/api/evolution/world/${worldId}`)
        this.evolutionHistory = Array.isArray(response.evolutions) ? response.evolutions : []
        this.syncEvolutionHistoryPolling()
      } catch (error) {
        console.error('加载推演记录失败:', error)
        if (!silent) {
          this.evolutionHistory = []
        }
        this.evolutionHistoryError = error.message || '加载推演记录失败'
      } finally {
        if (!silent) {
          this.isLoadingEvolutionHistory = false
        }
      }
    },
    hasActiveEvolutions() {
      return (this.evolutionHistory || []).some(record => ['created', 'planning', 'running', 'consolidating'].includes(record?.status))
    },
    syncEvolutionHistoryPolling() {
      if (this.hasActiveEvolutions()) {
        this.startEvolutionHistoryPolling()
      } else {
        this.stopEvolutionHistoryPolling()
      }
    },
    startEvolutionHistoryPolling() {
      if (this.evolutionHistoryPollTimer || !this.worldId) return
      this.evolutionHistoryPollTimer = setInterval(() => {
        this.loadEvolutionHistory(this.worldId, { silent: true })
      }, 2500)
    },
    stopEvolutionHistoryPolling() {
      if (this.evolutionHistoryPollTimer) {
        clearInterval(this.evolutionHistoryPollTimer)
        this.evolutionHistoryPollTimer = null
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
        planning: '规划中',
        running: '进行中',
        consolidating: '整合中',
        completed: '已完成',
        failed: '失败',
      }
      return labels[status] || status || '未知'
    },
    isEvolutionActive(record) {
      return ['created', 'planning', 'running', 'consolidating'].includes(record?.status)
    },
    getEvolutionTotalRounds(record) {
      return Math.max(Number(record?.config?.rounds || 5), 1)
    },
    getEvolutionProgress(record) {
      const total = this.getEvolutionTotalRounds(record)
      const current = Math.min(Math.max((record?.rounds || []).length, 0), total)
      return Math.min(100, Math.max(0, Math.round((current / total) * 100)))
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
    updateStructuredMaps(maps) {
      this.mapData = {
        ...this.mapData,
        structuredMaps: JSON.parse(JSON.stringify(maps || []))
      }
    },
    getWorldPayloadSignature(payload = this.buildWorldPayload()) {
      try {
        return JSON.stringify(payload)
      } catch (error) {
        console.warn('生成自动保存签名失败:', error)
        return `${Date.now()}`
      }
    },
    markWorldAsSaved(payload = this.buildWorldPayload()) {
      this.autoSaveSignature = this.getWorldPayloadSignature(payload)
      this.autoSaveLastSavedAt = Date.now()
      this.savedWorldTemplateId = this.resolveKnownTemplateId(payload.template_id || this.selectedTemplateId)
      this.savedWorldTemplateName = payload.template_name || this.getWorldTemplateName(this.savedWorldTemplateId)
    },
    isWorldBuilderRouteActive() {
      return this.$route?.name === 'WorldBuilder'
    },
    clearPendingAutoSave() {
      if (this.autoSaveTimer) {
        clearTimeout(this.autoSaveTimer)
        this.autoSaveTimer = null
      }
      if (this.editHistoryTimer) {
        clearTimeout(this.editHistoryTimer)
        this.editHistoryTimer = null
      }
    },
    scheduleAutoSave(delay = 5000) {
      if (this.isApplyingStoredWorld || !this.isWorldBuilderRouteActive()) return
      if (this.autoSaveTimer) {
        clearTimeout(this.autoSaveTimer)
      }
      const minInterval = 15000
      const elapsed = Date.now() - (this.autoSaveLastSavedAt || 0)
      const waitTime = Math.max(delay, minInterval - elapsed, 0)
      this.saveStatus = this.worldId ? '有未保存修改，将稍后自动保存' : '有未保存修改，将自动创建世界观'
      this.autoSaveTimer = window.setTimeout(() => {
        this.autoSaveTimer = null
        if (!this.isWorldBuilderRouteActive()) return
        this.saveWorld({ silent: true, skipReload: true })
      }, waitTime)
    },
    async flushAutoSave(options = {}) {
      const { requireActiveRoute = true } = options
      if (this.autoSaveTimer) {
        clearTimeout(this.autoSaveTimer)
        this.autoSaveTimer = null
      }
      if (requireActiveRoute && !this.isWorldBuilderRouteActive()) {
        return false
      }
      if (this.isApplyingStoredWorld) {
        await this.$nextTick()
      }
      return await this.saveWorld({ silent: true, skipReload: true, requireActiveRoute })
    },
    buildWorldPayload() {
      this.syncEntitySettingLinks()
      const templateId = this.resolveKnownTemplateId(this.selectedTemplateId)
      return {
        world_info: { ...this.world },
        template_id: templateId,
        template_name: this.getWorldTemplateName(templateId),
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
    resolveKnownTemplateId(templateId) {
      const normalizedId = String(templateId || '').trim()
      if (normalizedId && this.templateCandidates.some(template => template.id === normalizedId)) {
        return normalizedId
      }
      const genericTemplate = this.templateCandidates.find(template => template.id === DEFAULT_WORLD_TEMPLATE_ID)
      if (genericTemplate?.id) {
        return genericTemplate.id
      }
      return this.worldTemplateDefaultId || DEFAULT_WORLD_TEMPLATE_ID
    },
    getWorldTemplateName(templateId) {
      const normalizedId = this.resolveKnownTemplateId(templateId)
      const match = this.templateCandidates.find(template => template.id === normalizedId)
      return match?.name || (normalizedId === DEFAULT_WORLD_TEMPLATE_ID ? '通用模板' : normalizedId)
    },
    buildTemplateConflictMessage(targetTemplateId, actionLabel = '继续使用') {
      const targetName = this.getWorldTemplateName(targetTemplateId)
      const currentName = this.savedWorldTemplate?.name || this.savedWorldTemplateName || this.getWorldTemplateName(this.savedWorldTemplateId)
      const template = this.worldTemplates.find(item => item.id === this.resolveKnownTemplateId(targetTemplateId))
      const warning = template?.conflict_warning || '不同世界模板的实体属性和设定字段可能不一致。'
      return `当前世界观已经有内容。\n\n从“${currentName}”切换到“${targetName}”后，继续提取或保存可能出现字段冲突。\n\n${warning}\n\n确定要${actionLabel}“${targetName}”吗？`
    },
    async loadWorldTemplates() {
      try {
        const now = Date.now()
        let responseTemplates = null
        if (cachedWorldTemplates && now - cachedWorldTemplatesAt < CACHE_TTL_MS) {
          responseTemplates = cachedWorldTemplates
        } else {
          const response = await worldApi.listWorldTemplates()
          responseTemplates = Array.isArray(response.templates) && response.templates.length > 0
            ? response.templates
            : buildFallbackWorldTemplates()
          cachedWorldTemplates = responseTemplates
          cachedWorldTemplatesAt = now
        }
        const fallbackTemplate = buildFallbackWorldTemplates()[0]
        this.worldTemplates = responseTemplates.map(template => ({
          ...fallbackTemplate,
          ...template,
          detail_sections: Array.isArray(template.detail_sections) && template.detail_sections.length > 0
            ? template.detail_sections
            : (template.id === DEFAULT_WORLD_TEMPLATE_ID ? fallbackTemplate.detail_sections : []),
          setting_collections: Array.isArray(template.setting_collections) && template.setting_collections.length > 0
            ? template.setting_collections
            : [],
        }))
        if (!this.worldTemplates.some(template => template.id === DEFAULT_WORLD_TEMPLATE_ID)) {
          this.worldTemplates.unshift(fallbackTemplate)
        }
        this.worldTemplateDefaultId = DEFAULT_WORLD_TEMPLATE_ID
        this.selectedTemplateId = this.resolveKnownTemplateId(this.selectedTemplateId || this.worldTemplateDefaultId)
        this.savedWorldTemplateId = this.resolveKnownTemplateId(this.savedWorldTemplateId || this.worldTemplateDefaultId)
        this.savedWorldTemplateName = this.getWorldTemplateName(this.savedWorldTemplateId)
        this.worldTemplateLoadError = ''
      } catch (error) {
        console.error('加载世界模板失败:', error)
        this.worldTemplates = buildFallbackWorldTemplates()
        this.worldTemplateDefaultId = DEFAULT_WORLD_TEMPLATE_ID
        this.selectedTemplateId = this.resolveKnownTemplateId(this.selectedTemplateId || DEFAULT_WORLD_TEMPLATE_ID)
        this.savedWorldTemplateId = this.resolveKnownTemplateId(this.savedWorldTemplateId || DEFAULT_WORLD_TEMPLATE_ID)
        this.savedWorldTemplateName = this.getWorldTemplateName(this.savedWorldTemplateId)
        this.worldTemplateLoadError = '世界模板加载失败，已回退到通用模板显示。'
      }
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
    goToLlmConfig(role = '') {
      const query = role ? { role } : undefined
      this.$router.push({ name: 'LlmConfig', query })
    },
    openLlmConfigDialog() {
      this.goToLlmConfig()
    },
    closeLlmConfigDialog() {
      this.showLlmConfigDialog = false
    },
    async loadLlmConfigStatus() {
      try {
        const now = Date.now()
        let config = null
        if (cachedLlmConfig && now - cachedLlmConfigAt < CACHE_TTL_MS) {
          config = cachedLlmConfig
        } else {
          const response = await worldApi.getLlmConfig()
          config = response.config || null
          cachedLlmConfig = config
          cachedLlmConfigAt = now
        }
        if (config) {
          this.llmConfigStatus = config
        }
        if (!this.llmConfig.baseUrl) {
          this.llmConfig.baseUrl = (config && config.base_url) || this.llmConfigStatus.base_url || 'https://api.openai.com/v1'
        }
        if (!this.llmConfig.modelName) {
          this.llmConfig.modelName = (config && config.model_name) || this.llmConfigStatus.model_name || ''
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
    buildCollectionSnapshot(collection) {
      if (!collection || typeof collection !== 'object') {
        return null
      }

      return {
        id: String(collection.id || '').trim(),
        name: String(collection.name || '').trim(),
        category: normalizeSettingCategory(collection.category),
      }
    },
    buildSettingSnapshot(setting) {
      if (!setting || typeof setting !== 'object') {
        return null
      }

      return {
        id: String(setting.id || '').trim(),
        name: String(setting.name || '').trim(),
        category: normalizeSettingCategory(setting.category),
        linkedEntityId: String(setting.linkedEntityId || '').trim(),
      }
    },
    findCollectionBySnapshot(snapshot) {
      if (!snapshot || typeof snapshot !== 'object') {
        return null
      }

      const snapshotId = String(snapshot.id || '').trim()
      if (snapshotId) {
        const byId = this.settings.find(setting => setting.settingType === 'collection' && setting.id === snapshotId)
        if (byId) {
          return byId
        }
      }

      const snapshotName = String(snapshot.name || '').trim()
      const snapshotCategory = normalizeSettingCategory(snapshot.category)
      if (!snapshotName) {
        return null
      }

      return this.settings.find(setting => (
        setting.settingType === 'collection'
        && normalizeSettingCategory(setting.category) === snapshotCategory
        && String(setting.name || '').trim() === snapshotName
      )) || null
    },
    findSettingBySnapshot(snapshot) {
      if (!snapshot || typeof snapshot !== 'object') {
        return null
      }

      const snapshotId = String(snapshot.id || '').trim()
      if (snapshotId) {
        const byId = this.settings.find(setting => setting.settingType === 'setting' && setting.id === snapshotId)
        if (byId) {
          return byId
        }
      }

      const linkedEntityId = String(snapshot.linkedEntityId || '').trim()
      if (linkedEntityId) {
        const byEntity = this.settings.find(setting => (
          setting.settingType === 'setting' && String(setting.linkedEntityId || '').trim() === linkedEntityId
        ))
        if (byEntity) {
          return byEntity
        }
      }

      const snapshotName = String(snapshot.name || '').trim()
      const snapshotCategory = normalizeSettingCategory(snapshot.category)
      if (!snapshotName) {
        return null
      }

      return this.settings.find(setting => (
        setting.settingType === 'setting'
        && normalizeSettingCategory(setting.category) === snapshotCategory
        && String(setting.name || '').trim() === snapshotName
      )) || null
    },
    captureSettingsViewState() {
      return {
        activeCategory: this.activeCategory,
        activeCollection: this.buildCollectionSnapshot(this.activeSettingCollection || this.findCollectionBySnapshot(this.activeCollectionSnapshot)),
        currentSetting: this.buildSettingSnapshot(this.currentSetting),
        showSettingDetail: Boolean(this.showSettingDetail),
        activeSidebarSettingId: String(this.activeSidebarSettingId || '').trim(),
      }
    },
    restoreSettingsViewState(snapshot = null) {
      if (!snapshot || typeof snapshot !== 'object') {
        this.activeCollectionId = ''
        this.activeCollectionSnapshot = null
        this.activeSidebarSettingId = ''
        this.currentSetting = null
        this.showSettingDetail = false
        return
      }

      if (snapshot.activeCategory && this.settingCategories.some(category => category.id === snapshot.activeCategory)) {
        this.activeCategory = snapshot.activeCategory
      }

      const activeCategory = this.settingCategories.find(category => category.id === this.activeCategory)
      if (activeCategory) {
        activeCategory.expanded = true
      }

      const collection = this.findCollectionBySnapshot(snapshot.activeCollection)
      this.activeCollectionId = collection ? collection.id : ''
      this.activeCollectionSnapshot = collection ? this.buildCollectionSnapshot(collection) : null
      if (collection) {
        collection.expanded = true
      }

      const setting = this.findSettingBySnapshot(snapshot.currentSetting || { id: snapshot.activeSidebarSettingId })
      this.activeSidebarSettingId = setting ? setting.id : ''

      if (snapshot.showSettingDetail && setting) {
        this.currentSetting = JSON.parse(JSON.stringify(setting))
        this.showSettingDetail = true
      } else {
        this.currentSetting = null
        this.showSettingDetail = false
      }
    },
    ensureCollabClientId() {
      let clientId = localStorage.getItem(CLIENT_ID_KEY)
      if (!clientId) {
        clientId = `client_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
        localStorage.setItem(CLIENT_ID_KEY, clientId)
      }
      this.collabClientId = clientId
      return clientId
    },
    async ensureWorldCollabRoom() {
      if (!this.worldId) return
      this.ensureCollabClientId()
      const collabIdentity = ensureCollabIdentity()
      try {
        const response = await collabApi.ensureWorldRoom(this.worldId, {
          world_name: this.world.name || '未命名世界观',
          user_id: collabIdentity.userId,
          display_name: collabIdentity.displayName,
        })
        this.collabRoom = response.room
        this.collabMembers = response.members || []
        this.collabLatestSeq = response.latest_seq || this.collabLatestSeq || 0
        this.collabStatus = '协作已连接'
        this.startWorldCollabSync()
      } catch (error) {
        this.collabStatus = '协作未启用'
      }
    },
    startWorldCollabSync() {
      if (this.collabPollTimer) clearInterval(this.collabPollTimer)
      if (this.collabHeartbeatTimer) clearInterval(this.collabHeartbeatTimer)
      this.collabPollTimer = setInterval(() => this.pollWorldCollabEvents().catch(() => {}), 3000)
      this.collabHeartbeatTimer = setInterval(() => this.sendWorldCollabHeartbeat().catch(() => {}), 10000)
    },
    disconnectWorldCollab({ clearWidget = true } = {}) {
      if (this.collabPollTimer) {
        clearInterval(this.collabPollTimer)
        this.collabPollTimer = null
      }
      if (this.collabHeartbeatTimer) {
        clearInterval(this.collabHeartbeatTimer)
        this.collabHeartbeatTimer = null
      }
      this.collabRoom = null
      this.collabMembers = []
      this.collabEvents = []
      this.collabLatestSeq = 0
      this.collabStatus = '协作未连接'
      this.hasRemoteWorldUpdate = false
      this.remoteWorldEvent = null
      if (clearWidget) {
        this.isCollabWidgetActive = false
      }
    },
    async sendWorldCollabHeartbeat() {
      if (!this.collabRoom) return
      const collabIdentity = ensureCollabIdentity()
      await collabApi.heartbeat(this.collabRoom.id, { user_id: collabIdentity.userId })
      const members = await collabApi.listMembers(this.collabRoom.id)
      this.collabMembers = members.members || []
    },
    async pollWorldCollabEvents() {
      if (!this.collabRoom) return
      const response = await collabApi.listEvents(this.collabRoom.id, this.collabLatestSeq, 100)
      const incoming = response.events || []
      if (incoming.length) {
        this.collabEvents.push(...incoming)
        incoming.forEach(this.handleWorldCollabEvent)
      }
      this.collabLatestSeq = response.latest_seq || this.collabLatestSeq
    },
    handleWorldCollabEvent(event) {
      if (!event || event.type !== 'world.saved') return
      const payload = event.payload || {}
      if (payload.world_id !== this.worldId) return
      if (payload.client_id && payload.client_id === this.collabClientId) return
      this.hasRemoteWorldUpdate = true
      this.remoteWorldEvent = event
      this.collabStatus = '检测到远端更新'
    },
    async publishWorldCollabEvent(type, payload = {}) {
      if (!this.worldId) return
      if (!this.collabRoom) {
        await this.ensureWorldCollabRoom()
      }
      if (!this.collabRoom) return
      const collabIdentity = ensureCollabIdentity()
      try {
        await collabApi.appendWorldEvent(this.worldId, {
          type,
          user_id: collabIdentity.userId,
          world_name: this.world.name || '未命名世界观',
          summary: payload.summary || '',
          client_id: this.ensureCollabClientId(),
          base_seq: this.collabLatestSeq,
          payload: {
            ...payload,
            client_id: this.collabClientId,
          },
        })
        await this.pollWorldCollabEvents()
      } catch (error) {
        if (error?.status === 409 || /已被其他成员更新/.test(error?.message || '')) {
          this.hasRemoteWorldUpdate = true
          this.collabStatus = '保存冲突：需先同步远端更新'
        } else {
          console.warn('发布世界观协作事件失败:', error)
        }
      }
    },
    async syncRemoteWorldUpdate() {
      if (!this.worldId) return
      await this.loadWorld(this.worldId, { preserveSettingState: true, successStatus: '已同步远端更新' })
      this.hasRemoteWorldUpdate = false
      this.remoteWorldEvent = null
      this.collabStatus = '协作已连接'
    },
    openCollabRoom() {
      this.$router.push({
        name: 'Collab',
        query: {
          roomId: this.collabRoom?.id || '',
          worldId: this.worldId || '',
        },
      })
    },
    async handleWorldUpdated(event) {
      const worldId = String(event?.detail?.worldId || '').trim()
      if (!worldId || !this.worldId || worldId !== this.worldId) {
        return
      }

      if (this.agentWorldRefreshTimer) {
        clearTimeout(this.agentWorldRefreshTimer)
      }

      this.saveStatus = 'Agent 已修改世界观，正在同步...'
      this.agentWorldRefreshTimer = window.setTimeout(async () => {
        this.agentWorldRefreshTimer = null
        await this.loadWorld(this.worldId, {
          preserveSettingState: true,
          successStatus: '已同步 Agent 变更',
        })
      }, 240)
    },
    applyStoredWorld(world, options = {}) {
      const settingsViewState = options.settingsViewState || null

      if (!world) {
        return
      }

      this.isApplyingStoredWorld = true
      try {
        this.worldId = world.id || ''
        const savedTemplateId = this.resolveKnownTemplateId(world.template_id || world.templateId || DEFAULT_WORLD_TEMPLATE_ID)
        const savedTemplateName = world.template_name || world.templateName || this.getWorldTemplateName(savedTemplateId)
        this.selectedTemplateId = savedTemplateId
        this.savedWorldTemplateId = savedTemplateId
        this.savedWorldTemplateName = savedTemplateName
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
        this.restoreSettingsViewState(settingsViewState)
        this.markWorldAsSaved()
        this.resetEditHistory()
      } finally {
        this.$nextTick(() => {
          this.isApplyingStoredWorld = false
        })
      }
    },
    resetBlankWorldBuilder() {
      this.worldId = ''
      this.linkedProjectId = ''
      this.linkedProjectStatus = ''
      this.isSaving = false
      this.isDeleting = false
      this.isProjectLaunching = false
      this.saveStatus = ''
      this.pendingAutoSave = false
      this.extractError = ''
      this.activeTab = 'basic'
      this.world = {
        name: '',
        description: '',
        era: '',
        anchor_time: '',
        writing_style: '',
        reference_text: '',
      }
      this.selectedTemplateId = this.resolveKnownTemplateId(this.worldTemplateDefaultId || DEFAULT_WORLD_TEMPLATE_ID)
      this.savedWorldTemplateId = this.selectedTemplateId
      this.savedWorldTemplateName = this.getWorldTemplateName(this.savedWorldTemplateId)
      this.extractText = ''
      this.extractScanSource = 'input'
      this.extractionMode = 'fast'
      this.isExtracting = false
      this.extractProgress = { status: '', stage: '', progress: 0, message: '', detail: {}, ragProgress: null, updatedAt: '', startedAt: '', running: false, estimatedTextChars: 0, estimatedTextCharsLabel: '', textEstimateBreakdown: [] }
      this.extractTaskId = ''
      this.isCancellingExtract = false
      this.isPausingExtract = false
      this.isResumingExtract = false
      this.isDeletingExtractTask = false
      this.showExtractScanPanel = false
      this.extractPanelDismissed = false
      this.showExtractResultDialog = false
      this.extractResultDialogDismissed = false
      this.extractedData = null
      if (this.extractPollTimer) {
        clearTimeout(this.extractPollTimer)
        this.extractPollTimer = null
      }
      this.extractPollingTaskId = ''
      this.stopExtractUiTicker()
      this.selectedFiles = []
      this.isDragOver = false
      this.entities = []
      this.events = []
      if (this.agentWorldRefreshTimer) {
        clearTimeout(this.agentWorldRefreshTimer)
        this.agentWorldRefreshTimer = null
      }
      this.stopEvolutionHistoryPolling()
      this.evolutionHistory = []
      this.evolutionHistoryError = ''
      this.showEntitiesExpanded = true
      this.showEventsExpanded = true
      this.expandedBios = {}
      this.entityItems = []
      this.eventItems = []
      this.disabledEntityIds = new Set()
      this.disabledEventIds = new Set()
      this.showAddEntityDialog = false
      this.showAddEventDialog = false
      this.showEditEventDialog = false
      this.newEntity = {
        name: '',
        type: '',
        customType: '',
        attributes: [],
      }
      this.newEvent = {
        name: '',
        description: '',
        date: '',
        selectedSettings: [],
      }
      this.mapData = createDefaultMapData()
      this.selectedEvent = null
      this.selectedTimelineItemId = ''
      this.timelineSearchQuery = ''
      this.timelineTypeFilter = 'all'
      this.calendarGraphicZoom = 1
      this.calendarGraphicCenter = 0
      this.activeCategory = 'character'
      this.activeCollectionId = ''
      this.activeCollectionSnapshot = null
      this.settingsSearchQuery = ''
      this.settingCategories = createDefaultSettingCategories()
      this.settings = createDefaultSettings()
      this.showNewSettingDialog = false
      this.currentSetting = null
      this.currentSettingNewAlias = ''
      this.activeSidebarSettingId = ''
      this.showSettingDetail = false
      this.showSettingSelector = false
      this.selectedSettings = []
      this.selectedCategoryFilter = 'all'
      this.showCalendarEdit = false
      this.showCalendarDetailEdit = false
      this.currentCalendar = null
      this.calendars = createDefaultCalendars()
      this.editCalendars = []
      this.disconnectWorldCollab({ clearWidget: false })
      this.lastPublishedWorldSignature = ''
      this.markWorldAsSaved(this.buildWorldPayload())
      this.resetEditHistory()
    },
    syncRouteWorldId() {
      if (!this.worldId || !this.$router || !this.$route || !this.isWorldBuilderRouteActive()) {
        return
      }

      this.$router.replace({
        query: {
          ...this.$route.query,
          worldId: this.worldId
        }
      })
    },
    async loadWorld(worldId, options = {}) {
      const { preserveSettingState = false, successStatus = '已加载世界观' } = options

      if (!worldId) {
        return
      }

      const settingsViewState = preserveSettingState && worldId === this.worldId
        ? this.captureSettingsViewState()
        : null

      try {
        const response = await worldApi.getWorld(worldId)
        this.applyStoredWorld(response.world, { settingsViewState })
        await this.loadLinkedProject(worldId)
        await this.loadEvolutionHistory(worldId)
        this.$nextTick(() => this.ensureWorldCollabRoom())
        this.saveStatus = successStatus
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
    loadEntityCardRowLayoutPreference() {
      this.entityCardRowAligned = readEntityCardRowLayoutPreference()
    },
    toggleEntityCardRowAlignment(event) {
      const nextValue = typeof event?.target?.checked === 'boolean'
        ? event.target.checked
        : !this.entityCardRowAligned
      this.entityCardRowAligned = nextValue
      writeEntityCardRowLayoutPreference(nextValue)
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
        return await this.saveWorld({ silent: true, skipReload: true })
      } catch (e) {
        console.warn('ensureWorldId 失败，RAG 索引将被跳过:', e)
        return false
      }
    },

    async saveWorld(options = {}) {
      const { silent = false, successMessage, skipReload = false, requireActiveRoute = true } = options
      if (requireActiveRoute && !this.isWorldBuilderRouteActive()) {
        return false
      }
      if (this.isSaving) {
        this.pendingAutoSave = true
        return false
      }

      const payload = this.buildWorldPayload()
      const signature = this.getWorldPayloadSignature(payload)
      if (signature === this.autoSaveSignature) {
        if (!silent) {
          this.saveStatus = successMessage || '已保存'
        }
        return true
      }

      this.isSaving = true
      this.saveStatus = this.worldId ? '自动保存中...' : '正在自动创建世界观...'

      try {
        if (!this.worldId) {
          const createResponse = await worldApi.createWorld({
            ...this.world,
            settings: payload.settings,
            template_id: payload.template_id,
            template_name: payload.template_name,
          })
          this.worldId = createResponse.world_id
          this.syncRouteWorldId()
          await this.ensureWorldCollabRoom()
        }

        const settingsViewState = this.captureSettingsViewState()
        const response = await worldApi.updateWorld(this.worldId, payload)
        if (!skipReload) {
          this.applyStoredWorld(response.world, { settingsViewState })
        }
        this.markWorldAsSaved(skipReload ? payload : this.buildWorldPayload())
        this.syncRouteWorldId()
        if (!skipReload) {
          await this.loadLinkedProject(this.worldId)
          await this.loadEvolutionHistory(this.worldId)
        }
        this.saveStatus = successMessage || '已自动保存'
        if (signature !== this.lastPublishedWorldSignature) {
          this.lastPublishedWorldSignature = signature
          await this.publishWorldCollabEvent('world.saved', {
            summary: this.saveStatus,
            version_signature: signature,
            saved_at: new Date().toISOString(),
          })
        }

        if (!silent) {
          alert(successMessage || '世界观已自动保存！')
        }
        return true
      } catch (error) {
        console.error('保存世界观失败:', error)
        this.saveStatus = '自动保存失败，将在下次修改后重试'
        if (!silent) {
          alert('保存失败，请重试')
        }
        return false
      } finally {
        this.isSaving = false
        if (this.pendingAutoSave) {
          this.pendingAutoSave = false
          if (requireActiveRoute && !this.isWorldBuilderRouteActive()) {
            this.clearPendingAutoSave()
          } else {
            this.scheduleAutoSave()
          }
        }
      }
    },
    async launchProjectFromWorld() {
      if (this.isProjectLaunching) return
      this.isProjectLaunching = true
      this.saveStatus = '正在准备推演...'

      try {
        if (!this.worldId) {
          await this.flushAutoSave()
        } else if (this.autoSaveTimer) {
          await this.flushAutoSave()
        }
        if (!this.worldId) {
          throw new Error('自动创建世界观失败，请稍后重试')
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

    startExtractUiTicker() {
      if (this.extractUiTickTimer) return
      this.extractUiTickTimer = window.setInterval(() => {
        this.extractUiTick += 1
      }, 1000)
    },
    stopExtractUiTicker() {
      if (this.extractUiTickTimer) {
        clearInterval(this.extractUiTickTimer)
        this.extractUiTickTimer = null
      }
    },
    formatScanDuration(seconds) {
      const safeSeconds = Math.max(0, Math.round(Number(seconds || 0)))
      if (safeSeconds >= 3600) {
        return `${Math.floor(safeSeconds / 3600)}时${Math.floor((safeSeconds % 3600) / 60)}分`
      }
      if (safeSeconds >= 60) {
        return `${Math.floor(safeSeconds / 60)}分${safeSeconds % 60}秒`
      }
      return `${safeSeconds}秒`
    },
    formatScanCharCount(chars) {
      const safeChars = Math.max(0, Math.round(Number(chars || 0)))
      if (safeChars >= 10000) return `${(safeChars / 10000).toFixed(1)}万字`
      return `${safeChars}字`
    },
    secondsSince(timestamp) {
      if (!timestamp) return 0
      const time = new Date(timestamp).getTime()
      if (!Number.isFinite(time)) return 0
      return Math.max(0, Math.round((Date.now() - time) / 1000))
    },
    clearStoredExtractTask(taskId) {
      if (!taskId || localStorage.getItem(LAST_EXTRACT_TASK_KEY) === taskId) {
        localStorage.removeItem(LAST_EXTRACT_TASK_KEY)
      }
    },
    resetExtractTaskState(taskId = this.extractTaskId) {
      if (this.extractPollTimer) {
        clearTimeout(this.extractPollTimer)
        this.extractPollTimer = null
      }
      this.extractPollingTaskId = ''
      this.stopExtractUiTicker()
      this.clearStoredExtractTask(taskId)
      if (taskId && this.extractTaskId && taskId !== this.extractTaskId) {
        return
      }
      this.extractTaskId = ''
      this.isExtracting = false
      this.isCancellingExtract = false
      this.isPausingExtract = false
      this.isResumingExtract = false
      this.showExtractScanPanel = false
      this.extractPanelDismissed = true
      this.showExtractResultDialog = false
      this.extractResultDialogDismissed = false
      this.extractProgress = { status: '', stage: '', progress: 0, message: '', detail: {}, ragProgress: null, updatedAt: '', startedAt: '', running: false, estimatedTextChars: 0, estimatedTextCharsLabel: '', textEstimateBreakdown: [] }
    },
    emitExtractTaskDeleted(taskId) {
      window.dispatchEvent(new CustomEvent(EXTRACT_TASK_DELETED_EVENT, { detail: { taskId } }))
    },
    handleExtractTaskDeleted(event) {
      const taskId = event.detail?.taskId
      if (!taskId || taskId !== this.extractTaskId) return
      this.resetExtractTaskState(taskId)
    },
    emitExtractTaskSync(taskId = this.extractTaskId, extra = {}) {
      if (!taskId) return
      window.dispatchEvent(new CustomEvent(EXTRACT_TASK_SYNC_EVENT, {
        detail: {
          taskId,
          worldId: this.worldId,
          extractionMode: this.extractionMode,
          status: this.extractProgress.status || this.extractProgress.stage || 'running',
          stage: this.extractProgress.stage || 'starting',
          progress: this.extractProgress.progress || 0,
          message: this.extractProgress.message || '提取任务已启动',
          detail: this.extractProgress.detail || {},
          ragProgress: this.extractProgress.ragProgress || null,
          updatedAt: this.extractProgress.updatedAt || '',
          startedAt: this.extractProgress.startedAt || '',
          running: this.extractProgress.running || false,
          extractedData: this.extractedData || null,
          resultSummary: this.extractedResultSummary || null,
          estimatedTextChars: this.extractProgress.estimatedTextChars || 0,
          estimatedTextCharsLabel: this.extractProgress.estimatedTextCharsLabel || '',
          textEstimateBreakdown: this.extractProgress.textEstimateBreakdown || [],
          ...extra,
        }
      }))
    },
    removeExtractTaskRouteQuery(taskId) {
      if (!this.$router || !this.$route || this.$route.query?.extractTaskId !== taskId) return
      const query = { ...this.$route.query }
      delete query.extractTaskId
      delete query.showExtractPanel
      this.$router.replace({ query })
    },
    openExtractScanPanel(options = {}) {
      const { syncRoute = true } = options
      if (!this.extractTaskId) return
      this.showExtractScanPanel = true
      this.extractPanelDismissed = false
      if (!syncRoute || !this.$router || !this.$route) return
      const query = {
        ...this.$route.query,
        extractTaskId: this.extractTaskId,
        showExtractPanel: '1',
      }
      if (this.worldId) {
        query.worldId = this.worldId
      }
      this.$router.replace({ query })
    },

    openExtractResultDialog(auto = false) {
      if (!this.extractedData) return
      this.showExtractResultDialog = true
      if (!auto) {
        this.extractResultDialogDismissed = false
      }
    },
    dismissExtractResultDialog() {
      this.showExtractResultDialog = false
      this.extractResultDialogDismissed = true
    },
    discardExtractedData() {
      this.extractedData = null
      this.showExtractResultDialog = false
      this.extractResultDialogDismissed = false
      this.extractText = ''
      this.clearSelectedFilesCache()
    },
    maybeOpenExtractResultDialog(progResp = {}) {
      const status = progResp.status || progResp.stage || this.extractStatus
      if (!progResp.done || !['completed', 'done'].includes(status)) return
      if (!this.extractedData || this.extractResultDialogDismissed) return
      this.showExtractScanPanel = false
      this.extractPanelDismissed = true
      this.showExtractResultDialog = true
    },
    applyExtractProgress(progResp = {}) {
      const rawDetail = progResp.detail || {}
      const completedChunks = progResp.completed_chunks ?? rawDetail.completed_chunks
      const failedChunks = progResp.failed_chunks ?? rawDetail.failed_chunks
      const processedChunks = progResp.processed_chunks ?? rawDetail.processed_chunks ?? ((Number(completedChunks || 0) + Number(failedChunks || 0)) || 0)
      const progressValue = Math.max(0, Math.min(100, Math.round(Number(progResp.progress || 0))))
      this.extractProgress = {
        status: progResp.status || progResp.stage || '',
        stage: progResp.stage || '',
        progress: progressValue,
        message: progResp.message || '',
        done: Boolean(progResp.done),
        running: Boolean(progResp.running),
        updatedAt: progResp.updated_at || rawDetail.updated_at || this.extractProgress.updatedAt || '',
        startedAt: progResp.started_at || rawDetail.started_at || this.extractProgress.startedAt || '',
        finishedAt: progResp.finished_at || rawDetail.finished_at || '',
        estimatedTextChars: Number(progResp.estimated_text_chars ?? rawDetail.estimated_text_chars ?? this.extractProgress.estimatedTextChars ?? 0),
        estimatedTextCharsLabel: progResp.estimated_text_chars_label || rawDetail.estimated_text_chars_label || this.extractProgress.estimatedTextCharsLabel || '',
        textEstimateBreakdown: progResp.text_estimate_breakdown || rawDetail.text_estimate_breakdown || this.extractProgress.textEstimateBreakdown || [],
        detail: {
          ...rawDetail,
          cache_key: progResp.cache_key || rawDetail.cache_key,
          cache_status: progResp.cache_status || rawDetail.cache_status,
          resumed_from_cache: progResp.resumed_from_cache ?? rawDetail.resumed_from_cache,
          completed_chunks: completedChunks,
          failed_chunks: failedChunks,
          processed_chunks: processedChunks,
          total_chunks: progResp.total_chunks ?? rawDetail.total_chunks,
          processed_chars: progResp.processed_chars ?? rawDetail.processed_chars,
          total_chars: progResp.total_chars ?? rawDetail.total_chars,
          processed_chars_label: progResp.processed_chars_label || rawDetail.processed_chars_label,
          total_chars_label: progResp.total_chars_label || rawDetail.total_chars_label,
          context_window: progResp.context_window || rawDetail.context_window,
          target_chunk_chars: progResp.target_chunk_chars || rawDetail.target_chunk_chars,
        },
        ragProgress: progResp.rag_progress || rawDetail.rag_progress || null,
      }
      if (progResp.extraction_mode) {
        this.extractionMode = progResp.extraction_mode
      }
      if (progResp.template_id) {
        this.selectedTemplateId = this.resolveKnownTemplateId(progResp.template_id)
      }
      if (progResp.extracted_data) {
        const wasEmpty = !this.extractedData
        this.extractedData = progResp.extracted_data
        if (wasEmpty) {
          this.extractResultDialogDismissed = false
        }
        this.maybeOpenExtractResultDialog(progResp)
      }
      if (progResp.error) {
        this.extractError = progResp.error
      }
    },
    startExtractPolling(taskId) {
      if (!taskId) return
      if (this.extractPollTimer) {
        clearTimeout(this.extractPollTimer)
      }
      this.extractPollingTaskId = taskId
      this.startExtractUiTicker()
      const pollInterval = 1500
      const pollProgress = async () => {
        if (this.extractPollingTaskId !== taskId) return
        try {
          const progResp = await worldApi.getExtractProgress(taskId)
          if (this.extractPollingTaskId !== taskId) return
          this.applyExtractProgress(progResp)
          this.emitExtractTaskSync(taskId, {
            worldId: progResp.world_id || this.worldId,
            extractionMode: progResp.extraction_mode || this.extractionMode,
            status: progResp.status || progResp.stage || 'running',
            stage: progResp.stage || 'starting',
            progress: progResp.progress || 0,
            message: progResp.message || '扫描任务正在运行',
            detail: progResp.detail || {},
            ragProgress: progResp.rag_progress || progResp.detail?.rag_progress || null,
            updatedAt: progResp.updated_at || '',
            startedAt: progResp.started_at || '',
            finishedAt: progResp.finished_at || '',
            running: Boolean(progResp.running),
            done: Boolean(progResp.done),
            resultSummary: progResp.result_summary || null,
            extractedData: progResp.extracted_data || null,
          })
          if (progResp.done) {
            this.isExtracting = false
            this.isCancellingExtract = false
            this.isPausingExtract = false
            this.isResumingExtract = false
            this.extractPollingTaskId = ''
            this.stopExtractUiTicker()
            if (['completed', 'failed', 'error', 'done'].includes(progResp.status || progResp.stage)) {
              this.clearStoredExtractTask(taskId)
            }
            return
          }
        } catch (e) {
          console.warn('进度轮询失败:', e)
        }
        if (this.isExtracting && this.extractPollingTaskId === taskId) {
          this.extractPollTimer = setTimeout(pollProgress, pollInterval)
        }
      }
      pollProgress()
    },
    async extractWorldInfo(forceRebuild = false) {
      const needsManualInput = this.extractNeedsManualInput
      const hasText = needsManualInput ? this.extractText.trim() : ''
      const hasFiles = needsManualInput ? this.selectedFiles.length > 0 : false
      if (this.extractUsesRagSource && !this.worldId) {
        this.extractError = '请先创建或保存世界观，再使用已有 RAG 知识库扫描。'
        return
      }
      if (needsManualInput && !hasText && !hasFiles) return

      if (!this.hasLlmConfig) {
        this.extractError = '请先配置可用的 LLM API Key、Base URL 和 Model。'
        this.openLlmConfigDialog()
        return
      }
      if (this.extractRequiresEmbedding && !this.hasEmbeddingConfig) {
        this.extractError = '请先配置 Embedding 模型，或在 LLM 配置页选择本地 Embedding 模型。'
        this.goToLlmConfig('embedding')
        return
      }

      this.isExtracting = true
      this.extractError = ''
      this.extractedData = null
      this.extractTaskId = ''
      this.isCancellingExtract = false
      this.isPausingExtract = false
      this.isResumingExtract = false
      this.isDeletingExtractTask = false
      this.showExtractScanPanel = true
      this.extractPanelDismissed = false
      this.showExtractResultDialog = false
      this.extractResultDialogDismissed = false
      this.extractProgress = { status: 'running', stage: 'starting', progress: 0, message: '正在提交提取任务并预估文本总量...', detail: {}, ragProgress: null, updatedAt: new Date().toISOString(), startedAt: new Date().toISOString(), running: true, estimatedTextChars: 0, estimatedTextCharsLabel: '', textEstimateBreakdown: [] }
      try {
        if (this.templateSwitchHasConflict) {
          const confirmed = window.confirm(this.buildTemplateConflictMessage(this.selectedTemplateId, '继续使用'))
          if (!confirmed) {
            this.isExtracting = false
            this.showExtractScanPanel = false
            this.extractPanelDismissed = true
            this.showExtractResultDialog = false
            this.extractResultDialogDismissed = false
            this.extractProgress = { status: '', stage: '', progress: 0, message: '', detail: {}, ragProgress: null, updatedAt: '', startedAt: '', running: false, estimatedTextChars: 0, estimatedTextCharsLabel: '', textEstimateBreakdown: [] }
            return
          }
        }

        if (!this.extractUsesRagSource) {
          // input 模式下，如果没有 worldId，先轻量创建以便自动 RAG 索引
          const hasWorldId = await this.ensureWorldId()
          if (!hasWorldId && !this.worldId) {
            console.warn('世界观创建失败，提取将跳过 RAG 索引')
          }
        }
        if (this.worldId && this.selectedTemplateId !== this.savedWorldTemplateId) {
          await this.saveWorld({ silent: true, skipReload: true, successMessage: '世界模板已更新' })
        }

        // 1. 提交提取任务（附带 worldId 用于自动 RAG 索引）
        const extractOptions = {
          scan_source: this.extractScanSource,
          extraction_mode: this.extractionMode,
          template_id: this.selectedTemplateId,
          force_rebuild: forceRebuild
        }
        let initResponse
        if (hasFiles) {
          const formData = new FormData()
          this.selectedFiles.forEach(file => {
            formData.append('files', file)
          })
          if (hasText) {
            formData.append('text', this.extractText)
          }
          initResponse = await worldApi.extractWorldFromFile(formData, this.worldId, extractOptions)
        } else {
          initResponse = await worldApi.extractWorld(hasText ? this.extractText : '', this.worldId, extractOptions)
        }

        const taskId = initResponse.task_id
        this.extractTaskId = taskId || ''
        if (taskId) {
          this.applyExtractProgress({
            ...initResponse,
            status: 'running',
            stage: 'starting',
            progress: 0,
            done: false,
            running: true,
            detail: {
              estimated_text_chars: initResponse.estimated_text_chars,
              estimated_text_chars_label: initResponse.estimated_text_chars_label,
              text_estimate_breakdown: initResponse.text_estimate_breakdown,
            },
          })
          localStorage.setItem(LAST_EXTRACT_TASK_KEY, taskId)
          this.emitExtractTaskSync(taskId, {
            worldId: initResponse.world_id || this.worldId,
            extractionMode: initResponse.extraction_mode || this.extractionMode,
            status: 'running',
            stage: 'starting',
            message: initResponse.message || '提取任务已启动',
          })
        }
        if (!taskId) {
          // 可能是直接 JSON 数据返回
          if (initResponse.template_id) {
            this.selectedTemplateId = this.resolveKnownTemplateId(initResponse.template_id)
          }
          this.extractedData = initResponse.extracted_data
          this.isExtracting = false
          return
        }

        // 2. 轮询进度（无超时限制，直到后端完成）
        this.startExtractPolling(taskId)
      } catch (error) {
        console.error('提取失败:', error)
        const serverMsg = error.response?.data?.message
        this.extractError = serverMsg || error.message || '提取失败，请重试'
        if (/api key|api_key|invalid_api_key|llm/i.test(this.extractError)) {
          this.openLlmConfigDialog()
        }
        this.isExtracting = false
        this.isCancellingExtract = false
        this.isPausingExtract = false
        this.extractPollingTaskId = ''
        this.stopExtractUiTicker()
      }
    },
    closeExtractScanPanel() {
      this.extractPanelDismissed = true
      this.showExtractScanPanel = false
      if (this.$router && this.$route?.query?.showExtractPanel === '1') {
        const query = { ...this.$route.query }
        delete query.showExtractPanel
        this.$router.replace({ query })
      }
    },
    async restoreExtractTaskFromRoute() {
      const taskId = this.$route?.query?.extractTaskId
      if (!taskId) return
      try {
        const progResp = await worldApi.getExtractProgress(taskId)
        this.extractTaskId = taskId
        this.applyExtractProgress(progResp)
        this.showExtractScanPanel = this.$route?.query?.showExtractPanel === '1'
        this.extractPanelDismissed = false
        localStorage.setItem(LAST_EXTRACT_TASK_KEY, taskId)
        this.emitExtractTaskSync(taskId, {
          worldId: progResp.world_id || this.worldId,
          extractionMode: progResp.extraction_mode || this.extractionMode,
          status: progResp.status || progResp.stage || 'running',
          stage: progResp.stage || 'starting',
          progress: progResp.progress || 0,
          message: progResp.message || '正在恢复扫描任务...',
        })
        if (!progResp.done) {
          this.isExtracting = true
          this.startExtractPolling(taskId)
        }
      } catch (error) {
        console.warn('恢复扫描任务失败:', error)
      }
    },
    async pauseExtraction() {
      if (!this.extractTaskId || this.isPausingExtract) return
      this.isPausingExtract = true
      try {
        await worldApi.pauseExtract(this.extractTaskId)
        this.extractProgress = {
          ...this.extractProgress,
          status: 'pause_requested',
          stage: 'pause_requested',
          message: '正在立即暂停当前扫描，并会从当前章节继续...',
        }
      } catch (error) {
        console.error('暂停提取失败:', error)
        this.extractError = error.response?.data?.message || error.message || '暂停请求失败'
        this.isPausingExtract = false
      }
    },
    async resumeExtraction() {
      if (!this.extractTaskId || this.isResumingExtract) return
      this.isResumingExtract = true
      this.isExtracting = true
      try {
        await worldApi.resumeExtract(this.extractTaskId)
        this.extractProgress = {
          ...this.extractProgress,
          status: 'running',
          stage: 'starting',
          message: '正在从上次 checkpoint 继续解析...',
        }
        this.emitExtractTaskSync(this.extractTaskId, {
          worldId: this.worldId,
          extractionMode: this.extractionMode,
          status: 'running',
          stage: 'starting',
          message: '正在从上次 checkpoint 继续解析...',
        })
        this.startExtractPolling(this.extractTaskId)
      } catch (error) {
        console.error('继续提取失败:', error)
        this.extractError = error.response?.data?.message || error.message || '继续请求失败'
      } finally {
        this.isResumingExtract = false
      }
    },
    async deleteExtractionTask() {
      if (!this.extractTaskId || this.isDeletingExtractTask) return
      if (!confirm('确定删除这条扫描记录吗？不会删除已合并到世界观的数据。')) return
      this.isDeletingExtractTask = true
      try {
        await worldApi.deleteExtractTask(this.extractTaskId)
        const deletedTaskId = this.extractTaskId
        this.resetExtractTaskState(deletedTaskId)
        this.removeExtractTaskRouteQuery(deletedTaskId)
        this.emitExtractTaskDeleted(deletedTaskId)
      } catch (error) {
        console.error('删除扫描失败:', error)
        this.extractError = error.response?.data?.message || error.message || '删除扫描失败'
      } finally {
        this.isDeletingExtractTask = false
      }
    },
    async cancelExtraction() {
      if (!this.extractTaskId || this.isCancellingExtract) return
      this.isCancellingExtract = true
      try {
        await worldApi.cancelExtract(this.extractTaskId)
        this.extractProgress = {
          ...this.extractProgress,
          status: 'cancel_requested',
          stage: 'cancel_requested',
          message: '正在强制中止当前扫描...',
        }
      } catch (error) {
        console.error('中断提取失败:', error)
        this.extractError = error.response?.data?.message || error.message || '中断请求失败'
        this.isCancellingExtract = false
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
      let changed = false
      for (const file of fileList) {
        const ext = file.name.split('.').pop()?.toLowerCase()
        if (ext === 'json') {
          // JSON 文件走直接导入路径
          this.importJsonFile(file)
        } else if (textExts.includes(ext)) {
          // 文本文件走 LLM 提取
          if (!this.selectedFiles.some(f => f.name === file.name && f.size === file.size && f.lastModified === file.lastModified)) {
            this.selectedFiles.push(file)
            changed = true
          }
        }
      }
      if (changed) {
        this.syncSelectedFilesCache()
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
        this.extractResultDialogDismissed = false
        this.showExtractResultDialog = true
        if (data.template_id) {
          this.selectedTemplateId = this.resolveKnownTemplateId(data.template_id)
        }
        this.extractError = ''
      } catch (err) {
        console.error('JSON 导入失败:', err)
        this.extractError = 'JSON 解析失败: ' + (err.message || '格式错误')
      }
    },
    removeFile(index) {
      this.selectedFiles.splice(index, 1)
      this.syncSelectedFilesCache()
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
        this.extractResultDialogDismissed = false
        this.showExtractResultDialog = true
        if (data.template_id) {
          this.selectedTemplateId = this.resolveKnownTemplateId(data.template_id)
        }
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
        const extractedTemplateId = this.resolveKnownTemplateId(this.extractedData.template_id || this.selectedTemplateId)
        if (this.worldHasStructuredContent && extractedTemplateId !== this.savedWorldTemplateId) {
          const confirmed = window.confirm(this.buildTemplateConflictMessage(extractedTemplateId, '应用'))
          if (!confirmed) {
            return
          }
        }
        this.selectedTemplateId = extractedTemplateId
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
        this.showExtractResultDialog = false
        this.extractResultDialogDismissed = false
        this.extractText = ''
        this.selectedFiles = []
        await this.saveWorld({ silent: true, skipReload: true, successMessage: 'AI 提取结果已保存到世界观' })
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
      const entity = this.entities.find(item => String(item.id || '').trim() === String(id || '').trim())
      if (!entity) {
        return
      }

      const linkedSetting = findSettingForEntityRecord(this.settings, entity)
      const entityName = String(entity.name || '').trim() || '未命名实体'
      const linkedSettingName = String(linkedSetting?.name || '').trim()
      const confirmMessage = linkedSettingName
        ? `确定要删除实体“${entityName}”吗？\n这会同时删除对应设定“${linkedSettingName}”。`
        : `确定要删除实体“${entityName}”吗？`

      if (!confirm(confirmMessage)) {
        return
      }

      this.entities = this.entities.filter(item => String(item.id || '').trim() !== String(entity.id || '').trim())

      if (linkedSetting) {
        this.settings = this.settings.filter(setting => String(setting.id || '').trim() !== String(linkedSetting.id || '').trim())
        this.removeSettingReferences(linkedSetting.id)
        if (this.currentSetting && String(this.currentSetting.id || '').trim() === String(linkedSetting.id || '').trim()) {
          this.closeSettingDetail()
        }
      }

      this.removeEntityNamesFromEvents([entityName, linkedSettingName])
      this.syncEntitySettingLinks()
      this.saveStatus = linkedSetting ? '已删除实体及对应设定，正在自动保存...' : '已删除实体，正在自动保存...'
    },
    findEntityForSetting(setting) {
      if (!setting || typeof setting !== 'object') {
        return null
      }

      const linkedEntityId = String(setting.linkedEntityId || '').trim()
      const settingName = String(setting.name || '').trim()

      return this.entities.find((entity) => {
        if (!entity || typeof entity !== 'object') {
          return false
        }

        const entityId = String(entity.id || '').trim()
        if (linkedEntityId && entityId === linkedEntityId) {
          return true
        }

        return settingName && String(entity.name || '').trim() === settingName
      }) || null
    },
    removeSettingReferences(settingId) {
      const normalizedId = String(settingId || '').trim()
      if (!normalizedId) {
        return
      }

      this.selectedSettings = this.selectedSettings.filter(id => String(id || '').trim() !== normalizedId)
      this.newEvent.selectedSettings = this.newEvent.selectedSettings.filter(id => String(id || '').trim() !== normalizedId)
      if (String(this.activeSidebarSettingId || '').trim() === normalizedId) {
        this.activeSidebarSettingId = ''
      }
    },
    removeEntityNamesFromEvents(names = []) {
      const blockedNames = new Set(
        (names || [])
          .map(name => String(name || '').trim())
          .filter(Boolean)
      )

      if (!blockedNames.size) {
        return
      }

      this.events = this.events.map((event) => {
        if (!event || typeof event !== 'object' || !Array.isArray(event.entities)) {
          return event
        }

        const nextEntities = event.entities.filter(name => !blockedNames.has(String(name || '').trim()))
        return nextEntities.length === event.entities.length
          ? event
          : { ...event, entities: nextEntities }
      })
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
      const category = normalizeSettingCategory(this.newSetting.category || this.activeCategory)
      const setting = {
        id: Date.now(),
        name: this.newSetting.name,
        settingType: this.newSetting.settingType,
        category,
        collectionId: this.newSetting.settingType === 'setting'
          ? (this.newSetting.parentCollection || getDefaultCollectionIdForCategory(category))
          : this.newSetting.parentCollection,
        description: this.newSetting.description,
        aliases: [...this.newSetting.aliases],
        showInList: this.newSetting.showInList,
        detailContent: '',
        structuredDetail: createEmptySettingStructuredDetail(this.newSetting.description)
      }
      this.settings = normalizeSettingsForUi([...this.settings, setting])
      if (setting.settingType === 'setting') {
        const createdSetting = this.settings.find(item => item.name === setting.name && item.settingType === 'setting')
        this.openSidebarSetting(createdSetting || setting)
      }
      this.syncEntitySettingLinks()
      this.showNewSettingDialog = false
      alert('设定创建成功！')
    },
    
    // 展开/折叠分类
    toggleCategory(categoryId) {
      const category = this.settingCategories.find(cat => cat.id === categoryId)
      if (category) {
        category.expanded = !category.expanded
      }
    },
    selectCategory(categoryId) {
      this.activeCategory = categoryId
      this.activeCollectionId = ''
      this.activeCollectionSnapshot = null
      if (this.currentSetting && this.currentSetting.category !== categoryId) {
        this.activeSidebarSettingId = ''
      }
    },
    toggleCollectionExpand(collectionId) {
      const collection = this.settings.find(setting => setting.id === collectionId && setting.settingType === 'collection')
      if (collection) {
        collection.expanded = !collection.expanded
      }
    },
    openSettingCollection(collection) {
      if (!collection) {
        return
      }

      this.activeCategory = normalizeSettingCategory(collection.category)
      const category = this.settingCategories.find(item => item.id === this.activeCategory)
      if (category) {
        category.expanded = true
      }

      this.activeCollectionId = collection.id
      this.activeCollectionSnapshot = this.buildCollectionSnapshot(collection)
      if (this.currentSetting && this.currentSetting.collectionId !== collection.id) {
        this.activeSidebarSettingId = ''
      }
    },
    clearActiveCollectionFilter() {
      if (this.activeSettingCollection) {
        this.activeCategory = normalizeSettingCategory(this.activeSettingCollection.category)
      }
      this.activeCollectionId = ''
      this.activeCollectionSnapshot = null
    },
    openSidebarSetting(setting) {
      if (!setting) {
        return
      }

      this.activeCategory = normalizeSettingCategory(setting.category)
      const category = this.settingCategories.find(item => item.id === this.activeCategory)
      if (category) {
        category.expanded = true
      }

      const parentCollection = this.settings.find(item => item.settingType === 'collection' && item.id === setting.collectionId)
      if (parentCollection) {
        parentCollection.expanded = true
        this.activeCollectionId = parentCollection.id
        this.activeCollectionSnapshot = this.buildCollectionSnapshot(parentCollection)
      } else {
        this.activeCollectionId = ''
        this.activeCollectionSnapshot = null
      }

      this.viewSettingDetail(setting)
    },
    
    // 查看设定详情
    viewSettingDetail(setting) {
      this.activeSidebarSettingId = setting?.id || ''
      const editingSetting = JSON.parse(JSON.stringify(setting || {}))
      const linkedEntity = this.findEntityForSetting(editingSetting)
      const existingStructuredDetail = normalizeSettingStructuredDetail(
        editingSetting.structuredDetail,
        editingSetting.description || editingSetting.detailContent
      )

      editingSetting.aliases = normalizeAliases(editingSetting.aliases)
      editingSetting.category = normalizeSettingCategory(editingSetting.category)
      editingSetting.collectionId = editingSetting.collectionId || editingSetting.parentCollection || getDefaultCollectionIdForCategory(editingSetting.category)
      editingSetting.detailContent = String(editingSetting.detailContent || '').trim()
      editingSetting.description = String(editingSetting.description || '').trim()
      editingSetting.structuredDetail = linkedEntity && !editingSetting.structuredDetail
        ? createSettingStructuredDetailFromEntity(linkedEntity, editingSetting.description || editingSetting.detailContent)
        : existingStructuredDetail

      this.currentSetting = editingSetting
      this.currentSettingNewAlias = ''
      this.showSettingDetail = true
    },
    
    // 关闭设定详情
    closeSettingDetail() {
      this.showSettingDetail = false
      this.currentSetting = null
      this.currentSettingNewAlias = ''
    },
    addCurrentSettingAlias() {
      const alias = String(this.currentSettingNewAlias || '').trim()
      if (!alias || !this.currentSetting) {
        return
      }
      if (!Array.isArray(this.currentSetting.aliases)) {
        this.currentSetting.aliases = []
      }
      if (!this.currentSetting.aliases.includes(alias)) {
        this.currentSetting.aliases.push(alias)
      }
      this.currentSettingNewAlias = ''
    },
    removeCurrentSettingAlias(index) {
      if (!Array.isArray(this.currentSetting?.aliases)) {
        return
      }
      this.currentSetting.aliases.splice(index, 1)
    },
    assignCurrentSettingDefaultCollection() {
      if (!this.currentSetting || this.currentSetting.settingType !== 'setting') {
        return
      }
      const category = normalizeSettingCategory(this.currentSetting.category)
      this.currentSetting.category = category
      this.currentSetting.collectionId = getDefaultCollectionIdForCategory(category)
    },
    ensureCurrentSettingStructuredDetail() {
      if (!this.currentSetting) {
        return null
      }
      this.currentSetting.structuredDetail = normalizeSettingStructuredDetail(
        this.currentSetting.structuredDetail,
        this.currentSetting.description || this.currentSetting.detailContent
      )
      return this.currentSetting.structuredDetail
    },
    addSettingFact() {
      const detail = this.ensureCurrentSettingStructuredDetail()
      if (!detail) return
      detail.facts.push(createSettingDetailField('', '', detail.facts.length))
    },
    removeSettingFact(index) {
      const detail = this.ensureCurrentSettingStructuredDetail()
      if (!detail) return
      detail.facts.splice(index, 1)
    },
    addSettingRelationship() {
      const detail = this.ensureCurrentSettingStructuredDetail()
      if (!detail) return
      detail.relationships.push({
        id: createLocalId('setting_relation', detail.relationships.length),
        target: '',
        type: '关联',
        description: '',
        time_period: '',
        source_event: '',
      })
    },
    removeSettingRelationship(index) {
      const detail = this.ensureCurrentSettingStructuredDetail()
      if (!detail) return
      detail.relationships.splice(index, 1)
    },
    addSettingStage() {
      const detail = this.ensureCurrentSettingStructuredDetail()
      if (!detail) return
      detail.stages.push({
        id: createLocalId('setting_stage', detail.stages.length),
        name: '',
        era: '',
        description: '',
        fields: [],
      })
    },
    removeSettingStage(index) {
      const detail = this.ensureCurrentSettingStructuredDetail()
      if (!detail) return
      detail.stages.splice(index, 1)
    },
    addSettingStageField(stageIndex) {
      const detail = this.ensureCurrentSettingStructuredDetail()
      const stage = detail?.stages?.[stageIndex]
      if (!stage) return
      if (!Array.isArray(stage.fields)) {
        stage.fields = []
      }
      stage.fields.push(createSettingDetailField('', '', stage.fields.length))
    },
    removeSettingStageField(stageIndex, fieldIndex) {
      const detail = this.ensureCurrentSettingStructuredDetail()
      const stage = detail?.stages?.[stageIndex]
      if (!stage || !Array.isArray(stage.fields)) return
      stage.fields.splice(fieldIndex, 1)
    },
    refreshCurrentSettingFromEntity() {
      if (!this.currentSetting) return
      const linkedEntity = this.findEntityForSetting(this.currentSetting)
      if (!linkedEntity) return
      this.currentSetting.structuredDetail = createSettingStructuredDetailFromEntity(
        linkedEntity,
        this.currentSetting.description || this.currentSetting.detailContent
      )
      const summary = buildEntitySettingSummary(linkedEntity)
      if (!this.currentSetting.description) {
        this.currentSetting.description = summary.description
      }
      if (!this.currentSetting.detailContent) {
        this.currentSetting.detailContent = summary.detailContent
      }
    },
    buildCurrentSettingDetailContent(setting) {
      const detail = normalizeSettingStructuredDetail(setting.structuredDetail, setting.description || setting.detailContent)
      const lines = []
      if (detail.intro) lines.push(detail.intro)
      if (detail.facts.length) {
        lines.push(detail.facts.map(field => `${field.label || '字段'}：${field.value}`).join('\n'))
      }
      if (detail.relationships.length) {
        lines.push(`关系网络：\n${detail.relationships.map(item => `- ${item.target || '未命名对象'}${item.type ? `（${item.type}）` : ''}${item.description ? `：${item.description}` : ''}`).join('\n')}`)
      }
      if (detail.stages.length) {
        lines.push(`阶段 / 演变：\n${detail.stages.map(stage => {
          const stageTitle = stage.era ? `[${stage.name || '未命名阶段'}｜${stage.era}]` : `[${stage.name || '未命名阶段'}]`
          const fieldText = stage.fields.length ? `｜${stage.fields.map(field => `${field.label || '字段'}：${field.value}`).join('；')}` : ''
          return `- ${stageTitle} ${stage.description || ''}${fieldText}`.trim()
        }).join('\n')}`)
      }
      const freeform = String(setting.detailContent || '').trim()
      if (freeform && !lines.includes(freeform)) {
        lines.push(freeform)
      }
      return lines.filter(Boolean).join('\n\n')
    },
    
    // 保存设定详情
    saveSettingDetail() {
      if (!this.currentSetting) {
        return
      }
      const index = this.settings.findIndex(setting => setting.id === this.currentSetting.id)
      if (index !== -1) {
        const normalizedCurrentSetting = JSON.parse(JSON.stringify(this.currentSetting))
        normalizedCurrentSetting.aliases = normalizeAliases(normalizedCurrentSetting.aliases)
        normalizedCurrentSetting.category = normalizeSettingCategory(normalizedCurrentSetting.category)
        if (normalizedCurrentSetting.settingType === 'setting') {
          normalizedCurrentSetting.collectionId = normalizedCurrentSetting.collectionId || getDefaultCollectionIdForCategory(normalizedCurrentSetting.category)
        }
        normalizedCurrentSetting.structuredDetail = normalizeSettingStructuredDetail(
          normalizedCurrentSetting.structuredDetail,
          normalizedCurrentSetting.description || normalizedCurrentSetting.detailContent
        )
        normalizedCurrentSetting.detailContent = this.buildCurrentSettingDetailContent(normalizedCurrentSetting)
        this.settings[index] = normalizedCurrentSetting
        this.settings = normalizeSettingsForUi(this.settings)
      }
      this.syncEntitySettingLinks()
      this.showSettingDetail = false
      this.currentSetting = null
      this.currentSettingNewAlias = ''
      alert('设定详情保存成功！')
    },
    deleteSetting(settingId) {
      const targetSetting = this.settings.find(setting => String(setting.id || '').trim() === String(settingId || '').trim())
      if (!targetSetting) {
        return
      }

      const linkedEntity = this.findEntityForSetting(targetSetting)
      const settingName = String(targetSetting.name || '').trim() || '未命名设定'
      const linkedEntityName = String(linkedEntity?.name || '').trim()
      const confirmMessage = linkedEntityName
        ? `确定要删除设定“${settingName}”吗？\n这会同时删除对应实体“${linkedEntityName}”。`
        : `确定要删除设定“${settingName}”吗？`

      if (!confirm(confirmMessage)) {
        return
      }

      this.settings = this.settings.filter(setting => String(setting.id || '').trim() !== String(targetSetting.id || '').trim())
      this.removeSettingReferences(targetSetting.id)

      if (linkedEntity) {
        this.entities = this.entities.filter(entity => String(entity.id || '').trim() !== String(linkedEntity.id || '').trim())
        this.removeEntityNamesFromEvents([linkedEntityName, settingName])
      }

      if (this.currentSetting && String(this.currentSetting.id || '').trim() === String(targetSetting.id || '').trim()) {
        this.closeSettingDetail()
      }

      this.syncEntitySettingLinks()
      this.saveStatus = linkedEntity ? '已删除设定及对应实体，正在自动保存...' : '已删除设定，正在自动保存...'
    },
    deleteCurrentSetting() {
      if (!this.currentSetting?.id) {
        return
      }

      this.deleteSetting(this.currentSetting.id)
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
        startYear: 0,
        endYear: 1,
        baseTime: 0,
        timeRange: '0 ~ 1',
        unit: '年',
        ratio: '×1',
        calendarType: '未开启',
        description: '',
        absoluteBaseTime: '',
        localBaseYear: 0
      }
      this.editCalendars.push(newCalendar)
      this.currentCalendar = {
        ...JSON.parse(JSON.stringify(newCalendar)),
        startYear: 0,
        endYear: 1,
        noEndTime: false,
        ratioValue: '1',
        absoluteBaseTime: '',
        localBaseYear: 0,
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
        this.currentCalendar.startYear = normalizeCalendarNumber(calendar.startYear ?? timeRange[0] ?? calendar.baseTime, 0)
        this.currentCalendar.noEndTime = timeRange[1] === '无'
        this.currentCalendar.endYear = this.currentCalendar.noEndTime ? '' : normalizeCalendarNumber(calendar.endYear ?? timeRange[1], this.currentCalendar.startYear + 1)
      } else {
        this.currentCalendar.startYear = normalizeCalendarNumber(calendar.startYear ?? calendar.baseTime, 0)
        this.currentCalendar.endYear = normalizeCalendarNumber(calendar.endYear, this.currentCalendar.startYear + 1)
        this.currentCalendar.noEndTime = false
      }
      // 解析比例系数
      if (calendar.ratio) {
        this.currentCalendar.ratioValue = calendar.ratio.replace('×', '')
      } else {
        this.currentCalendar.ratioValue = '1'
      }
      this.currentCalendar.absoluteBaseTime = calendar.absoluteBaseTime || ''
      this.currentCalendar.localBaseYear = Number.isFinite(Number(calendar.localBaseYear)) ? Number(calendar.localBaseYear) : 0
      this.currentCalendar.customCalendar = String(calendar.calendarType || '').trim() && calendar.calendarType !== '未开启'
      // 打开编辑窗口
      this.showCalendarDetailEdit = true
    },
    
    // 保存历法详情
    saveCalendarDetail() {
      const startYear = normalizeCalendarNumber(this.currentCalendar.startYear, 0)
      const endYear = this.currentCalendar.noEndTime ? '' : normalizeCalendarNumber(this.currentCalendar.endYear, startYear)
      const ratioValue = String(this.currentCalendar.ratioValue || '1').trim() || '1'
      const localBaseYear = startYear
      const savedCalendar = {
        id: this.currentCalendar.id,
        name: String(this.currentCalendar.name || '').trim() || '未命名历法',
        type: String(this.currentCalendar.type || '纪元').trim() || '纪元',
        startYear,
        endYear,
        noEndTime: Boolean(this.currentCalendar.noEndTime),
        baseTime: startYear,
        timeRange: `${startYear} ~ ${this.currentCalendar.noEndTime ? '无' : endYear}`, 
        unit: String(this.currentCalendar.unit || '年').trim() || '年',
        ratio: `×${ratioValue.replace(/^×/, '')}`,
        calendarType: String(this.currentCalendar.calendarType || '未开启').trim() || '未开启',
        description: String(this.currentCalendar.description || '').trim(),
        absoluteBaseTime: String(this.currentCalendar.absoluteBaseTime || '').trim(),
        localBaseYear,
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
    getTimelinePosition(year) {
      if (!Number.isFinite(year)) return 50
      const segments = this.timelineScaleSegments || []
      if (!segments.length) {
        const { min: minTime, max: maxTime } = this.getTimeRange()
        return ((year - minTime) / Math.max(maxTime - minTime, 1)) * 100
      }
      let segment = segments.find(item => year >= item.start && year <= item.end)
      if (!segment) {
        segment = segments.reduce((closest, item) => {
          const distance = year < item.start ? item.start - year : year - item.end
          const closestDistance = closest ? (year < closest.start ? closest.start - year : year - closest.end) : Infinity
          return distance < closestDistance ? item : closest
        }, null)
      }
      if (!segment) return 50
      const local = segment.end === segment.start ? 0.5 : Math.max(0, Math.min(1, (year - segment.start) / (segment.end - segment.start)))
      return (segment.visualStart + (segment.visualEnd - segment.visualStart) * local) * 100
    },

    getTimelineSpanPosition(start, end, options = {}) {
      const positionGetter = options.positionGetter || this.getTimelinePosition
      const left = positionGetter(start)
      const right = positionGetter(Number.isFinite(end) ? end : this.getTimeRange().max)
      const rawWidth = Math.abs(right - left)
      const minWidth = options.minWidth ?? 3
      return { left: Math.min(left, right), width: Math.max(rawWidth, minWidth), rawWidth }
    },

    calculateSpanLayout(items, options = {}) {
      const layout = new Map()
      const rowEnds = []
      const safetyGap = options.safetyGap ?? 0.35

      ;[...items]
        .map(item => {
          const start = Number.isFinite(item.start) ? item.start : 0
          const end = Number.isFinite(item.end) ? item.end : start + 1
          const spanPosition = this.getTimelineSpanPosition(start, end, { minWidth: 0, positionGetter: options.positionGetter })
          const displayPosition = this.getTimelineSpanPosition(start, end, { minWidth: options.minDisplayWidth ?? 0.8, positionGetter: options.positionGetter })
          return {
            item,
            start,
            end,
            visualStart: spanPosition.left,
            visualEnd: spanPosition.left + spanPosition.rawWidth,
            displayLeft: displayPosition.left,
            displayWidth: displayPosition.width,
          }
        })
        .sort((a, b) => a.visualStart - b.visualStart || a.visualEnd - b.visualEnd)
        .forEach(entry => {
          let row = 0

          while (row < rowEnds.length && rowEnds[row] + safetyGap > entry.visualStart) {
            row += 1
          }

          rowEnds[row] = Math.max(rowEnds[row] || -Infinity, entry.visualEnd)
          layout.set(entry.item.id, {
            row,
            start: entry.start,
            end: entry.end,
            visualStart: entry.visualStart,
            visualEnd: entry.visualEnd,
            displayLeft: entry.displayLeft,
            displayWidth: entry.displayWidth,
          })
        })

      return layout
    },

    calculatePointLayout(items, proximity = 4, maxRows = 10) {
      const layout = new Map()
      const rowPositions = []
      ;[...items]
        .sort((a, b) => (a.year || 0) - (b.year || 0) || b.weight - a.weight)
        .forEach(item => {
          const year = Number.isFinite(item.year) ? item.year : this.getTimeRange().min
          const position = this.getTimelinePosition(year)
          let row = rowPositions.findIndex(lastPosition => Math.abs(position - lastPosition) >= proximity)
          if (row < 0 && rowPositions.length < maxRows) {
            row = rowPositions.length
          }
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

    getCalendarGraphicPosition(year) {
      const range = this.calendarGraphicRange
      if (!Number.isFinite(year) || !range || range.span <= 0) return 50
      return ((year - range.min) / range.span) * 100
    },

    handleCalendarGraphicWheel(event) {
      event.preventDefault()
      const range = this.calendarGraphicRange
      const delta = event.deltaY || event.deltaX || 0
      if (event.ctrlKey || event.metaKey) {
        const centerBefore = (range.min + range.max) / 2
        const factor = delta > 0 ? 0.8 : 1.25
        this.calendarGraphicCenter = (Number.isFinite(this.calendarGraphicCenter) && this.calendarGraphicCenter !== 0)
          ? this.calendarGraphicCenter
          : centerBefore
        this.calendarGraphicZoom = Math.max(0.4, Math.min(8, this.calendarGraphicZoom * factor))
        return
      }
      const move = (delta / 900) * range.span
      const nextCenter = (Number.isFinite(this.calendarGraphicCenter) && this.calendarGraphicCenter !== 0)
        ? this.calendarGraphicCenter + move
        : (range.min + range.max) / 2 + move
      const padding = range.fullSpan || range.span
      this.calendarGraphicCenter = Math.max(range.fullMin - padding, Math.min(range.fullMax + padding, nextCenter))
    },

    getCalendarGraphicBandClass(segment) {
      return [
        `is-${segment.item.kind}`,
        {
          selected: this.selectedTimelineItemId === segment.item.id,
          'is-low-confidence': segment.item.confidence === 'low',
          'is-connected-prev': segment.connectedPrev,
          'is-connected-next': segment.connectedNext,
          'is-clipped-start': segment.clippedStart,
          'is-clipped-end': segment.clippedEnd,
          'is-open-ended': segment.item.openEnded,
        }
      ]
    },

    getCalendarGraphicBandStyle(segment) {
      return {
        left: `${segment.left}%`,
        width: `${Math.max(0.8, Math.min(segment.width, 100 - segment.left))}%`,
        '--clip-offset': segment.clippedStart ? '14px' : '0px',
      }
    },

    getTimelineBandStyle(item, layout, index, topOffset, paletteSet) {
      const layoutInfo = layout.get(item.id)
      if (!layoutInfo) {
        return {}
      }

      const left = Number.isFinite(layoutInfo.displayLeft) ? layoutInfo.displayLeft : layoutInfo.visualStart
      const width = Number.isFinite(layoutInfo.displayWidth) ? layoutInfo.displayWidth : Math.max(layoutInfo.visualEnd - layoutInfo.visualStart, 3)
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
        width: `${Math.max(0.2, Math.min(width, 100 - left))}%`,
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
        if (!Number.isFinite(year)) return
        minTime = Math.min(minTime, year)
        maxTime = Math.max(maxTime, year)
      }

      const focus = this.timelineFocusWindow
      if (focus) {
        return { min: focus.min, max: focus.max }
      }

      const anchorYear = this.timelineAnchor?.year

      this.calendarTimelineItems.forEach(calendar => {
        registerYear(calendar.start)
        registerYear(calendar.end)
      })
      this.timelineEventItems.forEach(event => registerYear(event.year))
      this.timelineStageItems.forEach(stage => registerYear(stage.year))
      registerYear(anchorYear)

      if (!Number.isFinite(minTime) || !Number.isFinite(maxTime)) {
        const fallback = Number.isFinite(anchorYear) ? anchorYear : 0
        return { min: fallback - 1000, max: fallback + 1000 }
      }

      if (!Number.isFinite(anchorYear)) {
        const padding = Math.max(100, Math.round((maxTime - minTime) * 0.1))
        return { min: minTime - padding, max: maxTime + padding }
      }

      const leftSpan = Math.max(anchorYear - minTime, 0)
      const rightSpan = Math.max(maxTime - anchorYear, 0)
      const half = Math.max(leftSpan, rightSpan, 100)
      const paddedHalf = Math.ceil(half * 1.15)
      return {
        min: anchorYear - paddedHalf,
        max: anchorYear + paddedHalf,
      }
    },
    
    // 获取事件在时间轴上的位置
    getEventPosition(date) {
      const year = resolveTimelineExpression(date, this.timelineContext)?.year
      if (!Number.isFinite(year)) return 50

      return this.getTimelinePosition(year)
    },
    
    // 获取锚定时间的位置
    getAnchorTimePosition() {
      const year = this.timelineAnchor?.year
      if (!Number.isFinite(year)) return 50

      return this.getTimelinePosition(year)
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
        if (this.timelineAnchor) {
          this.scrollToPosition(this.getAnchorTimePosition())
        }
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
    window.addEventListener(EXTRACT_TASK_DELETED_EVENT, this.handleExtractTaskDeleted)
    window.addEventListener(WORLD_UPDATED_EVENT, this.handleWorldUpdated)
    window.addEventListener('keydown', this.handleEditHistoryShortcut)
    this.isCollabWidgetActive = true
    this.resetEditHistory()
    this.syncTimelineRefs()
    this.updateTimelineZoom()
    this.loadLlmConfigStatus()
    this.loadWorldTemplates()
    this.loadEntityCardRowLayoutPreference()

    const worldId = String(this.$route?.query?.worldId || '').trim()
    if (worldId) {
      this.loadWorld(worldId)
    } else {
      this.resetBlankWorldBuilder()
    }
    this.restoreExtractTaskFromRoute()
  },
  activated() {
    this.isCollabWidgetActive = true
    this.loadLlmConfigStatus()
    this.loadWorldTemplates()
    this.loadEntityCardRowLayoutPreference()
    const worldId = String(this.$route?.query?.worldId || '').trim()
    if (worldId && worldId !== this.worldId) {
      this.loadWorld(worldId)
    } else if (worldId && worldId === this.worldId) {
      this.loadWorld(worldId, { preserveSettingState: true, successStatus: '' })
    } else {
      this.resetBlankWorldBuilder()
    }
    this.restoreExtractTaskFromRoute()
  },
  deactivated() {
    this.syncSelectedFilesCache()
    this.clearPendingAutoSave()
    this.disconnectWorldCollab()
  },
  beforeRouteLeave(to, from, next) {
    this.syncSelectedFilesCache()
    this.clearPendingAutoSave()
    next()
  },
  beforeUnmount() {
    this.syncSelectedFilesCache()
    window.removeEventListener(EXTRACT_TASK_DELETED_EVENT, this.handleExtractTaskDeleted)
    this.disconnectWorldCollab()
    window.removeEventListener(WORLD_UPDATED_EVENT, this.handleWorldUpdated)
    window.removeEventListener('keydown', this.handleEditHistoryShortcut)
    this.clearPendingAutoSave()
    if (this.extractPollTimer) {
      clearTimeout(this.extractPollTimer)
      this.extractPollTimer = null
    }
    this.stopExtractUiTicker()
    if (this.agentWorldRefreshTimer) {
      clearTimeout(this.agentWorldRefreshTimer)
      this.agentWorldRefreshTimer = null
    }
    if (this.collabPollTimer) {
      clearInterval(this.collabPollTimer)
      this.collabPollTimer = null
    }
    if (this.collabHeartbeatTimer) {
      clearInterval(this.collabHeartbeatTimer)
      this.collabHeartbeatTimer = null
    }
    this.stopEvolutionHistoryPolling()
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

.builder-header-side {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--spacing-sm);
}

.builder-header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.history-actions {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.collab-status-card {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 5px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--wf-border-light);
  background: rgba(255, 255, 255, 0.03);
  color: var(--wf-text-secondary);
  font-size: 14px;
  font-weight: 500;
}

.collab-status-card.active {
  border-color: var(--wf-border-light);
  background: rgba(255, 255, 255, 0.03);
}

.collab-status-card span {
  color: var(--wf-text-secondary);
  white-space: nowrap;
}

.inline-sync-btn {
  margin-top: 0;
  border: 0;
  border-left: 1px solid var(--wf-border);
  padding: 0 0 0 10px;
  background: transparent;
  color: var(--wf-accent);
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  text-align: left;
  line-height: 1.2;
}

.inline-sync-btn:hover {
  color: var(--wf-accent-hover);
  text-decoration: none;
}

.history-btn {
  width: 34px;
  min-width: 34px;
  height: 34px;
  min-height: 34px;
  padding: 0;
  border-radius: var(--radius-full);
  box-shadow: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
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
  border-color: var(--wf-accent);
  box-shadow: 0 0 0 3px var(--wf-accent-muted);
}

.extraction-mode-section {
  margin-top: var(--spacing-md);
  padding: var(--spacing-lg);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-xl);
  background: var(--wf-bg-card);
}

.compact-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.small-title {
  font-size: 1rem;
  color: var(--wf-text-primary);
}

.type-selector {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: var(--spacing-md);
}

.type-btn {
  padding: var(--spacing-lg);
  min-height: 96px;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-xl);
  background: var(--wf-bg-card);
  color: var(--wf-text-primary);
  cursor: pointer;
  text-align: left;
  font-weight: 600;
  display: grid;
  align-content: center;
  gap: 4px;
}

.type-btn:hover:not(.active) {
  border-color: var(--wf-border-light);
  background: var(--wf-bg-hover);
}

.type-btn span {
  display: block;
  margin-top: 0;
  color: var(--wf-text-muted);
  font-size: 0.86rem;
  font-weight: 400;
}

.type-btn.active {
  border-color: var(--wf-accent);
  background: var(--wf-accent-muted);
  color: var(--wf-accent);
  box-shadow: var(--shadow-glow);
}

.template-candidate-bar {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  padding: var(--spacing-md) var(--spacing-lg);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.03);
}

.template-candidate-label {
  flex-shrink: 0;
  padding-top: 2px;
  color: var(--wf-text-muted);
  font-size: 12px;
  letter-spacing: 0.02em;
}

.template-candidate-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
}

.template-candidate-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--radius-full);
  border: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.template-candidate-btn:hover {
  border-color: var(--wf-border-light);
  background: rgba(255, 255, 255, 0.06);
  color: var(--wf-text-primary);
}

.template-candidate-btn.active {
  border-color: var(--wf-accent);
  background: var(--wf-accent-muted);
  color: var(--wf-accent);
  box-shadow: var(--shadow-glow);
}

.template-candidate-name {
  white-space: nowrap;
}

.template-candidate-badge {
  padding: 1px 6px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-muted);
  font-size: 11px;
}

.single-template-panel {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--spacing-lg);
  padding: var(--spacing-lg);
  border: 1px solid var(--wf-border);
}

.single-template-main {
  min-width: 0;
  flex: 1;
}

.single-template-title-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.single-template-title {
  font-size: 1rem;
  font-weight: 700;
  color: var(--wf-text-primary);
}

.template-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: var(--radius-full);
  border: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-muted);
  font-size: 12px;
}

.single-template-description {
  margin: var(--spacing-sm) 0 0;
  color: var(--wf-text-secondary);
  line-height: 1.7;
}

.template-detail-link {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  align-self: flex-start;
  margin-top: 2px;
  padding: 7px 12px;
  border-radius: var(--radius-full);
  border: 1px solid var(--wf-border-light);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-accent);
  font-size: 0.82rem;
  font-weight: 600;
  text-decoration: none;
  transition: all var(--transition-fast);
}

.template-detail-link:hover {
  background: var(--wf-accent-muted);
  border-color: var(--wf-accent);
  color: var(--wf-accent-hover);
}

.template-tag-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-md);
}

.template-tag {
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

.type-btn.active .template-tag {
  border-color: rgba(14, 165, 233, 0.22);
  background: rgba(14, 165, 233, 0.12);
  color: var(--wf-accent);
}

.extract-action-row {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.extract-action-row .extract-btn {
  min-width: 132px;
}

.extract-source-section {
  margin-bottom: var(--spacing-md);
}

.extract-source-note {
  margin-top: var(--spacing-sm);
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: rgba(59, 130, 246, 0.08);
  border: 1px solid rgba(59, 130, 246, 0.2);
  color: var(--wf-text-secondary);
  font-size: 0.88rem;
}

.extract-source-note.is-warning {
  background: rgba(245, 158, 11, 0.12);
  border-color: rgba(245, 158, 11, 0.26);
  color: var(--wf-warning);
}

.extract-guidance {
  margin-top: var(--spacing-sm);
  display: grid;
  gap: 6px;
}

.extract-guidance-item {
  margin: 0;
  color: var(--wf-text-muted);
  font-size: 0.84rem;
}

.extract-inline-actions,
.deep-actions-row {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
  margin-top: var(--spacing-sm);
}

.cache-progress-note {
  margin-top: var(--spacing-sm);
  font-size: 0.82rem;
  color: var(--wf-text-muted);
}

.deep-scan-overlay {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-lg);
  background: rgba(0, 0, 0, 0.62);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

.deep-scan-modal {
  width: min(760px, calc(100vw - 32px));
  max-height: calc(100vh - 64px);
  overflow-y: auto;
  border: 1px solid var(--wf-border-light);
  border-radius: var(--radius-xl);
  background: rgba(17, 17, 19, 0.96);
  color: var(--wf-text-primary);
  box-shadow: var(--shadow-lg);
}

.deep-scan-top,
.deep-scan-section,
.deep-scan-footer {
  padding: var(--spacing-lg);
  border-bottom: 1px solid var(--wf-border);
}

.deep-scan-footer {
  border-bottom: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--spacing-md);
}

.deep-stats-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-md);
  color: var(--wf-accent);
  font-family: var(--font-mono);
  font-size: 0.88rem;
}

.deep-scan-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
}

.deep-scan-title-row h3,
.deep-scan-section h4 {
  margin: 0;
  color: var(--wf-text-primary);
}

.deep-scan-title-row span {
  color: var(--wf-accent);
  font-family: var(--font-mono);
}

.scan-title-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.scan-close-btn {
  width: 30px;
  height: 30px;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.06);
  color: var(--wf-text-primary);
  cursor: pointer;
  font-size: 1.1rem;
  line-height: 1;
}

.scan-close-btn:hover {
  border-color: var(--wf-border-light);
  background: rgba(255, 255, 255, 0.1);
}

.deep-main-bar,
.deep-chunk-bar {
  height: 8px;
  background: var(--wf-bg-input);
}

.deep-scan-meta,
.deep-empty,
.deep-summary {
  margin-top: var(--spacing-sm);
  color: var(--wf-text-secondary);
  font-size: 0.9rem;
}

.scan-complete-banner {
  margin-top: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid rgba(16, 185, 129, 0.28);
  border-radius: var(--radius-md);
  background: rgba(16, 185, 129, 0.10);
  color: #86efac;
  font-weight: 600;
  line-height: 1.6;
}

.scan-live-note {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--wf-accent);
}

.scan-live-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--wf-accent);
  box-shadow: 0 0 10px var(--wf-accent-glow);
  animation: scanLivePulse 1.4s ease-in-out infinite;
  flex: 0 0 auto;
}

@keyframes scanLivePulse {
  0%, 100% { opacity: 0.45; transform: scale(0.85); }
  50% { opacity: 1; transform: scale(1.15); }
}

.deep-row {
  display: grid;
  grid-template-columns: 96px 1fr;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
}

.deep-row:last-child {
  margin-bottom: 0;
}

.deep-row.stacked {
  grid-template-columns: 96px 1fr auto;
}

.deep-label {
  color: var(--wf-text-muted);
  font-size: 0.86rem;
}

.deep-discovery-list {
  margin: var(--spacing-sm) 0 0;
  padding-left: 1.1rem;
  color: var(--wf-text-secondary);
}

.deep-discovery-list li {
  margin: 4px 0;
}

.deep-summary {
  padding: var(--spacing-md);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  background: var(--wf-bg-input);
  line-height: 1.7;
}

.rag-sub-progress {
  margin-top: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid rgba(59, 130, 246, 0.16);
  border-radius: var(--radius-sm);
  background: rgba(59, 130, 246, 0.04);
}

.rag-sub-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--wf-text-secondary);
}

.sub-progress-bar {
  height: 6px;
}

.rag-progress-fill {
  background: linear-gradient(90deg, #10b981, #3b82f6);
}

.rag-sub-message {
  margin: 6px 0 0;
  font-size: 0.78rem;
  color: var(--wf-text-muted);
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
  background: var(--wf-accent);
  color: var(--wf-text-on-accent);
  border-color: var(--wf-accent);
  font-weight: 600;
}
.btn-primary:hover:not(:disabled) {
  background: var(--wf-accent-hover);
  box-shadow: var(--shadow-glow-strong);
}

.btn-secondary {
  background: transparent;
  color: var(--wf-accent);
  border-color: var(--wf-border-light);
}
.btn-secondary:hover:not(:disabled) {
  background: var(--wf-accent-muted);
  border-color: var(--wf-accent);
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
  border-bottom: 1px solid var(--wf-border);
  background: rgba(255, 255, 255, 0.035);
  position: sticky;
  top: 0;
  z-index: 10;
  backdrop-filter: blur(10px);
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
  background: rgba(255, 255, 255, 0.06);
  color: var(--wf-text-primary);
}

.category-item.expanded {
  background: rgba(255, 255, 175, 0.06);
  color: var(--wf-accent);
  border: 1px solid rgba(255, 255, 175, 0.12);
  font-weight: 600;
}

.collection-item.active,
.setting-item.active {
  background: rgba(255, 255, 175, 0.08);
  color: var(--wf-accent);
  font-weight: 600;
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
  background: rgba(255, 255, 255, 0.10);
}

.tree-node::before {
  content: '';
  position: absolute;
  left: 10px;
  top: 20px;
  width: 10px;
  height: 1px;
  background: rgba(255, 255, 255, 0.10);
}

.tree-expand-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 20px;
  padding: 0;
  margin: 0 2px 0 0;
  border: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  z-index: 2;
  flex: 0 0 14px;
}

.tree-expand-button:hover .expand-icon {
  color: var(--wf-text-primary);
}

.tree-item-main {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  min-width: 0;
  align-self: stretch;
  padding: 0;
  border: 0;
  background: transparent;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
  z-index: 2;
  flex: 1 1 auto;
}

.expand-icon {
  width: 14px;
  height: 14px;
  color: var(--wf-text-muted);
  flex: 0 0 14px;
}

.collection-item-main {
  height: 100%;
  justify-content: flex-start;
}

.category-icon, .collection-icon, .setting-icon {
  margin-right: var(--spacing-sm);
  z-index: 2;
  color: var(--wf-accent);
  flex: 0 0 auto;
}

.item-name, .category-name, .collection-name, .setting-name {
  z-index: 2;
  min-width: 0;
  text-align: left;
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
.search-input { width: 100%; max-width: 400px; padding: var(--spacing-sm) var(--spacing-md); border: 1px solid var(--wf-border); border-radius: var(--radius-sm); background: var(--wf-bg-input); color: var(--wf-text-primary); }

.content-header { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  margin-bottom: var(--spacing-lg); 
}

.settings-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: var(--spacing-lg);
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: rgba(64, 145, 255, 0.08);
  border: 1px solid rgba(64, 145, 255, 0.16);
}

.settings-filter-chip {
  color: var(--primary-blue-dark);
  font-weight: 500;
}

.settings-filter-clear {
  border: none;
  background: transparent;
  color: var(--primary-blue-dark);
  cursor: pointer;
  font-size: 0.9rem;
}

.settings-filter-clear:hover {
  text-decoration: underline;
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

/* =========== Timeline Workspace =========== */
.timeline-section {
  background: var(--wf-bg-card);
  padding: var(--spacing-xl);
  border-radius: var(--radius-xl);
  box-shadow: none;
  border: 1px solid var(--wf-border);
}

.timeline-workspace {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.timeline-hero-panel {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-lg);
  padding: var(--spacing-xl);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-xl);
  background:
    radial-gradient(circle at 10% 0%, rgba(255, 255, 175, 0.10), transparent 34%),
    rgba(255, 255, 255, 0.035);
}

.timeline-hero-copy { max-width: 680px; }

.timeline-eyebrow {
  display: inline-flex;
  margin-bottom: var(--spacing-sm);
  color: var(--wf-accent);
  font-family: var(--font-mono);
  font-size: 0.78rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.timeline-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
  justify-content: flex-end;
}

.timeline-view-tabs,
.timeline-filter-chips {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-full);
  background: rgba(0, 0, 0, 0.22);
}

.timeline-view-tabs button,
.timeline-filter-chips button {
  border: 0;
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--wf-text-secondary);
  padding: 8px 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  line-height: 1;
  min-height: 32px;
}

.timeline-view-tabs button.active,
.timeline-filter-chips button.active {
  background: var(--wf-accent);
  color: var(--wf-text-on-accent);
  box-shadow: var(--shadow-glow);
}

.timeline-overview-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--spacing-md);
}

.timeline-overview-card {
  position: relative;
  overflow: hidden;
  padding: var(--spacing-lg);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.035);
  transition: border-color 0.18s ease, background 0.18s ease, transform 0.18s ease;
}

.timeline-overview-card::after {
  content: '';
  position: absolute;
  inset: auto 16px 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 175, 0.42), transparent);
  opacity: 0.4;
}

.timeline-overview-card:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 175, 0.22);
  background: rgba(255, 255, 255, 0.05);
}

.timeline-overview-card span,
.status-label {
  display: block;
  color: var(--wf-text-muted);
  font-size: 0.78rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  margin-bottom: 6px;
}

.timeline-overview-card strong {
  display: block;
  color: var(--wf-text-primary);
  font-size: 1.35rem;
  line-height: 1.2;
}

.timeline-overview-card small {
  display: block;
  margin-top: 6px;
  color: var(--wf-text-muted);
}

.timeline-overview-card.is-primary {
  background: var(--wf-accent-muted);
  border-color: rgba(255, 255, 175, 0.18);
}

.timeline-overview-card.has-warning strong { color: var(--wf-warning); }

.timeline-filter-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.timeline-search-box {
  flex: 1;
  min-width: 280px;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 0 var(--spacing-md);
  height: 42px;
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-full);
  background: var(--wf-bg-input);
  color: var(--wf-text-muted);
}

.timeline-search-box input {
  flex: 1;
  border: 0;
  background: transparent;
  padding: 0;
  color: var(--wf-text-primary);
  box-shadow: none;
}

.timeline-search-box input:focus { box-shadow: none; }

.timeline-workspace-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: var(--spacing-lg);
  align-items: start;
}

.timeline-main-panel,
.timeline-detail-panel {
  min-width: 0;
}

.timeline-story-view,
.timeline-calendar-view,
.timeline-diagnostics-view,
.timeline-detail-card,
.timeline-detail-empty {
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-xl);
  background: rgba(0, 0, 0, 0.22);
  padding: var(--spacing-lg);
}

.chronology-group {
  display: grid;
  grid-template-columns: 140px minmax(0, 1fr);
  gap: var(--spacing-lg);
  padding: var(--spacing-lg) 0;
  border-bottom: 1px solid var(--wf-border);
}

.chronology-group:last-child { border-bottom: 0; }

.chronology-year-rail {
  position: sticky;
  top: 16px;
  align-self: start;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.chronology-year {
  color: var(--wf-accent);
  font-family: var(--font-mono);
  font-weight: 700;
}

.chronology-count {
  color: var(--wf-text-muted);
  font-size: 0.78rem;
}

.chronology-card-stack {
  display: grid;
  gap: var(--spacing-sm);
}

.chronology-card {
  position: relative;
  width: 100%;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) auto;
  align-items: center;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
  background:
    linear-gradient(90deg, rgba(255, 255, 175, 0.035), transparent 42%),
    rgba(255, 255, 255, 0.035);
  color: var(--wf-text-primary);
  text-align: left;
  white-space: normal;
  transition: transform 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.chronology-card:hover,
.chronology-card.selected,
.calendar-line-card:hover,
.calendar-line-card.selected,
.diagnostic-row:hover {
  border-color: rgba(255, 255, 175, 0.35);
  background: var(--wf-accent-muted);
  transform: translateY(-1px);
}

.chronology-card-icon,
.diagnostic-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.06);
  color: var(--wf-accent);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 175, 0.08);
}

.chronology-hover-card {
  position: absolute;
  left: 54px;
  bottom: calc(100% + 10px);
  z-index: 25;
  width: min(360px, calc(100vw - 80px));
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 11px 13px;
  border: 1px solid rgba(255, 255, 175, 0.24);
  border-radius: var(--radius-md);
  background: rgba(17, 17, 19, 0.96);
  color: var(--wf-text-primary);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.48), var(--shadow-glow);
  backdrop-filter: blur(14px);
  opacity: 0;
  pointer-events: none;
  transform: translateY(8px);
  transition: opacity 0.16s ease, transform 0.16s ease;
}

.chronology-hover-card strong {
  color: var(--wf-accent);
  font-size: 0.92rem;
}

.chronology-hover-card small,
.chronology-hover-card em {
  color: var(--wf-text-secondary);
  font-size: 0.78rem;
  font-style: normal;
  line-height: 1.5;
}

.chronology-card:hover .chronology-hover-card,
.chronology-card:focus-visible .chronology-hover-card {
  opacity: 1;
  transform: translateY(0);
}

.chronology-card-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
  gap: 4px;
}

.chronology-card-kicker,
.chronology-card-body small,
.calendar-line-range,
.diagnostic-main small,
.detail-time {
  color: var(--wf-text-muted);
  font-size: 0.82rem;
}

.chronology-card-body strong,
.calendar-line-name,
.diagnostic-main strong {
  color: var(--wf-text-primary);
  font-size: 0.98rem;
}

.chronology-confidence {
  justify-self: end;
  padding: 4px 8px;
  border-radius: var(--radius-full);
  border: 1px solid var(--wf-border);
  color: var(--wf-text-muted);
  font-size: 0.72rem;
}

.chronology-confidence.is-high { color: var(--wf-success); border-color: rgba(0, 212, 170, 0.28); }
.chronology-confidence.is-low { color: var(--wf-warning); border-color: rgba(255, 165, 2, 0.28); }

.calendar-graphic-panel {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-lg);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-xl);
  background:
    radial-gradient(circle at 8% 0%, rgba(255, 255, 175, 0.08), transparent 28%),
    rgba(255, 255, 255, 0.025);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.calendar-graphic-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.calendar-graphic-header strong {
  color: var(--wf-text-primary);
  font-size: 1rem;
}

.calendar-graphic-header p {
  margin: 4px 0 0;
  color: var(--wf-text-muted);
  font-size: 0.84rem;
  line-height: 1.6;
}

.calendar-graphic-header span,
.calendar-axis-meter {
  flex: 0 0 auto;
  color: var(--wf-accent);
  font-family: var(--font-mono);
  font-size: 0.82rem;
}

.calendar-axis-meter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 7px 10px;
  border: 1px solid rgba(255, 255, 175, 0.18);
  border-radius: var(--radius-full);
  background: rgba(255, 255, 175, 0.07);
  line-height: 1;
}

.calendar-graphic-stage {
  position: relative;
  isolation: isolate;
  min-height: 260px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  border-radius: var(--radius-lg);
  background: transparent;
  --calendar-stage-bg:
    radial-gradient(circle at 12% 18%, rgba(255, 255, 175, 0.10), transparent 24%),
    linear-gradient(90deg, rgba(255, 255, 255, 0.055) 1px, transparent 1px),
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(0, 0, 0, 0.20));
  background-size: auto, 10% 100%, auto;
  overflow: visible;
  padding: 0 12px;
  cursor: grab;
  outline: none;
}

.calendar-graphic-stage:active { cursor: grabbing; }

.calendar-graphic-stage:focus-visible {
  border-color: rgba(255, 255, 175, 0.36);
  box-shadow: 0 0 0 3px rgba(255, 255, 175, 0.08);
}

.calendar-graphic-stage::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: inherit;
  pointer-events: none;
  background: var(--calendar-stage-bg);
  background-size: auto, 10% 100%, auto;
  clip-path: inset(0 round var(--radius-lg));
}

.calendar-graphic-axis {
  position: absolute;
  left: 24px;
  right: 24px;
  top: 30px;
  height: 38px;
}

.calendar-axis-line {
  position: absolute;
  left: 0;
  right: 0;
  top: 12px;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(255, 255, 175, 0.18), rgba(255, 255, 175, 0.9), rgba(255, 255, 175, 0.18));
  box-shadow: 0 0 18px rgba(255, 255, 175, 0.18);
}

.calendar-axis-start,
.calendar-axis-end,
.calendar-axis-tick {
  position: absolute;
  top: 20px;
  color: var(--wf-text-muted);
  font-family: var(--font-mono);
  font-size: 0.68rem;
  white-space: nowrap;
  padding-top: 2px;
  text-shadow: 0 1px 10px rgba(0, 0, 0, 0.65);
}

.calendar-axis-start { left: 0; }
.calendar-axis-end { right: 0; }
.calendar-axis-tick { transform: translateX(-50%); }

.calendar-axis-tick::before {
  content: '';
  position: absolute;
  left: 50%;
  top: -13px;
  width: 1px;
  height: 9px;
  background: rgba(255, 255, 255, 0.22);
}

.calendar-graphic-row {
  position: absolute;
  left: 24px;
  right: 24px;
  height: 58px;
}

.calendar-graphic-band {
  position: absolute;
  height: 58px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 2px;
  padding: 0 14px 0 calc(14px + var(--clip-offset, 0px));
  border-radius: var(--radius-md);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: var(--wf-text-primary);
  overflow: visible;
  text-align: left;
  white-space: nowrap;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.08);
  transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease, filter 0.16s ease;
}

.calendar-graphic-band.is-era {
  background:
    linear-gradient(90deg, rgba(255, 255, 175, 0.24), rgba(255, 255, 175, 0.08)),
    linear-gradient(180deg, rgba(255, 255, 255, 0.08), transparent);
  border-color: rgba(255, 255, 175, 0.32);
}

.calendar-graphic-band.is-year {
  background:
    linear-gradient(90deg, rgba(59, 130, 246, 0.24), rgba(59, 130, 246, 0.08)),
    linear-gradient(180deg, rgba(255, 255, 255, 0.08), transparent);
  border-color: rgba(59, 130, 246, 0.32);
}

.calendar-graphic-band.is-open-ended {
  border-right-style: dashed;
}

.calendar-graphic-band.is-open-ended .calendar-band-duration {
  color: rgba(0, 212, 170, 0.9);
}

.calendar-graphic-band.is-low-confidence {
  background: linear-gradient(90deg, rgba(255, 165, 2, 0.20), rgba(255, 165, 2, 0.08));
  border-color: rgba(255, 165, 2, 0.34);
}

.calendar-graphic-band.is-connected-prev,
.calendar-graphic-band.is-clipped-start {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
  border-left-color: rgba(255, 255, 255, 0.22);
}

.calendar-graphic-band.is-connected-next,
.calendar-graphic-band.is-clipped-end {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
}

.calendar-graphic-band.is-connected-prev::before,
.calendar-graphic-band.is-clipped-start::before {
  content: '';
  position: absolute;
  left: -1px;
  top: 8px;
  bottom: 8px;
  width: 1px;
  background: rgba(255, 255, 255, 0.28);
}

.calendar-graphic-band.is-clipped-start::after,
.calendar-graphic-band.is-clipped-end::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  width: 18px;
  pointer-events: none;
  opacity: 0.72;
}

.calendar-graphic-band.is-clipped-start::after {
  left: 0;
  background: linear-gradient(90deg, rgba(17, 17, 19, 0.82), transparent);
}

.calendar-graphic-band.is-clipped-end::after {
  right: 0;
  background: linear-gradient(270deg, rgba(17, 17, 19, 0.82), transparent);
}

.calendar-graphic-band:hover,
.calendar-graphic-band.selected {
  transform: translateY(-2px);
  border-color: var(--wf-accent);
  box-shadow: var(--shadow-glow), 0 16px 28px rgba(0, 0, 0, 0.28);
  filter: saturate(1.08);
}

.calendar-band-title,
.calendar-band-range,
.calendar-band-duration {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.calendar-band-title {
  font-weight: 700;
  font-size: 0.9rem;
}

.calendar-band-range {
  color: var(--wf-text-muted);
  font-family: var(--font-mono);
  font-size: 0.68rem;
}

.calendar-band-duration {
  color: rgba(255, 255, 175, 0.82);
  font-family: var(--font-mono);
  font-size: 0.66rem;
  letter-spacing: 0.02em;
}

.calendar-band-hover-card {
  position: absolute;
  left: max(12px, min(50%, calc(100vw - 360px)));
  bottom: calc(100% + 10px);
  z-index: 120;
  min-width: 220px;
  max-width: min(340px, calc(100vw - 64px));
  transform: translate(-50%, 8px);
  opacity: 0;
  pointer-events: none;
  display: flex;
  flex-direction: column;
  gap: 5px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid rgba(255, 255, 175, 0.24);
  background: rgba(17, 17, 19, 0.96);
  color: var(--wf-text-primary);
  box-shadow: 0 18px 42px rgba(0, 0, 0, 0.48), var(--shadow-glow);
  backdrop-filter: blur(14px);
  transition: opacity 0.16s ease, transform 0.16s ease;
  white-space: normal;
}

.calendar-band-hover-card strong {
  color: var(--wf-accent);
  font-size: 0.92rem;
}

.calendar-band-hover-card small,
.calendar-band-hover-card em {
  color: var(--wf-text-secondary);
  font-size: 0.78rem;
  font-style: normal;
  line-height: 1.5;
}

.calendar-graphic-band:hover .calendar-band-hover-card,
.calendar-graphic-band:focus-visible .calendar-band-hover-card {
  opacity: 1;
  transform: translate(-50%, 0);
}

.calendar-graphic-band.is-clipped-start .calendar-band-hover-card {
  left: 12px;
  transform: translate(0, 8px);
}

.calendar-graphic-band.is-clipped-start:hover .calendar-band-hover-card,
.calendar-graphic-band.is-clipped-start:focus-visible .calendar-band-hover-card {
  transform: translate(0, 0);
}

.calendar-graphic-band.is-clipped-end .calendar-band-hover-card {
  left: auto;
  right: 12px;
  transform: translate(0, 8px);
}

.calendar-graphic-band.is-clipped-end:hover .calendar-band-hover-card,
.calendar-graphic-band.is-clipped-end:focus-visible .calendar-band-hover-card {
  transform: translate(0, 0);
}

.calendar-view-columns {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--spacing-lg);
}

.calendar-view-title {
  margin-bottom: var(--spacing-md);
  color: var(--wf-accent);
  font-weight: 700;
}

.calendar-line-card,
.diagnostic-row {
  width: 100%;
  margin-bottom: var(--spacing-sm);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.035);
  color: var(--wf-text-primary);
  text-align: left;
  white-space: normal;
}

.calendar-line-card {
  position: relative;
  flex-direction: column;
  align-items: flex-start;
  overflow: hidden;
}

.calendar-line-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(255, 255, 175, 0.75), rgba(59, 130, 246, 0.38));
  opacity: 0.7;
}

.diagnostics-header-card {
  display: flex;
  gap: var(--spacing-md);
  align-items: flex-start;
  padding: var(--spacing-md);
  border: 1px solid rgba(255, 165, 2, 0.22);
  border-radius: var(--radius-lg);
  background: rgba(255, 165, 2, 0.08);
  color: var(--wf-warning);
  margin-bottom: var(--spacing-md);
}

.diagnostics-header-card p {
  margin: 4px 0 0;
  color: var(--wf-text-secondary);
  line-height: 1.6;
}

.diagnostic-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.diagnostic-raw {
  max-width: 180px;
  color: var(--wf-text-muted);
  font-size: 0.78rem;
  overflow: hidden;
  text-overflow: ellipsis;
}

.timeline-empty-state,
.timeline-detail-empty {
  min-height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: var(--spacing-sm);
  color: var(--wf-text-muted);
}

.timeline-empty-state.compact { min-height: 180px; }
.timeline-empty-state svg,
.timeline-detail-empty svg { color: var(--wf-accent); opacity: 0.8; }

.info-list li {
  display: flex;
  align-items: center;
  gap: 7px;
}

.info-list li svg {
  flex: 0 0 auto;
  color: var(--wf-accent);
}

.timeline-detail-panel {
  position: sticky;
  top: var(--spacing-lg);
}

.timeline-detail-card h4 {
  margin: var(--spacing-md) 0 var(--spacing-sm);
  color: var(--wf-text-primary);
}

.detail-type-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: var(--radius-full);
  background: var(--wf-accent-muted);
  color: var(--wf-accent);
  border: 1px solid rgba(255, 255, 175, 0.16);
  font-size: 0.78rem;
  font-weight: 700;
}

.detail-description {
  color: var(--wf-text-secondary);
  line-height: 1.7;
}

.detail-meta-list {
  display: grid;
  grid-template-columns: 90px minmax(0, 1fr);
  gap: 8px 10px;
  margin: var(--spacing-lg) 0 0;
}

.detail-meta-list dt {
  color: var(--wf-text-muted);
  font-size: 0.8rem;
}

.detail-meta-list dd {
  margin: 0;
  color: var(--wf-text-secondary);
  word-break: break-word;
}

.detail-warning {
  margin-top: var(--spacing-md);
  display: flex;
  gap: 6px;
  align-items: flex-start;
  padding: var(--spacing-sm);
  border-radius: var(--radius-md);
  background: rgba(255, 165, 2, 0.08);
  color: var(--wf-warning);
}

@media (max-width: 1100px) {
  .timeline-hero-panel,
  .timeline-filter-row { flex-direction: column; align-items: stretch; }
  .timeline-overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .timeline-workspace-layout { grid-template-columns: 1fr; }
  .timeline-detail-panel { position: static; }
  .calendar-view-columns { grid-template-columns: 1fr; }
}

@media (max-width: 720px) {
  .timeline-overview-grid { grid-template-columns: 1fr; }
  .chronology-group { grid-template-columns: 1fr; gap: var(--spacing-sm); }
  .chronology-year-rail { position: static; }
  .chronology-card { grid-template-columns: 32px minmax(0, 1fr); }
  .chronology-confidence { grid-column: 2; justify-self: start; }
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
    min-width: 0;
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

.timeline-compressed-gap {
  position: absolute;
  top: -14px;
  transform: translateX(-50%);
  color: var(--wf-warning);
  font-family: var(--font-mono);
  font-size: 0.86rem;
  z-index: 3;
  pointer-events: none;
}

.timeline-compressed-gap span {
  display: block;
  margin-top: 18px;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.28);
  color: var(--wf-text-secondary);
  font-size: 0.66rem;
  white-space: nowrap;
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
  min-width: 0;
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

  .entity-card-grid.entity-card-grid-row-aligned {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .entity-layout-control {
    margin-left: 0;
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

  .entity-layout-control {
    width: 100%;
    justify-content: space-between;
  }

  .entity-card-grid.entity-card-grid-row-aligned {
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

.setting-detail-dialog .dialog-footer .delete-btn {
  margin-right: auto;
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
.entity-layout-control {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--wf-border-light);
  background: rgba(255, 255, 255, 0.04);
  color: var(--wf-text-secondary);
  white-space: nowrap;
}
.entity-layout-control-label {
  font-size: 0.75rem;
  font-weight: 500;
}
.entity-layout-toggle {
  flex-shrink: 0;
}
.entity-card-list, .event-card-list {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--spacing-sm);
}
.entity-card-grid {
  display: block;
  column-width: 360px;
  column-gap: var(--spacing-md);
}
.entity-card-grid.entity-card-grid-row-aligned {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  column-width: auto;
  column-gap: 0;
  gap: var(--spacing-md);
  align-items: stretch;
}
.entity-card-grid.entity-card-grid-row-aligned .entity-card {
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: none;
  min-width: 0;
  margin: 0;
  align-self: stretch;
  height: 100%;
}
.entity-card {
  content-visibility: auto;
  contain-intrinsic-size: auto 200px;
  display: inline-block;
  width: 100%;
  break-inside: avoid;
  page-break-inside: avoid;
  align-self: start;
  margin: 0 0 var(--spacing-md);
  background: var(--wf-bg-card);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  min-width: 0;
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
.entity-card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
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
.entity-delete-link {
  border: 1px solid rgba(239, 68, 68, 0.24);
  background: rgba(239, 68, 68, 0.08);
  color: #ef4444;
  font-size: 0.75rem;
  font-weight: 500;
  border-radius: var(--radius-full);
  padding: 4px 12px;
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
  flex-shrink: 0;
}
.entity-delete-link:hover {
  background: rgba(239, 68, 68, 0.16);
  border-color: rgba(239, 68, 68, 0.32);
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

.evolution-status-badge.is-created,
.evolution-status-badge.is-planning,
.evolution-status-badge.is-consolidating {
  background: rgba(250, 204, 21, 0.16);
  color: #fde68a;
}

.evolution-history-progress {
  height: 6px;
  overflow: hidden;
  border-radius: 999px;
  margin: 0 0 var(--spacing-md);
  background: rgba(148, 163, 184, 0.16);
}

.evolution-history-progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(59, 130, 246, 0.95), rgba(250, 204, 21, 0.95));
  transition: width 0.25s ease;
}

.setting-detail-workbench {
  width: min(1180px, calc(100vw - 32px));
  max-height: calc(100vh - 40px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid rgba(255, 255, 175, 0.16);
  background:
    radial-gradient(circle at 12% 0%, rgba(255, 255, 175, 0.12), transparent 30%),
    rgba(17, 17, 19, 0.97);
  box-shadow: 0 28px 72px rgba(0, 0, 0, 0.55), var(--shadow-glow);
}

.setting-detail-topbar {
  flex: 0 0 auto;
  border-bottom: 1px solid var(--wf-border);
  background: rgba(0, 0, 0, 0.18);
}

.detail-eyebrow {
  display: inline-flex;
  margin-bottom: 4px;
  color: var(--wf-accent);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  letter-spacing: 0.12em;
}

.setting-detail-editor {
  flex: 1 1 auto;
  min-height: 0;
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: var(--spacing-lg);
  overflow: hidden;
  padding: var(--spacing-lg);
}

.setting-detail-profile,
.setting-detail-main {
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.setting-detail-profile {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.setting-detail-main {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-content: start;
  gap: var(--spacing-md);
}

.detail-profile-card,
.detail-meta-grid,
.detail-alias-editor,
.linked-entity-panel,
.detail-editor-section {
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-xl);
  background: rgba(255, 255, 255, 0.035);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
}

.detail-profile-card {
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr);
  gap: var(--spacing-md);
  padding: var(--spacing-md);
}

.detail-avatar {
  width: 58px;
  height: 58px;
  border-radius: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--wf-accent-muted);
  color: var(--wf-accent);
  border: 1px solid rgba(255, 255, 175, 0.22);
  font-size: 1.6rem;
  font-weight: 700;
}

.detail-title-input,
.detail-description-input {
  width: 100%;
  border: 1px solid transparent;
  background: rgba(0, 0, 0, 0.16);
  color: var(--wf-text-primary);
  border-radius: var(--radius-sm);
  padding: 8px 10px;
  font-family: inherit;
}

.detail-title-input {
  font-size: 1.18rem;
  font-weight: 700;
  margin-bottom: 8px;
}

.detail-description-input {
  resize: vertical;
  min-height: 148px;
  line-height: 1.6;
  color: var(--wf-text-secondary);
}

.detail-title-input:focus,
.detail-description-input:focus {
  outline: none;
  border-color: var(--wf-accent);
  box-shadow: 0 0 0 3px var(--wf-accent-muted);
}

.detail-meta-grid {
  display: grid;
  gap: var(--spacing-sm);
  padding: var(--spacing-md);
}

.detail-meta-field {
  display: grid;
  gap: 6px;
  color: var(--wf-text-muted);
  font-size: 0.8rem;
}

.detail-meta-field span {
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.detail-panel-heading {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-sm);
}

.detail-panel-heading strong {
  color: var(--wf-text-primary);
  font-size: 0.95rem;
}

.detail-panel-heading span {
  color: var(--wf-accent);
  font-family: var(--font-mono);
  font-size: 0.74rem;
}

.detail-alias-editor,
.linked-entity-panel,
.detail-editor-section {
  padding: var(--spacing-md);
}

.editable-aliases {
  min-height: 34px;
}

.alias-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 8px;
  border-radius: var(--radius-full);
  border: 1px solid rgba(255, 255, 175, 0.14);
  background: rgba(255, 255, 175, 0.06);
  color: var(--wf-accent);
  font-size: 0.8rem;
}

.alias-chip button,
.icon-remove-btn {
  border: 0;
  background: rgba(255, 255, 255, 0.08);
  color: var(--wf-text-secondary);
  border-radius: 50%;
  cursor: pointer;
}

.alias-chip button {
  width: 18px;
  height: 18px;
  line-height: 16px;
}

.alias-input-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}

.empty-inline-hint,
.empty-structured-state {
  color: var(--wf-text-muted);
  font-size: 0.86rem;
}

.linked-entity-panel p {
  margin: 0 0 var(--spacing-sm);
  color: var(--wf-text-secondary);
}

.detail-editor-section.is-wide {
  grid-column: 1 / -1;
}

.setting-detail-workbench textarea,
.setting-detail-workbench .form-textarea,
.structured-intro-textarea,
.detail-textarea,
.structured-description-textarea {
  width: 100%;
  box-sizing: border-box;
  resize: vertical;
  line-height: 1.7;
}

.structured-intro-textarea {
  min-height: 220px;
}

.structured-description-textarea {
  min-height: 150px;
}

.detail-textarea {
  min-height: 300px;
}

.structured-field-list,
.structured-card-editor-list {
  display: grid;
  gap: var(--spacing-sm);
}

.structured-field-row {
  display: grid;
  grid-template-columns: minmax(120px, 0.45fr) minmax(0, 1fr) 30px;
  gap: var(--spacing-sm);
  align-items: center;
}

.structured-card-editor {
  display: grid;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: var(--radius-lg);
  background: rgba(0, 0, 0, 0.16);
}

.structured-card-editor-header,
.structured-card-editor-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(120px, 0.5fr) 30px;
  gap: var(--spacing-sm);
  align-items: center;
}

.structured-card-editor-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.icon-remove-btn {
  width: 30px;
  height: 30px;
  font-size: 1rem;
}

.icon-remove-btn:hover,
.alias-chip button:hover {
  background: rgba(255, 71, 87, 0.18);
  color: var(--wf-danger);
}

.inline-add-btn {
  border: 1px solid rgba(255, 255, 175, 0.16);
  border-radius: var(--radius-full);
  background: var(--wf-accent-muted);
  color: var(--wf-accent);
  padding: 5px 10px;
  cursor: pointer;
  font-size: 0.78rem;
}

.inline-add-btn:hover {
  border-color: rgba(255, 255, 175, 0.32);
  background: rgba(255, 255, 175, 0.12);
}

.compact-heading {
  margin: 2px 0 0;
}

.compact-field-list {
  padding-top: 2px;
}

.empty-structured-state {
  padding: var(--spacing-md);
  border: 1px dashed var(--wf-border);
  border-radius: var(--radius-md);
  background: rgba(0, 0, 0, 0.12);
  line-height: 1.6;
}

.setting-detail-hint {
  margin: 0 0 var(--spacing-sm);
  color: var(--wf-text-muted);
  font-size: 0.86rem;
  line-height: 1.6;
}

@media (max-width: 980px) {
  .template-candidate-bar,
  .single-template-panel {
    flex-direction: column;
  }

  .template-detail-link {
    align-self: flex-start;
    margin-top: 0;
  }

  .setting-detail-profile,
  .setting-detail-main {
    overflow: visible;
  }

  .setting-detail-main {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .setting-detail-workbench {
    width: calc(100vw - 16px);
  }

  .detail-profile-card,
  .structured-field-row,
  .structured-card-editor-header,
  .structured-card-editor-grid,
  .alias-input-row {
    grid-template-columns: 1fr;
  }
}

.extract-result-reminder,
.extract-preview { background: var(--wf-bg-card); border: 1px solid var(--wf-border); border-radius: var(--radius-md); padding: var(--spacing-lg); margin-top: var(--spacing-md); box-shadow: none; }
.extract-result-reminder {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  color: var(--wf-text-secondary);
}
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

.extract-result-dialog { width: min(860px, calc(100vw - 32px)); }
.extract-result-dialog .dialog-body { max-height: calc(100vh - 220px); overflow-y: auto; }
.dialog-subtitle { margin-top: 4px; color: var(--wf-text-muted); font-size: 0.9rem; }
.extract-result-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}
.extract-result-summary-grid > div {
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.04);
}
.extract-result-summary-grid span {
  display: block;
  color: var(--wf-text-muted);
  font-size: 0.8rem;
  margin-bottom: 4px;
}
.extract-result-summary-grid strong { color: var(--wf-text-primary); font-size: 1rem; }
.result-rag-badge { margin: 0 0 var(--spacing-md) 0; }
.result-preview-code { max-height: 360px; }
.extract-result-actions { display: flex; justify-content: flex-end; gap: var(--spacing-sm); }

.llm-config-dialog { width: 680px; }
.form-hint { font-size: 0.85rem; color: var(--wf-text-muted); }
.config-feedback { margin-top: var(--spacing-md); padding: var(--spacing-sm) var(--spacing-md); border-radius: var(--radius-sm); font-size: 0.9rem; }
.config-feedback.success { background: #ecfdf5; border: 1px solid #86efac; color: var(--wf-success); }
.config-feedback.error { background: rgba(255, 71, 87, 0.1); border: 1px solid #fca5a5; color: var(--wf-danger); }

.legacy-map-details {
  margin-top: var(--spacing-lg);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-lg);
  background: var(--wf-bg-card);
  color: var(--wf-text-primary);
  padding: var(--spacing-md);
}

.legacy-map-details summary {
  cursor: pointer;
  color: var(--wf-text-secondary);
  font-weight: 600;
}

.legacy-map-form {
  margin-top: var(--spacing-md);
}
</style>
