<template>
  <div class="plg-page">
    <!-- ── 顶部标题栏 ── -->
    <div class="plg-header">
      <div class="plg-header-left">
        <h2 class="plg-title">插件管理</h2>
        <span class="plg-subtitle">插件配置 · 安装</span>
      </div>
      <div class="plg-header-right">
        <button class="plg-btn plg-btn-outline" @click="loadPage" :disabled="loading || !agentOnline || !activeServerKey">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          刷新
        </button>
        <button class="plg-btn plg-btn-outline" @click="doReload" :disabled="!agentOnline || !activeServerKey || reloading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-.49-3.18"/>
          </svg>
          {{ reloading ? '重载中…' : '立即重载' }}
        </button>
      </div>
    </div>

    <!-- Agent 离线提示 -->
    <div v-if="!agentOnline" class="plg-offline">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span>Agent 未连接，无法管理插件。请先启动服务器。</span>
    </div>

    <template v-else>
      <!-- ── 标签页切换：配置 / 安装 ── -->
      <div class="plg-tabs">
        <button :class="['plg-tab', { active: tab === 'configs' }]" @click="tab = 'configs'">插件配置</button>
        <button :class="['plg-tab', { active: tab === 'local' }]" @click="switchToLocal">已安装</button>
        <button :class="['plg-tab', { active: tab === 'install' }]" @click="switchToInstall">安装插件</button>
      </div>

      <!-- ═══════════════ 插件配置 Tab ═══════════════ -->
      <div v-if="tab === 'configs'" class="plg-panel">
        <div v-if="configsLoading" class="plg-loading">
          <div class="plg-spinner"></div><span>正在扫描插件配置文件…</span>
        </div>
        <div v-else-if="configFiles.length === 0" class="plg-empty">
          <svg class="plg-empty-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/>
          </svg>
          <p>未找到插件配置文件（tshock/ 目录中的非系统 JSON 文件）</p>
          <button class="plg-btn plg-btn-primary" @click="loadConfigs">重新扫描</button>
        </div>
        <template v-else>
          <!-- 两栏：左侧文件列表，右侧编辑区 -->
          <div class="plg-cfg-layout">
            <!-- 左侧文件列表 -->
            <div class="plg-cfg-sidebar">
              <div class="plg-cfg-search">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <input v-model="configSearch" placeholder="搜索配置文件…" class="plg-cfg-search-input" />
              </div>
              <div class="plg-cfg-list">
                <div v-for="f in filteredConfigFiles" :key="f.full_path"
                  :class="['plg-cfg-item', { active: selectedConfig?.full_path === f.full_path }]"
                  @click="selectConfig(f)">
                  <div class="plg-cfg-item-name">{{ fileName(f.name) }}</div>
                  <div class="plg-cfg-item-meta">
                    <span v-if="isLibraryConfigFile(f)" class="plg-lib-badge">插件库</span>
                    <span class="plg-cfg-item-size">{{ formatSize(f.size) }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- 右侧编辑区 -->
            <div class="plg-cfg-main">
              <div v-if="!selectedConfig" class="plg-cfg-placeholder">
                <svg class="plg-empty-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
                  <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
                </svg>
                <p>从左侧选择一个插件配置文件</p>
              </div>
              <template v-else>
                <!-- 标题栏 -->
                <div class="plg-cfg-editor-header">
                  <div class="plg-cfg-editor-title">
                    <span class="plg-cfg-file-name">{{ fileName(selectedConfig.name) }}</span>
                    <span v-if="isLibraryConfigFile(selectedConfig)" class="plg-lib-badge">TShockPlugin 插件库</span>
                    <span v-if="cfgModified" class="plg-modified-badge">● 未保存</span>
                  </div>
                  <div class="plg-cfg-editor-actions">
                    <div class="plg-mode-toggle">
                      <button :class="['plg-mode-btn', { active: editorMode === 'ui' }]" @click="editorMode = 'ui'">UI 模式</button>
                      <button :class="['plg-mode-btn', { active: editorMode === 'json' }]" @click="editorMode = 'json'">JSON 模式</button>
                    </div>
                    <button class="plg-btn plg-btn-outline plg-btn-sm" @click="reloadCfg">
                      重新读取
                    </button>
                    <button class="plg-btn plg-btn-primary plg-btn-sm" @click="saveCfg"
                      :disabled="!cfgModified || cfgSaving">
                      {{ cfgSaving ? '保存中…' : '保存' }}
                    </button>
                  </div>
                </div>

                <!-- 读取中 -->
                <div v-if="cfgLoading" class="plg-loading" style="margin:24px">
                  <div class="plg-spinner"></div><span>读取文件中…</span>
                </div>
                <div v-else-if="cfgError" class="plg-error">{{ cfgError }}</div>

                <!-- 正文：编辑器（中）+ 文档面板（右，仅插件库） -->
                <div v-else class="plg-content-row">
                  <!-- 编辑器区域 -->
                  <div class="plg-editor-wrap">
                    <div v-if="cfgSaveResult" :class="['plg-toast', cfgSaveResult.ok ? 'plg-toast-ok' : 'plg-toast-err']">
                      {{ cfgSaveResult.msg }}
                      <button class="plg-toast-close" @click="cfgSaveResult = null">✕</button>
                    </div>
                    <!-- UI 模式 -->
                    <div v-if="editorMode === 'ui' && cfgParsed !== null" class="plg-ui-editor">
                      <PluginJsonEditor :key="selectedConfig.full_path" :data="cfgParsed" @change="onUiChange" />
                    </div>
                    <div v-else-if="editorMode === 'ui'" class="plg-parse-err">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;flex-shrink:0"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                      无法解析 JSON，请切换到 JSON 模式修复后重试。
                    </div>
                    <!-- JSON 模式 -->
                    <textarea v-else
                      ref="cfgJsonTextarea"
                      class="plg-json-editor"
                      v-model="cfgText"
                      @input="onCfgInput"
                      spellcheck="false"
                      placeholder="{}"
                    ></textarea>
                    <div v-if="editorMode === 'json' && cfgJsonError" class="plg-json-err">
                      <div class="plg-json-err-title">JSON 语法错误</div>
                      <div v-if="cfgJsonErrorPos" class="plg-json-err-meta">
                        第 {{ cfgJsonErrorPos.line }} 行，第 {{ cfgJsonErrorPos.col }} 列（position {{ cfgJsonErrorPos.idx }}）
                        <button class="plg-json-err-jump" @click="jumpToJsonError">定位到错误</button>
                      </div>
                      <div v-if="cfgJsonErrorPos" class="plg-json-err-loc">
                        <div class="plg-json-err-line">{{ getJsonErrorLine(cfgText, cfgJsonErrorPos) }}</div>
                        <div class="plg-json-err-caret" :style="{ paddingLeft: `${Math.max(0, (cfgJsonErrorPos.col || 1) - 1)}ch` }">^</div>
                      </div>
                      <div class="plg-json-err-msg">{{ cfgJsonErrorRaw || cfgJsonError }}</div>
                    </div>
                  </div>
                  <!-- 文档面板（右侧，库插件或有本地 md） -->
                  <div v-if="isLibraryConfigFile(selectedConfig) || selectedConfig.md_path" class="plg-doc-panel">
                    <div class="plg-doc-header">
                      <span class="plg-doc-header-title">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                          <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                        </svg>
                        插件说明
                      </span>
                      <a v-if="isLibraryConfigFile(selectedConfig)" :href="pluginDocUrl(selectedConfig.assembly_name || selectedConfig.name)" target="_blank" class="plg-doc-link">在 GitHub 查看</a>
                    </div>
                    <div v-if="docLoading" class="plg-loading" style="margin:16px">
                      <div class="plg-spinner"></div><span>加载文档中…</span>
                    </div>
                    <div v-else-if="docContent" class="plg-doc-content" v-html="renderedDoc"></div>
                    <div v-else class="plg-doc-empty">暂无文档或加载失败</div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </template>
      </div>

      <!-- ═══════════════ 已安装插件 Tab ═══════════════ -->
      <div v-if="tab === 'local'" class="plg-panel">
        <!-- 搜索栏 -->
        <div class="plg-local-toolbar">
          <div class="plg-install-search-wrap" style="flex:1">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input v-model="localSearch" placeholder="搜索已安装插件…" class="plg-install-search" />
          </div>
          <button class="plg-btn plg-btn-outline plg-btn-sm" @click="checkUpdates"
            :disabled="updateCheckLoading || !agentOnline || !activeServerKey">
            <svg v-if="updateCheckLoading" viewBox="0 0 24 24" class="spinning" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.49-2.82"/></svg>
            {{ updateCheckLoading ? '检测中…' : '检查更新' }}
          </button>
          <button v-if="updateCheckResult?.updates?.length > 0" class="plg-btn plg-btn-primary plg-btn-sm"
            @click="updateAll" :disabled="updatingIdx !== null || !agentOnline">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:12px;height:12px"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.49-2.82"/></svg>
            一键更新 ({{ updateCheckResult.updates.length }})
          </button>
          <button class="plg-btn plg-btn-outline plg-btn-sm" @click="loadLocalList" :disabled="localLoading || !agentOnline">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px;height:13px">
              <polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
            </svg>
            刷新
          </button>
        </div>

        <!-- 更新检测结果 -->
        <div v-if="updateCheckResult" :class="['plg-local-result', updateCheckResult.ok ? 'ok' : 'err']">
          <svg v-if="updateCheckResult.ok" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0"><polyline points="20 6 9 17 4 12"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
          {{ updateCheckResult.msg }}
        </div>

        <!-- 操作结果提示 -->
        <div v-if="localResult" :class="['plg-local-result', localResult.ok ? 'ok' : 'err']">
          <svg v-if="localResult.ok" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0"><polyline points="20 6 9 17 4 12"/></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:14px;height:14px;flex-shrink:0"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
          {{ localResult.msg }}
        </div>

        <!-- 加载中 -->
        <div v-if="localLoading" class="plg-loading" style="margin:48px auto">
          <div class="plg-spinner"></div><span>正在获取已安装插件列表…</span>
        </div>

        <!-- 空状态 -->
        <div v-else-if="!localLoading && localPlugins.length === 0" class="plg-empty">
          <svg class="plg-empty-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
          </svg>
          <p>暂无已安装插件，或服务器未连接</p>
          <button class="plg-btn plg-btn-primary" @click="loadLocalList">重新加载</button>
        </div>

        <!-- 插件列表 -->
        <div v-else class="plg-local-list">
          <div v-for="plugin in filteredLocalPlugins" :key="plugin.assembly_name" class="plg-local-item">
            <!-- 插件信息 -->
            <div class="plg-local-item-info">
              <div class="plg-local-item-name">
                {{ plugin.name || plugin.assembly_name }}
                <span :class="['plg-local-badge', plugin.enabled ? 'ok' : 'off']">
                  {{ plugin.enabled ? '运行中' : '已禁用' }}
                </span>
                <span v-if="getUpdateInfo(plugin) && !plugin.blacklisted" class="plg-local-badge upd">
                  有更新 → {{ getUpdateInfo(plugin).cloud_version }}
                </span>
                <span v-if="plugin.blacklisted" class="plg-local-badge blk">跳过更新</span>
              </div>
              <div class="plg-local-item-meta">
                <template v-if="plugin.author">
                  <span class="plg-local-meta-label">作者</span>{{ plugin.author }}
                </template>
                <template v-if="plugin.author && plugin.version"><span class="plg-local-meta-sep">·</span></template>
                <template v-if="plugin.version">
                  <span class="plg-local-meta-label">版本</span>{{ plugin.version }}
                </template>
                <span v-if="plugin.assembly_name" class="plg-local-meta-sep">·</span>
                <span v-if="plugin.assembly_name" class="plg-local-meta-asm">{{ plugin.assembly_name }}</span>
              </div>
            </div>
            <!-- 操作按钮 -->
            <div class="plg-local-actions">
              <!-- 更新 -->
              <button v-if="getUpdateInfo(plugin) && !plugin.blacklisted"
                class="plg-action-btn upd"
                :disabled="updatingIdx !== null || !agentOnline"
                @click="updatePlugin(plugin)" title="更新到最新版">
                <svg v-if="updatingIdx === plugin.assembly_name || updatingIdx === '__all__'" viewBox="0 0 24 24" class="spinning" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 1 1-.49-2.82"/></svg>
                {{ (updatingIdx === plugin.assembly_name || updatingIdx === '__all__') ? '更新中…' : '更新' }}
              </button>
              <!-- 启用/禁用 -->
              <button class="plg-action-btn"
                :disabled="(plugin.enabled ? disablingIdx : enablingIdx) === plugin.assembly_name || !agentOnline"
                @click="toggleDisable(plugin)"
                :title="plugin.enabled ? '点击禁用（热卸载）' : '点击启用（热加载）'">
                <svg v-if="(plugin.enabled ? disablingIdx : enablingIdx) === plugin.assembly_name" viewBox="0 0 24 24" class="spinning" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
                <svg v-else-if="plugin.enabled" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px"><polyline points="5 12 10 17 20 7"/></svg>
                {{ (plugin.enabled ? disablingIdx : enablingIdx) === plugin.assembly_name ? '…' : (plugin.enabled ? '禁用' : '启用') }}
              </button>
              <!-- 跳过更新 -->
              <button :class="['plg-action-btn', plugin.blacklisted ? 'active' : '']"
                :disabled="blacklistingIdx === plugin.assembly_name || !agentOnline"
                @click="toggleBlacklist(plugin)"
                :title="plugin.blacklisted ? '取消跳过更新' : '更新时跳过此插件'">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px">
                  <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
                </svg>
                {{ plugin.blacklisted ? '取消跳过' : '跳过更新' }}
              </button>
              <!-- 卸载 -->
              <button class="plg-btn plg-btn-danger-sm"
                :disabled="uninstallingIdx === plugin.assembly_name || !agentOnline"
                @click="uninstallPlugin(plugin)">
                <svg v-if="uninstallingIdx === plugin.assembly_name" viewBox="0 0 24 24" class="spinning" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/></svg>
                {{ uninstallingIdx === plugin.assembly_name ? '卸载中…' : '卸载' }}
              </button>
              <!-- 文档 -->
              <button class="plg-action-btn doc"
                @click="openPluginDoc(plugin.assembly_name, plugin.name)"
                title="查看插件文档">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px">
                  <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                  <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
                </svg>
                文档
              </button>
              <!-- 修改配置 -->
              <button class="plg-action-btn cfg" @click="goToPluginConfig(plugin)" title="跳转到插件配置">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:11px;height:11px">
                  <circle cx="12" cy="12" r="3"/>
                  <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                </svg>
                修改配置
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════ 安装插件 Tab ═══════════════ -->
      <div v-if="tab === 'install'" class="plg-panel">
        <!-- 云端列表 -->
        <div v-if="cloudLoading" class="plg-loading">
            <div class="plg-spinner"></div><span>正在从云端拉取插件列表…</span>
          </div>
          <div v-else-if="cloudError" class="plg-error" style="margin:24px">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            <div>
              <strong>获取云端列表失败</strong>
              <p>{{ cloudError }}</p>
              <button class="plg-btn plg-btn-outline" style="margin-top:8px" @click="loadCloudList">重试</button>
            </div>
          </div>
          <template v-else-if="cloudPlugins.length > 0">
            <div class="plg-install-bar">
              <div class="plg-install-search-wrap">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                </svg>
                <input v-model="cloudSearch" placeholder="搜索插件名称或描述…" class="plg-install-search" />
              </div>
              <span class="plg-install-count">共 {{ filteredCloudPlugins.length }} 个</span>
            </div>
            <div v-if="installResult" :class="['plg-toast plg-toast-float', installResult.ok ? 'plg-toast-ok' : 'plg-toast-err']">
              {{ installResult.msg }}
              <button class="plg-toast-close" @click="installResult = null">✕</button>
            </div>
            <div class="plg-cloud-list">
              <div v-for="(plugin, idx) in filteredCloudPlugins" :key="plugin.AssemblyName" class="plg-cloud-item">
                <div class="plg-cloud-item-info">
                  <div class="plg-cloud-item-top">
                    <span class="plg-cloud-name">{{ plugin.Name }}</span>
                    <span class="plg-cloud-version">v{{ plugin.Version }}</span>
                    <span class="plg-cloud-author">by {{ plugin.Author }}</span>
                  </div>
                  <div class="plg-cloud-desc">{{ getDesc(plugin) }}</div>
                </div>
                <div class="plg-cloud-item-action">
                  <button class="plg-btn plg-btn-sm"
                    :class="installedAsmSet.has(plugin.AssemblyName.toLowerCase()) ? 'plg-btn-installed' : 'plg-btn-primary'"
                    :disabled="installingIdx === plugin.AssemblyName || installedAsmSet.has(plugin.AssemblyName.toLowerCase())"
                    @click="installPlugin(plugin)">
                    {{ installingIdx === plugin.AssemblyName ? '安装中…' : installedAsmSet.has(plugin.AssemblyName.toLowerCase()) ? '已安装' : '安装' }}
                  </button>
                  <button class="plg-btn plg-btn-sm plg-btn-outline"
                    @click="openPluginDoc(plugin.AssemblyName, plugin.Name)"
                    title="查看插件文档"
                    style="margin-left: 8px;">
                    文档
                  </button>
                </div>
              </div>
              <div v-if="filteredCloudPlugins.length === 0" class="plg-empty">
                <p>没有匹配"{{ cloudSearch }}"的插件</p>
              </div>
            </div>
          </template>
          <div v-else-if="!cloudLoading" class="plg-empty">
            <svg class="plg-empty-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
            </svg>
            <p>尚未加载云端插件列表</p>
            <button class="plg-btn plg-btn-primary" @click="loadCloudList">拉取列表</button>
          </div>
      </div>

      <!-- 插件文档弹窗（用于已安装/安装插件） -->
      <div v-if="showDocModal" class="plg-modal-overlay" @click.self="closeDocModal">
        <div class="plg-modal-box">
          <div class="plg-modal-header">
            <div class="plg-modal-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
                <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
              </svg>
              {{ docModalTitle }} 文档
            </div>
            <button class="plg-modal-close" @click="closeDocModal">✕</button>
          </div>
          <div class="plg-modal-body">
            <div v-if="docModalLoading" class="plg-loading" style="margin: 36px auto;">
              <div class="plg-spinner"></div><span>加载文档中…</span>
            </div>
            <div v-else-if="docModalContent" class="plg-doc-content" v-html="renderedModalDoc"></div>
            <div v-else class="plg-doc-empty">暂无文档或加载失败</div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, inject } from 'vue'
import PluginJsonEditor from '../components/config/PluginJsonEditor.vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// marked 配置
marked.setOptions({ breaks: true, gfm: true })

const props = defineProps({
  agentOnline: { type: Boolean, default: false },
})

const activeServerKey = inject('activeServerKey', ref(''))

// ── Tab ────────────────────────────────────────────────────────────────
const tab = ref('configs')

// ── 插件配置 Tab 状态 ──────────────────────────────────────────────────
const loading        = ref(false)
const configsLoading = ref(false)
const reloading      = ref(false)
const configFiles    = ref([])
const configSearch   = ref('')
const selectedConfig = ref(null)
const cfgLoading     = ref(false)
const cfgText        = ref('')
const cfgJsonTextarea = ref(null)
const cfgModified    = ref(false)
const cfgSaving      = ref(false)
const cfgError       = ref('')
const cfgJsonError   = ref('')
const cfgJsonErrorRaw = ref('')
const cfgJsonErrorPos = ref(null)
const cfgSaveResult  = ref(null)
const editorMode     = ref('ui')   // 'ui' | 'json'
const docLoading     = ref(false)
const docContent     = ref('')
const showDocModal   = ref(false)
const docModalTitle  = ref('')
const docModalLoading = ref(false)
const docModalContent = ref('')

// 界面模式使用的已解析 JSON（由 cfgText 派生）
const cfgParsed = computed(() => {
  try { return cfgText.value.trim() ? JSON.parse(cfgText.value) : null } catch { return null }
})

// ── 安装 Tab 状态 ───────────────────────────────────────────────────────
const cloudLoading   = ref(false)
const cloudError     = ref('')
const cloudPlugins   = ref([])
const cloudSearch    = ref('')
const installingIdx  = ref(null)
const installResult  = ref(null)
const apmInstalling  = ref(false)
const apmResult      = ref(null)
const apmInstalled   = ref(null)   // null=检测中，false=未安装，true=已安装

// ── 已安装 Tab 状态 ──────────────────────────────────────────────────────
const localPlugins    = ref([])
const localLoading    = ref(false)
const localSearch     = ref('')
const uninstallingIdx = ref(null)
const localResult     = ref(null)
const updateCheckLoading = ref(false)
const updateCheckResult  = ref(null)   // {ok, msg, updates: [{assembly_name, name, local_version, cloud_version}]}
const updatingIdx        = ref(null)   // 正在更新的程序集名，或 '__all__'
const enablingIdx        = ref(null)
const disablingIdx       = ref(null)
const blacklistingIdx    = ref(null)
const filteredLocalPlugins = computed(() => {
  const q = localSearch.value.trim().toLowerCase()
  if (!q) return localPlugins.value
  return localPlugins.value.filter(p =>
    p.assembly_name?.toLowerCase().includes(q) ||
    p.name?.toLowerCase().includes(q) ||
    p.author?.toLowerCase().includes(q)
  )
})

// 已安装插件的 assembly_name 集合（大小写不敏感）
const installedAsmSet = computed(() => {
  const s = new Set()
  for (const p of localPlugins.value) s.add(p.assembly_name.toLowerCase())
  return s
})

const cloudAsmSet = computed(() => {
  const s = new Set()
  for (const p of cloudPlugins.value) {
    const asm = (p?.AssemblyName || p?.assembly_name || '').toString().trim().toLowerCase()
    if (asm) s.add(asm)
  }
  return s
})

// ── TShockPlugin 插件库已知 AssemblyName 集（与 GitHub 仓库 subdir 名一致）
// 这份列表是静态维护的代表性列表；通过匹配配置文件名（不含 .json）来判断
const LIBRARY_NAMES = new Set([
  'AutoPluginManager','AutoBiomeControl','AutoClear','AutoFishing',
  'AutoTeam','BanNPC','BetterWhitelist','Buildbox','Catbomb',
  'CaiBot','CaiPacketDebug','CnpcSpawn','CSR','DamageRulePlus','DeathDrop',
  'DTwoAssist','EconomicsAPI','EconomicsShop','EconomicsTechnology',
  'EconomicsTeam','EconomicsTowns','EconomicsEnchants','EconomicsPunish',
  'ExperienceSystem','GeneralVariables','HistorySystem',
  'HouseRegion','Invincibility','ItemDecoration','JourneyUnlock',
  'LazyAPI','LifemaxExtra','Lagrange.Hsu.CaiBot','LiquidLimit',
  'MapTeleport','MiniGames','Misaka','MoePlugin',
  'OnlineAction','PermaBuff','PKhiteReg','PlayerHelperPlugin',
  'PluginManager','PvPer','RegionExtension','RegionView',
  'ResetCharacter','SelectiveStaff','ServerTools','SignInPlugin',
  'SmartRegion','SpanwRoaming','StatusTextManager','SwitchCommand',
  'TerrariaControl','TerrariaRulesPlugin','MoreCommand','NPC_Evolution',
  'ChatGPT_Terraria','RecipesBrowser','SurfaceControl','DeathTeam',
  'TeleportToken','TranslationHelper','TimeRate','WarpPlate','WorldModify',
  'Chireiden','ChinoChatPlugin'
])

// 去掉语言后缀（.zh-CN .en-US .es-ES 等）
function stripLangSuffix(base) {
  return base.replace(/\.[a-z]{2,3}(-[A-Za-z]{2,4})?$/i, '')
}

function isLibraryPlugin(name) {
  const base = name.replace(/\.json$/i, '')
  return LIBRARY_NAMES.has(base) || LIBRARY_NAMES.has(stripLangSuffix(base))
}

function isLibraryConfigFile(file) {
  if (!file) return false
  if (file.is_plugin_library) return true

  const asm = (file.assembly_name || '').toString()
  if (asm && (isLibraryPlugin(asm) || cloudAsmSet.value.has(asm.toLowerCase()))) return true

  const name = (file.name || '').toString()
  if (!name) return false

  const base = name.replace(/\.json$/i, '')
  const stripped = stripLangSuffix(base)
  if (cloudAsmSet.value.has(base.toLowerCase()) || cloudAsmSet.value.has(stripped.toLowerCase())) return true

  return isLibraryPlugin(name)
}

function pluginDocUrl(name) {
  const base = stripLangSuffix(name.replace(/\.json$/i, ''))
  return `https://github.com/UnrealMultiple/TShockPlugin/blob/master/src/${base}/README.md`
}

// ── 过滤 ──────────────────────────────────────────────────────────────
const filteredConfigFiles = computed(() => {
  const q = configSearch.value.trim().toLowerCase()
  if (!q) return configFiles.value
  return configFiles.value.filter(f => f.name.toLowerCase().includes(q))
})

const filteredCloudPlugins = computed(() => {
  const q = cloudSearch.value.trim().toLowerCase()
  if (!q) return cloudPlugins.value
  return cloudPlugins.value.filter(p =>
    p.Name?.toLowerCase().includes(q) ||
    p.AssemblyName?.toLowerCase().includes(q) ||
    getDesc(p).toLowerCase().includes(q)
  )
})

// ── 初始加载 ──────────────────────────────────────────────────────────
function loadPage() {
  loadConfigs()
  if (cloudPlugins.value.length === 0 && !cloudLoading.value) {
    loadCloudList()
  }
}

function doReload() {
  if (!activeServerKey.value) return
  reloading.value = true
  window.__tshockSend?.({
    type: 'reload_tshock',
    msg_id: `plg-reload-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function loadConfigs() {
  if (!activeServerKey.value) return
  configsLoading.value = true
  configFiles.value = []
  window.__tshockSend?.({
    type: 'plugin_list_configs',
    msg_id: `plg-list-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function switchToLocal() {
  tab.value = 'local'
  loadLocalList()
}

function loadLocalList() {
  if (!activeServerKey.value) return
  localLoading.value = true
  localPlugins.value = []
  window.__tshockSend?.({
    type: 'plugin_local_list',
    msg_id: `plg-local-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function checkUpdates() {
  if (!activeServerKey.value) return
  updateCheckLoading.value = true
  updateCheckResult.value = null
  window.__tshockSend?.({
    type: 'plugin_check_updates',
    msg_id: `plg-chkupd-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function updatePlugin(plugin) {
  updatingIdx.value = plugin.assembly_name
  window.__tshockSend?.({
    type: 'plugin_update',
    msg_id: `plg-update-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, assembly_name: plugin.assembly_name },
  })
}

function updateAll() {
  updatingIdx.value = '__all__'
  window.__tshockSend?.({
    type: 'plugin_update',
    msg_id: `plg-updateall-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function toggleDisable(plugin) {
  if (plugin.enabled) {
    disablingIdx.value = plugin.assembly_name
    window.__tshockSend?.({
      type: 'plugin_disable',
      msg_id: `plg-disable-${Date.now()}`,
      timestamp: Date.now(),
      payload: { agent_key: activeServerKey.value, assembly_name: plugin.assembly_name },
    })
  } else {
    enablingIdx.value = plugin.assembly_name
    window.__tshockSend?.({
      type: 'plugin_enable',
      msg_id: `plg-enable-${Date.now()}`,
      timestamp: Date.now(),
      payload: { agent_key: activeServerKey.value, assembly_name: plugin.assembly_name },
    })
  }
}

function toggleBlacklist(plugin) {
  blacklistingIdx.value = plugin.assembly_name
  const action = plugin.blacklisted ? 'remove' : 'add'
  window.__tshockSend?.({
    type: 'plugin_blacklist',
    msg_id: `plg-bl-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, action, assembly_name: plugin.assembly_name },
  })
}

function getUpdateInfo(plugin) {
  if (!updateCheckResult.value?.updates) return null
  return updateCheckResult.value.updates.find(u => u.assembly_name === plugin.assembly_name) || null
}

function uninstallPlugin(plugin) {
  uninstallingIdx.value = plugin.assembly_name
  localResult.value = null
  window.__tshockSend?.({
    type: 'plugin_uninstall',
    msg_id: `plg-uninst-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, assembly_name: plugin.assembly_name },
  })
}

function switchToInstall() {
  tab.value = 'install'
  if (cloudPlugins.value.length === 0 && !cloudLoading.value) {
    loadCloudList()
  }
}

function checkApmStatus() {
  if (!activeServerKey.value) return
  apmInstalled.value = null
  window.__tshockSend?.({
    type: 'plugin_check_apm',
    msg_id: `plg-checkapm-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function installApm() {
  if (!activeServerKey.value) return
  apmInstalling.value = true
  apmResult.value = null
  window.__tshockSend?.({
    type: 'plugin_install_apm',
    msg_id: `plg-installapm-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

function loadCloudList() {
  if (!activeServerKey.value) return
  cloudLoading.value = true
  cloudError.value = ''
  window.__tshockSend?.({
    type: 'plugin_cloud_list',
    msg_id: `plg-cloud-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
}

// ── 选中并读取配置文件 ──────────────────────────────────────────────────
function selectConfig(f) {
  if (selectedConfig.value?.full_path === f.full_path) return
  selectedConfig.value = f
  cfgModified.value = false
  editorMode.value = 'ui'
  cfgError.value = ''
  cfgJsonError.value = ''
  docContent.value = ''
  reloadCfg()
  if (f.md_path) {
    loadLocalDoc(f.md_path)
  } else if (isLibraryConfigFile(f)) {
    loadDoc(f.assembly_name || f.name)
  }
}

function reloadCfg() {
  if (!selectedConfig.value) return
  cfgLoading.value = true
  cfgError.value = ''
  window.__tshockSend?.({
    type: 'file_read',
    msg_id: `plg-read-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: selectedConfig.value.full_path },
  })
}

function saveCfg() {
  if (!cfgModified.value || !selectedConfig.value) return
  // 验证 JSON
  try { JSON.parse(cfgText.value) } catch (e) {
    setJsonErrorState(cfgText.value, e)
    jumpToJsonError()
    return
  }
  cfgSaving.value = true
  window.__tshockSend?.({
    type: 'file_write',
    msg_id: `plg-write-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: selectedConfig.value.full_path, content: cfgText.value },
  })
}

function onCfgInput() {
  cfgModified.value = true
  try {
    JSON.parse(cfgText.value)
    cfgJsonError.value = ''
    cfgJsonErrorRaw.value = ''
    cfgJsonErrorPos.value = null
  } catch (e) {
    setJsonErrorState(cfgText.value, e)
  }
}

function setJsonErrorState(text, err) {
  const pos = parseJsonErrorPos(text, err)
  const raw = String(err?.message || '未知错误')
  cfgJsonErrorPos.value = pos
  cfgJsonErrorRaw.value = raw
  cfgJsonError.value = formatJsonError(text, err)
}

function parseJsonErrorPos(text, err) {
  const msg = String(err?.message || '')
  const m = msg.match(/position\s+(\d+)/i)
  if (!m) return null

  const idx = Number(m[1])
  if (!Number.isFinite(idx) || idx < 0) return null

  const safeIdx = Math.min(idx, text.length)
  const head = text.slice(0, safeIdx)
  const lines = head.split('\n')
  const line = lines.length
  const col = lines[lines.length - 1].length + 1
  return { idx: safeIdx, line, col }
}

function formatJsonError(text, err) {
  const raw = String(err?.message || '未知错误')
  const pos = parseJsonErrorPos(text, err)
  if (!pos) return `JSON 格式错误: ${raw}`
  return `第 ${pos.line} 行，第 ${pos.col} 列（position ${pos.idx}）`
}

function focusJsonError(pos) {
  if (!pos || !cfgJsonTextarea.value) return
  const ta = cfgJsonTextarea.value
  ta.focus()
  ta.setSelectionRange(pos.idx, pos.idx)
}

function jumpToJsonError() {
  if (!cfgJsonErrorPos.value) return
  focusJsonError(cfgJsonErrorPos.value)
}

function getJsonErrorLine(text, pos) {
  if (!pos || !text) return ''
  const lineIdx = Math.max(0, (pos.line || 1) - 1)
  const lines = String(text).split('\n')
  return lines[lineIdx] ?? ''
}

function onUiChange(newObj) {
  cfgText.value = JSON.stringify(newObj, null, 2)
  cfgModified.value = true
  cfgJsonError.value = ''
}

// ── 插件库文档加载（浏览器并发竞速多镜像） ───────────────────────────────
const README_MIRRORS = [
  n => `https://cdn.jsdelivr.net/gh/UnrealMultiple/TShockPlugin@master/src/${n}/README.md`,
  n => `https://raw.gitmirror.com/UnrealMultiple/TShockPlugin/master/src/${n}/README.md`,
  n => `https://ghfast.top/https://raw.githubusercontent.com/UnrealMultiple/TShockPlugin/master/src/${n}/README.md`,
  n => `https://raw.githubusercontent.com/UnrealMultiple/TShockPlugin/master/src/${n}/README.md`,
]

async function loadDoc(name) {
  const baseName = stripLangSuffix(name.replace(/\.json$/i, ''))
  docLoading.value = true
  docContent.value = ''
  try {
    const text = await Promise.any(
      README_MIRRORS.map(fn => {
        const url = fn(baseName)
        return fetch(url, { signal: AbortSignal.timeout(12000) })
          .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.text() })
          .then(t => { if (!t.trim()) throw new Error('empty'); return t })
      })
    )
    docContent.value = text
  } catch {
    // 所有镜像均失败，保持 docContent 为空，前端显示"暂无文档"
  }
  docLoading.value = false
}

function normalizeDocName(name) {
  return stripLangSuffix((name || '').replace(/\.(json|dll)$/i, ''))
}

async function openPluginDoc(primaryName, fallbackName = '') {
  showDocModal.value = true
  docModalTitle.value = primaryName || fallbackName || '插件'
  docModalLoading.value = true
  docModalContent.value = ''

  const candidates = [
    normalizeDocName(primaryName),
    normalizeDocName(fallbackName),
  ].filter(Boolean)

  const uniqueCandidates = [...new Set(candidates)]
  try {
    for (const baseName of uniqueCandidates) {
      try {
        const text = await Promise.any(
          README_MIRRORS.map(fn => {
            const url = fn(baseName)
            return fetch(url, { signal: AbortSignal.timeout(12000) })
              .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.text() })
              .then(t => { if (!t.trim()) throw new Error('empty'); return t })
          })
        )
        docModalContent.value = text
        break
      } catch {
        // 继续尝试下一个候选地址
      }
    }
  } finally {
    docModalLoading.value = false
  }
}

function closeDocModal() {
  showDocModal.value = false
  docModalContent.value = ''
}

// 本地 MD 文档（通过 file_read 发给 Agent 读取）
let _docReadMsgId = null
function loadLocalDoc(mdPath) {
  docLoading.value = true
  docContent.value = ''
  const msgId = `plg-docread-${Date.now()}`
  _docReadMsgId = msgId
  window.__tshockSend?.({
    type: 'file_read',
    msg_id: msgId,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: mdPath },
  })
}

// ── Markdown 渲染 ────────────────────────────────────────────────────────
const renderedDoc = computed(() => {
  if (!docContent.value) return ''
  return DOMPurify.sanitize(marked.parse(docContent.value))
})

const renderedModalDoc = computed(() => {
  if (!docModalContent.value) return ''
  return DOMPurify.sanitize(marked.parse(docModalContent.value))
})

// ── 安装插件（直接通过 Agent 下载并热重载）──────────────────────────────────
function installPlugin(plugin) {
  installingIdx.value = plugin.AssemblyName
  installResult.value = null
  window.__tshockSend?.({
    type: 'plugin_install',
    msg_id: `plg-install-${Date.now()}`,
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, assembly_name: plugin.AssemblyName },
  })
}

// ── 已安装插件→跳转配置 Tab ───────────────────────────────────────
function goToPluginConfig(plugin) {
  const asmLower = (plugin.assembly_name || '').toLowerCase()
  // 如果配置列表尚未加载，先加载再导航
  if (configFiles.value.length === 0) {
    localResult.value = { ok: false, msg: '配置列表尚未加载，正在加载中，请稍候切换到「插件配置」 Tab 查看' }
    loadConfigs()
    setTimeout(() => { localResult.value = null }, 5000)
    return
  }
  const match = configFiles.value.find(f => {
    const base = f.name.replace(/\.json$/i, '')
    const stripped = stripLangSuffix(base)
    return stripped.toLowerCase() === asmLower || base.toLowerCase() === asmLower
  })
  if (match) {
    tab.value = 'configs'
    selectConfig(match)
  } else {
    localResult.value = { ok: false, msg: `${plugin.name || plugin.assembly_name} 没有对应的插件配置文件` }
    setTimeout(() => { localResult.value = null }, 4000)
  }
}

// ── 工具函数 ──────────────────────────────────────────────────────────
function fileName(name) {
  return name.replace(/\.json$/i, '')
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
}

function getDesc(plugin) {
  const desc = plugin.Description
  if (!desc) return ''
  if (typeof desc === 'string') return desc
  return desc['zh-CN'] || desc['en-US'] || Object.values(desc)[0] || ''
}

// ── WS 消息处理 ────────────────────────────────────────────────────────
function onWsMessage(e) {
  const pkt = e.detail
  const p   = pkt.payload || {}

  // 插件配置列表
  if (pkt.type === 'plugin_list_configs_resp') {
    configsLoading.value = false
    if (p.success) {
      configFiles.value = p.files || []
    }
    return
  }

  // 文件读取（共用 file_read_resp）
  if (pkt.type === 'file_read_resp') {
    // 本地 MD 文档读取（用 payload.ref_id 匹配请求 msg_id，因为响应的 msg_id 是新生成的 GUID）
    if (p.ref_id === _docReadMsgId) {
      _docReadMsgId = null
      docLoading.value = false
      if (p.success) docContent.value = p.content
      return
    }
    // 配置文件读取
    cfgLoading.value = false
    if (!selectedConfig.value) return
    if (p.success) {
      cfgText.value = p.content
      cfgModified.value = false
      cfgError.value = ''
      cfgJsonError.value = ''
      cfgJsonErrorRaw.value = ''
      cfgJsonErrorPos.value = null
    } else {
      cfgError.value = p.msg || '读取失败'
    }
    return
  }

  // 文件写入（共用 file_write_resp）
  if (pkt.type === 'file_write_resp') {
    cfgSaving.value = false
    if (p.success) {
      cfgModified.value = false
      cfgSaveResult.value = { ok: true, msg: '配置已保存' }
    } else {
      cfgSaveResult.value = { ok: false, msg: p.msg || '保存失败' }
    }
    setTimeout(() => { cfgSaveResult.value = null }, 4000)
    return
  }

  // 云端插件列表
  if (pkt.type === 'plugin_cloud_list_resp') {
    cloudLoading.value = false
    if (p.success) {
      // API 返回格式可能是数组或 { data: [...] }
      const raw = p.data
      cloudPlugins.value = Array.isArray(raw) ? raw : (raw?.data ?? [])
    } else {
      cloudError.value = p.msg || '获取云端列表失败'
    }
    return
  }

  // 插件安装回执
  if (pkt.type === 'plugin_install_resp') {
    installingIdx.value = null
    installResult.value = { ok: p.success, msg: p.msg || (p.success ? '安装成功' : '安装失败') }
    if (p.success) {
      // 安装成功后自动刷新已安装列表
      if (tab.value === 'local') loadLocalList()
    }
    setTimeout(() => { installResult.value = null }, 8000)
    return
  }

  // 插件卸载回执
  if (pkt.type === 'plugin_uninstall_resp') {
    uninstallingIdx.value = null
    if (p.success) {
      localPlugins.value = localPlugins.value.filter(pl => pl.assembly_name !== p.assembly_name)
    }
    localResult.value = { ok: p.success, msg: p.msg || (p.success ? '卸载成功' : '卸载失败') }
    setTimeout(() => { localResult.value = null }, 6000)
    return
  }

  // 已安装插件列表
  if (pkt.type === 'plugin_local_list_resp') {
    localLoading.value = false
    if (p.success) localPlugins.value = p.plugins || []
    return
  }

  // 检查更新结果
  if (pkt.type === 'plugin_check_updates_resp') {
    updateCheckLoading.value = false
    updateCheckResult.value = { ok: p.success, msg: p.msg || '', updates: p.updates || [] }
    return
  }

  // 更新回执
  if (pkt.type === 'plugin_update_resp') {
    updatingIdx.value = null
    localResult.value = { ok: p.success, msg: p.msg || (p.success ? '更新成功' : '更新失败') }
    if (p.success) loadLocalList()
    setTimeout(() => { localResult.value = null }, 8000)
    return
  }

  // 禁用回执
  if (pkt.type === 'plugin_disable_resp') {
    disablingIdx.value = null
    if (p.success) {
      const idx = localPlugins.value.findIndex(pl => pl.assembly_name === p.assembly_name)
      if (idx !== -1) localPlugins.value[idx] = { ...localPlugins.value[idx], enabled: false, initialized: false }
    }
    localResult.value = { ok: p.success, msg: p.msg || (p.success ? '已禁用' : '禁用失败') }
    setTimeout(() => { localResult.value = null }, 5000)
    return
  }

  // 启用回执
  if (pkt.type === 'plugin_enable_resp') {
    enablingIdx.value = null
    if (p.success) {
      const idx = localPlugins.value.findIndex(pl => pl.assembly_name === p.assembly_name)
      if (idx !== -1) localPlugins.value[idx] = { ...localPlugins.value[idx], enabled: true, initialized: true }
    }
    localResult.value = { ok: p.success, msg: p.msg || (p.success ? '已启用' : '启用失败') }
    setTimeout(() => { localResult.value = null }, 5000)
    return
  }

  // 黑名单操作回执
  if (pkt.type === 'plugin_blacklist_resp') {
    blacklistingIdx.value = null
    if (p.success && p.blacklist) {
      const bl = new Set(p.blacklist)
      localPlugins.value = localPlugins.value.map(pl => ({ ...pl, blacklisted: bl.has(pl.assembly_name) }))
    }
    return
  }

  // APM 状态检测结果
  if (pkt.type === 'plugin_check_apm_resp') {
    if (p.success) {
      apmInstalled.value = !!(p.installed || p.loaded)
      if (apmInstalled.value && cloudPlugins.value.length === 0 && !cloudLoading.value) {
        loadCloudList()
      }
    } else {
      apmInstalled.value = false
    }
    return
  }

  // APM 安装响应
  if (pkt.type === 'plugin_install_apm_resp') {
    apmInstalling.value = false
    const hotReloaded = p.hot_reloaded === true
    apmResult.value = {
      ok: p.success,
      msg: p.success
        ? (p.msg || (hotReloaded ? 'APM 热重载成功' : '已安装，重启服务器后生效'))
        : (p.msg || '安装失败'),
    }
    if (p.success && hotReloaded) {
      apmInstalled.value = true
      if (cloudPlugins.value.length === 0) loadCloudList()
    }
    return
  }

  // TShock 热重载响应
  if (pkt.type === 'reload_tshock_resp') {
    reloading.value = false
    cfgSaveResult.value = { ok: p.success ?? false, msg: p.msg || (p.success ? '重载成功' : '重载失败') }
    setTimeout(() => { cfgSaveResult.value = null }, 4000)
    return
  }
}

// ── 生命周期 ──────────────────────────────────────────────────────────
onMounted(() => {
  window.addEventListener('ws-message', onWsMessage)
  if (props.agentOnline && activeServerKey.value) loadPage()
})
onUnmounted(() => {
  window.removeEventListener('ws-message', onWsMessage)
})

watch([activeServerKey, () => props.agentOnline], ([key, online]) => {
  if (!key) return
  configFiles.value = []
  selectedConfig.value = null
  cfgText.value = ''
  cloudPlugins.value = []
  cloudError.value = ''
  apmInstalled.value = null
  localPlugins.value = []
  localResult.value = null
  updateCheckResult.value = null
  updatingIdx.value = null
  enablingIdx.value = null
  disablingIdx.value = null
  blacklistingIdx.value = null
  if (online) loadPage()
})
</script>

<style scoped>
/* ── 页面容器 ── */
.plg-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: #f8fafc;
}

/* ── 顶部标题栏 ── */
.plg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px 16px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}
.plg-header-left  { display: flex; align-items: center; gap: 10px; }
.plg-header-right { display: flex; align-items: center; gap: 8px; }
.plg-title        { margin: 0; font-size: 18px; font-weight: 700; color: #0f172a; }
.plg-subtitle {
  font-size: 12px; color: #64748b;
  background: #f1f5f9; border: 1px solid #e2e8f0;
  padding: 2px 8px; border-radius: 20px;
}

/* ── 按钮 ── */
.plg-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 500; cursor: pointer;
  border: none; transition: all .15s; white-space: nowrap;
}
.plg-btn svg { width: 14px; height: 14px; flex-shrink: 0; }
.plg-btn:disabled { opacity: .45; cursor: not-allowed; }
.plg-btn-primary { background: #3b82f6; color: #fff; }
.plg-btn-primary:hover:not(:disabled) { background: #2563eb; }
.plg-btn-installed { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.plg-btn-outline { background: #fff; color: #374151; border: 1px solid #d1d5db; }
.plg-btn-outline:hover:not(:disabled) { background: #f9fafb; border-color: #9ca3af; }
.plg-btn-sm { padding: 5px 12px; font-size: 12px; }

/* ── 离线提示 ── */
.plg-offline {
  display: flex; align-items: center; gap: 10px;
  margin: 24px; padding: 14px 18px;
  background: #fef3c7; border: 1px solid #fde68a; border-radius: 10px;
  color: #92400e; font-size: 14px;
}
.plg-offline svg { width: 18px; height: 18px; flex-shrink: 0; }

/* ── 标签页 ── */
.plg-tabs {
  display: flex;
  gap: 4px;
  padding: 12px 24px 0;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}
.plg-tab {
  padding: 8px 18px;
  font-size: 13px; font-weight: 500; cursor: pointer;
  background: none; border: none; border-bottom: 2px solid transparent;
  color: #64748b; transition: all .15s; border-radius: 6px 6px 0 0;
}
.plg-tab:hover { color: #3b82f6; background: #f8fafc; }
.plg-tab.active { color: #3b82f6; border-bottom-color: #3b82f6; background: #f0f7ff; }

/* ── 面板 ── */
.plg-panel {
  flex: 1; overflow: hidden; display: flex; flex-direction: column;
}

/* ── 加载/空/错误 ── */
.plg-loading {
  display: flex; align-items: center; gap: 10px;
  padding: 32px; color: #64748b; font-size: 14px;
}
.plg-spinner {
  width: 18px; height: 18px; border-radius: 50%;
  border: 2px solid #e2e8f0; border-top-color: #3b82f6;
  animation: spin .8s linear infinite; flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

.plg-empty {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; flex: 1; gap: 10px;
  color: #94a3b8; padding: 48px;
}
.plg-empty-icon { font-size: 40px; }
.plg-empty p    { margin: 0; font-size: 14px; }

.plg-error {
  display: flex; align-items: flex-start; gap: 10px;
  color: #dc2626; font-size: 13px; padding: 16px;
  background: #fef2f2; border-radius: 8px; margin: 16px;
}
.plg-error svg { width: 18px; height: 18px; flex-shrink: 0; margin-top: 1px; }

/* ── 配置 Tab 两栏布局 ── */
.plg-cfg-layout {
  flex: 1; display: flex; overflow: hidden;
}

.plg-cfg-sidebar {
  width: 220px; min-width: 180px; max-width: 260px;
  border-right: 1px solid #e2e8f0;
  background: #fff; display: flex; flex-direction: column;
  flex-shrink: 0;
}

.plg-cfg-search {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 12px; border-bottom: 1px solid #f1f5f9;
}
.plg-cfg-search svg { width: 14px; height: 14px; color: #94a3b8; flex-shrink: 0; }
.plg-cfg-search-input {
  flex: 1; border: none; outline: none; font-size: 12px; color: #374151;
}

.plg-cfg-list { flex: 1; overflow-y: auto; }

.plg-cfg-item {
  padding: 10px 12px; cursor: pointer;
  border-bottom: 1px solid #f8fafc;
  transition: background .1s;
}
.plg-cfg-item:hover { background: #f8fafc; }
.plg-cfg-item.active { background: #eff6ff; }

.plg-cfg-item-name {
  font-size: 13px; font-weight: 500; color: #1e293b;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.plg-cfg-item-meta {
  display: flex; align-items: center; gap: 6px; margin-top: 3px;
}
.plg-lib-badge {
  font-size: 10px; background: #e0f2fe; color: #0369a1;
  border: 1px solid #bae6fd; border-radius: 4px; padding: 0 5px; flex-shrink: 0;
}
.plg-cfg-item-size { font-size: 11px; color: #94a3b8; }

.plg-cfg-main {
  flex: 1; display: flex; flex-direction: column; overflow: hidden;
}
.plg-cfg-placeholder {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; flex: 1; gap: 10px;
  color: #94a3b8; padding: 48px;
}
.plg-cfg-placeholder .plg-empty-icon { font-size: 36px; }
.plg-cfg-placeholder p { font-size: 14px; margin: 0; }

.plg-cfg-editor-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-shrink: 0;
}
.plg-cfg-editor-title { display: flex; align-items: center; gap: 8px; }
.plg-cfg-file-name    { font-size: 14px; font-weight: 600; color: #0f172a; }
.plg-modified-badge {
  font-size: 11px; color: #d97706;
  background: #fef3c7; border: 1px solid #fde68a;
  padding: 1px 7px; border-radius: 20px;
  animation: pulse-dot 1.5s ease-in-out infinite;
}
@keyframes pulse-dot { 0%,100% { opacity:1; } 50% { opacity:.5; } }
.plg-cfg-editor-actions { display: flex; gap: 8px; }

/* 内容行：编辑器（中）+ 文档（右） */
.plg-content-row {
  flex: 1; display: flex; overflow: hidden;
}

.plg-doc-panel {
  width: 460px; min-width: 320px; max-width: 600px;
  border-left: 1px solid #e2e8f0;
  background: #fff; display: flex; flex-direction: column;
  flex-shrink: 0; overflow: hidden;
}
.plg-doc-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; font-size: 13px; font-weight: 600; color: #374151;
  border-bottom: 1px solid #e2e8f0; flex-shrink: 0;
}
.plg-doc-link { font-size: 12px; color: #3b82f6; text-decoration: none; }
.plg-doc-link:hover { text-decoration: underline; }
.plg-doc-content {
  flex: 1; overflow-y: auto; padding: 14px 16px;
  font-size: 13px; line-height: 1.7; color: #374151;
}
.plg-doc-empty {
  padding: 24px; text-align: center; color: #94a3b8; font-size: 13px;
}

/* Markdown 渲染样式（marked 输出的标准标签） */
:deep(.plg-doc-content h1) { font-size: 17px; font-weight: 700; color: #0f172a; margin: 18px 0 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 6px; }
:deep(.plg-doc-content h2) { font-size: 15px; font-weight: 700; color: #1e293b; margin: 16px 0 7px; border-bottom: 1px solid #f1f5f9; padding-bottom: 4px; }
:deep(.plg-doc-content h3) { font-size: 13.5px; font-weight: 600; color: #334155; margin: 12px 0 5px; }
:deep(.plg-doc-content h4) { font-size: 13px; font-weight: 600; color: #475569; margin: 10px 0 4px; }
:deep(.plg-doc-content p)  { margin: 6px 0; line-height: 1.75; }
:deep(.plg-doc-content ul),
:deep(.plg-doc-content ol) { margin: 6px 0 6px 18px; padding: 0; }
:deep(.plg-doc-content li) { margin: 3px 0; line-height: 1.65; }
:deep(.plg-doc-content a)  { color: #3b82f6; text-decoration: none; }
:deep(.plg-doc-content a:hover) { text-decoration: underline; }
:deep(.plg-doc-content strong) { font-weight: 600; color: #1e293b; }
:deep(.plg-doc-content em) { font-style: italic; color: #475569; }
:deep(.plg-doc-content blockquote) {
  border-left: 3px solid #cbd5e1; margin: 8px 0; padding: 4px 12px;
  color: #64748b; background: #f8fafc; border-radius: 0 4px 4px 0;
}
:deep(.plg-doc-content pre) {
  background: #1e293b; color: #e2e8f0; border-radius: 8px;
  padding: 12px 14px; font-size: 12px; overflow-x: auto;
  font-family: 'SFMono-Regular', Consolas, monospace;
  white-space: pre; margin: 8px 0; line-height: 1.6;
}
:deep(.plg-doc-content code) {
  background: #f1f5f9; color: #e11d48; border: 1px solid #e2e8f0;
  border-radius: 3px; padding: 1px 5px; font-size: 12px;
  font-family: 'SFMono-Regular', Consolas, monospace;
}
:deep(.plg-doc-content pre code) {
  background: none; color: inherit; border: none; padding: 0; font-size: inherit;
}
:deep(.plg-doc-content table) {
  border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 12.5px;
}
:deep(.plg-doc-content th) {
  background: #f1f5f9; font-weight: 600; color: #374151;
  border: 1px solid #e2e8f0; padding: 6px 10px; text-align: left;
}
:deep(.plg-doc-content td) {
  border: 1px solid #e2e8f0; padding: 5px 10px; color: #4b5563;
}
:deep(.plg-doc-content tr:nth-child(even) td) { background: #f8fafc; }
:deep(.plg-doc-content img) { max-width: 100%; border-radius: 6px; margin: 6px 0; }
:deep(.plg-doc-content hr) { border: none; border-top: 1px solid #e2e8f0; margin: 14px 0; }

/* 编辑器 */
/* 模式切换 */
.plg-mode-toggle {
  display: flex; border: 1px solid #e2e8f0; border-radius: 7px; overflow: hidden; flex-shrink: 0;
}
.plg-mode-btn {
  padding: 4px 13px; font-size: 12px; font-weight: 500;
  background: #fff; color: #64748b; border: none; cursor: pointer; transition: all .15s;
}
.plg-mode-btn + .plg-mode-btn { border-left: 1px solid #e2e8f0; }
.plg-mode-btn:hover { background: #f8fafc; color: #374151; }
.plg-mode-btn.active { background: #3b82f6; color: #fff; }
.plg-mode-btn.active:hover { background: #2563eb; }

.plg-editor-wrap {
  flex: 1; display: flex; flex-direction: column; overflow: hidden; position: relative;
}
.plg-ui-editor {
  flex: 1; overflow-y: auto; padding: 6px 4px;
}
.plg-parse-err {
  display: flex; align-items: center; gap: 8px;
  margin: 24px 16px; padding: 12px 16px;
  background: #fef3c7; border: 1px solid #fde68a; border-radius: 8px;
  color: #92400e; font-size: 13px;
}
.plg-json-editor {
  flex: 1; padding: 14px 16px; font-size: 13px; line-height: 1.6;
  font-family: 'SFMono-Regular', Consolas, monospace;
  border: none; outline: none; resize: none;
  background: #fafafa; color: #1e293b;
}
.plg-json-err {
  padding: 10px 14px;
  font-size: 12.5px;
  line-height: 1.5;
  color: #b91c1c;
  background: #fef2f2;
  border-top: 1px solid #fecaca;
  white-space: pre-wrap;
  flex-shrink: 0;
}
.plg-json-err-title {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 4px;
}
.plg-json-err-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
  color: #991b1b;
}
.plg-json-err-msg {
  color: #7f1d1d;
}
.plg-json-err-loc {
  font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace;
  background: #fff;
  border: 1px solid #fecaca;
  border-radius: 6px;
  padding: 6px 8px;
  margin-bottom: 6px;
  overflow-x: auto;
}
.plg-json-err-line {
  color: #111827;
  white-space: pre;
}
.plg-json-err-caret {
  color: #dc2626;
  font-weight: 700;
  line-height: 1;
  white-space: pre;
}
.plg-json-err-jump {
  border: 1px solid #f87171;
  background: #fff;
  color: #b91c1c;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 12px;
  cursor: pointer;
}
.plg-json-err-jump:hover {
  background: #fee2e2;
}

/* ── 安装 Tab ── */
.plg-install-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 16px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-shrink: 0;
}
.plg-install-search-wrap {
  display: flex; align-items: center; gap: 8px;
  border: 1px solid #e2e8f0; border-radius: 8px;
  padding: 7px 12px; background: #fff; flex: 1; max-width: 400px;
}
.plg-install-search-wrap svg { width: 14px; height: 14px; color: #94a3b8; flex-shrink: 0; }
.plg-install-search { flex: 1; border: none; outline: none; font-size: 13px; color: #374151; }
.plg-install-count  { font-size: 12px; color: #64748b; flex-shrink: 0; }

.plg-cloud-list {
  flex: 1; overflow-y: auto; padding: 8px 12px; display: flex; flex-direction: column; gap: 6px;
}
.plg-cloud-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px; background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
  transition: border-color .15s, box-shadow .15s;
}
.plg-cloud-item:hover { border-color: #bfdbfe; box-shadow: 0 1px 3px rgba(59,130,246,.08); }
.plg-cloud-item-info { flex: 1; min-width: 0; }
.plg-cloud-item-top  { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.plg-cloud-name      { font-size: 14px; font-weight: 600; color: #0f172a; }
.plg-cloud-version   { font-size: 11px; color: #64748b; background: #f1f5f9; padding: 1px 7px; border-radius: 20px; }
.plg-cloud-author    { font-size: 11px; color: #94a3b8; }
.plg-cloud-desc      { font-size: 12px; color: #64748b; margin-top: 4px; line-height: 1.5; }
.plg-cloud-item-action { flex-shrink: 0; }

/* ── Toast ── */
.plg-toast {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 14px; font-size: 13px; border-radius: 8px;
  margin: 8px 12px; flex-shrink: 0;
}
.plg-toast-float {
  position: sticky; top: 8px; z-index: 10;
  box-shadow: 0 2px 8px rgba(0,0,0,.1);
}
.plg-toast-ok  { background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; }
.plg-toast-err { background: #fef2f2; border: 1px solid #fee2e2; color: #991b1b; }
.plg-toast-close {
  background: none; border: none; cursor: pointer; font-size: 14px;
  color: inherit; opacity: .6; padding: 0 0 0 12px;
}
.plg-toast-close:hover { opacity: 1; }

/* ── SVG 空状态图标 ── */
.plg-empty-svg {
  width: 48px; height: 48px; stroke: #cbd5e1; flex-shrink: 0;
}
.plg-cfg-placeholder .plg-empty-svg { width: 40px; height: 40px; }

/* ── 文档面板标题（含 SVG 图标） ── */
.plg-doc-header-title {
  display: inline-flex; align-items: center; gap: 6px;
}
.plg-doc-header-title svg { width: 14px; height: 14px; flex-shrink: 0; }

/* ── APM 安装引导（未安装状态） ── */
.plg-apm-guide {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  padding: 60px 24px; text-align: center; gap: 16px; min-height: 320px;
}
.plg-apm-guide-icon {
  width: 72px; height: 72px; border-radius: 18px;
  background: #eff6ff; border: 1px solid #bfdbfe;
  display: flex; align-items: center; justify-content: center; color: #3b82f6;
}
.plg-apm-guide-icon svg { width: 36px; height: 36px; }
.plg-apm-guide-title { font-size: 20px; font-weight: 700; color: #0f172a; }
.plg-apm-guide-desc { font-size: 14px; color: #64748b; max-width: 460px; line-height: 1.65; }
.plg-apm-guide-btn { padding: 11px 28px; font-size: 14px; margin-top: 4px; }
.plg-apm-result-block {
  display: flex; align-items: center; gap: 8px;
  padding: 10px 16px; border-radius: 8px; font-size: 13px; max-width: 460px;
}
.plg-apm-result-block.ok  { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.plg-apm-result-block.err { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
/* ── APM 状态栏（已安装） ── */
.plg-apm-ok-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 20px; background: #f0fdf4; border-bottom: 1px solid #bbf7d0; flex-shrink: 0;
}
.plg-apm-ok-badge {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 600; color: #166534;
}
.plg-apm-ok-badge svg { width: 14px; height: 14px; }
.plg-apm-inline-result {
  font-size: 12px; padding: 2px 8px; border-radius: 4px;
  max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.plg-apm-inline-result.ok  { background: #dcfce7; color: #166534; }
.plg-apm-inline-result.err { background: #fee2e2; color: #991b1b; }
.spinning { animation: spin .8s linear infinite; }

/* ── 已安装插件 Tab ─────────────────────────────────────────────────── */
.plg-local-toolbar {
  display: flex; align-items: center; gap: 10px; padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0; flex-shrink: 0; background: #fff;
}

.plg-local-list {
  flex: 1; overflow-y: auto; display: flex; flex-direction: column;
  gap: 0; padding: 8px 16px 16px;
}

.plg-local-item-info { flex: 1; min-width: 0; }

.plg-local-item-name {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  font-size: 14px; font-weight: 600; color: #1e293b;
}

.plg-local-badge {
  font-size: 10px; border-radius: 4px; padding: 1px 6px; flex-shrink: 0;
  font-weight: 500; border: 1px solid;
}
.plg-local-badge.ok  { background: #dcfce7; color: #166534; border-color: #bbf7d0; }
.plg-local-badge.off { background: #f1f5f9; color: #64748b; border-color: #e2e8f0; }
.plg-local-badge.upd { background: #fef3c7; color: #92400e; border-color: #fde68a; }
.plg-local-badge.blk { background: #f1f5f9; color: #94a3b8; border-color: #e2e8f0; }

.plg-local-item-meta {
  font-size: 12px; color: #64748b; margin-top: 4px;
  display: flex; align-items: center; gap: 4px; flex-wrap: wrap;
}
.plg-local-meta-label { color: #94a3b8; }
.plg-local-meta-sep   { color: #cbd5e1; }
.plg-local-meta-asm   { color: #94a3b8; font-family: monospace; font-size: 11px; }

.plg-local-item {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 12px 14px; border: 1px solid #e2e8f0; border-radius: 8px;
  background: #fff; margin-top: 8px; transition: box-shadow .15s; flex-wrap: wrap;
}
.plg-local-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,.06); }

.plg-local-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; flex-wrap: wrap; }

.plg-action-btn {
  padding: 4px 10px; font-size: 11px; border-radius: 5px;
  border: 1px solid #e2e8f0; background: #f8fafc; color: #374151;
  cursor: pointer; display: inline-flex; align-items: center; gap: 4px;
  white-space: nowrap; transition: background .15s;
}
.plg-action-btn:hover:not(:disabled) { background: #f1f5f9; }
.plg-action-btn:disabled { opacity: .5; cursor: not-allowed; }
.plg-action-btn.active { background: #ffe4e6; color: #be123c; border-color: #fecdd3; }
.plg-action-btn.active:hover:not(:disabled) { background: #fecdd3; }
.plg-action-btn.upd { background: #fffbeb; color: #92400e; border-color: #fde68a; }
.plg-action-btn.upd:hover:not(:disabled) { background: #fef3c7; }
.plg-action-btn.cfg { background: #f0fdf4; color: #166534; border-color: #bbf7d0; }
.plg-action-btn.cfg:hover:not(:disabled) { background: #dcfce7; }
.plg-action-btn.doc { background: #f0f9ff; color: #0369a1; border-color: #bae6fd; }
.plg-action-btn.doc:hover:not(:disabled) { background: #e0f2fe; }

/* ── 文档弹窗 ── */
.plg-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
}

.plg-modal-box {
  width: min(920px, 92vw);
  height: min(760px, 86vh);
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e2e8f0;
  box-shadow: 0 20px 45px rgba(15, 23, 42, 0.28);
  display: flex;
  flex-direction: column;
}

.plg-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;
}

.plg-modal-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: #0f172a;
}

.plg-modal-title svg {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  color: #64748b;
}

.plg-modal-close {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  cursor: pointer;
  line-height: 1;
}

.plg-modal-close:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.plg-modal-body {
  flex: 1;
  overflow-y: auto;
}

.plg-local-result {
  display: flex; align-items: center; gap: 8px;
  margin: 10px 16px 0; padding: 8px 12px;
  border-radius: 6px; font-size: 13px; font-weight: 500;
}
.plg-local-result.ok  { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.plg-local-result.err { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }

.plg-btn-danger-sm {
  padding: 5px 12px; font-size: 12px; border-radius: 6px; border: 1px solid #fecaca;
  background: #fff; color: #dc2626; cursor: pointer; display: flex;
  align-items: center; gap: 5px; white-space: nowrap; flex-shrink: 0;
  transition: background .15s, color .15s;
}
.plg-btn-danger-sm:hover:not(:disabled) { background: #fee2e2; }
.plg-btn-danger-sm:disabled { opacity: .5; cursor: not-allowed; }
</style>
