<template>
  <div class="agent-root">
    <!-- 最小化时的浮动按钮 -->
    <button
      v-if="minimized"
      class="agent-mini-btn"
      @click="minimized = false"
      :title="$t('agent.expand') || '展开 Agent'"
    >
      <div class="agent-mini-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M8 12h8M12 8v8"/>
        </svg>
      </div>
      <div class="agent-mini-pulse" v-if="hasUnread"></div>
    </button>

    <!-- 展开的悬浮窗 -->
    <div v-else class="agent-window" :class="{ 'agent-fullscreen': fullscreen }">
      <!-- 标题栏 -->
      <div class="agent-header">
        <div class="agent-header-left">
          <button class="agent-btn-icon" @click="minimized = true" :title="$t('agent.minimize') || '最小化'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
          </button>
          <span class="agent-title" v-if="!showSettings">WorldFish Agent</span>
          <span class="agent-title" v-else>Agent 配置</span>
        </div>
        <div class="agent-header-right">
          <!-- 世界观选择 -->
          <select
            v-model="currentWorldId"
            class="agent-world-select"
            @change="onWorldChange"
          >
            <option value="">{{ $t('全局模式') || '全局模式' }}</option>
            <option v-for="w in worldList" :key="w.id" :value="w.id">{{ w.name }}</option>
          </select>
          <!-- Session 切换 -->
          <button v-if="!showSettings" class="agent-btn-icon" @click="showSessions = !showSessions" :title="$t('agent.sessions') || '会话列表'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="18" height="18" rx="3"/>
              <line x1="9" y1="9" x2="15" y2="9"/>
              <line x1="9" y1="13" x2="15" y2="13"/>
              <line x1="9" y1="17" x2="12" y2="17"/>
            </svg>
          </button>
          <!-- 新建 Session -->
          <button v-if="!showSettings" class="agent-btn-icon" @click="createNewSession" :title="$t('agent.newSession') || '新建会话'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
          </button>
          <!-- 全屏 -->
          <button v-if="!showSettings" class="agent-btn-icon" @click="fullscreen = !fullscreen" :title="$t('agent.fullscreen') || '全屏'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15 3 21 3 21 9"/>
              <polyline points="9 21 3 21 3 15"/>
              <line x1="21" y1="3" x2="14" y2="10"/>
              <line x1="3" y1="21" x2="10" y2="14"/>
            </svg>
          </button>
          <!-- 设置 -->
          <button class="agent-btn-icon" :class="{ active: showSettings }" @click="toggleSettings" :title="$t('agent.settings') || '设置'">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="3"/>
              <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Session 面板 -->
      <div v-if="showSessions && !showSettings" class="agent-sessions-panel">
        <div class="agent-sessions-header">
          <span>{{ $t('agent.conversations') || '对话列表' }}</span>
          <button class="agent-btn-sm" @click="showSessions = false" title="关闭会话列表"><SvgIcon name="close" :size="13" /></button>
        </div>
        <div class="agent-sessions-list">
          <div
            v-for="s in sessionList"
            :key="s.session_id"
            class="agent-session-item"
            :class="{ active: s.session_id === currentSessionId }"
            @click="switchSession(s.session_id)"
          >
            <div class="agent-session-title">{{ s.title }}</div>
            <div class="agent-session-meta">
              <span>{{ s.message_count }} 条消息</span>
              <span class="agent-session-world" v-if="s.world_id"><SvgIcon name="globe" :size="13" /></span>
              <button
                class="agent-session-delete-btn"
                @click.stop="deleteSessionItem(s.session_id)"
                title="删除此会话"
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                </svg>
                删除
              </button>
            </div>
          </div>
          <div v-if="sessionList.length === 0" class="agent-empty">
            {{ $t('agent.noSessions') || '暂无对话' }}
          </div>
        </div>
      </div>

      <!-- Context / Token 状态 -->
      <div v-if="!showSettings" class="agent-context-strip">
        <div class="agent-context-line">
          <span class="agent-context-label">Context</span>
          <span class="agent-context-value">
            {{ formatTokens(contextMeterTokens) }}
            /
            {{ formatTokens(agentContextStats?.context_window || agentSettings.context_window || 0) }}
          </span>
        </div>
        <div class="agent-context-meter">
          <div
            class="agent-context-fill"
            :class="{ hot: contextRatio >= compressionThreshold }"
            :style="{ width: `${Math.min(contextRatio * 100, 100)}%` }"
          ></div>
          <div
            class="agent-context-threshold"
            :style="{ left: `${Math.min(compressionThreshold * 100, 100)}%` }"
          ></div>
        </div>
        <div class="agent-usage-chips">
          <span>Prompt {{ formatTokens(lastUsage.prompt_tokens || 0) }}</span>
          <span>Output {{ formatTokens(lastUsage.completion_tokens || 0) }}</span>
          <span>Reserve {{ formatTokens(agentContextStats?.reserved_tokens || 0) }}</span>
          <span>Cache {{ formatTokens(cacheHitTokens) }}</span>
          <span>Total {{ formatTokens(totalUsage.total_tokens || 0) }}</span>
        </div>
      </div>

      <!-- ============================================================ -->
      <!-- 设置面板 -->
      <!-- ============================================================ -->
      <div v-if="showSettings" class="agent-settings">
        <!-- Tab 导航 -->
        <div class="settings-tabs">
          <button
            v-for="tab in settingsTabs"
            :key="tab.id"
            class="settings-tab"
            :class="{ active: activeSettingsTab === tab.id }"
            @click="activeSettingsTab = tab.id"
          >{{ tab.label }}</button>
        </div>

        <div class="settings-content">
          <!-- ========== Runtime Tab ========== -->
          <div v-if="activeSettingsTab === 'runtime'" class="settings-section">
            <div class="agent-runtime-card">
              <div>
                <div class="agent-runtime-title">{{ agentSettings.model_name || '未配置模型' }}</div>
                <div class="agent-runtime-meta">
                  {{ agentSettings.model_profile || 'openai-compatible' }} · {{ formatTokens(agentSettings.context_window || 0) }} context
                </div>
              </div>
              <div class="agent-runtime-pill">{{ agentSettings.thinking_enabled ? 'Thinking On' : 'Thinking Off' }}</div>
            </div>

            <div class="settings-field settings-inline-field">
              <div>
                <label class="settings-label">思考模式</label>
                <p class="settings-hint">DeepSeek V4 默认开启，可手动关闭以降低延迟与输出消耗。</p>
              </div>
              <label class="agent-toggle">
                <input type="checkbox" v-model="agentSettingsForm.thinking_enabled" />
                <span></span>
              </label>
            </div>

            <div class="settings-field">
              <label class="settings-label">思考深度</label>
              <div class="agent-segmented">
                <button
                  type="button"
                  :class="{ active: agentSettingsForm.reasoning_effort === 'high' }"
                  @click="agentSettingsForm.reasoning_effort = 'high'"
                >High</button>
                <button
                  type="button"
                  :class="{ active: agentSettingsForm.reasoning_effort === 'max' }"
                  @click="agentSettingsForm.reasoning_effort = 'max'"
                >Max</button>
              </div>
            </div>

            <div class="settings-field">
              <label class="settings-label">上下文窗口</label>
              <input
                v-model.number="agentSettingsForm.context_window"
                class="settings-input"
                type="number"
                min="0"
                step="1024"
                placeholder="0 表示按模型默认"
              />
              <p class="settings-hint">DeepSeek V4 建议 1000000；填 0 则由模型 profile 自动决定。</p>
            </div>

            <div class="settings-field">
              <label class="settings-label">自动压缩阈值 {{ Math.round(agentSettingsForm.compression_threshold * 100) }}%</label>
              <input
                v-model.number="agentSettingsForm.compression_threshold"
                class="agent-range"
                type="range"
                min="0.5"
                max="0.95"
                step="0.01"
              />
              <p class="settings-hint">当已使用上下文 + 预留输出达到总上下文的该比例时，Agent 会先压缩旧对话再继续。</p>
            </div>

            <div class="settings-field settings-inline-field">
              <div>
                <label class="settings-label">工具调用默认折叠</label>
                <p class="settings-hint">工具调用与结果会保持紧凑，可点击每条记录展开参数和返回内容。</p>
              </div>
              <label class="agent-toggle">
                <input type="checkbox" v-model="agentDisplaySettings.collapseTools" @change="saveDisplaySettings" />
                <span></span>
              </label>
            </div>

            <div class="settings-actions">
              <button class="settings-btn settings-btn-save" :disabled="agentSettingsSaving" @click="saveRuntimeSettings">
                {{ agentSettingsSaving ? '保存中...' : '保存运行设置' }}
              </button>
              <button class="settings-btn settings-btn-reset" @click="loadRuntimeSettings">
                重载
              </button>
            </div>
          </div>

          <!-- ========== System Prompt Tab ========== -->
          <div v-if="activeSettingsTab === 'prompt'" class="settings-section">
            <div class="settings-field">
              <label class="settings-label">世界观</label>
              <select v-model="settingsWorldId" class="settings-select" @change="loadAgentMdForSettings">
                <option value="">全局</option>
                <option v-for="w in worldList" :key="w.id" :value="w.id">{{ w.name }}</option>
              </select>
            </div>
            <div class="settings-field">
              <label class="settings-label">System Prompt</label>
              <p class="settings-hint">
                自定义 Agent 的系统提示词。会加载在默认指令之前。支持 Markdown。
              </p>
              <textarea
                v-model="agentMdContent"
                class="settings-textarea"
                rows="12"
                placeholder="在此编写自定义指令，例如：&#10;&#10;# 角色&#10;你是一个专精于构建奇幻世界观的助手...&#10;&#10;# 规则&#10;1. 所有种族必须有详细的社会结构&#10;2. 魔法系统需要基于明确的规则"
              ></textarea>
            </div>
            <div class="settings-actions">
              <button class="settings-btn settings-btn-save" :disabled="agentMdSaving" @click="saveAgentMdContent">
                {{ agentMdSaving ? '保存中...' : '保存 System Prompt' }}
              </button>
              <button class="settings-btn settings-btn-reset" @click="loadAgentMdForSettings">
                重置
              </button>
            </div>
          </div>

          <!-- ========== MCP Tab ========== -->
          <div v-if="activeSettingsTab === 'mcp'" class="settings-section">
            <div class="settings-field">
              <label class="settings-label">MCP 服务器</label>
              <p class="settings-hint">
                配置 MCP (Model Context Protocol) 服务器，扩展 Agent 的能力。每个服务器需要一个 Stdio 命令或 HTTP 端点。
              </p>
            </div>
            <div class="mcp-list">
              <div v-for="(srv, idx) in mcpServers" :key="idx" class="mcp-item">
                <div class="mcp-item-header">
                  <span class="mcp-item-name">{{ srv.name || '未命名' }}</span>
                  <button class="agent-btn-xs" @click="removeMcpServer(idx)" title="删除"><SvgIcon name="trash" :size="13" /></button>
                </div>
                <div class="mcp-item-row">
                  <input v-model="srv.name" class="settings-input" placeholder="服务器名称" />
                </div>
                <div class="mcp-item-row">
                  <select v-model="srv.transport" class="settings-select settings-select-sm">
                    <option value="stdio">Stdio (命令行)</option>
                    <option value="http">HTTP (URL)</option>
                  </select>
                </div>
                <div class="mcp-item-row">
                  <input v-if="srv.transport === 'stdio'" v-model="srv.command" class="settings-input" placeholder="命令，如: npx -y @anthropic/mcp-server" />
                  <input v-else v-model="srv.url" class="settings-input" placeholder="HTTP URL，如: http://localhost:8080" />
                </div>
                <div class="mcp-item-row" v-if="srv.transport === 'stdio'">
                  <input v-model="srv.args" class="settings-input" placeholder="额外参数（可选）" />
                </div>
                <div class="mcp-item-row">
                  <input v-model="srv.env" class="settings-input" placeholder="环境变量（可选），如: KEY=value" />
                </div>
              </div>
              <div v-if="mcpServers.length === 0" class="agent-empty">
                暂无 MCP 服务器，点击下方按钮添加
              </div>
            </div>
            <div class="settings-actions">
              <button class="settings-btn settings-btn-add" @click="addMcpServer">
                + 添加 MCP 服务器
              </button>
              <button class="settings-btn settings-btn-save" @click="saveMcpConfig">
                保存 MCP 配置
              </button>
            </div>
          </div>

          <!-- ========== Skills Tab ========== -->
          <div v-if="activeSettingsTab === 'skills'" class="settings-section">
            <div class="settings-field">
              <label class="settings-label">Skills</label>
              <p class="settings-hint">
                Skill 是一组指令，Agent 在处理特定任务时会自动加载对应的 Skill。按世界观区分。
              </p>
            </div>
            <div class="skills-filter">
              <select v-model="skillFilterWorldId" class="settings-select settings-select-sm" @change="loadSkills">
                <option value="">全部 Skill</option>
                <option value="global">全局</option>
                <option v-for="w in worldList" :key="w.id" :value="w.id">{{ w.name }}</option>
              </select>
            </div>

            <!-- 已创建的 Skills -->
            <div class="skills-subtitle">已创建</div>
            <div class="skills-list">
              <div v-for="sk in filteredSkills" :key="sk.skill_id" class="skill-item">
                <div class="skill-item-header">
                  <span class="skill-item-name">{{ sk.name }}</span>
                  <span class="skill-item-world" v-if="sk.world_id"><SvgIcon name="globe" :size="13" /> {{ getWorldName(sk.world_id) }}</span>
                  <span class="skill-item-world" v-else><SvgIcon name="world" :size="13" /> 全局</span>
                  <button class="agent-btn-xs" @click="deleteSkillItem(sk.skill_id)" title="删除"><SvgIcon name="trash" :size="13" /></button>
                </div>
                <div class="skill-item-desc" v-if="sk.description">{{ sk.description }}</div>
                <div class="skill-item-inst" v-if="showSkillDetail === sk.skill_id">{{ sk.instructions }}</div>
                <button
                  v-if="sk.instructions"
                  class="skill-toggle-detail"
                  @click="showSkillDetail = showSkillDetail === sk.skill_id ? null : sk.skill_id"
                >{{ showSkillDetail === sk.skill_id ? '收起指令' : '查看指令' }}</button>
              </div>
              <div v-if="filteredSkills.length === 0" class="agent-empty">
                暂无自定义 Skill
              </div>
            </div>

            <!-- 发现的 Skills（来自本地文件夹） -->
            <div class="skills-subtitle">
              发现的 Skills
              <button class="skill-scan-btn" :disabled="discoveringLoading" @click="loadDiscoveredSkills">
                <template v-if="discoveringLoading">扫描中...</template>
                <template v-else><SvgIcon name="search" :size="13" /> 扫描</template>
              </button>
            </div>
            <div class="skills-list">
              <div v-for="ds in discoveredSkills" :key="ds.name" class="skill-item" :class="{ disabled: !ds.enabled }">
                <div class="skill-item-header">
                  <label class="skill-toggle">
                    <input
                      type="checkbox"
                      :checked="ds.enabled"
                      @change="toggleSkillEnabled(ds.name, !ds.enabled)"
                    />
                    <span class="skill-toggle-slider"></span>
                  </label>
                  <span class="skill-item-name" :class="{ muted: !ds.enabled }">{{ ds.name }}</span>
                  <span class="skill-item-source">{{ ds.source_dir }}</span>
                </div>
                <div class="skill-item-desc" v-if="ds.description">{{ ds.description }}</div>
                <div class="skill-item-inst" v-if="showSkillDetail === 'disc_' + ds.name">{{ ds.instructions }}</div>
                <button
                  v-if="ds.instructions"
                  class="skill-toggle-detail"
                  @click="showSkillDetail = showSkillDetail === 'disc_' + ds.name ? null : 'disc_' + ds.name"
                >{{ showSkillDetail === 'disc_' + ds.name ? '收起指令' : '查看指令' }}</button>
              </div>
              <div v-if="discoveredSkills.length === 0 && !discoveringLoading" class="agent-empty">
                未发现 Skill，点击扫描按钮搜索本地 .agents/.claude/.openclaw 目录
              </div>
            </div>

            <!-- 新增 Skill -->
            <div class="skill-add-form">
              <div class="skill-add-title">新增 Skill</div>
              <input v-model="newSkill.name" class="settings-input" placeholder="Skill 名称" />
              <input v-model="newSkill.description" class="settings-input" placeholder="描述（可选）" />
              <textarea v-model="newSkill.instructions" class="settings-textarea settings-textarea-sm" rows="4" placeholder="指令内容..."></textarea>
              <select v-model="newSkill.worldId" class="settings-select settings-select-sm">
                <option value="">全局</option>
                <option v-for="w in worldList" :key="w.id" :value="w.id">{{ w.name }}</option>
              </select>
              <button class="settings-btn settings-btn-add" @click="addSkill">+ 添加 Skill</button>
            </div>
          </div>
        </div>
      </div>

      <!-- ============================================================ -->
      <!-- 消息列表 -->
      <!-- ============================================================ -->
      <div v-if="!showSettings" class="agent-messages" ref="messagesEl">
        <div v-if="messages.length === 0 && !streaming" class="agent-welcome">
          <div class="agent-welcome-icon"><SvgIcon name="fish" :size="34" :stroke-width="1.7" /></div>
          <div class="agent-welcome-text">
            {{ $t('agent.welcome') || '你好！我是 WorldFish Agent，可以帮你管理世界观数据。\n\n你可以尝试：\n• 查看当前世界观概况\n• 添加/修改实体和事件\n• 批量导入设定\n• 让我提问以了解你的需求' }}
          </div>
          <div class="agent-welcome-hints">
            <button
              v-for="hint in quickHints"
              :key="hint"
              class="agent-hint-btn"
              @click="sendMessage(hint)"
            >{{ hint }}</button>
          </div>
        </div>

        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="agent-message"
          :class="'agent-msg-' + msg.role"
        >
          <!-- Tool Call 流式 Chunk — 可折叠 -->
          <div v-if="msg.type === 'tool_call'" class="agent-tool-call" :class="{ expanded: expandedTools.has(idx) }">
            <div class="agent-tool-call-header" @click="toggleToolExpand(idx)">
              <SvgIcon class="agent-tool-chevron" :name="expandedTools.has(idx) ? 'chevron-down' : 'chevron-right'" :size="13" />
              <span class="agent-tool-call-icon"><SvgIcon name="settings" :size="14" /></span>
              <span>{{ msg.content }}</span>
            </div>
            <div v-if="expandedTools.has(idx) && msg.data?.arguments" class="agent-tool-call-detail">
              <pre>{{ formatJson(msg.data.arguments) }}</pre>
            </div>
          </div>

          <!-- Tool Result 消息 — 可折叠 -->
          <div v-else-if="msg.role === 'tool'" class="agent-tool-msg" :class="{ expanded: expandedTools.has(idx) }">
            <div class="agent-tool-header" @click="toggleToolExpand(idx)">
              <SvgIcon class="agent-tool-chevron" :name="expandedTools.has(idx) ? 'chevron-down' : 'chevron-right'" :size="13" />
              <span class="agent-tool-icon"><SvgIcon name="tool" :size="14" /></span>
              <span class="agent-tool-name">{{ msg.name || 'Tool' }}</span>
              <span class="agent-tool-summary">{{ toolSummary(msg) }}</span>
            </div>
            <div v-if="expandedTools.has(idx)" class="agent-tool-content">{{ msg.content }}</div>
          </div>

          <!-- 系统状态消息 -->
          <div v-else-if="msg.role === 'system'" class="agent-system-msg">
            <span>{{ msg.content }}</span>
          </div>

          <!-- 选项 (User Prompt) -->
          <div v-else-if="msg.options" class="agent-options-msg">
            <div class="agent-options-content" v-html="renderMarkdown(msg.content)"></div>
            <div class="agent-options-box">
              <div class="agent-options-question">{{ msg.options.question }}</div>
              <div
                v-for="(opt, oi) in msg.options.options"
                :key="oi"
                class="agent-option-item"
                :class="{ selected: selectedOptions.includes(opt.label) }"
                @click="toggleOption(opt.label, msg.options.multiSelect, idx)"
              >
                <span class="agent-option-check">
                  <template v-if="msg.options.multiSelect">
                    <SvgIcon :name="selectedOptions.includes(opt.label) ? 'checkbox-on' : 'checkbox-off'" :size="16" />
                  </template>
                  <template v-else>
                    <SvgIcon :name="selectedOptions.includes(opt.label) ? 'radio-on' : 'radio-off'" :size="16" />
                  </template>
                </span>
                <div>
                  <div class="agent-option-label">{{ opt.label }}</div>
                  <div class="agent-option-desc" v-if="opt.description">{{ opt.description }}</div>
                </div>
              </div>
              <button
                class="agent-options-confirm"
                :disabled="selectedOptions.length === 0 || activeOptionsMsgIdx !== idx"
                @click="confirmOptions()"
              >
                {{ $t('agent.confirm') || '确认选择' }}
              </button>
            </div>
          </div>

          <!-- 普通消息 -->
          <div v-else class="agent-bubble">
            <div class="agent-bubble-content" v-html="renderMarkdown(msg.content)"></div>
            <div class="agent-bubble-time">{{ formatTime(msg.timestamp) }}</div>
          </div>
        </div>

        <!-- 流式输出中的文本 -->
        <div v-if="streaming" class="agent-message agent-msg-assistant">
          <div class="agent-bubble">
            <div class="agent-bubble-content" v-html="renderMarkdown(streamText)"></div>
            <div class="agent-typing-indicator">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 输入区 -->
      <div v-if="!showSettings" class="agent-input-area">
        <!-- 文件缩略 -->
        <div v-if="pendingFiles.length > 0" class="agent-pending-files">
          <div v-for="(f, fi) in pendingFiles" :key="fi" class="agent-pending-file">
            <span><SvgIcon name="paperclip" :size="14" /> {{ f.name }}</span>
            <button @click="removeFile(fi)" title="移除文件"><SvgIcon name="close" :size="12" /></button>
          </div>
        </div>
        <div class="agent-input-row">
          <!-- 文件上传 -->
          <label class="agent-upload-btn" :title="$t('agent.upload') || '上传文件'">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <input type="file" hidden multiple accept=".pdf,.md,.txt" @change="onFileChange" />
          </label>
          <textarea
            v-model="inputText"
            class="agent-input"
            :placeholder="$t('agent.placeholder') || '输入消息... (Shift+Enter 换行，Enter 发送)'"
            rows="1"
            @keydown="onKeyDown"
            ref="inputEl"
          ></textarea>
          <button
            class="agent-send-btn"
            :disabled="!inputText.trim() || streaming"
            @click="sendMessage()"
          >
            <svg v-if="!streaming" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"/>
              <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="agent-stop-icon" @click.stop="stopStreaming">
              <rect x="6" y="4" width="4" height="16" rx="1"/>
              <rect x="14" y="4" width="4" height="16" rx="1"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, reactive } from 'vue'
import {
  listSessions, createSession, getSession, deleteSession,
  chatStream, respondToOptions, uploadFile,
  getAgentSettings, saveAgentSettings,
  getAgentMd, saveAgentMd, listSkills, saveSkill, deleteSkill,
  discoverSkills, toggleDiscoveredSkill,
} from '../api/agent.js'
import { worldApi } from '../api/world.js'
import SvgIcon from './ui/SvgIcon.vue'

const WORLD_UPDATED_EVENT = 'worldfish:world-updated'
const WORLD_MUTATION_TOOLS = new Set([
  'add_entity',
  'update_entity',
  'delete_entity',
  'add_event',
  'update_event',
  'delete_event',
  'update_world_meta',
  'create_calendar',
  'update_calendar',
  'delete_calendar',
  'create_setting_collection',
  'create_setting_item',
  'update_map_cell',
  'batch_update_map_cells',
])

// ---- State ----
const minimized = ref(true)
const fullscreen = ref(false)
const showSessions = ref(false)
const showSettings = ref(false)
const streaming = ref(false)
const hasUnread = ref(false)

const currentSessionId = ref('')
const currentWorldId = ref('')
const sessionList = ref([])
const worldList = ref([])
const messages = ref([])
const inputText = ref('')
const streamText = ref('')
const pendingFiles = ref([])
const selectedOptions = ref([])
const activeOptionsMsgIdx = ref(-1)
const expandedTools = ref(new Set())
const agentContextStats = ref(null)
const agentUsage = ref({})
const lastUsage = computed(() => agentUsage.value.last || {})
const contextMeterTokens = computed(() => {
  const stats = agentContextStats.value || {}
  const actualPrompt = Number(stats.actual_prompt_tokens || 0)
  const estimatedTotal = Number(stats.estimated_total_tokens || 0)
  const estimatedContext = Number(stats.estimated_context_tokens || 0)
  const reserved = Number(stats.reserved_tokens || 0)
  return actualPrompt ? actualPrompt + reserved : (estimatedTotal || estimatedContext)
})
const contextRatio = computed(() => {
  const windowSize = Number(agentContextStats.value?.context_window || agentSettings.value.context_window || 0)
  if (!windowSize) return 0
  return contextMeterTokens.value / windowSize
})
const compressionThreshold = computed(() => agentContextStats.value?.compression_threshold || agentSettings.value.compression_threshold || 0.7)
const totalUsage = computed(() => agentUsage.value.total || {})
const cacheHitTokens = computed(() => {
  return Number(totalUsage.value.prompt_cache_hit_tokens || agentUsage.value.cache_hit_tokens || lastUsage.value.prompt_cache_hit_tokens || 0)
})

let abortController = null
const messagesEl = ref(null)
const inputEl = ref(null)

// ---- Quick Hints ----
const quickHints = [
  '帮我查看当前世界观概况',
  '添加一个新的人物实体',
  '列出所有事件',
]

// ---- Settings State ----
const settingsTabs = [
  { id: 'runtime', label: '运行' },
  { id: 'prompt', label: 'System Prompt' },
  { id: 'mcp', label: 'MCP' },
  { id: 'skills', label: 'Skills' },
]
const activeSettingsTab = ref('runtime')
const settingsWorldId = ref('')
const agentMdContent = ref('')
const agentMdSaving = ref(false)
const agentSettingsSaving = ref(false)
const agentSettings = ref({
  model_name: '',
  model_profile: 'openai-compatible',
  thinking_enabled: false,
  reasoning_effort: 'max',
  context_window: 0,
  context_window_override: 0,
  compression_threshold: 0.7,
})
const agentSettingsForm = reactive({
  thinking_enabled: false,
  reasoning_effort: 'max',
  context_window: 0,
  compression_threshold: 0.7,
})
const agentDisplaySettings = reactive({
  collapseTools: true,
})

// MCP
const mcpServers = ref([])

// Skills
const skillsList = ref([])
const skillFilterWorldId = ref('')
const discoveredSkills = ref([])
const discoveringLoading = ref(false)
const showSkillDetail = ref(null)
const newSkill = reactive({ name: '', description: '', instructions: '', worldId: '' })

// ---- Lifecycle ----
onMounted(async () => {
  loadDisplaySettings()
  await loadRuntimeSettings()
  await loadWorlds()
  await loadSessions()
})

// ---- Load Data ----
async function loadWorlds() {
  try {
    const res = await worldApi.listWorlds()
    worldList.value = res.worlds || []
  } catch (e) {
    console.warn('Failed to load worlds:', e)
  }
}

async function loadSessions() {
  try {
    const res = await listSessions(currentWorldId.value)
    sessionList.value = (res.sessions || []).slice(0, 20)
  } catch (e) {
    console.warn('Failed to load sessions:', e)
  }
}

// ---- Session Management ----
async function createNewSession() {
  try {
    const res = await createSession(currentWorldId.value)
    currentSessionId.value = res.session.session_id
    messages.value = []
    streamText.value = ''
    agentContextStats.value = res.session.context_stats || null
    agentUsage.value = res.session.usage || {}
    showSessions.value = false
    await loadSessions()
  } catch (e) {
    console.error('Failed to create session:', e)
  }
}

async function switchSession(sid) {
  if (sid === currentSessionId.value) return
  try {
    const res = await getSession(sid)
    currentSessionId.value = sid
    currentWorldId.value = res.session.world_id || ''
    messages.value = (res.session.messages || []).map(m => ({
      ...m,
      isHistory: true,
    }))
    agentContextStats.value = res.session.context_stats || null
    agentUsage.value = res.session.usage || {}
    streamText.value = ''
    showSessions.value = false
  } catch (e) {
    console.error('Failed to load session:', e)
  }
}

async function deleteSessionItem(sid) {
  await deleteSession(sid)
  if (sid === currentSessionId.value) {
    currentSessionId.value = ''
    messages.value = []
    agentContextStats.value = null
    agentUsage.value = {}
  }
  await loadSessions()
}

function onWorldChange() {
  // Switch to a new session for the new world context
}

function emitWorldUpdated(chunk) {
  const toolName = String(chunk?.data?.name || '').trim()
  if (!toolName || !chunk?.data?.success || !WORLD_MUTATION_TOOLS.has(toolName)) {
    return
  }

  const worldId = String(
    chunk?.data?.world_id
    || chunk?.data?.result?.world_id
    || currentWorldId.value
    || ''
  ).trim()
  if (!worldId) {
    return
  }

  window.dispatchEvent(new CustomEvent(WORLD_UPDATED_EVENT, {
    detail: {
      worldId,
      toolName,
      updatedAt: Date.now(),
    },
  }))
}

// ---- Chat ----
async function sendMessage(text) {
  const msg = text || inputText.value.trim()
  if (!msg || streaming.value) return

  // If no session, create one
  if (!currentSessionId.value) {
    await createNewSession()
  }

  const userMsg = { role: 'user', content: msg, timestamp: new Date().toISOString() }
  messages.value.push(userMsg)
  inputText.value = ''
  streamText.value = ''

  // Upload pending files first
  if (pendingFiles.value.length > 0) {
    try {
      await uploadFile(currentSessionId.value, pendingFiles.value, currentWorldId.value)
    } catch (e) {
      console.error('File upload failed:', e)
    }
    pendingFiles.value = []
  }

  // Start streaming
  streaming.value = true
  abortController = chatStream(
    currentSessionId.value,
    msg,
    currentWorldId.value,
    {
      onChunk: (chunk) => {
        if (chunk.type === 'context') {
          agentContextStats.value = chunk.data || agentContextStats.value
          if (chunk.content) {
            messages.value.push({
              role: 'system',
              content: chunk.content,
              timestamp: new Date().toISOString(),
            })
          }
        } else if (chunk.type === 'usage') {
          agentUsage.value = {
            ...(agentUsage.value || {}),
            ...(chunk.data || {}),
          }
          if (chunk.data?.context_stats) {
            agentContextStats.value = chunk.data.context_stats
          }
        } else if (chunk.type === 'text') {
          streamText.value += chunk.content
        } else if (chunk.type === 'tool_call') {
          const msgIndex = messages.value.length
          messages.value.push({
            role: 'tool',
            type: 'tool_call',
            content: chunk.content,
            name: chunk.data?.name,
            data: chunk.data,
          })
          applyToolCollapseDefault(msgIndex)
        } else if (chunk.type === 'tool_result') {
          const msgIndex = messages.value.length
          messages.value.push({
            role: 'tool',
            content: chunk.content,
            name: chunk.data?.name || 'Tool',
            data: chunk.data,
          })
          applyToolCollapseDefault(msgIndex)
          emitWorldUpdated(chunk)
        } else if (chunk.type === 'user_prompt') {
          // Agent 需要用户交互
          if (chunk.data) {
            messages.value.push({
              role: 'assistant',
              content: chunk.content,
              options: chunk.data,
            })
          }
          streaming.value = false
          streamText.value = ''
        } else if (chunk.type === 'done') {
          if (streamText.value) {
            messages.value.push({
              role: 'assistant',
              content: streamText.value,
              timestamp: new Date().toISOString(),
            })
            streamText.value = ''
          }
          streaming.value = false
          updateSessionTitle()
          loadSessions()
        }
      },
      onDone: () => {
        streaming.value = false
      },
      onError: (err) => {
        console.error('Chat error:', err)
        messages.value.push({
          role: 'assistant',
          content: `出错了: ${err.message}`, 
          timestamp: new Date().toISOString(),
        })
        streaming.value = false
      },
    }
  )
}

function stopStreaming() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
  if (streamText.value) {
    messages.value.push({
      role: 'assistant',
      content: streamText.value,
      timestamp: new Date().toISOString(),
    })
    streamText.value = ''
  }
  streaming.value = false
}

async function updateSessionTitle() {
  if (currentSessionId.value) {
    await loadSessions()
  }
}

// ---- Tool Expand/Collapse ----
function applyToolCollapseDefault(idx) {
  if (agentDisplaySettings.collapseTools) return
  const next = new Set(expandedTools.value)
  next.add(idx)
  expandedTools.value = next
}

function toggleToolExpand(idx) {
  const next = new Set(expandedTools.value)
  if (next.has(idx)) {
    next.delete(idx)
  } else {
    next.add(idx)
  }
  expandedTools.value = next
}

function toolSummary(msg) {
  const content = msg.content || ''
  const lines = content.split('\n')
  const firstLine = lines.find(l => l.trim()) || ''
  return firstLine.length > 60 ? firstLine.slice(0, 60) + '...' : firstLine
}

function formatJson(str) {
  try {
    const obj = typeof str === 'string' ? JSON.parse(str) : str
    return JSON.stringify(obj, null, 2)
  } catch {
    return str
  }
}

// ---- Options ----
function toggleOption(label, multiSelect, msgIdx) {
  activeOptionsMsgIdx.value = msgIdx
  if (multiSelect) {
    const idx = selectedOptions.value.indexOf(label)
    if (idx >= 0) {
      selectedOptions.value.splice(idx, 1)
    } else {
      selectedOptions.value.push(label)
    }
  } else {
    selectedOptions.value = [label]
  }
}

async function confirmOptions() {
  if (selectedOptions.value.length === 0) return
  const options = [...selectedOptions.value]
  selectedOptions.value = []
  activeOptionsMsgIdx.value = -1

  streaming.value = true
  abortController = respondToOptions(
    currentSessionId.value,
    options,
    currentWorldId.value,
    {
      onChunk: (chunk) => {
        if (chunk.type === 'context') {
          agentContextStats.value = chunk.data || agentContextStats.value
          if (chunk.content) {
            messages.value.push({
              role: 'system',
              content: chunk.content,
              timestamp: new Date().toISOString(),
            })
          }
        } else if (chunk.type === 'usage') {
          agentUsage.value = {
            ...(agentUsage.value || {}),
            ...(chunk.data || {}),
          }
          if (chunk.data?.context_stats) {
            agentContextStats.value = chunk.data.context_stats
          }
        } else if (chunk.type === 'text') {
          streamText.value += chunk.content
        } else if (chunk.type === 'tool_call') {
          const msgIndex = messages.value.length
          messages.value.push({
            role: 'tool', type: 'tool_call',
            content: chunk.content, name: chunk.data?.name, data: chunk.data,
          })
          applyToolCollapseDefault(msgIndex)
        } else if (chunk.type === 'tool_result') {
          const msgIndex = messages.value.length
          messages.value.push({
            role: 'tool',
            content: chunk.content, name: chunk.data?.name || 'Tool', data: chunk.data,
          })
          applyToolCollapseDefault(msgIndex)
          emitWorldUpdated(chunk)
        } else if (chunk.type === 'user_prompt') {
          if (chunk.data) {
            messages.value.push({
              role: 'assistant',
              content: chunk.content,
              options: chunk.data,
            })
          }
          streaming.value = false
          streamText.value = ''
        } else if (chunk.type === 'done') {
          if (streamText.value) {
            messages.value.push({
              role: 'assistant',
              content: streamText.value,
              timestamp: new Date().toISOString(),
            })
            streamText.value = ''
          }
          streaming.value = false
          updateSessionTitle()
          loadSessions()
        }
      },
      onDone: () => { streaming.value = false },
      onError: (err) => {
        console.error('Respond error:', err)
        streaming.value = false
      },
    }
  )
}

// ---- File ----
function onFileChange(e) {
  const files = Array.from(e.target.files || [])
  pendingFiles.value.push(...files)
  e.target.value = ''
}

function removeFile(idx) {
  pendingFiles.value.splice(idx, 1)
}

// ---- Input ----
function onKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

// ---- Settings ----
function toggleSettings() {
  showSettings.value = !showSettings.value
  showSessions.value = false
  if (showSettings.value) {
    settingsWorldId.value = currentWorldId.value
    loadRuntimeSettings()
    loadAgentMdForSettings()
    loadSkills()
    loadMcpConfig()
    loadDiscoveredSkills()
  }
}

// -- Runtime --
function assignAgentSettings(settings = {}) {
  agentSettings.value = {
    ...agentSettings.value,
    ...settings,
  }
  agentSettingsForm.thinking_enabled = Boolean(agentSettings.value.thinking_enabled)
  agentSettingsForm.reasoning_effort = agentSettings.value.reasoning_effort || 'max'
  agentSettingsForm.context_window = Number(agentSettings.value.context_window_override || 0)
  agentSettingsForm.compression_threshold = Number(agentSettings.value.compression_threshold || 0.7)
}

async function loadRuntimeSettings() {
  try {
    const res = await getAgentSettings()
    assignAgentSettings(res.settings || {})
  } catch (e) {
    console.warn('Failed to load Agent runtime settings:', e)
    try {
      const fallback = await worldApi.getLlmConfig()
      assignAgentSettings(fallback.config || {})
    } catch (fallbackError) {
      console.warn('Failed to load LLM config fallback:', fallbackError)
    }
  }
}

async function saveRuntimeSettings() {
  agentSettingsSaving.value = true
  try {
    const res = await saveAgentSettings({
      thinking_enabled: agentSettingsForm.thinking_enabled,
      reasoning_effort: agentSettingsForm.reasoning_effort,
      context_window: Number(agentSettingsForm.context_window || 0),
      compression_threshold: Number(agentSettingsForm.compression_threshold || 0.7),
    })
    assignAgentSettings(res.settings || {})
  } catch (e) {
    console.error('Failed to save Agent runtime settings:', e)
  } finally {
    agentSettingsSaving.value = false
  }
}

function loadDisplaySettings() {
  try {
    const stored = localStorage.getItem('worldfish_agent_display_settings')
    if (stored) {
      Object.assign(agentDisplaySettings, JSON.parse(stored))
    }
  } catch (e) {
    agentDisplaySettings.collapseTools = true
  }
}

function saveDisplaySettings() {
  try {
    localStorage.setItem('worldfish_agent_display_settings', JSON.stringify(agentDisplaySettings))
  } catch (e) {
    console.warn('Failed to save Agent display settings:', e)
  }
}

// -- System Prompt --
async function loadAgentMdForSettings() {
  try {
    const res = await getAgentMd(settingsWorldId.value)
    agentMdContent.value = res.content || ''
  } catch (e) {
    console.warn('Failed to load Agent.md:', e)
    agentMdContent.value = ''
  }
}

async function saveAgentMdContent() {
  agentMdSaving.value = true
  try {
    await saveAgentMd(agentMdContent.value, settingsWorldId.value)
  } catch (e) {
    console.error('Failed to save Agent.md:', e)
  } finally {
    agentMdSaving.value = false
  }
}

// -- MCP --
function loadMcpConfig() {
  try {
    const stored = localStorage.getItem('worldfish_mcp_servers')
    if (stored) {
      mcpServers.value = JSON.parse(stored)
    }
  } catch (e) {
    mcpServers.value = []
  }
}

function saveMcpConfig() {
  try {
    localStorage.setItem('worldfish_mcp_servers', JSON.stringify(mcpServers.value))
  } catch (e) {
    console.error('Failed to save MCP config:', e)
  }
}

function addMcpServer() {
  mcpServers.value.push({
    name: '',
    transport: 'stdio',
    command: '',
    args: '',
    url: '',
    env: '',
  })
}

function removeMcpServer(idx) {
  mcpServers.value.splice(idx, 1)
}

// -- Skills --
async function loadSkills() {
  try {
    const worldId = skillFilterWorldId.value === 'global' ? '' : skillFilterWorldId.value
    const res = await listSkills(worldId)
    skillsList.value = res.skills || []
  } catch (e) {
    console.warn('Failed to load skills:', e)
    skillsList.value = []
  }
}

const filteredSkills = computed(() => {
  if (!skillFilterWorldId.value) return skillsList.value
  if (skillFilterWorldId.value === 'global') return skillsList.value.filter(s => !s.world_id)
  return skillsList.value.filter(s => s.world_id === skillFilterWorldId.value)
})

function getWorldName(worldId) {
  const w = worldList.value.find(w => w.id === worldId)
  return w ? w.name : worldId
}

async function addSkill() {
  if (!newSkill.name.trim()) return
  try {
    await saveSkill({
      name: newSkill.name.trim(),
      description: newSkill.description.trim(),
      instructions: newSkill.instructions.trim(),
      world_id: newSkill.worldId || '',
    })
    newSkill.name = ''
    newSkill.description = ''
    newSkill.instructions = ''
    newSkill.worldId = ''
    await loadSkills()
  } catch (e) {
    console.error('Failed to add skill:', e)
  }
}

async function deleteSkillItem(skillId) {
  try {
    await deleteSkill(skillId, skillFilterWorldId.value === 'global' ? '' : skillFilterWorldId.value)
    await loadSkills()
  } catch (e) {
    console.error('Failed to delete skill:', e)
  }
}

// -- Discovered Skills --
async function loadDiscoveredSkills() {
  discoveringLoading.value = true
  try {
    const res = await discoverSkills()
    discoveredSkills.value = res.skills || []
  } catch (e) {
    console.error('Failed to discover skills:', e)
    discoveredSkills.value = []
  } finally {
    discoveringLoading.value = false
  }
}

async function toggleSkillEnabled(name, enabled) {
  try {
    await toggleDiscoveredSkill(name, enabled)
    // Update local state immediately for responsive UI
    const ds = discoveredSkills.value.find(s => s.name === name)
    if (ds) ds.enabled = enabled
  } catch (e) {
    console.error('Failed to toggle skill:', e)
  }
}

// ---- Helpers ----
function formatTokens(value) {
  const n = Number(value || 0)
  if (n >= 1000000) return `${(n / 1000000).toFixed(n >= 10000000 ? 0 : 1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}K`
  return `${Math.round(n)}`
}

function formatTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function renderMarkdown(text) {
  if (!text) return ''
  let html = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^### (.+)/gm, '<h4>$1</h4>')
    .replace(/^## (.+)/gm, '<h3>$1</h3>')
    .replace(/^# (.+)/gm, '<h2>$1</h2>')
    .replace(/^- (.+)/gm, '<li>$1</li>')
    .replace(/\n/g, '<br>')
  return html
}

// ---- Auto-scroll ----
watch([messages, streamText], () => {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}, { deep: true })

// ---- Minimized 时的未读提示 ----
watch(() => minimized.value, (val) => {
  if (!val) {
    hasUnread.value = false
  }
})
watch(messages, () => {
  if (minimized.value) {
    hasUnread.value = true
  }
}, { deep: true })

// ---- Expose for parent ----
defineExpose({
  open(worldId) {
    minimized.value = false
    if (worldId) {
      currentWorldId.value = worldId
    }
  },
  toggle() {
    minimized.value = !minimized.value
  },
})
</script>

<style scoped>
/* ============================================================
   Root — 固定于右下角的悬浮系统
   ============================================================ */
.agent-root {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 9999;
  font-family: var(--font-sans);
}

/* ---- 最小化按钮 ---- */
.agent-mini-btn {
  width: 50px;
  height: 50px;
  border-radius: 50%;
  background: var(--wf-accent);
  color: var(--wf-text-on-accent);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(255, 255, 175, 0.3);
  transition: all var(--transition-normal);
  position: relative;
}
.agent-mini-btn:hover {
  transform: scale(1.08);
  box-shadow: 0 6px 24px rgba(255, 255, 175, 0.45);
}
.agent-mini-icon { display: flex; align-items: center; justify-content: center; }
.agent-mini-pulse {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--wf-danger);
  animation: pulseGlow 2s infinite;
}

/* ---- 展开窗口 ---- */
.agent-window {
  width: 500px;
  height: 680px;
  background: rgba(17, 17, 19, 0.96);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.10);
  border-radius: var(--radius-xl);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.6), 0 0 0 1px rgba(255, 255, 255, 0.04);
  transition: all var(--transition-normal);
  animation: fadeInUp 0.3s ease;
}
.agent-fullscreen {
  position: fixed;
  top: 10px;
  right: 10px;
  bottom: 10px;
  width: 700px;
  height: auto;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ---- 标题栏 ---- */
.agent-header {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.02);
}
.agent-header-left,
.agent-header-right {
  display: flex;
  align-items: center;
  gap: 6px;
}
.agent-title {
  font-weight: 600;
  font-size: 16px;
  color: var(--wf-text-primary);
  margin-left: 4px;
}

.agent-btn-icon {
  width: 32px;
  height: 32px;
  background: none;
  border: none;
  color: var(--wf-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  padding: 0;
}
.agent-btn-icon:hover {
  color: var(--wf-text-primary);
  background: rgba(255, 255, 255, 0.08);
}
.agent-btn-icon.active {
  color: var(--wf-accent);
  background: var(--wf-accent-muted);
}

.agent-world-select {
  font-family: var(--font-sans);
  font-size: 14px;
  padding: 5px 10px;
  border-radius: var(--radius-sm);
  background: var(--wf-dropdown-bg);
  border: 1px solid var(--wf-dropdown-border);
  color: var(--wf-text-primary);
  color-scheme: dark;
  max-width: 140px;
  outline: none;
  cursor: pointer;
}
.agent-world-select option {
  background: var(--wf-dropdown-panel);
  color: var(--wf-text-primary);
  padding: 6px 8px;
}
.agent-world-select option:checked,
.agent-world-select option:hover,
.agent-world-select option:focus {
  background: var(--wf-dropdown-option-active);
}
.agent-world-select:focus {
  border-color: var(--wf-accent);
}

/* ---- Context / Token 状态 ---- */
.agent-context-strip {
  padding: 9px 14px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(255, 255, 255, 0.025);
  flex-shrink: 0;
}
.agent-context-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 12px;
  line-height: 1.2;
  margin-bottom: 7px;
}
.agent-context-label {
  color: var(--wf-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}
.agent-context-value {
  color: var(--wf-text-secondary);
  font-family: var(--font-mono);
}
.agent-context-meter {
  position: relative;
  height: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}
.agent-context-fill {
  height: 100%;
  min-width: 2px;
  border-radius: inherit;
  background: linear-gradient(90deg, rgba(255, 255, 175, 0.75), rgba(108, 220, 175, 0.75));
  transition: width var(--transition-normal), background var(--transition-fast);
}
.agent-context-fill.hot {
  background: linear-gradient(90deg, rgba(255, 184, 92, 0.9), rgba(255, 71, 87, 0.9));
}
.agent-context-threshold {
  position: absolute;
  top: -3px;
  width: 1px;
  height: 11px;
  background: rgba(255, 255, 255, 0.55);
}
.agent-usage-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 7px;
}
.agent-usage-chips span {
  padding: 2px 7px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.055);
  border: 1px solid rgba(255, 255, 255, 0.07);
  color: var(--wf-text-muted);
  font-size: 11px;
  font-family: var(--font-mono);
}

/* ---- Session 面板 ---- */
.agent-sessions-panel {
  position: absolute;
  top: 48px;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(17, 17, 19, 0.98);
  z-index: 10;
  display: flex;
  flex-direction: column;
  border-radius: 0 0 var(--radius-xl) var(--radius-xl);
}
.agent-sessions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 16px;
  font-weight: 600;
  color: var(--wf-text-primary);
}
.agent-btn-sm {
  width: 28px;
  height: 28px;
  background: none;
  border: none;
  color: var(--wf-text-muted);
  cursor: pointer;
  padding: 0;
}
.agent-sessions-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.agent-session-item {
  padding: 10px 12px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid transparent;
  margin-bottom: 4px;
}
.agent-session-item:hover {
  background: rgba(255, 255, 255, 0.04);
}
.agent-session-item.active {
  background: var(--wf-accent-muted);
  border-color: rgba(255, 255, 175, 0.2);
}
.agent-session-title {
  font-size: 16px;
  color: var(--wf-text-primary);
  font-weight: 500;
}
.agent-session-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--wf-text-muted);
  margin-top: 2px;
}
.agent-btn-xs {
  width: 26px;
  height: 26px;
  background: none;
  border: none;
  color: var(--wf-text-muted);
  cursor: pointer;
  opacity: 0.55;
  padding: 0;
}
.agent-btn-xs:hover { opacity: 1; }
.agent-session-delete-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: rgba(255, 71, 87, 0.08);
  border: 1px solid rgba(255, 71, 87, 0.15);
  color: var(--wf-danger);
  font-size: 11px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  margin-left: auto;
}
.agent-session-delete-btn:hover {
  background: rgba(255, 71, 87, 0.18);
  border-color: rgba(255, 71, 87, 0.35);
}
.agent-empty {
  text-align: center;
  color: var(--wf-text-muted);
  padding: 24px;
  font-size: 16px;
}

/* ---- 消息区 ---- */
.agent-messages {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.agent-messages::-webkit-scrollbar { width: 4px; }
.agent-messages::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }

/* 欢迎 */
.agent-welcome {
  text-align: center;
  padding: 28px 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.agent-welcome-icon {
  width: 58px;
  height: 58px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--wf-accent);
  background: var(--wf-accent-muted);
  border: 1px solid rgba(255, 255, 175, 0.16);
}
.agent-welcome-text {
  font-size: 16px;
  color: var(--wf-text-secondary);
  line-height: 1.8;
  white-space: pre-line;
}
.agent-welcome-hints {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
.agent-hint-btn {
  padding: 7px 14px;
  font-size: 15px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-full);
  color: var(--wf-text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.agent-hint-btn:hover {
  background: rgba(255, 255, 175, 0.1);
  border-color: rgba(255, 255, 175, 0.3);
  color: var(--wf-accent);
}

/* 消息气泡 */
.agent-msg-user .agent-bubble {
  background: var(--wf-accent-muted);
  border: 1px solid rgba(255, 255, 175, 0.15);
  border-radius: var(--radius-lg) var(--radius-lg) 4px var(--radius-lg);
  align-self: flex-end;
  margin-left: 40px;
}
.agent-msg-assistant .agent-bubble {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-lg) var(--radius-lg) var(--radius-lg) 4px;
  align-self: flex-start;
  margin-right: 40px;
}
.agent-bubble {
  padding: 12px 16px;
  font-size: 16px;
  line-height: 1.7;
  color: var(--wf-text-primary);
}
.agent-bubble-content :deep(h2) { font-size: 18px; margin: 8px 0 4px; }
.agent-bubble-content :deep(h3) { font-size: 17px; margin: 6px 0 3px; }
.agent-bubble-content :deep(h4) { font-size: 16px; margin: 4px 0 2px; }
.agent-bubble-content :deep(code) {
  background: rgba(255,255,255,0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 15px;
  font-family: var(--font-mono);
}
.agent-bubble-content :deep(li) { margin-left: 16px; }
.agent-bubble-time {
  font-size: 13px;
  color: var(--wf-text-muted);
  margin-top: 4px;
  text-align: right;
}

/* ---- Tool 消息 (可折叠) ---- */
.agent-tool-msg {
  padding: 0;
  margin: 0 16px;
  background: rgba(100, 100, 200, 0.06);
  border: 1px solid rgba(100, 100, 200, 0.12);
  border-radius: var(--radius-md);
  font-size: 15px;
  overflow: hidden;
  transition: all var(--transition-fast);
}
.agent-tool-msg:hover {
  border-color: rgba(100, 100, 200, 0.25);
}
.agent-tool-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  cursor: pointer;
  user-select: none;
  transition: background var(--transition-fast);
}
.agent-tool-header:hover {
  background: rgba(100, 100, 200, 0.08);
}
.agent-tool-chevron {
  font-size: 13px;
  color: var(--wf-text-muted);
  width: 14px;
  text-align: center;
  flex-shrink: 0;
  transition: transform var(--transition-fast);
}
.agent-tool-icon { font-size: 15px; }
.agent-tool-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--wf-text-secondary);
  flex-shrink: 0;
}
.agent-tool-summary {
  font-size: 13px;
  color: var(--wf-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  min-width: 0;
}
.agent-tool-content {
  color: var(--wf-text-secondary);
  white-space: pre-wrap;
  font-size: 14px;
  padding: 6px 10px 10px 28px;
  border-top: 1px solid rgba(100, 100, 200, 0.08);
  max-height: 220px;
  overflow-y: auto;
  line-height: 1.5;
}

/* Tool Call 流式 */
.agent-tool-call {
  padding: 0;
  margin: 0 16px;
  font-size: 14px;
  color: var(--wf-text-muted);
  border: 1px solid rgba(100, 100, 200, 0.10);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.agent-tool-call-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  cursor: pointer;
  user-select: none;
}
.agent-tool-call-header:hover {
  background: rgba(100, 100, 200, 0.06);
}
.agent-tool-call-icon,
.agent-tool-icon,
.agent-session-world,
.skill-item-world,
.agent-pending-file span {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.agent-tool-chevron {
  color: var(--wf-text-muted);
}
.agent-tool-call-detail {
  padding: 6px 10px 8px 28px;
  border-top: 1px solid rgba(100, 100, 200, 0.08);
}
.agent-tool-call-detail pre {
  font-family: var(--font-mono);
  font-size: 13px;
  color: var(--wf-text-secondary);
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  max-height: 160px;
  overflow-y: auto;
}
.agent-system-msg {
  align-self: center;
  max-width: calc(100% - 32px);
  padding: 5px 10px;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.055);
  border: 1px solid rgba(255, 255, 255, 0.07);
  color: var(--wf-text-muted);
  font-size: 12px;
}

/* ---- 选项 ---- */
.agent-options-msg {
  margin: 0 12px;
}
.agent-options-box {
  margin-top: 8px;
  padding: 14px;
  background: rgba(255, 255, 175, 0.05);
  border: 1px solid rgba(255, 255, 175, 0.15);
  border-radius: var(--radius-md);
}
.agent-options-question {
  font-size: 16px;
  font-weight: 600;
  color: var(--wf-text-primary);
  margin-bottom: 10px;
}
.agent-option-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
  border: 1px solid transparent;
  margin-bottom: 4px;
}
.agent-option-item:hover {
  background: rgba(255, 255, 255, 0.04);
}
.agent-option-item.selected {
  background: var(--wf-accent-muted);
  border-color: rgba(255, 255, 175, 0.3);
}
.agent-option-check {
  color: var(--wf-accent);
  margin-top: 1px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  flex: 0 0 18px;
}
.agent-option-label {
  font-size: 15px;
  font-weight: 500;
  color: var(--wf-text-primary);
}
.agent-option-desc {
  font-size: 14px;
  color: var(--wf-text-muted);
  margin-top: 2px;
}
.agent-options-confirm {
  margin-top: 10px;
  width: 100%;
  padding: 8px;
  background: var(--wf-accent);
  color: var(--wf-text-on-accent);
  border: none;
  border-radius: var(--radius-sm);
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-fast);
}
.agent-options-confirm:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.agent-options-confirm:hover:not(:disabled) {
  box-shadow: var(--shadow-glow);
}

/* ---- 输入区 ---- */
.agent-input-area {
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  padding: 12px 14px;
  flex-shrink: 0;
  background: rgba(0, 0, 0, 0.2);
}
.agent-pending-files {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.agent-pending-file {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  background: rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-sm);
  font-size: 14px;
  color: var(--wf-text-secondary);
}
.agent-pending-file button {
  width: 20px;
  height: 20px;
  background: none;
  border: none;
  color: var(--wf-text-muted);
  cursor: pointer;
  padding: 0;
}
.agent-input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.agent-upload-btn {
  width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--wf-text-muted);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  flex-shrink: 0;
}
.agent-upload-btn:hover {
  color: var(--wf-accent);
  background: rgba(255, 255, 255, 0.06);
}
.agent-input {
  flex: 1;
  background: var(--wf-bg-input);
  border: 1px solid var(--wf-border);
  border-radius: var(--radius-md);
  padding: 9px 14px;
  font-size: 16px;
  color: var(--wf-text-primary);
  font-family: var(--font-sans);
  resize: none;
  outline: none;
  min-height: 38px;
  max-height: 140px;
}
.agent-input:focus {
  border-color: var(--wf-accent);
  box-shadow: 0 0 0 2px var(--wf-accent-muted);
}
.agent-send-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--wf-accent);
  color: var(--wf-text-on-accent);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition-normal);
  padding: 0;
}
.agent-send-btn:hover:not(:disabled) {
  box-shadow: var(--shadow-glow-strong);
}
.agent-send-btn:disabled {
  background: rgba(255, 255, 255, 0.06);
  color: var(--wf-text-muted);
  cursor: not-allowed;
}
.agent-stop-icon { cursor: pointer; }

/* 打字动画 */
.agent-typing-indicator {
  display: flex;
  gap: 5px;
  margin-top: 8px;
}
.agent-typing-indicator span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--wf-accent);
  animation: typeBounce 1.2s infinite;
}
.agent-typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.agent-typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typeBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-6px); opacity: 1; }
}

/* ============================================================
   设置面板
   ============================================================ */
.agent-settings {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Tab 导航 */
.settings-tabs {
  display: flex;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  padding: 0 12px;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.01);
}
.settings-tab {
  padding: 10px 16px;
  font-size: 15px;
  font-weight: 500;
  color: var(--wf-text-muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all var(--transition-fast);
  border-radius: 0;
  margin-bottom: -1px;
}
.settings-tab:hover {
  color: var(--wf-text-secondary);
}
.settings-tab.active {
  color: var(--wf-accent);
  border-bottom-color: var(--wf-accent);
}

/* 内容区 */
.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}
.settings-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.agent-runtime-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.045);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.agent-runtime-title {
  font-size: 16px;
  color: var(--wf-text-primary);
  font-weight: 650;
}
.agent-runtime-meta {
  margin-top: 3px;
  color: var(--wf-text-muted);
  font-size: 13px;
  font-family: var(--font-mono);
}
.agent-runtime-pill {
  flex-shrink: 0;
  padding: 5px 10px;
  border-radius: var(--radius-full);
  color: var(--wf-accent);
  background: var(--wf-accent-muted);
  border: 1px solid rgba(255, 255, 175, 0.18);
  font-size: 12px;
  font-weight: 700;
}
.settings-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.settings-inline-field {
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
}
.settings-label {
  font-size: 15px;
  font-weight: 600;
  color: var(--wf-text-primary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.settings-hint {
  font-size: 14px;
  color: var(--wf-text-muted);
  line-height: 1.5;
}
.settings-textarea {
  font-family: var(--font-mono);
  font-size: 15px;
  line-height: 1.6;
  padding: 10px;
  border-radius: var(--radius-md);
  background: var(--wf-bg-input);
  border: 1px solid var(--wf-border);
  color: var(--wf-text-primary);
  resize: vertical;
  outline: none;
  min-height: 220px;
}
.settings-textarea-sm {
  min-height: 90px;
}
.settings-textarea:focus {
  border-color: var(--wf-accent);
  box-shadow: 0 0 0 2px var(--wf-accent-muted);
}
.settings-input {
  font-family: var(--font-mono);
  font-size: 15px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: var(--wf-bg-input);
  border: 1px solid var(--wf-border);
  color: var(--wf-text-primary);
  outline: none;
  width: 100%;
}
.settings-input:focus {
  border-color: var(--wf-accent);
}
.agent-toggle {
  position: relative;
  width: 46px;
  height: 26px;
  flex-shrink: 0;
  cursor: pointer;
}
.agent-toggle input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.agent-toggle span {
  position: absolute;
  inset: 0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.10);
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition: all var(--transition-fast);
}
.agent-toggle span::after {
  content: "";
  position: absolute;
  top: 3px;
  left: 3px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--wf-text-muted);
  transition: all var(--transition-fast);
}
.agent-toggle input:checked + span {
  background: var(--wf-accent-muted);
  border-color: rgba(255, 255, 175, 0.32);
}
.agent-toggle input:checked + span::after {
  transform: translateX(20px);
  background: var(--wf-accent);
}
.agent-segmented {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 4px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.08);
}
.agent-segmented button {
  height: 32px;
  border: none;
  border-radius: var(--radius-sm);
  color: var(--wf-text-muted);
  background: transparent;
  cursor: pointer;
  font-weight: 650;
  transition: all var(--transition-fast);
}
.agent-segmented button.active {
  color: var(--wf-text-on-accent);
  background: var(--wf-accent);
}
.agent-range {
  width: 100%;
  accent-color: var(--wf-accent);
}
.settings-select {
  font-family: var(--font-sans);
  font-size: 15px;
  padding: 8px 10px;
  border-radius: var(--radius-sm);
  background: var(--wf-dropdown-bg);
  border: 1px solid var(--wf-dropdown-border);
  color: var(--wf-text-primary);
  color-scheme: dark;
  outline: none;
  cursor: pointer;
}
.settings-select option {
  background: var(--wf-dropdown-panel);
  color: var(--wf-text-primary);
}
.settings-select option:checked,
.settings-select option:hover,
.settings-select option:focus {
  background: var(--wf-dropdown-option-active);
}
.settings-select-sm {
  font-size: 14px;
  padding: 5px 8px;
}
.settings-select:focus {
  border-color: var(--wf-accent);
}
.settings-actions {
  display: flex;
  gap: 8px;
  padding-top: 8px;
}
.settings-btn {
  padding: 8px 16px;
  font-size: 15px;
  font-weight: 600;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.settings-btn-save {
  background: var(--wf-accent);
  color: var(--wf-text-on-accent);
}
.settings-btn-save:hover:not(:disabled) {
  box-shadow: var(--shadow-glow);
}
.settings-btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.settings-btn-reset {
  background: rgba(255, 255, 255, 0.06);
  color: var(--wf-text-secondary);
}
.settings-btn-reset:hover {
  background: rgba(255, 255, 255, 0.1);
}
.settings-btn-add {
  background: rgba(255, 255, 255, 0.06);
  color: var(--wf-accent);
  border: 1px dashed rgba(255, 255, 175, 0.2);
}
.settings-btn-add:hover {
  background: var(--wf-accent-muted);
  border-color: var(--wf-accent);
}

/* MCP */
.mcp-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.mcp-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-md);
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.mcp-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.mcp-item-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--wf-text-primary);
}
.mcp-item-row {
  display: flex;
  gap: 6px;
}

/* Skills */
.skills-filter {
  margin-bottom: 4px;
}
.skills-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 260px;
  overflow-y: auto;
}
.skill-item {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: var(--radius-md);
  padding: 8px 10px;
}
.skill-item-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.skill-item-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--wf-text-primary);
}
.skill-item-world {
  font-size: 13px;
  color: var(--wf-text-muted);
  padding: 1px 5px;
  background: rgba(255, 255, 255, 0.04);
  border-radius: var(--radius-sm);
}
.skill-item-desc {
  font-size: 14px;
  color: var(--wf-text-secondary);
  margin-top: 4px;
}
.skill-item-inst {
  font-size: 14px;
  color: var(--wf-text-muted);
  font-family: var(--font-mono);
  background: rgba(0, 0, 0, 0.3);
  padding: 8px;
  border-radius: var(--radius-sm);
  margin-top: 6px;
  white-space: pre-wrap;
  line-height: 1.5;
}
.skill-toggle-detail {
  background: none;
  border: none;
  color: var(--wf-accent);
  font-size: 13px;
  cursor: pointer;
  padding: 2px 0;
  margin-top: 4px;
}
.skill-toggle-detail:hover {
  text-decoration: underline;
}
.skill-add-form {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.skill-add-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--wf-text-primary);
}

/* Skills subtitle */
.skills-subtitle {
  font-size: 14px;
  font-weight: 600;
  color: var(--wf-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-top: 10px;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.skill-scan-btn {
  font-size: 13px;
  font-weight: 500;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--wf-border);
  color: var(--wf-text-secondary);
  padding: 3px 8px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.skill-scan-btn:hover:not(:disabled) {
  background: rgba(255, 255, 175, 0.1);
  border-color: var(--wf-accent);
  color: var(--wf-accent);
}
.skill-scan-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Toggle switch */
.skill-toggle {
  position: relative;
  display: inline-block;
  width: 28px;
  height: 16px;
  flex-shrink: 0;
}
.skill-toggle input {
  opacity: 0;
  width: 0;
  height: 0;
  position: absolute;
}
.skill-toggle-slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  transition: all var(--transition-fast);
}
.skill-toggle-slider::before {
  content: "";
  position: absolute;
  height: 12px;
  width: 12px;
  left: 2px;
  bottom: 2px;
  background: #666;
  border-radius: 50%;
  transition: all var(--transition-fast);
}
.skill-toggle input:checked + .skill-toggle-slider {
  background: var(--wf-accent-muted);
}
.skill-toggle input:checked + .skill-toggle-slider::before {
  transform: translateX(12px);
  background: var(--wf-accent);
}

/* Skill source badge */
.skill-item-source {
  font-size: 12px;
  color: var(--wf-text-muted);
  padding: 1px 6px;
  background: rgba(100, 100, 200, 0.12);
  border-radius: var(--radius-sm);
  margin-left: auto;
}

/* Disabled skill */
.skill-item.disabled {
  opacity: 0.55;
  border-color: transparent;
}
.skill-item-name.muted {
  color: var(--wf-text-muted);
}

/* Responsive */
@media (max-width: 480px) {
  .agent-window {
    width: calc(100vw - 20px);
    height: 70vh;
    right: 10px;
    bottom: 10px;
  }
  .agent-fullscreen {
    width: 100vw;
    top: 0;
    right: 0;
    bottom: 0;
    border-radius: 0;
  }
}
</style>
