<template>
  <div class="files-view">
    <!-- 头部 -->
    <PageHeader title="文件概览" class="files-header">
      <template #meta>
        <span class="fh-server" v-if="activeServer">{{ activeServer.name }}</span>
        <span class="fh-dir" v-if="serverDir" :title="serverDir">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          {{ serverDir }}
        </span>
      </template>
      <template #actions>
      <button class="refresh-btn" @click="requestFileList" :disabled="loading || !agentOnline || !activeServerKey">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ spinning: loading }">
          <polyline points="1 4 1 10 7 10"/>
          <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
        </svg>
        {{ loading ? '加载中…' : '刷新' }}
      </button>
      </template>
    </PageHeader>

    <!-- Agent 未连接提示 -->
    <AgentOfflineNotice v-if="!agentOnline" message="Agent 未连接，无法获取文件列表。请先启动服务器。" />

    <template v-else>
      <!-- 加载中 -->
      <div v-if="loading && !treeData" class="loading-state">
        <div class="spinner"></div>
        <span>正在从服务器获取文件列表…</span>
      </div>

      <!-- 初始空状态 -->
      <div v-else-if="!treeData" class="empty-state-full">
        <div class="empty-big-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
        </div>
        <p>点击"刷新"获取服务器文件列表</p>
        <button class="btn-fetch" @click="requestFileList">获取文件列表</button>
      </div>

      <template v-else>
        <!-- ══ Section 1: 完整目录结构 ══ -->
        <div class="section">
          <div class="section-header" @click="treeSectionOpen = !treeSectionOpen">
            <div class="sh-left">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
              </svg>
              目录结构
              <span class="sh-hint">点击文件夹可展开或收起</span>
            </div>
            <svg class="sh-chevron" :class="{ open: treeSectionOpen }"
                 viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </div>

          <div v-show="treeSectionOpen" class="tree-box">
            <div
              v-for="item in flatTree"
              :key="item._key"
              :class="['tree-row', 'tr-' + item.type]"
              :style="{ paddingLeft: item.depth * 18 + 14 + 'px' }"
              @click="item.type === 'dir' ? toggleDir(item.path) : null"
            >
              <span class="tr-icon">
                <template v-if="item.type === 'dir'">
                  <svg v-if="expandedDirs.has(item.path)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 7h5l2 3h11v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                    <path d="M3 7V5a2 2 0 0 1 2-2h4l2 3h6a2 2 0 0 1 2 2v2"/>
                  </svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                  </svg>
                </template>
                <template v-else>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                  </svg>
                </template>
              </span>
              <span class="tr-name">{{ item.name }}</span>
              <span v-if="item.type === 'file'" class="tr-size">{{ formatBytes(item.size) }}</span>
              <span v-if="item.type === 'file'" class="tr-date">{{ item.modified }}</span>
            </div>
          </div>
        </div>

        <!-- ══ Section 2: 分类概览 ══ -->
        <div class="section">
          <div class="section-title-bar">
            <span class="section-title">分类概览</span>
          </div>

          <div class="tab-bar">
            <button
              v-for="cat in sortedCategories"
              :key="cat.key"
              :class="['tab-btn', { active: activeTab === cat.key }]"
              @click="setTab(cat.key)"
            >
              {{ cat.name }}
              <span class="tab-count">{{ cat.files.length }}</span>
            </button>
          </div>

          <div class="file-panel" v-if="currentCategory">
            <div v-if="currentCategory.files.length === 0" class="empty-state">
              <p>该分类下暂无文件</p>
            </div>

            <!-- 插件列表 -->
            <template v-else-if="activeTab === 'plugins'">
              <div v-for="f in currentCategory.files" :key="f.name" class="plugin-row">
                <label class="row-check">
                  <input type="checkbox" :value="f.full_path || f.name" v-model="selectedPaths">
                </label>
                <div class="pr-info">
                  <span class="ft-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
                      <polyline points="7.5 4.21 12 6.81 16.5 4.21"/>
                      <polyline points="7.5 19.79 7.5 14.6 3 12"/>
                      <polyline points="21 12 16.5 14.6 16.5 19.79"/>
                      <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
                      <line x1="12" y1="22.08" x2="12" y2="12"/>
                    </svg>
                  </span>
                  <span class="pr-name">{{ f.name }}</span>
                  <span v-if="f.dir" class="ft-dir-badge" :title="f.dir">{{ shortDir(f.dir) }}</span>
                </div>
                <div class="pr-right">
                  <span class="pr-size">{{ formatBytes(f.size) }}</span>
                </div>
              </div>
            </template>

            <!-- 世界存档：卡片式，突出显示路径 -->
            <template v-else-if="activeTab === 'worlds'">
              <div v-for="f in currentCategory.files" :key="f.full_path || f.name" class="world-card">
                <label class="row-check world-check">
                  <input type="checkbox" :value="f.full_path || f.name" v-model="selectedPaths">
                </label>
                <div class="wc-body">
                  <div class="wc-head">
                    <span class="wc-icon">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
                    </span>
                    <span class="wc-name">{{ f.name }}</span>
                    <span class="wc-size">{{ formatBytes(f.size) }}</span>
                  </div>
                  <div class="wc-dir">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
                    </svg>
                    <span class="wc-dir-path">{{ f.dir }}</span>
                  </div>
                  <div class="wc-meta">最后修改：{{ f.modified }}</div>
                </div>
              </div>
            </template>

            <!-- 数据库文件：专用列表，带浏览按钮 -->
            <template v-else-if="activeTab === 'databases'">
              <div class="mgmt-head">
                <span></span><span>文件名</span><span>大小</span><span>修改时间</span><span></span>
              </div>
              <div v-for="f in currentCategory.files" :key="f.full_path || f.name" class="mgmt-row">
                <label class="row-check">
                  <input type="checkbox" :value="f.full_path || f.name" v-model="selectedPaths">
                </label>
                <span class="mr-name">
                  <span class="ft-icon ft-icon-db">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                  </span>
                  {{ f.name }}
                  <span v-if="f.dir" class="ft-dir-badge" :title="f.dir">{{ shortDir(f.dir) }}</span>
                </span>
                <span class="mr-size">{{ formatBytes(f.size) }}</span>
                <span class="mr-date">{{ f.modified }}</span>
                <span class="mr-actions">
                  <button
                    class="mr-edit-btn mr-db-btn"
                    @click.stop="openDbBrowser(f)"
                    :disabled="!canBrowseDatabase"
                    :title="canBrowseDatabase ? '浏览数据库' : '缺少数据库浏览权限'"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                    浏览
                  </button>
                </span>
              </div>
            </template>

            <!-- 通用文件管理（配置文件、日志等）-->
            <template v-else>
              <div class="mgmt-head">
                <span></span><span>文件名</span><span>大小</span><span>修改时间</span><span></span>
              </div>
              <div v-for="f in currentCategory.files" :key="f.full_path || f.name" class="mgmt-row">
                <label class="row-check">
                  <input type="checkbox" :value="f.full_path || f.name" v-model="selectedPaths">
                </label>
                <span class="mr-name">
                  <span class="ft-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                      <polyline points="14 2 14 8 20 8"/>
                    </svg>
                  </span>
                  {{ f.name }}
                  <span v-if="f.dir" class="ft-dir-badge" :title="f.dir">{{ shortDir(f.dir) }}</span>
                </span>
                <span class="mr-size">{{ formatBytes(f.size) }}</span>
                <span class="mr-date">{{ f.modified }}</span>
                <span class="mr-actions">
                  <button
                    class="mr-edit-btn"
                    @click.stop="editFile(f)"
                    :disabled="!canWriteFiles"
                    :title="canWriteFiles ? '编辑文件' : '缺少文件写入权限'"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 20h9"/>
                      <path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>
                    </svg>
                  </button>
                </span>
              </div>
            </template>
          </div>
        </div>
      </template>
    </template>

    <!-- ── 底部选中操作工具栏 ── -->
    <transition name="sel-bar">
      <div class="sel-toolbar" v-if="selectedPaths.length > 0">
        <span class="sel-count">已选 {{ selectedPaths.length }} 个文件</span>
        <div class="sel-actions">
          <button class="sel-btn sel-edit"
            v-if="selectedPaths.length === 1"
            :disabled="!canWriteFiles"
            @click="editSingleSelected">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>
            编辑
          </button>
          <button class="sel-btn sel-rename"
            v-if="selectedPaths.length === 1"
            :disabled="!canWriteFiles"
            @click="openRenameDialog">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.59 13.41 13.42 20.58a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>
            重命名
          </button>
          <button class="sel-btn sel-copy"
            v-if="selectedPaths.length === 1"
            :disabled="!canWriteFiles"
            @click="openCopyDialog">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            复制
          </button>
          <button class="sel-btn sel-del" @click="deleteSelected" :disabled="!canDeleteFiles">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
            删除
          </button>
          <button class="sel-btn sel-clear" @click="selectedPaths = []">清空</button>
        </div>
      </div>
    </transition>

    <DatabaseBrowserModal
      v-if="dbBrowserFile"
      :file="dbBrowserFile"
      :active-server-key="activeServerKey"
      :can-write-database="canWriteDatabase"
      :can-use-raw-sql="canUseRawSql"
      @close="closeDbBrowser"
    />

    <!-- ── 文件编辑模态框 ── -->
    <div class="modal-backdrop" v-if="editingFile" @click.self="closeEditor">
      <div class="editor-modal">
        <div class="em-header">
          <div class="em-title-row">
            <span class="em-filename">{{ editingFile.name }}</span>
            <span v-if="isEditingJson" class="em-lang-badge em-json">JSON</span>
            <span v-else-if="isEditingBinary" class="em-lang-badge em-binary">二进制</span>
          </div>
          <button class="em-close" @click="closeEditor" title="关闭">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <div v-if="editorLoading" class="em-loading">
          <div class="spinner"></div><span>正在读取文件…</span>
        </div>
        <template v-else-if="isEditingBinary">
          <div class="em-binary-notice">
            <span class="em-bi-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            </span>
            <div>
              <div class="em-bi-title">该文件为二进制格式，不支持文本编辑</div>
              <div class="em-bi-hint">SQLite/二进制数据库文件需使用专用 SQL 工具管理。</div>
            </div>
          </div>
          <div class="em-footer">
            <button class="em-cancel" @click="closeEditor">关闭</button>
          </div>
        </template>
        <template v-else>
          <div v-if="editorError" class="em-error">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/>
              <line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            {{ editorError }}
          </div>
          <div v-if="isEditingJson" class="em-json-panel">
            <div class="em-json-editor" :class="{ invalid: !!jsonValidErr }">
              <div ref="jsonLineGutterEl" class="em-json-gutter" aria-hidden="true">
                <span v-for="line in jsonLineNumbers" :key="line" :class="{ error: line === jsonErrorLine }">{{ line }}</span>
              </div>
              <pre ref="jsonHighlightEl" class="em-json-highlight" aria-hidden="true"><code v-html="highlightedJson"></code></pre>
              <textarea
                ref="jsonTextareaEl"
                class="em-json-input"
                v-model="editContent"
                spellcheck="false"
                @input="validateJson"
                @scroll="syncJsonScroll"
                @keydown.tab.prevent="insertJsonIndent"
              ></textarea>
            </div>
            <div v-if="jsonValidErr" class="em-json-err">
              <div class="em-json-err-head">
                <strong>JSON 格式不正确</strong>
                <button v-if="jsonErrorPos" class="em-json-err-jump" @click="jumpToJsonError">定位到错误</button>
              </div>
              <div class="em-json-err-msg">{{ jsonValidErr }}</div>
              <div v-if="jsonErrorPos" class="em-json-err-meta">
                第 {{ jsonErrorPos.line }} 行，第 {{ jsonErrorPos.col }} 列附近
              </div>
              <div v-if="jsonErrorContext.length" class="em-json-err-context">
                <template v-for="row in jsonErrorContext" :key="`${row.line}-${row.isCaret ? 'caret' : 'code'}`">
                  <div v-if="!row.isCaret" :class="['em-json-err-row', { error: row.isError }]">
                    <span class="em-json-err-no">{{ row.line }}</span>
                    <code>{{ row.text || ' ' }}</code>
                  </div>
                  <div v-else class="em-json-err-row em-json-err-caret">
                    <span class="em-json-err-no"></span>
                    <code :style="{ paddingLeft: `${Math.max(0, row.col - 1)}ch` }">^</code>
                  </div>
                </template>
              </div>
            </div>
          </div>
          <textarea v-else class="em-textarea" v-model="editContent" spellcheck="false"></textarea>
          <div class="em-footer">
            <button v-if="isEditingJson" class="em-fmt-btn" @click="formatJson" :disabled="editorSaving">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.1-3.1a5 5 0 0 1-6.6 6.6L8.6 18.4a2 2 0 1 1-2.8-2.8l5.6-5.6a5 5 0 0 1 6.6-6.6z"/>
              </svg>
              格式化
            </button>
            <span style="flex:1"></span>
            <button class="em-save" @click="saveFile" :disabled="editorSaving || !canWriteFiles || (isEditingJson && !!jsonValidErr)">
              <svg v-if="!editorSaving" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
              {{ editorSaving ? '保存中…' : '保存' }}
            </button>
            <button class="em-cancel" @click="closeEditor" :disabled="editorSaving">取消</button>
          </div>
        </template>
      </div>
    </div>

    <!-- ── 删除确认模态框 ── -->
    <div class="modal-backdrop" v-if="deleteTarget" @click.self="deleteTarget = null">
      <div class="confirm-modal">
        <div class="cm-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
        </div>
        <div class="cm-title">确认删除</div>
        <div class="cm-body">确定要删除 <strong>{{ deleteTarget.name }}</strong> 吗？<br>此操作不可恢复。</div>
        <div class="cm-footer">
          <button class="cm-del" @click="doDelete" :disabled="deleteBusy || !canDeleteFiles">{{ deleteBusy ? '删除中…' : '确认删除' }}</button>
          <button class="cm-cancel" @click="deleteTarget = null" :disabled="deleteBusy">取消</button>
        </div>
      </div>
    </div>
    <!-- ── 批量删除确认弹窗 ── -->
    <div class="modal-backdrop" v-if="batchDeleteTarget.length > 0 && !batchDeleteBusy && !batchDeleteDone" @click.self="batchDeleteTarget = []">
      <div class="confirm-modal">
        <div class="cm-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
        </div>
        <div class="cm-title">确认批量删除</div>
        <div class="cm-body">将删除 <strong>{{ batchDeleteTarget.length }}</strong> 个文件，此操作不可恢复。<br>
          <span style="font-size:11px;color:#94a3b8">包括：{{ batchDeleteTarget.map(f=>f.name).join('、') }}</span>
        </div>
        <div class="cm-footer">
          <button class="cm-del" @click="startBatchDelete" :disabled="!canDeleteFiles">确认删除</button>
          <button class="cm-cancel" @click="batchDeleteTarget = []">取消</button>
        </div>
      </div>
    </div>

    <!-- ── 批量删除进行中提示 ── -->
    <div class="modal-backdrop" v-if="batchDeleteBusy">
      <div class="confirm-modal">
        <div class="cm-icon"><div class="spinner" style="margin:0 auto"></div></div>
        <div class="cm-title">删除中…</div>
        <div class="cm-body">还剩 {{ batchDeleteQueue.length }} 个文件等待删除</div>
      </div>
    </div>

    <!-- ── 批量删除完成 ── -->
    <div class="modal-backdrop" v-if="batchDeleteDone" @click.self="batchDeleteDone = false; batchDeleteTarget = []; selectedPaths = []">
      <div class="confirm-modal">
        <div class="cm-icon cm-icon-ok">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
        </div>
        <div class="cm-title">删除完成</div>
        <div class="cm-body">已删除 {{ batchDeleteTarget.length }} 个文件。</div>
        <div class="cm-footer">
          <button class="cm-cancel" style="flex:1" @click="batchDeleteDone = false; batchDeleteTarget = []; selectedPaths.value = []">确定</button>
        </div>
      </div>
    </div>

    <div class="modal-backdrop" v-if="pathDialogVisible" @click.self="closePathDialog">
      <div class="confirm-modal path-modal">
        <div class="cm-title">{{ pathDialogTitle }}</div>
        <div class="cm-body">{{ pathDialogHint }}</div>
        <input
          class="path-input"
          v-model="pathDialogInput"
          :placeholder="pathDialogPlaceholder"
          @keyup.enter="confirmPathDialog"
        />
        <div class="cm-footer">
          <button class="cm-del" @click="confirmPathDialog" :disabled="!canWriteFiles">确认</button>
          <button class="cm-cancel" @click="closePathDialog">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted, nextTick } from 'vue'
import { useFeedback } from '@/composables/useFeedback'
import AgentOfflineNotice from '@/components/AgentOfflineNotice.vue'
import PageHeader from '@/components/PageHeader.vue'
import DatabaseBrowserModal from '@/components/files/DatabaseBrowserModal.vue'

const props = defineProps({
  wsState:     { type: String, default: 'disconnected' },
  agentOnline: { type: Boolean, default: false },
})

const activeServer    = inject('activeServer',    ref(null))
const activeServerKey = inject('activeServerKey', ref(''))
const hasPerm         = inject('hasPerm', () => false)
const { toast } = useFeedback()

const loading         = ref(false)
const treeData        = ref(null)
const categories      = ref([])
const serverDir       = ref('')
const activeTab       = ref('')
const treeSectionOpen = ref(false)
const expandedDirs    = ref(new Set())

const serverCapabilities = computed(() =>
  activeServer.value?.capabilities || activeServer.value?.agent_capabilities || null
)

function hasCapability(name) {
  const caps = serverCapabilities.value
  if (!caps) return true
  if (Array.isArray(caps)) return caps.includes(name)
  return caps[name] !== false
}

const canWriteFiles = computed(() =>
  hasPerm('panel.files.write') && hasCapability('file_write')
)
const canDeleteFiles = computed(() =>
  hasPerm('panel.files.delete') && hasCapability('file_delete')
)
const canBrowseDatabase = computed(() =>
  hasPerm('panel.database') && hasCapability('database')
)
const canWriteDatabase = computed(() =>
  hasPerm('panel.database.write') && hasCapability('database_write')
)
const canUseRawSql = computed(() =>
  hasPerm('panel.database.sql') && hasCapability('database_sql')
)

// ── 选中文件集合 ──
const selectedPaths = ref([])
const pathDialogVisible = ref(false)
const pathDialogMode = ref('')
const pathDialogTitle = ref('')
const pathDialogHint = ref('')
const pathDialogPlaceholder = ref('')
const pathDialogInput = ref('')

const selectedFiles = computed(() => {
  const all = []
  for (const cat of categories.value) all.push(...cat.files)
  return all.filter(f => selectedPaths.value.includes(f.full_path || f.name))
})

// 切换 Tab 时清空选中
function setTab(key) {
  activeTab.value   = key
  selectedPaths.value = []
}

// 编辑单个选中文件
function editSingleSelected() {
  if (!canWriteFiles.value) { toast.warning('缺少文件写入权限'); return }
  const f = selectedFiles.value[0]
  if (!f) return
  editFile(f)
  selectedPaths.value = []
}

function openRenameDialog() {
  if (!canWriteFiles.value) { toast.warning('缺少文件写入权限'); return }
  const f = selectedFiles.value[0]
  if (!f) return
  pathDialogMode.value = 'rename'
  pathDialogTitle.value = '重命名文件'
  pathDialogHint.value = '输入新文件名（不含路径）'
  pathDialogPlaceholder.value = '例如: new_name.json'
  pathDialogInput.value = f.name || ''
  pathDialogVisible.value = true
}

function openCopyDialog() {
  if (!canWriteFiles.value) { toast.warning('缺少文件写入权限'); return }
  const f = selectedFiles.value[0]
  if (!f) return
  pathDialogMode.value = 'copy'
  pathDialogTitle.value = '复制文件'
  pathDialogHint.value = '输入复制后的文件名（不含路径）'
  pathDialogPlaceholder.value = '例如: copy_of_file.json'
  pathDialogInput.value = f.name || ''
  pathDialogVisible.value = true
}

function closePathDialog() {
  pathDialogVisible.value = false
}

function confirmPathDialog() {
  if (!canWriteFiles.value) { toast.warning('缺少文件写入权限'); return }
  const f = selectedFiles.value[0]
  if (!f) return
  const text = (pathDialogInput.value || '').trim()
  if (!text) return
  const baseDir = getSafeBaseDir()
  if (!baseDir) { toast.warning('请先点击刷新，获取服务器目录后再操作'); return }
  const srcPath = f.full_path || f.name
  const dstPath = `${baseDir.replace(/[\\/]+$/, '')}\\${text}`
  const type = pathDialogMode.value === 'copy' ? 'file_copy' : 'file_move'
  window.__tshockSend?.({
    type,
    msg_id: Date.now().toString(),
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, src_path: srcPath, dst_path: dstPath },
  })
  pathDialogVisible.value = false
}

function normalizeWinPath(path) {
  return (path || '').replace(/\//g, '\\').toLowerCase()
}

function isInsideServerDir(path) {
  const s = normalizeWinPath(serverDir.value).replace(/[\\]+$/, '')
  const p = normalizeWinPath(path)
  return !!s && (p === s || p.startsWith(s + '\\'))
}

function getSafeBaseDir() {
  if (!serverDir.value) return ''
  const fromSelected = selectedFiles.value[0]?.dir
  if (fromSelected && isInsideServerDir(fromSelected)) return fromSelected
  const catDir = currentCategory.value?.files?.[0]?.dir
  if (catDir && isInsideServerDir(catDir)) return catDir
  return serverDir.value
}

// 删除选中文件（目前转单个确认；批量删除可后续扩展）
function deleteSelected() {
  if (!canDeleteFiles.value) { toast.warning('缺少文件删除权限'); return }
  if (selectedFiles.value.length === 1) {
    deleteFile(selectedFiles.value[0])
  } else if (selectedFiles.value.length > 1) {
    batchDeleteTarget.value = [...selectedFiles.value]
    batchDeleteBusy.value   = false
    batchDeleteDone.value   = false
  }
}

// ── 批量删除状态 ──
const batchDeleteTarget = ref([])
const batchDeleteBusy   = ref(false)
const batchDeleteDone   = ref(false)
const batchDeleteQueue  = ref([])

function startBatchDelete() {
  if (!canDeleteFiles.value) { toast.warning('缺少文件删除权限'); return }
  batchDeleteBusy.value  = true
  batchDeleteQueue.value = batchDeleteTarget.value.map(f => f.full_path || f.name)
  sendNextDelete()
}

function sendNextDelete() {
  if (!canDeleteFiles.value) { toast.warning('缺少文件删除权限'); return }
  const path = batchDeleteQueue.value.shift()
  if (!path) { batchDeleteDone.value = true; batchDeleteBusy.value = false; return }
  window.__tshockSend?.({
    type: 'file_delete', msg_id: Date.now().toString(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path, _batch: true },
  })
}

const dbBrowserFile = ref(null)

function openDbBrowser(f) {
  if (!canBrowseDatabase.value) { toast.warning('缺少数据库浏览权限'); return }
  dbBrowserFile.value = f
}

function closeDbBrowser() {
  dbBrowserFile.value = null
}

// ── 编辑器状态 ──
const editingFile    = ref(null)
const editContent    = ref('')
const editorLoading  = ref(false)
const editorSaving   = ref(false)
const editorError    = ref('')
const editorIsBinary = ref(false)
const jsonValidErr   = ref('')
const jsonErrorPos   = ref(null)
const jsonTextareaEl = ref(null)
const jsonHighlightEl = ref(null)
const jsonLineGutterEl = ref(null)

const isEditingJson   = computed(() =>
  editingFile.value?.name?.toLowerCase().endsWith('.json') ?? false
)
const isEditingBinary = computed(() => editorIsBinary.value)
const jsonLineNumbers = computed(() => {
  const count = Math.max(1, String(editContent.value || '').split('\n').length)
  return Array.from({ length: count }, (_, index) => index + 1)
})
const jsonErrorLine = computed(() => jsonErrorPos.value?.line || 0)
const jsonErrorContext = computed(() => getJsonErrorContext(editContent.value, jsonErrorPos.value))
const highlightedJson = computed(() => highlightJson(editContent.value, jsonErrorLine.value))

function validateJson() {
  if (!editContent.value.trim()) {
    jsonValidErr.value = ''
    jsonErrorPos.value = null
    nextTick(syncJsonScroll)
    return
  }
  try {
    JSON.parse(editContent.value)
    jsonValidErr.value = ''
    jsonErrorPos.value = null
  }
  catch (e) {
    jsonErrorPos.value = parseJsonErrorPosition(editContent.value, e)
    jsonValidErr.value = formatFriendlyJsonError(editContent.value, e)
  }
  nextTick(syncJsonScroll)
}

function formatJson() {
  try {
    const parsed = JSON.parse(editContent.value)
    editContent.value = JSON.stringify(parsed, null, 2)
    jsonValidErr.value = ''
    jsonErrorPos.value = null
    nextTick(syncJsonScroll)
  } catch (e) {
    jsonErrorPos.value = parseJsonErrorPosition(editContent.value, e)
    jsonValidErr.value = formatFriendlyJsonError(editContent.value, e)
    jumpToJsonError()
  }
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function highlightJsonLine(value) {
  const text = String(value || '')
  const tokenPattern = /("(?:\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*"(\s*:)?|\btrue\b|\bfalse\b|\bnull\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g
  let html = ''
  let cursor = 0
  for (const match of text.matchAll(tokenPattern)) {
    const token = match[0]
    const index = match.index ?? 0
    html += escapeHtml(text.slice(cursor, index))
    let cls = 'json-number'
    if (token.startsWith('"')) cls = /:\s*$/.test(token) ? 'json-key' : 'json-string'
    else if (token === 'true' || token === 'false') cls = 'json-bool'
    else if (token === 'null') cls = 'json-null'
    html += `<span class="${cls}">${escapeHtml(token)}</span>`
    cursor = index + token.length
  }
  html += escapeHtml(text.slice(cursor))
  return html
}

function highlightJson(value, errorLine = 0) {
  const text = String(value || '')
  if (!text) return '<span class="json-line"><span class="json-muted">{}</span></span>'
  return text.split('\n').map((line, index) => {
    const lineNo = index + 1
    const cls = lineNo === errorLine ? 'json-line is-error' : 'json-line'
    return `<span class="${cls}">${highlightJsonLine(line) || '&nbsp;'}</span>`
  }).join('')
}

function parseJsonErrorPosition(text, err) {
  const msg = String(err?.message || '')
  const lineCol = msg.match(/line\s+(\d+)\s+column\s+(\d+)/i)
  if (lineCol) {
    const line = Number(lineCol[1])
    const col = Number(lineCol[2])
    const lines = String(text || '').split('\n')
    const idx = lines.slice(0, Math.max(0, line - 1)).reduce((sum, lineText) => sum + lineText.length + 1, 0) + Math.max(0, col - 1)
    return { idx: Math.min(idx, text.length), line, col }
  }

  const posMatch = msg.match(/position\s+(\d+)/i)
  if (!posMatch) return null
  const idx = Math.min(Number(posMatch[1]), text.length)
  if (!Number.isFinite(idx) || idx < 0) return null
  const head = text.slice(0, idx)
  const lines = head.split('\n')
  return {
    idx,
    line: lines.length,
    col: lines[lines.length - 1].length + 1,
  }
}

function clampJsonContextLine(lineText, col = 1, isError = false) {
  const text = String(lineText ?? '')
  if (text.length <= 160) return { text, col }
  if (!isError) return { text: `${text.slice(0, 157)}...`, col: 1 }
  const safeCol = Math.max(1, col || 1)
  const start = Math.max(0, safeCol - 81)
  const end = Math.min(text.length, start + 160)
  const prefix = start > 0 ? '...' : ''
  const suffix = end < text.length ? '...' : ''
  return {
    text: `${prefix}${text.slice(start, end)}${suffix}`,
    col: safeCol - start + prefix.length,
  }
}

function getJsonErrorContext(text, pos, radius = 2) {
  if (!pos) return []
  const lines = String(text || '').split('\n')
  const errorLine = Math.max(1, pos.line || 1)
  const start = Math.max(1, errorLine - radius)
  const end = Math.min(lines.length, errorLine + radius)
  const rows = []
  for (let lineNo = start; lineNo <= end; lineNo += 1) {
    const isError = lineNo === errorLine
    const lineInfo = clampJsonContextLine(lines[lineNo - 1] ?? '', pos.col || 1, isError)
    rows.push({ line: lineNo, text: lineInfo.text, isError })
    if (isError) rows.push({ line: lineNo, isCaret: true, col: lineInfo.col })
  }
  return rows
}

function friendlyJsonHint(err) {
  const msg = String(err?.message || '')
  if (/Expected double-quoted property name/i.test(msg)) {
    return '对象属性名必须使用英文双引号，也可能是上一项末尾多了逗号。'
  }
  if (/Unexpected end of JSON input/i.test(msg)) {
    return '内容还没有写完整，请检查结尾处是否缺少括号、方括号或引号。'
  }
  if (/Unterminated string/i.test(msg)) {
    return '字符串没有正确结束，请检查是否缺少英文双引号。'
  }
  if (/Bad control character/i.test(msg)) {
    return '字符串中包含未转义的换行或控制字符。'
  }
  if (/Unexpected token/i.test(msg) && /}/.test(msg)) {
    return '可能存在多余逗号，或对象里缺少有效的键值对。'
  }
  if (/Unexpected string/i.test(msg)) {
    return '可能缺少逗号，或键和值之间缺少冒号。'
  }
  if (/Unexpected non-whitespace character/i.test(msg)) {
    return 'JSON 根节点后面还有多余内容。'
  }
  return '请检查逗号、冒号、英文双引号和括号是否成对。'
}

function formatFriendlyJsonError(text, err) {
  const pos = parseJsonErrorPosition(text, err)
  const hint = friendlyJsonHint(err)
  return pos
    ? `JSON 格式不正确：第 ${pos.line} 行，第 ${pos.col} 列附近。${hint}`
    : `JSON 格式不正确：${hint}`
}

function jumpToJsonError() {
  const pos = jsonErrorPos.value
  const el = jsonTextareaEl.value
  if (!pos || !el) return
  const lineHeight = parseFloat(getComputedStyle(el).lineHeight) || 21
  const colWidth = Math.max(7, (parseFloat(getComputedStyle(el).fontSize) || 13) * 0.62)
  el.focus()
  el.scrollTop = Math.max(0, (pos.line - 3) * lineHeight)
  el.scrollLeft = Math.max(0, (pos.col - 36) * colWidth)
  el.setSelectionRange(pos.idx ?? 0, pos.idx ?? 0)
  syncJsonScroll({ target: el })
}

function syncJsonScroll(event) {
  const source = event?.target
  const target = jsonHighlightEl.value
  if (!source || !target) return
  target.scrollTop = source.scrollTop
  target.scrollLeft = source.scrollLeft
  if (jsonLineGutterEl.value) jsonLineGutterEl.value.scrollTop = source.scrollTop
}

function insertJsonIndent(event) {
  const el = event.target
  const start = el.selectionStart
  const end = el.selectionEnd
  editContent.value = editContent.value.slice(0, start) + '  ' + editContent.value.slice(end)
  validateJson()
  nextTick(() => {
    el.selectionStart = start + 2
    el.selectionEnd = start + 2
    syncJsonScroll({ target: el })
  })
}

// ── 删除对话框 ──
const deleteTarget  = ref(null)
const deleteBusy    = ref(false)

const currentCategory = computed(
  () => categories.value.find(c => c.key === activeTab.value) || null
)

const CAT_ORDER = ['plugins', 'configs', 'worlds', 'logs', 'databases']
const sortedCategories = computed(() => {
  const cats = [...categories.value]
  cats.sort((a, b) => {
    const ai = CAT_ORDER.indexOf(a.key)
    const bi = CAT_ORDER.indexOf(b.key)
    return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
  })
  return cats
})

function toggleDir(path) {
  const s = new Set(expandedDirs.value)
  s.has(path) ? s.delete(path) : s.add(path)
  expandedDirs.value = s
}

// 把树递归展平为带 depth 的行列表，依赖 expandedDirs 决定是否展开
function buildFlat(node, depth, result) {
  if (!node) return
  result.push({ ...node, depth, _key: node.path || `${depth}-${node.name}`, children: undefined })
  if (node.type === 'dir' && expandedDirs.value.has(node.path)) {
    for (const child of (node.children || []))
      buildFlat(child, depth + 1, result)
  }
}

const flatTree = computed(() => {
  if (!treeData.value) return []
  const result = []
  buildFlat(treeData.value, 0, result)
  return result
})

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i]
}

// 对目录路径取最后两级，避免表格内容过长
function shortDir(dir) {
  if (!dir) return ''
  const parts = dir.replace(/\\/g, '/').split('/').filter(Boolean)
  return parts.slice(-2).join('/')
}

// ── 通用文件管理 ──
function editFile(f) {
  if (!canWriteFiles.value) { toast.warning('缺少文件写入权限'); return }
  editingFile.value    = f
  editContent.value    = ''
  editorError.value    = ''
  editorIsBinary.value = false
  jsonValidErr.value   = ''
  jsonErrorPos.value   = null
  editorLoading.value  = true
  window.__tshockSend?.({
    type: 'file_read', msg_id: Date.now().toString(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: f.full_path },
  })
}

function closeEditor() {
  if (editorSaving.value) return
  editingFile.value    = null
  editContent.value    = ''
  editorError.value    = ''
  editorIsBinary.value = false
  jsonValidErr.value   = ''
  jsonErrorPos.value   = null
  editorLoading.value  = false
}

function saveFile() {
  if (!canWriteFiles.value) { editorError.value = '缺少文件写入权限'; return }
  if (!editingFile.value) return
  // JSON 保存前校验语法
  if (isEditingJson.value) {
    try { JSON.parse(editContent.value) }
    catch (e) {
      jsonErrorPos.value = parseJsonErrorPosition(editContent.value, e)
      jsonValidErr.value = formatFriendlyJsonError(editContent.value, e)
      jumpToJsonError()
      return
    }
  }
  editorSaving.value = true
  editorError.value  = ''
  window.__tshockSend?.({
    type: 'file_write', msg_id: Date.now().toString(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: editingFile.value.full_path, content: editContent.value },
  })
}

function deleteFile(f) {
  if (!canDeleteFiles.value) { toast.warning('缺少文件删除权限'); return }
  deleteTarget.value = f
}

function doDelete() {
  if (!canDeleteFiles.value) { toast.warning('缺少文件删除权限'); return }
  if (!deleteTarget.value) return
  deleteBusy.value = true
  window.__tshockSend?.({
    type: 'file_delete', msg_id: Date.now().toString(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: deleteTarget.value.full_path },
  })
}

function requestFileList() {
  if (!props.agentOnline || !activeServerKey.value) return
  loading.value = true
  window.__tshockSend?.({
    type: 'file_list',
    msg_id: Date.now().toString(),
    timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value },
  })
  setTimeout(() => { loading.value = false }, 15000)
}

function onWsMessage(e) {
  const pkt = e.detail
  const p   = pkt.payload || {}

  if (pkt.type === 'file_list_resp') {
    loading.value    = false
    treeData.value   = p.tree        || null
    categories.value = p.categories  || []
    serverDir.value  = p.server_dir  || ''
    if (sortedCategories.value.length > 0 && !activeTab.value)
      activeTab.value = sortedCategories.value[0].key
    selectedPaths.value = []
  }

  if (pkt.type === 'file_read_resp') {
    editorLoading.value = false
    if (p.success) {
      editContent.value    = p.content ?? ''
      editorError.value    = ''
      editorIsBinary.value = false
      if (isEditingJson.value) validateJson()
    } else {
      editorIsBinary.value = p.binary === true
      editorError.value    = editorIsBinary.value ? '' : (p.msg || '读取失败')
    }
    return
  }

  if (pkt.type === 'file_write_resp') {
    editorSaving.value = false
    if (p.success) closeEditor()
    else           editorError.value = p.msg || '保存失败'
    return
  }

  if (pkt.type === 'file_move_resp' || pkt.type === 'file_copy_resp') {
    if (p.success) {
      requestFileList()
      selectedPaths.value = []
    } else {
      toast.error(p.msg || '操作失败')
    }
    return
  }

  if (pkt.type === 'file_delete_resp') {
    deleteBusy.value = false
    if (p.success) {
      const deletedPath = p.path || deleteTarget.value?.full_path
      categories.value = categories.value.map(c => ({
        ...c, files: c.files.filter(f => (f.full_path || f.name) !== deletedPath)
      }))
      selectedPaths.value = selectedPaths.value.filter(x => x !== deletedPath)
      deleteTarget.value = null
      // 批量删除：继续发送下一个
      if (batchDeleteQueue.value.length > 0) { sendNextDelete(); return }
      if (batchDeleteBusy.value)             { batchDeleteDone.value = true; batchDeleteBusy.value = false }
    }
    return
  }
}

onMounted(() => {
  window.addEventListener('ws-message', onWsMessage)
  if (props.agentOnline && activeServerKey.value) requestFileList()
})
onUnmounted(() => {
  window.removeEventListener('ws-message', onWsMessage)
})
</script>

<style scoped>
.files-view {
  padding: 28px 32px;
  overflow-y: auto;
  height: 100%;
  box-sizing: border-box;
}

.files-header { margin: -28px -32px 24px; }
.fh-server {
  font-size: 12px; color: #64748b;
  background: #f1f5f9; border: 1px solid #e2e8f0;
  padding: 3px 10px; border-radius: 20px;
}
.fh-dir {
  display: flex; align-items: center; gap: 5px;
  font-size: 11px; color: #94a3b8;
  background: #f8fafc; border: 1px solid #e2e8f0;
  padding: 3px 10px; border-radius: 6px;
  max-width: 380px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  font-family: 'Courier New', monospace; cursor: default;
}
.fh-dir svg { width: 12px; height: 12px; flex-shrink: 0; }

.refresh-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 18px;
  background: #fff; border: 1px solid #e2e8f0;
  border-radius: 8px; font-size: 13px; color: #475569;
  cursor: pointer; transition: all .15s; white-space: nowrap;
}
.refresh-btn:hover:not(:disabled) { background: #f1f5f9; border-color: #cbd5e1; }
.refresh-btn:disabled              { opacity: .5; cursor: not-allowed; }
.refresh-btn svg { width: 14px; height: 14px; }
.spinning { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }


/* ── Section 容器 ── */
.section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  margin-bottom: 20px;
  overflow: hidden;
}

/* ── 目录结构 Section 头部 ── */
.section-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 18px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  cursor: pointer;
  user-select: none;
  transition: background .12s;
}
.section-header:hover { background: #f1f5f9; }
.sh-left {
  display: flex; align-items: center; gap: 8px;
  font-size: 14px; font-weight: 600; color: #0f172a;
}
.sh-left svg   { width: 16px; height: 16px; color: #64748b; }
.sh-hint       { font-size: 11px; color: #94a3b8; font-weight: 400; }
.sh-chevron    { width: 16px; height: 16px; color: #94a3b8; transition: transform .2s; }
.sh-chevron.open { transform: rotate(180deg); }

/* ── 分类 Section 头部 ── */
.section-title-bar {
  padding: 14px 18px 0;
}
.section-title {
  font-size: 13px; font-weight: 700; color: #94a3b8;
  letter-spacing: .06em; text-transform: uppercase;
}

/* ── 目录树 ── */
.tree-box {
  overflow-x: auto;
  max-height: 420px;
  overflow-y: auto;
}
.tree-row {
  display: flex; align-items: center; gap: 6px;
  padding: 5px 14px;
  font-size: 13px; color: #334155;
  border-top: 1px solid #f8fafc;
  transition: background .1s;
  white-space: nowrap;
  min-width: max-content;
}
.tr-dir  { cursor: pointer; }
.tr-dir:hover  { background: #f0f9ff; }
.tr-file:hover { background: #f8fafc; }
.tr-icon {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; flex-shrink: 0; color: #64748b;
}
.tr-icon svg { width: 14px; height: 14px; }
.tr-name {
  flex: 1; overflow: hidden; text-overflow: ellipsis;
}
.tr-dir .tr-name  { font-weight: 600; color: #0f172a; }
.tr-size { font-size: 11px; color: #94a3b8; font-family: 'Courier New', monospace; margin-left: 12px; }
.tr-date { font-size: 11px; color: #cbd5e1; margin-left: 8px; }

/* ── 分类 Tabs ── */
.tab-bar {
  display: flex; gap: 6px;
  padding: 14px 18px;
  flex-wrap: wrap;
}
.tab-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 14px;
  border: 1px solid #e2e8f0; border-radius: 8px;
  background: #fff; color: #64748b;
  font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all .15s;
}
.tab-btn:hover  { background: #f1f5f9; }
.tab-btn.active { background: #eff6ff; border-color: #bfdbfe; color: #2563eb; }
.tab-count {
  background: #e2e8f0; color: #64748b;
  font-size: 11px; padding: 1px 6px; border-radius: 10px; font-weight: 700;
}
.tab-btn.active .tab-count { background: #dbeafe; color: #2563eb; }

/* ── 文件面板 ── */
.file-panel {
  border-top: 1px solid #f1f5f9;
  overflow: hidden;
}

/* ── 世界存档卡片 ── */
.world-card {
  position: relative;
  display: flex; align-items: flex-start; gap: 6px;
  padding: 14px 18px 14px 42px;
  border-top: 1px solid #f1f5f9;
  transition: background .1s;
}
.world-card:first-child { border-top: none; }
.world-card:hover { background: #f8fafc; }
.wc-body { flex: 1; min-width: 0; }

.wc-head {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 6px;
}
.wc-icon {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; flex-shrink: 0;
  background: #eff6ff; border-radius: 6px;
}
.wc-icon svg { width: 16px; height: 16px; stroke: #3b82f6; }
.wc-name { font-size: 15px; font-weight: 700; color: #0f172a; flex: 1; }
.wc-size { font-size: 12px; color: #94a3b8; font-family: 'Courier New', monospace; }

.wc-dir {
  display: flex; align-items: center; gap: 6px;
  padding: 6px 10px;
  background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 7px;
  margin-bottom: 5px;
}
.wc-dir svg { width: 13px; height: 13px; color: #3b82f6; flex-shrink: 0; }
.wc-dir-path {
  font-size: 12px; color: #1d4ed8; font-family: 'Courier New', monospace;
  word-break: break-all;
}
.wc-meta { font-size: 12px; color: #94a3b8; }

/* ── 普通文件表格 ── */
.ft-head {
  display: grid; grid-template-columns: 1fr 110px 185px;
  background: #f8fafc; padding: 10px 18px;
  font-size: 11px; font-weight: 700; color: #94a3b8;
  letter-spacing: .05em; text-transform: uppercase;
}
.ft-row {
  display: grid; grid-template-columns: 1fr 110px 185px;
  padding: 11px 18px;
  border-top: 1px solid #f1f5f9;
  font-size: 13px; color: #0f172a;
  transition: background .1s;
}
.ft-row:hover  { background: #f8fafc; }
.ft-name  { display: flex; align-items: center; gap: 7px; font-weight: 500; }
.ft-icon  {
  display: inline-flex; align-items: center; justify-content: center;
  width: 16px; height: 16px; color: #64748b; flex-shrink: 0;
}
.ft-icon svg { width: 14px; height: 14px; stroke: currentColor; }
.ft-icon-db svg { stroke: currentColor; }
.ft-dir-badge {
  font-size: 10px; color: #64748b;
  background: #f1f5f9; border: 1px solid #e2e8f0;
  padding: 1px 6px; border-radius: 4px;
  font-family: 'Courier New', monospace;
  max-width: 160px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ft-size { color: #64748b; font-family: 'Courier New', monospace; font-size: 12px; }
.ft-date { color: #94a3b8; font-size: 12px; }

/* ── 各种状态 ── */
.loading-state {
  display: flex; flex-direction: column; align-items: center; gap: 14px;
  padding: 72px 0; color: #94a3b8; font-size: 14px;
}
.spinner {
  width: 34px; height: 34px;
  border: 3px solid #e2e8f0; border-top-color: #3b82f6;
  border-radius: 50%; animation: spin .8s linear infinite;
}
.empty-state {
  display: flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 48px 0; color: #94a3b8; font-size: 14px;
}
.empty-state p    { margin: 0; }
.empty-state-full {
  display: flex; flex-direction: column; align-items: center; gap: 14px;
  padding: 72px 0; color: #94a3b8;
}
.empty-big-icon {
  display: flex; align-items: center; justify-content: center;
  width: 58px; height: 58px; color: #94a3b8;
}
.empty-big-icon svg { width: 52px; height: 52px; }
.empty-state-full p { margin: 0; font-size: 14px; }
.btn-fetch {
  padding: 10px 28px; background: #2563eb; color: #fff;
  border: none; border-radius: 8px; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: background .15s;
}
.btn-fetch:hover:not(:disabled) { background: #1d4ed8; }

/* ── 行御复选框 ── */
.row-check {
  display: flex; align-items: center;
  padding: 0 4px 0 2px; flex-shrink: 0;
  cursor: pointer;
}
.row-check input[type=checkbox] {
  width: 15px; height: 15px; cursor: pointer;
  accent-color: #2563eb;
}
.world-check {
  position: absolute; top: 14px; left: 14px;
}

/* ── 插件行 ── */
.plugin-row {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding: 11px 18px;
  border-top: 1px solid #f1f5f9;
  transition: background .1s;
}
.plugin-row:first-child { border-top: none; }
.plugin-row:hover { background: #f8fafc; }
.pr-info  { display: flex; align-items: center; gap: 7px; flex: 1; min-width: 0; }
.pr-name  { font-size: 13px; font-weight: 600; color: #0f172a; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pr-right { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.pr-size  { font-size: 12px; color: #94a3b8; font-family: 'Courier New', monospace; white-space: nowrap; }
/* ── 配置文件行（带编辑列）── */
.cfg-head { grid-template-columns: 1fr 110px 185px 72px !important; }
.cfg-row  { grid-template-columns: 1fr 110px 185px 72px !important; }
.cfg-actions { display: flex; align-items: center; justify-content: flex-end; }
.cfg-edit-btn {
  padding: 3px 9px; border-radius: 5px; font-size: 12px; font-weight: 500;
  background: #f8fafc; color: #475569; border: 1px solid #e2e8f0;
  cursor: pointer; transition: all .12s;
}
.cfg-edit-btn:hover { background: #f1f5f9; border-color: #cbd5e1; }

/* ── 通用文件管理行 ── */
.mgmt-head {
  display: grid; grid-template-columns: 32px 1fr 90px 160px 48px;
  background: #f8fafc; padding: 10px 18px;
  font-size: 11px; font-weight: 700; color: #94a3b8;
  letter-spacing: .05em; text-transform: uppercase;
}
.mgmt-row {
  display: grid; grid-template-columns: 32px 1fr 90px 160px 48px;
  padding: 10px 18px; border-top: 1px solid #f1f5f9;
  font-size: 13px; color: #0f172a;
  align-items: center; transition: background .1s;
}
.mgmt-row:hover { background: #f8fafc; }
.mr-name { display: flex; align-items: center; gap: 7px; font-weight: 500; min-width: 0; overflow: hidden; }
.mr-size { color: #64748b; font-family: 'Courier New', monospace; font-size: 12px; }
.mr-date { color: #94a3b8; font-size: 12px; }
.mr-actions { display: flex; align-items: center; justify-content: center; }
.mr-edit-btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 28px; height: 24px;
  padding: 3px 7px; border-radius: 5px; font-size: 12px;
  background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0;
  cursor: pointer; transition: all .12s; line-height: 1;
  opacity: 0; white-space: nowrap;
}
.mr-edit-btn svg { width: 13px; height: 13px; }
.mgmt-row:hover .mr-edit-btn { opacity: 1; }
.mr-edit-btn:hover { background: #e0e7ff; color: #4338ca; border-color: #c7d2fe; }
.mr-edit-btn:disabled {
  opacity: .35;
  cursor: not-allowed;
  background: #f8fafc;
  color: #94a3b8;
}
.mr-db-btn {
  display: inline-flex !important; align-items: center; gap: 4px;
}
.mr-db-btn svg { width: 12px; height: 12px; }
.mr-db-btn:hover   { background: #fef3c7; color: #92400e; border-color: #fde68a; }

/* ── 底部选中工具栏 ── */
.sel-toolbar {
  position: fixed; bottom: 28px; right: 28px; z-index: 200;
  display: flex; align-items: center; gap: 14px;
  padding: 12px 20px;
  background: #1e293b; color: #fff;
  border-radius: 14px;
  box-shadow: 0 8px 32px rgba(0,0,0,.35);
  font-size: 14px;
}
.sel-count {
  font-weight: 600; white-space: nowrap;
  padding-right: 10px; border-right: 1px solid rgba(255,255,255,.2);
}
.sel-actions { display: flex; gap: 8px; }
.sel-btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 7px 16px; border-radius: 8px;
  font-size: 13px; font-weight: 500;
  cursor: pointer; border: 1px solid; transition: all .12s; white-space: nowrap;
}
.sel-btn svg { width: 13px; height: 13px; flex-shrink: 0; }
.sel-btn:disabled { opacity: .45; cursor: not-allowed; }
.sel-edit  { background: #fff; color: #2563eb; border-color: #bfdbfe; }
.sel-edit:hover  { background: #eff6ff; }
.sel-rename   { background: #fff7ed; color: #c2410c; border-color: #fed7aa; }
.sel-rename:hover   { background: #ffedd5; }
.sel-copy { background: #ecfdf5; color: #166534; border-color: #86efac; }
.sel-copy:hover { background: #dcfce7; }
.sel-del   { background: #dc2626; color: #fff; border-color: transparent; }
.sel-del:hover   { background: #b91c1c; }
.sel-clear { background: transparent; color: rgba(255,255,255,.7); border-color: rgba(255,255,255,.25); }
.sel-clear:hover { background: rgba(255,255,255,.1); color: #fff; }

/* ── 工具栏出入动画 ── */
.sel-bar-enter-active, .sel-bar-leave-active { transition: all .2s cubic-bezier(.34,1.56,.64,1); }
.sel-bar-enter-from, .sel-bar-leave-to { opacity: 0; transform: translateY(16px) scale(.95); }

/* ── 模态框公共底层 ── */
.modal-backdrop {
  position: fixed; inset: 0; z-index: 2000;
  background: rgba(15, 23, 42, .55);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}

/* ── 文件编辑模态框 ── */
.editor-modal {
  background: #fff; border-radius: 14px;
  width: 100%; max-width: 980px; height: min(90vh, 780px);
  display: flex; flex-direction: column;
  box-shadow: 0 25px 60px rgba(0,0,0,.25);
}
.em-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0; gap: 10px;
}
.em-title-row { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.em-filename { font-size: 15px; font-weight: 700; color: #0f172a; font-family: 'Courier New', monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.em-lang-badge {
  font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px;
  letter-spacing: .06em; flex-shrink: 0;
}
.em-json   { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
.em-binary { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.em-close {
  display: inline-flex; align-items: center; justify-content: center;
  width: 30px; height: 30px;
  background: none; border: none; font-size: 18px; color: #94a3b8;
  cursor: pointer; padding: 2px 6px; border-radius: 6px; transition: all .12s; line-height: 1; flex-shrink: 0;
}
.em-close svg { width: 16px; height: 16px; }
.em-close:hover { background: #f1f5f9; color: #0f172a; }
.em-loading { display: flex; align-items: center; gap: 12px; padding: 40px; color: #94a3b8; font-size: 14px; flex-shrink: 0; }
.em-error {
  display: flex; align-items: center; gap: 8px;
  margin: 10px 20px 0; padding: 10px 14px;
  background: #fff5f5; border: 1px solid #fecaca; border-radius: 8px;
  color: #dc2626; font-size: 13px; flex-shrink: 0;
}
.em-error svg { width: 15px; height: 15px; flex-shrink: 0; }
/* 二进制文件不可编辑提示 */
.em-binary-notice {
  display: flex; align-items: flex-start; gap: 16px;
  padding: 36px 28px; flex: 1;
}
.em-bi-icon {
  display: flex; align-items: center; justify-content: center;
  width: 52px; height: 52px; flex-shrink: 0;
  background: #f1f5f9; border-radius: 12px;
}
.em-bi-icon svg { width: 28px; height: 28px; stroke: #64748b; }
.em-bi-title { font-size: 16px; font-weight: 700; color: #0f172a; margin-bottom: 6px; }
.em-bi-hint  { font-size: 13px; color: #64748b; line-height: 1.6; }

.em-textarea {
  flex: 1; min-height: 360px;
  margin: 12px 16px; padding: 12px;
  border: 1px solid #e2e8f0; border-radius: 8px;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 13px; line-height: 1.6; color: #1e293b;
  resize: vertical; outline: none; background: #f8fafc;
  overflow-y: auto;
}
.em-textarea:focus { border-color: #93c5fd; background: #fff; }
.em-json-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.em-json-editor {
  position: relative;
  flex: 1;
  min-height: 320px;
  margin: 12px 16px 0;
  border: 1px solid #dbe3ef;
  border-radius: 8px;
  background: #0f172a;
  overflow: hidden;
}
.em-json-editor.invalid {
  border-color: #fca5a5;
  box-shadow: 0 0 0 3px rgba(248, 113, 113, 0.16);
}
.em-json-gutter {
  position: absolute;
  inset: 0 auto 0 0;
  z-index: 2;
  width: 48px;
  padding: 16px 0;
  box-sizing: border-box;
  overflow: hidden;
  border-right: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(15, 23, 42, 0.96);
  color: #64748b;
  font-family: 'Cascadia Code', 'SFMono-Regular', Consolas, monospace;
  font-size: 12px;
  line-height: 1.7875;
  text-align: right;
}
.em-json-gutter span {
  display: block;
  height: 21.45px;
  padding: 0 10px 0 4px;
  box-sizing: border-box;
}
.em-json-gutter span.error {
  color: #fecaca;
  background: rgba(248, 113, 113, 0.18);
  font-weight: 700;
}
.em-json-highlight,
.em-json-input {
  position: absolute;
  inset: 0;
  margin: 0;
  padding: 16px 18px 16px 64px;
  border: none;
  box-sizing: border-box;
  font-family: 'Cascadia Code', 'SFMono-Regular', Consolas, monospace;
  font-size: 13px;
  line-height: 1.65;
  tab-size: 2;
  white-space: pre;
  overflow: auto;
}
.em-json-highlight {
  color: #cbd5e1;
  pointer-events: none;
}
.em-json-highlight code {
  font: inherit;
}
.em-json-highlight :deep(.json-line) {
  display: block;
  width: max-content;
  min-width: 100%;
  min-height: 1.65em;
}
.em-json-highlight :deep(.json-line.is-error) {
  background: rgba(248, 113, 113, 0.16);
  box-shadow: inset 3px 0 0 #f87171;
}
.em-json-input {
  resize: none;
  outline: none;
  background: transparent;
  color: transparent;
  caret-color: #f8fafc;
  -webkit-text-fill-color: transparent;
}
.em-json-input::selection {
  background: rgba(59, 130, 246, 0.35);
}
.em-json-input::-webkit-scrollbar,
.em-json-highlight::-webkit-scrollbar {
  width: 10px;
  height: 10px;
}
.em-json-input::-webkit-scrollbar-thumb,
.em-json-highlight::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.35);
  border-radius: 999px;
}
.em-json-highlight :deep(.json-key) { color: #93c5fd; }
.em-json-highlight :deep(.json-string) { color: #86efac; }
.em-json-highlight :deep(.json-number) { color: #fbbf24; }
.em-json-highlight :deep(.json-bool) { color: #f0abfc; }
.em-json-highlight :deep(.json-null) { color: #94a3b8; }
.em-json-highlight :deep(.json-muted) { color: #64748b; }
.em-json-err {
  padding: 10px 14px;
  font-size: 12.5px;
  line-height: 1.5;
  color: #b91c1c;
  background: #fef2f2;
  border-top: 1px solid #fecaca;
  white-space: pre-wrap;
  flex-shrink: 0;
}
.em-json-err-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
}
.em-json-err-msg {
  color: #7f1d1d;
}
.em-json-err-meta {
  margin-top: 2px;
  margin-bottom: 4px;
  color: #991b1b;
}
.em-json-err-jump {
  flex-shrink: 0;
  border: 1px solid #f87171;
  background: #fff;
  color: #b91c1c;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 12px;
  cursor: pointer;
}
.em-json-err-jump:hover {
  background: #fee2e2;
}
.em-json-err-context {
  font-family: ui-monospace, 'SFMono-Regular', Consolas, monospace;
  background: #fff;
  border: 1px solid #fecaca;
  border-radius: 6px;
  padding: 6px 0;
  margin-top: 8px;
  overflow-x: auto;
  font-size: 12px;
}
.em-json-err-row {
  display: flex;
  min-width: max-content;
  color: #111827;
  white-space: pre;
}
.em-json-err-row.error {
  background: #fee2e2;
}
.em-json-err-row code {
  font: inherit;
}
.em-json-err-no {
  width: 42px;
  padding: 0 8px;
  box-sizing: border-box;
  text-align: right;
  color: #94a3b8;
  user-select: none;
}
.em-json-err-caret code {
  color: #dc2626;
  font-weight: 700;
  line-height: 1;
}
.em-footer {
  display: flex; gap: 10px; align-items: center;
  padding: 14px 20px; border-top: 1px solid #e2e8f0; flex-shrink: 0;
}
.em-fmt-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 16px; background: #f8fafc; color: #475569;
  border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all .12s; white-space: nowrap;
}
.em-fmt-btn svg { width: 14px; height: 14px; flex-shrink: 0; }
.em-fmt-btn:hover:not(:disabled) { background: #f0fdf4; color: #16a34a; border-color: #86efac; }
.em-fmt-btn:disabled { opacity: .5; cursor: not-allowed; }
.em-save {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 9px 22px; background: #2563eb; color: #fff;
  border: none; border-radius: 8px; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: background .12s;
}
.em-save:hover:not(:disabled) { background: #1d4ed8; }
.em-save:disabled { opacity: .5; cursor: not-allowed; }
.em-cancel {
  padding: 9px 22px; background: #f1f5f9; color: #475569;
  border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px;
  cursor: pointer; transition: all .12s;
}
.em-cancel:hover:not(:disabled) { background: #e2e8f0; }
.em-cancel:disabled { opacity: .5; cursor: not-allowed; }

/* ── 删除确认模态框 ── */
.confirm-modal {
  background: #fff; border-radius: 14px;
  width: 100%; max-width: 420px; padding: 32px 28px;
  text-align: center; box-shadow: 0 25px 60px rgba(0,0,0,.25);
}
.cm-icon {
  display: flex; align-items: center; justify-content: center;
  width: 56px; height: 56px; margin: 0 auto 14px;
  background: #fef2f2; border-radius: 14px;
}
.cm-icon svg { width: 28px; height: 28px; stroke: #dc2626; }
.cm-icon-ok { background: #f0fdf4; }
.cm-icon-ok svg { stroke: #16a34a; }
.cm-title { font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 10px; }
.cm-body  { font-size: 14px; color: #64748b; line-height: 1.6; margin-bottom: 24px; }
.cm-body strong { color: #0f172a; font-family: 'Courier New', monospace; }
.cm-footer { display: flex; gap: 10px; justify-content: center; }
.cm-del {
  padding: 10px 24px; background: #dc2626; color: #fff;
  border: none; border-radius: 8px; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: background .12s;
}
.cm-del:hover:not(:disabled) { background: #b91c1c; }
.cm-del:disabled { opacity: .5; cursor: not-allowed; }
.cm-cancel {
  padding: 10px 24px; background: #f1f5f9; color: #475569;
  border: 1px solid #e2e8f0; border-radius: 8px; font-size: 14px;
  cursor: pointer; transition: all .12s;
}
.cm-cancel:hover:not(:disabled) { background: #e2e8f0; }
.cm-cancel:disabled { opacity: .5; cursor: not-allowed; }

.path-modal {
  text-align: left;
}

.path-input {
  width: 100%;
  box-sizing: border-box;
  margin-bottom: 16px;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 13px;
  color: #0f172a;
  outline: none;
}

.path-input:focus {
  border-color: #93c5fd;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, .12);
}

/* ── 响应式 ── */
@media (max-width: 700px) {
  .files-view { padding: 14px; }
  .ft-head, .ft-row { grid-template-columns: 1fr 80px; }
  .ft-head span:last-child, .ft-row .ft-date { display: none; }
  .fh-dir { max-width: 200px; }
}
</style>
