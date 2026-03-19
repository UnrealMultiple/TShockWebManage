<template>
  <div class="files-view">
    <!-- 头部 -->
    <div class="files-header">
      <div class="fh-left">
        <h2 class="fh-title">文件概览</h2>
        <span class="fh-server" v-if="activeServer">{{ activeServer.name }}</span>
        <span class="fh-dir" v-if="serverDir" :title="serverDir">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          {{ serverDir }}
        </span>
      </div>
      <button class="refresh-btn" @click="requestFileList" :disabled="loading || !agentOnline || !activeServerKey">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ spinning: loading }">
          <polyline points="1 4 1 10 7 10"/>
          <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
        </svg>
        {{ loading ? '加载中…' : '刷新' }}
      </button>
    </div>

    <!-- Agent 未连接提示 -->
    <div v-if="!agentOnline" class="offline-notice">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="8" x2="12" y2="12"/>
        <line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      <span>Agent 未连接，无法获取文件列表。请先确保服务器已启动。</span>
    </div>

    <template v-else>
      <!-- 加载中 -->
      <div v-if="loading && !treeData" class="loading-state">
        <div class="spinner"></div>
        <span>正在从服务器获取文件列表…</span>
      </div>

      <!-- 初始空状态 -->
      <div v-else-if="!treeData" class="empty-state-full">
        <div class="empty-big-icon">📁</div>
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
                  {{ expandedDirs.has(item.path) ? '📂' : '📁' }}
                </template>
                <template v-else>{{ fileIcon(item.name) }}</template>
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
              {{ catIcon(cat.key) }} {{ cat.name }}
              <span class="tab-count">{{ cat.files.length }}</span>
            </button>
          </div>

          <div class="file-panel" v-if="currentCategory">
            <div v-if="currentCategory.files.length === 0" class="empty-state">
              <span>📭</span>
              <p>该分类下暂无文件</p>
            </div>

            <!-- 插件列表 -->
            <template v-else-if="activeTab === 'plugins'">
              <div v-for="f in currentCategory.files" :key="f.name" class="plugin-row">
                <label class="row-check">
                  <input type="checkbox" :value="f.full_path || f.name" v-model="selectedPaths">
                </label>
                <div class="pr-info">
                  <span class="ft-icon">🔧</span>
                  <span class="pr-name">{{ f.name }}</span>
                  <span v-if="f.dir" class="ft-dir-badge" :title="f.dir">{{ shortDir(f.dir) }}</span>
                </div>
                <div class="pr-right">
                  <span class="pr-size">{{ formatBytes(f.size) }}</span>
                  <div class="pr-actions">
                    <button class="pr-btn pr-enable"  @click="enablePlugin(f)">启用</button>
                    <button class="pr-btn pr-disable" @click="disablePlugin(f)">关闭</button>
                    <button class="pr-btn pr-cfg"     @click="editPluginConfig(f)">编辑配置文件</button>
                  </div>
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
                  <button class="mr-edit-btn mr-db-btn" @click.stop="openDbBrowser(f)">
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
                  <span class="ft-icon">{{ fileIcon(f.name) }}</span>
                  {{ f.name }}
                  <span v-if="f.dir" class="ft-dir-badge" :title="f.dir">{{ shortDir(f.dir) }}</span>
                </span>
                <span class="mr-size">{{ formatBytes(f.size) }}</span>
                <span class="mr-date">{{ f.modified }}</span>
                <span class="mr-actions">
                  <button class="mr-edit-btn" @click.stop="editFile(f)" title="编辑文件">✏️</button>
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
            @click="editSingleSelected">✏️ 编辑</button>
          <button class="sel-btn sel-rename"
            v-if="selectedPaths.length === 1"
            @click="openRenameDialog">🏷 重命名</button>
          <button class="sel-btn sel-copy"
            v-if="selectedPaths.length === 1"
            @click="openCopyDialog">📄 复制</button>
          <button class="sel-btn sel-del" @click="deleteSelected">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg>
            删除
          </button>
          <button class="sel-btn sel-clear" @click="selectedPaths = []">清空</button>
        </div>
      </div>
    </transition>

    <!-- ── 数据库浏览器（可视化编辑） ── -->
    <div class="modal-backdrop" v-if="dbBrowserFile" @click.self="closeDbBrowser">
      <div class="db-modal">
        <!-- 顶部标题栏 -->
        <div class="db-header">
          <div class="db-title-row">
            <span class="db-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
            </span>
            <span class="db-filename">{{ dbBrowserFile.name }}</span>
            <span class="db-badge">SQLite</span>
          </div>
          <div class="db-header-tabs">
            <button :class="['db-view-btn', { active: dbViewMode === 'table' }]" @click="dbViewMode = 'table'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/></svg>
              表格
            </button>
            <button :class="['db-view-btn', { active: dbViewMode === 'sql' }]" @click="dbViewMode = 'sql'">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
              SQL
            </button>
          </div>
          <button class="em-close" @click="closeDbBrowser">✕</button>
        </div>

        <!-- 主体：侧边栏 + 内容区 -->
        <div class="db-body">
          <!-- 左侧表列表 -->
          <div class="db-sidebar">
            <div class="db-sidebar-hd">
              <span>数据表</span>
              <div v-if="dbTablesLoading" class="spinner" style="width:12px;height:12px;border-width:2px;flex-shrink:0"></div>
            </div>
            <div v-if="dbTablesErr" class="db-sidebar-err">{{ dbTablesErr }}</div>
            <button v-for="t in dbTables" :key="t"
              :class="['db-tbl-item', { active: dbActiveTable === t }]"
              @click="selectTable(t)">🗋 {{ t }}</button>
            <div v-if="!dbTablesLoading && dbTables.length === 0 && !dbTablesErr" class="db-sidebar-empty">暂无表</div>
          </div>

          <!-- 右侧主内容区 -->
          <div class="db-main">

            <!-- SQL 模式 -->
            <template v-if="dbViewMode === 'sql'">
              <div class="db-sql-wrap">
                <textarea class="db-sql-input" v-model="dbSqlInput" rows="3"
                  placeholder="输入 SQL（SELECT … 或 INSERT / UPDATE / DELETE），Ctrl+Enter 执行"
                  @keydown.ctrl.enter.prevent="runDbSql"></textarea>
                <div class="db-sql-btns">
                  <button class="db-run-btn" @click="runDbSql" :disabled="dbRunning">{{ dbRunning ? '执行中…' : '▶ 执行' }}</button>
                  <button class="db-clear-btn" @click="dbSqlInput = ''; dbResult = null; dbResultErr = ''">✕ 清空</button>
                </div>
              </div>
              <div class="db-result-area">
                <div v-if="dbRunning" class="db-result-loading"><div class="spinner" style="width:24px;height:24px;border-width:2px"></div><span>执行中…</span></div>
                <div v-else-if="dbResultErr" class="db-result-err">⚠️ {{ dbResultErr }}</div>
                <template v-else-if="dbResult">
                  <div v-if="dbResult.type === 'query'">
                    <div class="db-result-meta">返回 <strong>{{ dbResult.rows.length }}</strong> 行<span v-if="dbResult.truncated" class="db-truncated-hint">（已截断，最多 500 行）</span></div>
                    <div class="db-table-wrap">
                      <table class="db-table">
                        <thead><tr><th v-for="c in dbResult.columns" :key="c">{{ c }}</th></tr></thead>
                        <tbody>
                          <tr v-for="(row, ri) in dbResult.rows" :key="ri">
                            <td v-for="(cell, ci) in row" :key="ci" :class="{ 'db-null': cell === null }">{{ cell === null ? 'NULL' : cell }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                  <div v-else-if="dbResult.type === 'exec'" class="db-exec-ok">✅ 执行成功，影响 <strong>{{ dbResult.affected }}</strong> 行</div>
                </template>
                <div v-else class="db-result-empty">在上方输入 SQL 后按"▶ 执行"或 Ctrl+Enter</div>
              </div>
            </template>

            <!-- 表格可视化模式 -->
            <template v-else>
              <div v-if="!dbActiveTable" class="db-no-table">← 从左侧选择数据表</div>
              <template v-else>
                <!-- 工具栏 -->
                <div class="db-tbl-toolbar">
                  <span class="db-tbl-name">{{ dbActiveTable }}</span>
                  <span v-if="dbTableCols.length" class="db-col-badge">{{ dbTableCols.length }} 列</span>
                  <span class="db-spacer"></span>
                  <span v-if="dbResultErr" class="db-tbl-err">⚠️ {{ dbResultErr }}</span>
                  <button class="db-add-row-btn" @click="startAddRow" :disabled="dbTableLoading">+ 添加行</button>
                  <button class="db-pg-btn" @click="dbPagePrev" :disabled="dbPage === 0 || dbTableLoading">‹</button>
                  <span class="db-pg-info">第 {{ dbPage + 1 }} 页</span>
                  <button class="db-pg-btn" @click="dbPageNext" :disabled="!dbHasMore || dbTableLoading">›</button>
                  <button class="db-reload-btn" @click="loadTableData" :disabled="dbTableLoading" title="刷新">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:13px;height:13px"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.18"/></svg>
                  </button>
                </div>

                <!-- 可视化数据表格 -->
                <div class="db-visual-wrap">
                  <div v-if="dbTableLoading" class="db-result-loading">
                    <div class="spinner" style="width:24px;height:24px;border-width:2px"></div><span>加载中…</span>
                  </div>
                  <table v-else class="db-visual-table">
                    <thead>
                      <tr>
                        <th v-for="col in dbTableCols" :key="col.name" class="db-vth">
                          <span class="db-col-nm">{{ col.name }}</span>
                          <span class="db-col-tp">{{ col.type }}</span>
                          <span v-if="col.pk" class="db-pk">PK</span>
                        </th>
                        <th class="db-ops-th">操作</th>
                      </tr>
                    </thead>
                    <tbody>
                      <!-- 新增行表单 -->
                      <tr v-if="dbAddRowMode" class="db-add-row-tr">
                        <td v-for="col in dbTableCols" :key="col.name" class="db-add-td">
                          <input class="db-cell-inp" v-model="dbNewRowValues[col.name]" :placeholder="col.dflt ?? col.type" />
                        </td>
                        <td class="db-ops-cell">
                          <button class="db-ok-btn" @click="confirmAddRow" :disabled="dbAddRowSaving">✓</button>
                          <button class="db-cx-btn" @click="dbAddRowMode = false">✕</button>
                        </td>
                      </tr>
                      <!-- 数据行 -->
                      <tr v-for="(row, ri) in dbTableRows" :key="row[0]">
                        <td v-for="(col, ci) in dbTableCols" :key="col.name"
                          :class="['db-vtd', { 'db-null': row[ci+1] === null, 'db-cell-active': dbEditCell && dbEditCell.rowIdx === ri && dbEditCell.colIdx === ci }]"
                          @dblclick="startEditCell(ri, ci, row[ci+1])">
                          <template v-if="dbEditCell && dbEditCell.rowIdx === ri && dbEditCell.colIdx === ci">
                            <input class="db-cell-inp db-cell-inp-edit" v-model="dbEditCell.value"
                              @keydown.enter.prevent="saveEditCell"
                              @keydown.escape="cancelEditCell"
                              @blur="saveEditCell"
                              ref="dbCellInputRef" />
                          </template>
                          <template v-else>
                            <span class="db-cv">{{ row[ci+1] === null ? 'NULL' : row[ci+1] }}</span>
                          </template>
                        </td>
                        <td class="db-ops-cell">
                          <button class="db-del-row-btn" @click="deleteRow(ri, row[0])" title="删除此行">🗑</button>
                        </td>
                      </tr>
                      <tr v-if="dbTableRows.length === 0 && !dbTableLoading">
                        <td :colspan="dbTableCols.length + 1" class="db-empty-row">该表暂无数据</td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </template>
            </template>

          </div>
        </div>
      </div>
    </div>

    <!-- ── 文件编辑模态框 ── -->
    <div class="modal-backdrop" v-if="editingFile" @click.self="closeEditor">
      <div class="editor-modal">
        <div class="em-header">
          <div class="em-title-row">
            <span class="em-filename">{{ editingFile.name }}</span>
            <span v-if="isEditingJson" class="em-lang-badge em-json">JSON</span>
            <span v-else-if="isEditingBinary" class="em-lang-badge em-binary">二进制</span>
          </div>
          <button class="em-close" @click="closeEditor">✕</button>
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
          <div v-if="editorError" class="em-error">⚠️ {{ editorError }}</div>
          <div v-if="isEditingJson && jsonValidErr" class="em-json-warn">
            ⚠️ JSON 错误：{{ jsonValidErr }}
            <button v-if="jsonErrLine > 0" class="em-jump-btn" @click="jumpToErrorLine">跳转到第 {{ jsonErrLine }} 行</button>
          </div>
          <textarea class="em-textarea" v-model="editContent" spellcheck="false"
            @input="isEditingJson && validateJson()"></textarea>
          <div class="em-footer">
            <button v-if="isEditingJson" class="em-fmt-btn" @click="formatJson" :disabled="editorSaving">🔧 格式化</button>
            <span style="flex:1"></span>
            <button class="em-save" @click="saveFile" :disabled="editorSaving">
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
          <button class="cm-del" @click="doDelete" :disabled="deleteBusy">{{ deleteBusy ? '删除中…' : '确认删除' }}</button>
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
          <button class="cm-del" @click="startBatchDelete">确认删除</button>
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
        <div class="cm-icon">✅</div>
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
          <button class="cm-del" @click="confirmPathDialog">确认</button>
          <button class="cm-cancel" @click="closePathDialog">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps({
  wsState:     { type: String, default: 'disconnected' },
  agentOnline: { type: Boolean, default: false },
})

const activeServer    = inject('activeServer',    ref(null))
const activeServerKey = inject('activeServerKey', ref(''))

const loading         = ref(false)
const treeData        = ref(null)
const categories      = ref([])
const serverDir       = ref('')
const activeTab       = ref('')
const treeSectionOpen = ref(false)
const expandedDirs    = ref(new Set())

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
  const f = selectedFiles.value[0]
  if (!f) return
  editFile(f)
  selectedPaths.value = []
}

function openRenameDialog() {
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
  const f = selectedFiles.value[0]
  if (!f) return
  const text = (pathDialogInput.value || '').trim()
  if (!text) return
  const baseDir = getSafeBaseDir()
  if (!baseDir) { alert('请先点击刷新，获取服务器目录后再操作'); return }
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

function toAbsolutePath(input, baseDir) {
  const raw = (input || '').trim()
  if (!raw) return ''
  if (/^[a-zA-Z]:[\\/]/.test(raw) || raw.startsWith('\\\\')) return raw
  const normalizedBase = (baseDir || '').replace(/[\\/]+$/, '')
  if (!normalizedBase) return raw
  return `${normalizedBase}\\${raw.replace(/^[\\/]+/, '')}`
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
  batchDeleteBusy.value  = true
  batchDeleteQueue.value = batchDeleteTarget.value.map(f => f.full_path || f.name)
  sendNextDelete()
}

function sendNextDelete() {
  const path = batchDeleteQueue.value.shift()
  if (!path) { batchDeleteDone.value = true; batchDeleteBusy.value = false; return }
  window.__tshockSend?.({
    type: 'file_delete', msg_id: Date.now().toString(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path, _batch: true },
  })
}

// ── 数据库浏览器状态 ──
const dbBrowserFile   = ref(null)
const dbTables        = ref([])
const dbTablesLoading = ref(false)
const dbTablesErr     = ref('')
const dbActiveTable   = ref('')
const dbSqlInput      = ref('')
const dbRunning       = ref(false)
const dbResult        = ref(null)
const dbResultErr     = ref('')
const dbViewMode      = ref('table')    // 'table' | 'sql'
const dbTableCols     = ref([])         // [{cid,name,type,notnull,dflt,pk}]
const dbTableRows     = ref([])         // rows[ri][0]=rowid, [1..]=data
const dbTableLoading  = ref(false)
const dbHasMore       = ref(false)
const dbPage          = ref(0)
const dbPageSize      = 200
const dbEditCell      = ref(null)       // {rowIdx,colIdx,value,orig}
const dbEditSaving    = ref(false)
const dbAddRowMode    = ref(false)
const dbNewRowValues  = ref({})
const dbAddRowSaving  = ref(false)
const dbCellInputRef  = ref(null)

function openDbBrowser(f) {
  dbBrowserFile.value  = f
  dbTables.value       = []
  dbTablesLoading.value = true
  dbTablesErr.value    = ''
  dbActiveTable.value  = ''
  dbSqlInput.value     = ''
  dbResult.value       = null
  dbResultErr.value    = ''
  dbViewMode.value     = 'table'
  dbTableCols.value    = []
  dbTableRows.value    = []
  dbTableLoading.value = false
  dbHasMore.value      = false
  dbPage.value         = 0
  dbEditCell.value     = null
  dbAddRowMode.value   = false
  window.__tshockSend?.({
    type: 'db_query', msg_id: 'dbtables-' + Date.now(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: f.full_path,
      sql: "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name" },
  })
}

function closeDbBrowser() {
  dbBrowserFile.value = null; dbTables.value = []; dbResult.value = null
  dbTableCols.value = []; dbTableRows.value = []; dbEditCell.value = null
}

function selectTable(t) {
  dbActiveTable.value  = t
  dbViewMode.value     = 'table'
  dbPage.value         = 0
  dbEditCell.value     = null
  dbAddRowMode.value   = false
  dbResultErr.value    = ''
  dbTableCols.value    = []
  dbTableRows.value    = []
  dbTableLoading.value = true
  const safeT = t.replace(/"/g, '""')
  window.__tshockSend?.({
    type: 'db_query', msg_id: 'dbinfo-' + Date.now(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: dbBrowserFile.value.full_path,
      sql: `PRAGMA table_info("${safeT}")` },
  })
  loadTableData()
}

function loadTableData() {
  if (!dbActiveTable.value || !dbBrowserFile.value) return
  dbTableLoading.value = true
  const safeT  = dbActiveTable.value.replace(/"/g, '""')
  const offset = dbPage.value * dbPageSize
  window.__tshockSend?.({
    type: 'db_query', msg_id: 'dbdata-' + Date.now(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: dbBrowserFile.value.full_path,
      sql: `SELECT rowid AS __rowid__, * FROM "${safeT}" LIMIT ${dbPageSize + 1} OFFSET ${offset}` },
  })
}

function dbPagePrev() { if (dbPage.value > 0)    { dbPage.value--; loadTableData() } }
function dbPageNext() { if (dbHasMore.value)       { dbPage.value++; loadTableData() } }

function startEditCell(ri, ci, val) {
  if (dbEditSaving.value) return
  dbEditCell.value = { rowIdx: ri, colIdx: ci, value: val === null ? '' : String(val), orig: val }
  nextTick(() => {
    const inp = dbCellInputRef.value
    ;(Array.isArray(inp) ? inp[0] : inp)?.focus?.()
  })
}

function cancelEditCell() { dbEditCell.value = null }

function saveEditCell() {
  if (!dbEditCell.value || !dbBrowserFile.value) return
  const { rowIdx, colIdx, value, orig } = dbEditCell.value
  const newVal = value === '' ? null : value
  if (String(newVal) === String(orig) || (newVal === null && orig === null)) {
    dbEditCell.value = null; return
  }
  const row   = dbTableRows.value[rowIdx]
  const col   = dbTableCols.value[colIdx]?.name
  const rowid = row?.[0]
  if (!col) { dbEditCell.value = null; return }
  dbEditSaving.value = true
  window.__tshockSend?.({
    type: 'db_update_row', msg_id: 'dbedit-' + Date.now(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: dbBrowserFile.value.full_path,
      table: dbActiveTable.value, rowid, col, value: newVal },
  })
}

function deleteRow(rowIdx, rowid) {
  if (!confirm('确认删除此行？')) return
  dbTableRows.value.splice(rowIdx, 1)
  window.__tshockSend?.({
    type: 'db_delete_row', msg_id: 'dbdel-' + Date.now(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: dbBrowserFile.value.full_path,
      table: dbActiveTable.value, rowid },
  })
}

function startAddRow() {
  dbAddRowMode.value = true
  const vals = {}
  dbTableCols.value.forEach(c => { vals[c.name] = '' })
  dbNewRowValues.value = vals
}

function confirmAddRow() {
  if (!dbBrowserFile.value) return
  dbAddRowSaving.value = true
  const cols = dbTableCols.value.map(c => c.name).filter(c => dbNewRowValues.value[c] !== '')
  const vals = cols.map(c => { const v = dbNewRowValues.value[c]; return v === '' ? null : v })
  window.__tshockSend?.({
    type: 'db_insert_row', msg_id: 'dbins-' + Date.now(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: dbBrowserFile.value.full_path,
      table: dbActiveTable.value, cols, values: vals },
  })
}

function runDbSql() {
  if (!dbSqlInput.value.trim() || !dbBrowserFile.value) return
  dbRunning.value   = true
  dbResultErr.value = ''
  dbResult.value    = null
  const sql = dbSqlInput.value.trim()
  const isSelect = /^\s*select\b/i.test(sql)
  window.__tshockSend?.({
    type: isSelect ? 'db_query' : 'db_exec',
    msg_id: 'dbrun-' + Date.now(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: dbBrowserFile.value.full_path, sql },
  })
}

// ── 编辑器状态 ──
const editingFile    = ref(null)
const editContent    = ref('')
const editorLoading  = ref(false)
const editorSaving   = ref(false)
const editorError    = ref('')
const editorIsBinary = ref(false)
const jsonValidErr   = ref('')
const jsonErrLine    = ref(0)

const isEditingJson   = computed(() =>
  editingFile.value?.name?.toLowerCase().endsWith('.json') ?? false
)
const isEditingBinary = computed(() => editorIsBinary.value)

function validateJson() {
  if (!editContent.value.trim()) { jsonValidErr.value = ''; jsonErrLine.value = 0; return }
  try   { JSON.parse(editContent.value); jsonValidErr.value = ''; jsonErrLine.value = 0 }
  catch (e) {
    jsonValidErr.value = e.message
    const m = e.message.match(/line (\d+)/i)
    jsonErrLine.value = m ? parseInt(m[1]) : 0
  }
}

function jumpToErrorLine() {
  if (!jsonErrLine.value) return
  const ta = document.querySelector('.em-textarea')
  if (!ta) return
  const lines = editContent.value.split('\n')
  let pos = 0
  for (let i = 0; i < Math.min(jsonErrLine.value - 1, lines.length); i++)
    pos += lines[i].length + 1
  ta.focus()
  ta.setSelectionRange(pos, pos + (lines[jsonErrLine.value - 1]?.length ?? 0))
  const lineH = ta.scrollHeight / (lines.length || 1)
  ta.scrollTop = (jsonErrLine.value - 3) * lineH
}

function formatJson() {
  try {
    const parsed = JSON.parse(editContent.value)
    editContent.value = JSON.stringify(parsed, null, 2)
    jsonValidErr.value = ''
  } catch (e) {
    jsonValidErr.value = e.message
    editorError.value  = 'JSON 格式错误，无法格式化：' + e.message
  }
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

function catIcon(key) {
  return { worlds: '🌍', configs: '⚙️', logs: '📋', plugins: '🧩', databases: '🗄️' }[key] ?? '📁'
}

function fileIcon(name) {
  if (!name) return '📃'
  const ext = name.split('.').pop()?.toLowerCase()
  if (ext === 'wld')                                      return '🌐'
  if (ext === 'json')                                     return '📄'
  if (ext === 'txt' || ext === 'log')                     return '📝'
  if (ext === 'dll')                                      return '🔧'
  if (ext === 'exe')                                      return '⚙️'
  if (['zip','rar','7z'].includes(ext))                   return '📦'
  if (['sqlite','db','db3'].includes(ext))                return '🗄️'
  return '📃'
}

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

// ── 插件操作（功能暂留空）──
function enablePlugin(_f)     { /* TODO */ }
function disablePlugin(_f)    { /* TODO */ }
function editPluginConfig(_f) { /* TODO */ }

// ── 通用文件管理 ──
function editFile(f) {
  editingFile.value    = f
  editContent.value    = ''
  editorError.value    = ''
  editorIsBinary.value = false
  jsonValidErr.value   = ''
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
  jsonErrLine.value    = 0
  editorLoading.value  = false
}

function saveFile() {
  if (!editingFile.value) return
  // JSON 保存前校验语法
  if (isEditingJson.value) {
    try { JSON.parse(editContent.value) }
    catch (e) { editorError.value = 'JSON 语法错误，请修正后再保存：' + e.message; return }
  }
  editorSaving.value = true
  editorError.value  = ''
  window.__tshockSend?.({
    type: 'file_write', msg_id: Date.now().toString(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, path: editingFile.value.full_path, content: editContent.value },
  })
}

function deleteFile(f) {
  deleteTarget.value = f
}

function doDelete() {
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

  if (pkt.type === 'db_query_resp') {
    const refId = p.ref_id ?? ''
    if (refId.startsWith('dbtables-')) {
      dbTablesLoading.value = false
      if (p.success) {
        dbTables.value    = (p.rows || []).map(r => r[0])
        dbTablesErr.value = ''
        if (dbTables.value.length > 0) selectTable(dbTables.value[0])
      } else {
        dbTablesErr.value = p.msg || '获取表列表失败'
      }
    } else if (refId.startsWith('dbinfo-')) {
      if (p.success)
        dbTableCols.value = (p.rows || []).map(r => ({ cid: r[0], name: r[1], type: r[2] || '', notnull: r[3], dflt: r[4], pk: r[5] }))
    } else if (refId.startsWith('dbdata-')) {
      dbTableLoading.value = false
      if (p.success) {
        const rows = p.rows || []
        dbHasMore.value   = rows.length > dbPageSize
        dbTableRows.value = dbHasMore.value ? rows.slice(0, dbPageSize) : rows
      } else {
        dbResultErr.value = p.msg || '查询失败'
      }
    } else {
      dbRunning.value = false
      if (p.success) { dbResult.value = { type: 'query', columns: p.columns, rows: p.rows, truncated: p.truncated }; dbResultErr.value = '' }
      else           { dbResultErr.value = p.msg || '查询失败' }
    }
    return
  }

  if (pkt.type === 'db_exec_resp') {
    dbRunning.value = false
    if (p.success) { dbResult.value = { type: 'exec', affected: p.affected }; dbResultErr.value = '' }
    else           { dbResultErr.value = p.msg || '执行失败' }
    return
  }

  if (pkt.type === 'db_update_row_resp') {
    dbEditSaving.value = false
    if (p.success) {
      const ec = dbEditCell.value
      if (ec && dbTableRows.value[ec.rowIdx]) {
        const row = [...dbTableRows.value[ec.rowIdx]]
        row[ec.colIdx + 1] = ec.value === '' ? null : ec.value
        dbTableRows.value[ec.rowIdx] = row
      }
      dbEditCell.value = null
    } else {
      dbEditCell.value  = null
      dbResultErr.value = p.msg || '更新失败'
    }
    return
  }

  if (pkt.type === 'db_delete_row_resp') {
    if (!p.success) { dbResultErr.value = p.msg || '删除失败'; loadTableData() }
    return
  }

  if (pkt.type === 'db_insert_row_resp') {
    dbAddRowSaving.value = false
    if (p.success) { dbAddRowMode.value = false; dbNewRowValues.value = {}; loadTableData() }
    else           { dbResultErr.value = p.msg || '插入失败' }
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
      alert(p.msg || '操作失败')
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

/* ── 头部 ── */
.files-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 12px;
  flex-wrap: wrap;
}
.fh-left  { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.fh-title { margin: 0; font-size: 20px; font-weight: 700; color: #0f172a; }
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


/* ── 离线提示 ── */
.offline-notice {
  display: flex; align-items: center; gap: 12px;
  padding: 20px 24px;
  background: #fffbeb; border: 1px solid #fde68a; border-radius: 12px;
  color: #92400e; font-size: 14px;
}
.offline-notice svg { width: 20px; height: 20px; flex-shrink: 0; color: #f59e0b; }

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
.tr-icon { font-size: 14px; flex-shrink: 0; }
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
.ft-icon  { font-size: 14px; display: flex; align-items: center; }
.ft-icon-db { width: 16px; height: 16px; }
.ft-icon-db svg { width: 14px; height: 14px; stroke: #64748b; }
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
.empty-state span { font-size: 28px; }
.empty-state p    { margin: 0; }
.empty-state-full {
  display: flex; flex-direction: column; align-items: center; gap: 14px;
  padding: 72px 0; color: #94a3b8;
}
.empty-big-icon   { font-size: 52px; }
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
.pr-actions { display: flex; gap: 6px; }
.pr-btn {
  padding: 4px 10px; border-radius: 6px; font-size: 12px; font-weight: 500;
  cursor: pointer; border: 1px solid; transition: all .12s; white-space: nowrap;
}
.pr-enable  { background: #f0fdf4; color: #16a34a; border-color: #bbf7d0; }
.pr-enable:hover  { background: #dcfce7; }
.pr-disable { background: #fff7ed; color: #ea580c; border-color: #fed7aa; }
.pr-disable:hover { background: #ffedd5; }
.pr-cfg     { background: #eff6ff; color: #2563eb; border-color: #bfdbfe; }
.pr-cfg:hover     { background: #dbeafe; }

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
  padding: 3px 7px; border-radius: 5px; font-size: 12px;
  background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0;
  cursor: pointer; transition: all .12s; line-height: 1;
  opacity: 0; white-space: nowrap;
}
.mgmt-row:hover .mr-edit-btn { opacity: 1; }
.mr-edit-btn:hover { background: #e0e7ff; color: #4338ca; border-color: #c7d2fe; }
.mr-db-btn {
  display: inline-flex !important; align-items: center; gap: 4px;
}
.mr-db-btn svg { width: 12px; height: 12px; }
.mr-db-btn:hover   { background: #fef3c7; color: #92400e; border-color: #fde68a; }

/* ── JSON 跳转按钮 ── */
.em-json-warn {
  margin: 8px 20px 0; padding: 8px 14px;
  background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px;
  color: #92400e; font-size: 12px; flex-shrink: 0;
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
}
.em-jump-btn {
  padding: 3px 10px; border-radius: 5px; font-size: 11px; font-weight: 600;
  background: #fbbf24; color: #78350f; border: none; cursor: pointer;
  white-space: nowrap; transition: background .12s; flex-shrink: 0;
}
.em-jump-btn:hover { background: #f59e0b; }

/* ── 数据库浏览器（可视化/SQL 双模式） ── */
.db-modal {
  background: #fff; border-radius: 14px;
  width: min(95vw, 1160px); height: min(88vh, 800px);
  display: flex; flex-direction: column;
  box-shadow: 0 25px 60px rgba(0,0,0,.25);
}
.db-header {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 18px; border-bottom: 1px solid #e2e8f0; flex-shrink: 0;
}
.db-title-row { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.db-icon {
  display: flex; align-items: center; justify-content: center;
  width: 28px; height: 28px; background: #f0fdf4; border-radius: 6px; flex-shrink: 0;
}
.db-icon svg { width: 16px; height: 16px; stroke: #16a34a; }
.db-filename { font-size: 15px; font-weight: 700; color: #0f172a; font-family: 'Courier New', monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.db-badge { font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 4px; background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; flex-shrink: 0; }
.db-header-tabs { display: flex; gap: 4px; flex-shrink: 0; }
.db-view-btn {
  padding: 6px 12px; border-radius: 7px; font-size: 12px; font-weight: 500;
  background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0;
  cursor: pointer; transition: all .12s; white-space: nowrap;
  display: inline-flex; align-items: center; gap: 5px;
}
.db-view-btn svg { width: 13px; height: 13px; flex-shrink: 0; }
.db-view-btn:hover  { background: #e2e8f0; }
.db-view-btn.active { background: #eff6ff; color: #2563eb; border-color: #93c5fd; font-weight: 700; }

/* ── 双栏布局 ── */
.db-body { display: flex; flex: 1; min-height: 0; overflow: hidden; }

/* 左侧表列表 */
.db-sidebar {
  width: 160px; flex-shrink: 0; border-right: 1px solid #e2e8f0;
  overflow-y: auto; display: flex; flex-direction: column; background: #f8fafc;
}
.db-sidebar-hd {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px 8px;
  font-size: 11px; font-weight: 700; color: #64748b;
  letter-spacing: .06em; text-transform: uppercase;
  border-bottom: 1px solid #e2e8f0; flex-shrink: 0;
}
.db-tbl-item {
  display: flex; align-items: flex-start; gap: 5px;
  padding: 8px 12px; font-size: 12px; color: #334155;
  cursor: pointer; background: none; border: none; text-align: left; width: 100%;
  border-bottom: 1px solid #f1f5f9; transition: background .1s; word-break: break-all;
}
.db-tbl-item:hover  { background: #eff6ff; color: #2563eb; }
.db-tbl-item.active { background: #eff6ff; color: #2563eb; font-weight: 700; border-left: 3px solid #3b82f6; }
.db-sidebar-empty { padding: 18px 12px; font-size: 11px; color: #94a3b8; text-align: center; }
.db-sidebar-err   { padding: 8px 12px; font-size: 12px; color: #dc2626; }

/* 右侧主区 */
.db-main { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }

/* SQL 模式 */
.db-sql-wrap {
  display: flex; gap: 10px; align-items: flex-start;
  padding: 12px 16px; border-bottom: 1px solid #f1f5f9; flex-shrink: 0;
}
.db-sql-input {
  flex: 1; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 8px;
  font-family: 'Courier New', monospace; font-size: 13px; color: #1e293b;
  resize: none; outline: none; background: #f8fafc; line-height: 1.5;
}
.db-sql-input:focus { border-color: #93c5fd; background: #fff; }
.db-sql-btns { display: flex; flex-direction: column; gap: 6px; flex-shrink: 0; }
.db-run-btn {
  padding: 8px 18px; background: #2563eb; color: #fff;
  border: none; border-radius: 7px; font-size: 13px; font-weight: 600;
  cursor: pointer; white-space: nowrap; transition: background .12s;
}
.db-run-btn:hover:not(:disabled) { background: #1d4ed8; }
.db-run-btn:disabled { opacity: .5; cursor: not-allowed; }
.db-clear-btn {
  padding: 6px 14px; background: #f1f5f9; color: #64748b;
  border: 1px solid #e2e8f0; border-radius: 7px; font-size: 12px;
  cursor: pointer; transition: all .12s; text-align: center;
}
.db-clear-btn:hover { background: #e2e8f0; }

/* 表格模式工具栏 */
.db-tbl-toolbar {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 8px 14px; border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0; background: #f8fafc; min-height: 44px;
}
.db-tbl-name { font-size: 14px; font-weight: 700; color: #0f172a; font-family: 'Courier New', monospace; }
.db-col-badge {
  font-size: 11px; color: #64748b;
  background: #e2e8f0; border-radius: 4px; padding: 1px 7px; font-weight: 600;
}
.db-spacer { flex: 1; }
.db-tbl-err { font-size: 12px; color: #dc2626; }
.db-add-row-btn {
  padding: 5px 12px; background: #ecfdf5; color: #15803d; border: 1px solid #86efac;
  border-radius: 6px; font-size: 12px; font-weight: 600;
  cursor: pointer; transition: all .12s; white-space: nowrap;
}
.db-add-row-btn:hover:not(:disabled) { background: #dcfce7; }
.db-add-row-btn:disabled { opacity: .5; cursor: not-allowed; }
.db-pg-btn {
  padding: 4px 10px; background: #fff; color: #475569;
  border: 1px solid #e2e8f0; border-radius: 6px; font-size: 14px;
  cursor: pointer; transition: all .12s;
}
.db-pg-btn:hover:not(:disabled) { background: #f1f5f9; }
.db-pg-btn:disabled { opacity: .4; cursor: not-allowed; }
.db-pg-info { font-size: 12px; color: #64748b; white-space: nowrap; }
.db-reload-btn {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 5px 8px; background: #fff; color: #64748b;
  border: 1px solid #e2e8f0; border-radius: 6px;
  cursor: pointer; transition: all .12s;
}
.db-reload-btn:hover:not(:disabled) { background: #f1f5f9; }
.db-reload-btn:disabled { opacity: .4; cursor: not-allowed; }

/* 可视化数据表格 */
.db-visual-wrap { flex: 1; overflow: auto; }
.db-visual-table {
  border-collapse: collapse; font-size: 12px; font-family: 'Courier New', monospace;
  width: 100%; white-space: nowrap;
}
.db-vth {
  background: #f8fafc; border: 1px solid #e2e8f0;
  padding: 7px 10px; text-align: left; position: sticky; top: 0; z-index: 1;
}
.db-col-nm { font-size: 12px; color: #334155; font-weight: 700; }
.db-col-tp { font-size: 10px; color: #94a3b8; margin-left: 5px; font-weight: 400; }
.db-pk {
  font-size: 10px; background: #fef3c7; color: #92400e; border: 1px solid #fde68a;
  border-radius: 3px; padding: 1px 4px; margin-left: 4px; font-weight: 700;
}
.db-ops-th {
  background: #f8fafc; border: 1px solid #e2e8f0;
  padding: 7px 10px; position: sticky; top: 0; z-index: 1;
  text-align: center; font-size: 11px; color: #94a3b8; width: 48px;
}
.db-vtd {
  border: 1px solid #f1f5f9; padding: 5px 10px; color: #334155;
  max-width: 260px; cursor: default; user-select: none;
}
.db-vtd:hover { background: #f8fafc; }
.db-cell-active { background: #eff6ff !important; outline: 2px solid #3b82f6; outline-offset: -1px; }
.db-null { color: #94a3b8 !important; font-style: italic; }
.db-ops-cell { border: 1px solid #f1f5f9; padding: 3px 6px; text-align: center; }
.db-add-row-tr { background: #f0fdf4; }
.db-add-td { border: 1px solid #86efac; padding: 4px 6px; }
.db-cell-inp {
  width: 100%; padding: 3px 6px; border: 1px solid #e2e8f0; border-radius: 4px;
  font-family: 'Courier New', monospace; font-size: 12px; outline: none;
  background: #fff; box-sizing: border-box;
}
.db-cell-inp:focus { border-color: #3b82f6; }
.db-cell-inp-edit { min-width: 120px; }
.db-cv { display: block; overflow: hidden; text-overflow: ellipsis; }
.db-ok-btn {
  padding: 3px 8px; background: #16a34a; color: #fff;
  border: none; border-radius: 4px; font-size: 13px; cursor: pointer;
}
.db-ok-btn:hover { background: #15803d; }
.db-cx-btn {
  padding: 3px 8px; background: #f1f5f9; color: #475569;
  border: 1px solid #e2e8f0; border-radius: 4px; font-size: 13px; cursor: pointer; margin-left: 4px;
}
.db-cx-btn:hover { background: #e2e8f0; }
.db-del-row-btn {
  padding: 2px 6px; background: none; color: #94a3b8;
  border: none; border-radius: 4px; font-size: 13px; cursor: pointer;
  transition: all .12s; opacity: 0;
}
tr:hover .db-del-row-btn { opacity: 1; }
.db-del-row-btn:hover { background: #fee2e2; color: #dc2626; }
.db-empty-row { text-align: center; padding: 32px; color: #94a3b8; font-size: 13px; }
.db-no-table {
  display: flex; align-items: center; justify-content: center;
  flex: 1; color: #94a3b8; font-size: 14px;
}

/* SQL 模式结果区（复用）*/
.db-result-area { flex: 1; overflow: hidden; display: flex; flex-direction: column; min-height: 0; }
.db-result-loading { display: flex; align-items: center; gap: 12px; padding: 32px; color: #94a3b8; justify-content: center; }
.db-result-err {
  margin: 14px 16px; padding: 10px 14px;
  background: #fff5f5; border: 1px solid #fecaca; border-radius: 8px;
  color: #dc2626; font-size: 13px; font-family: 'Courier New', monospace;
}
.db-result-meta { padding: 10px 16px 6px; font-size: 13px; color: #475569; flex-shrink: 0; }
.db-truncated-hint { font-size: 11px; color: #f59e0b; margin-left: 8px; font-weight: 600; }
.db-table-wrap { flex: 1; overflow: auto; padding: 0 16px 12px; }
.db-table {
  border-collapse: collapse; font-size: 12px;
  font-family: 'Courier New', monospace; width: 100%; white-space: nowrap;
}
.db-table th {
  background: #f8fafc; border: 1px solid #e2e8f0;
  padding: 7px 12px; font-size: 11px; color: #64748b;
  font-weight: 700; text-align: left; letter-spacing: .04em; text-transform: uppercase;
  position: sticky; top: 0;
}
.db-table td { border: 1px solid #f1f5f9; padding: 5px 12px; color: #334155; max-width: 300px; overflow: hidden; text-overflow: ellipsis; }
.db-table tr:hover td { background: #f8fafc; }
.db-exec-ok { padding: 24px; font-size: 15px; color: #16a34a; text-align: center; }
.db-result-empty { padding: 40px; text-align: center; color: #94a3b8; font-size: 13px; }

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
  width: 100%; max-width: 860px; max-height: 90vh;
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
  background: none; border: none; font-size: 18px; color: #94a3b8;
  cursor: pointer; padding: 2px 6px; border-radius: 6px; transition: all .12s; line-height: 1; flex-shrink: 0;
}
.em-close:hover { background: #f1f5f9; color: #0f172a; }
.em-loading { display: flex; align-items: center; gap: 12px; padding: 40px; color: #94a3b8; font-size: 14px; flex-shrink: 0; }
.em-error {
  margin: 10px 20px 0; padding: 10px 14px;
  background: #fff5f5; border: 1px solid #fecaca; border-radius: 8px;
  color: #dc2626; font-size: 13px; flex-shrink: 0;
}
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
.em-footer {
  display: flex; gap: 10px; align-items: center;
  padding: 14px 20px; border-top: 1px solid #e2e8f0; flex-shrink: 0;
}
.em-fmt-btn {
  padding: 8px 16px; background: #f8fafc; color: #475569;
  border: 1px solid #cbd5e1; border-radius: 8px; font-size: 13px; font-weight: 500;
  cursor: pointer; transition: all .12s; white-space: nowrap;
}
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
