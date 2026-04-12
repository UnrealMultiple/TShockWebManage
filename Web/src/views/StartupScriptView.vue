<template>
  <div class="ss-page">
    <!-- 顶部标题栏 -->
    <div class="ss-header">
      <div class="ss-header-left">
        <h2 class="ss-title">启动脚本设置</h2>
        <span v-if="scriptInfo.platform" :class="['ss-badge', scriptInfo.platform === 'windows' ? 'win' : 'linux']">
          {{ scriptInfo.platform === 'windows' ? 'Windows' : 'Linux' }}
        </span>
        <span v-if="scriptInfo.found !== null" :class="['ss-badge', scriptInfo.found ? 'found' : 'notfound']">
          {{ scriptInfo.found ? `已找到 ${scriptInfo.filename}` : '未找到脚本，将新建' }}
        </span>
        <span v-if="modified" class="ss-badge unsaved">未保存</span>
      </div>
      <div class="ss-header-right">
        <button class="ss-btn ss-btn-outline" @click="loadScript" :disabled="loading || !agentOnline || !activeServerKey">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="1 4 1 10 7 10"/>
            <path d="M3.51 15a9 9 0 1 0 .49-3.18"/>
          </svg>
          刷新
        </button>
        <button class="ss-btn ss-btn-primary" @click="saveScript" :disabled="saving || !agentOnline || !activeServerKey">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
            <polyline points="17 21 17 13 7 13 7 21"/>
            <polyline points="7 3 7 8 15 8"/>
          </svg>
          {{ saving ? '保存中…' : '保存脚本' }}
        </button>
      </div>
    </div>

    <!-- 内容区（可滚动） -->
    <div class="ss-content">

    <!-- 离线提示 -->
    <div v-if="!agentOnline" class="ss-offline">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
      </svg>
      TShock 未连接，无法读取或保存脚本。
    </div>

    <template v-else>
      <div v-if="loading" class="ss-loading">
        <div class="ss-spinner"></div>
        <span>正在读取…</span>
      </div>
      <div v-else-if="loadError" class="ss-error">
        读取失败：{{ loadError }}
        <button class="ss-btn ss-btn-outline" style="margin-top:10px" @click="loadScript" :disabled="!agentOnline">重试</button>
      </div>

      <template v-else-if="scriptLoaded">
        <!-- Toast -->
        <div v-if="toast" :class="['ss-toast', toast.ok ? 'ok' : 'err']">
          {{ toast.msg }}
          <button class="ss-toast-close" @click="toast = null">✕</button>
        </div>

        <!-- Tab 切换 -->
        <div class="ss-tabs">
          <button :class="['ss-tab', mode === 'visual' && 'active']" @click="mode = 'visual'">可视化配置</button>
          <button :class="['ss-tab', mode === 'raw' && 'active']" @click="switchToRaw">原始编辑</button>
        </div>

        <!-- ── 可视化模式 ── -->
        <div v-if="mode === 'visual'" class="ss-body">
          <div class="ss-left">

            <!-- 世界配置 -->
            <div class="ss-section">
              <div class="ss-section-title">世界配置</div>

              <!-- 指定方式切换 -->
              <div class="ss-radio-group">
                <label class="ss-radio">
                  <input type="radio" v-model="params.worldMode" value="direct" @change="syncModified"/>
                  <span>直接指定世界文件路径 <small>-world</small></span>
                </label>
                <label class="ss-radio">
                  <input type="radio" v-model="params.worldMode" value="search" @change="syncModified"/>
                  <span>指定搜索目录 + 世界名 <small>-worldselectpath + -worldname</small></span>
                </label>
                <label class="ss-radio">
                  <input type="radio" v-model="params.worldMode" value="manual" @change="syncModified"/>
                  <span>启动时手动选择世界</span>
                </label>
              </div>

              <!-- 直接路径模式 -->
              <div v-if="params.worldMode === 'direct'" class="ss-field" style="margin-top:12px">
                <label class="ss-label">
                  世界文件路径
                  <span class="ss-hint">可为相对路径（如 ceshi.wld）或绝对路径</span>
                </label>
                <input class="ss-input" v-model="params.world"
                  :placeholder="scriptInfo.platform === 'linux' ? '/root/terraria/worlds/my.wld' : 'ceshi.wld'"
                  @input="syncModified"/>
              </div>

              <!-- 搜索目录模式 -->
              <div v-else-if="params.worldMode === 'search'" class="ss-field-col" style="margin-top:12px">
                <div class="ss-field">
                  <label class="ss-label">
                    世界文件搜索目录
                    <span class="ss-hint">-worldselectpath，服务器从该目录查找 .wld 文件</span>
                  </label>
                  <input class="ss-input" v-model="params.worldselectpath"
                    :placeholder="scriptInfo.platform === 'linux' ? '/root/terraria/worlds' : 'C:\\Terraria\\worlds'"
                    @input="syncModified"/>
                </div>
                <div class="ss-field" style="margin-top:8px">
                  <label class="ss-label">
                    世界名称
                    <span class="ss-hint">-worldname，不含扩展名，如 ceshi</span>
                  </label>
                  <input class="ss-input" v-model="params.worldname"
                    placeholder="ceshi"
                    @input="syncModified"/>
                </div>
              </div>

              <div class="ss-field-row" style="margin-top:12px">
                <div class="ss-field">
                  <label class="ss-label">
                    自动创建世界
                    <span class="ss-hint">-autocreate，无世界文件时生效</span>
                  </label>
                  <select class="ss-select" v-model="params.autocreate" @change="syncModified">
                    <option value="">不自动创建</option>
                    <option value="1">小型</option>
                    <option value="2">中型</option>
                    <option value="3">大型</option>
                  </select>
                </div>
                <div class="ss-field">
                  <label class="ss-label">
                    世界难度
                    <span class="ss-hint">-difficulty，仅影响新生成世界</span>
                  </label>
                  <select class="ss-select" v-model="params.difficulty" @change="syncModified">
                    <option value="">默认</option>
                    <option value="0">普通</option>
                    <option value="1">专家</option>
                    <option value="2">大师</option>
                    <option value="3">旅途</option>
                  </select>
                </div>
                <div class="ss-field">
                  <label class="ss-label">
                    世界邪恶类型
                    <span class="ss-hint">-worldevil，仅影响新生成世界</span>
                  </label>
                  <select class="ss-select" v-model="params.worldevil" @change="syncModified">
                    <option value="">默认（随机）</option>
                    <option value="random">随机</option>
                    <option value="0">腐化</option>
                    <option value="1">蹩红</option>
                  </select>
                </div>
              </div>
            </div>

            <!-- 网络配置 -->
            <div class="ss-section">
              <div class="ss-section-title">网络配置</div>
              <div class="ss-field-row">
                <div class="ss-field">
                  <label class="ss-label">端口 <span class="ss-hint">-port</span></label>
                  <input class="ss-input" type="number" v-model="params.port" placeholder="7777" @input="syncModified"/>
                </div>
                <div class="ss-field">
                  <label class="ss-label">最大玩家数 <span class="ss-hint">-maxplayers</span></label>
                  <input class="ss-input" type="number" v-model="params.maxplayers" placeholder="8" @input="syncModified"/>
                </div>
                <div class="ss-field">
                  <label class="ss-label">绑定 IP <span class="ss-hint">-ip，留空绑定全部</span></label>
                  <input class="ss-input" v-model="params.ip" placeholder="0.0.0.0" @input="syncModified"/>
                </div>
              </div>
              <div class="ss-field">
                <label class="ss-label">服务器密码 <span class="ss-hint">-password，留空表示无密码</span></label>
                <input class="ss-input" v-model="params.password" placeholder="留空不设密码" @input="syncModified"/>
              </div>
            </div>

            <!-- TShock 配置 -->
            <div class="ss-section">
              <div class="ss-section-title">TShock 配置</div>
              <div class="ss-field-row">
                <div class="ss-field">
                  <label class="ss-label">语言 <span class="ss-hint">-lang</span></label>
                  <select class="ss-select" v-model="params.lang" @change="syncModified">
                    <option value="">默认</option>
                    <option value="1">英语 (en-US)</option>
                    <option value="2">德语 (de-DE)</option>
                    <option value="3">意大利语 (it-IT)</option>
                    <option value="4">法语 (fr-FR)</option>
                    <option value="5">西班牙语 (es-ES)</option>
                    <option value="6">俄语 (ru-RU)</option>
                    <option value="7">简体中文 (zh-Hans)</option>
                    <option value="8">葡萄牙语 (pt-BR)</option>
                    <option value="9">波兰语 (pl-PL)</option>
                  </select>
                </div>
              </div>
              <div class="ss-field">
                <label class="ss-label">配置文件路径 <span class="ss-hint">-configpath，留空使用默认 tshock/ 目录</span></label>
                <input class="ss-input" v-model="params.configpath" placeholder="留空使用默认路径" @input="syncModified"/>
              </div>
              <div class="ss-field">
                <label class="ss-label">日志路径 <span class="ss-hint">-logpath，留空使用默认</span></label>
                <input class="ss-input" v-model="params.logpath" placeholder="留空使用默认路径" @input="syncModified"/>
              </div>
            </div>

            <!-- 高级选项 -->
            <div class="ss-section">
              <div class="ss-section-title">高级选项</div>
              <div class="ss-checkboxes">
                <label class="ss-check">
                  <input type="checkbox" v-model="params.forceupdate" @change="syncModified"/>
                  <span>强制持续运行 <small>-forceupdate，无玩家时不休眠，时间正常流逝</small></span>
                </label>
                <label class="ss-check">
                  <input type="checkbox" v-model="params.secure" @change="syncModified"/>
                  <span>反垃圾信息 <small>-secure，启用游戏内置反刷屏功能</small></span>
                </label>
                <label class="ss-check">
                  <input type="checkbox" v-model="params.ignoreversion" @change="syncModified"/>
                  <span>忽略插件版本检查 <small>-ignoreversion，允许运行旧版插件</small></span>
                </label>
                <label class="ss-check">
                  <input type="checkbox" v-model="params.logclear" @change="syncModified"/>
                  <span>覆盖旧日志 <small>-logclear，适合 Docker 等容器环境</small></span>
                </label>
                <label class="ss-check">
                  <input type="checkbox" v-model="params.heaptile" @change="syncModified"/>
                  <span>HeapTile 地图接口 <small>-heaptile，实验性，更省内存但可能不稳定</small></span>
                </label>
              </div>
            </div>

            <!-- 额外参数 -->
            <div class="ss-section">
              <div class="ss-section-title">额外参数</div>
              <div class="ss-field">
                <label class="ss-label">自定义追加参数 <span class="ss-hint">追加在命令末尾</span></label>
                <input class="ss-input" v-model="params.extra" placeholder="例：-additionalplugins /extra/plugins" @input="syncModified"/>
              </div>
            </div>

            <!-- 自动重启 -->
            <div class="ss-section">
              <div class="ss-section-title">自动重启</div>
              <label class="ss-check ss-check-lg">
                <input type="checkbox" v-model="params.autoRestart" @change="syncModified"/>
                <span>
                  崩溃/退出后自动重启
                  <small>使用循环脚本包裹启动命令，适配配置了"不保存关闭"/"重启"的外部脚本。</small>
                </span>
              </label>
            </div>
          </div>

          <!-- 预览 -->
          <div class="ss-right">
            <div class="ss-preview-header">
              <span>脚本预览</span>
              <span class="ss-preview-file">{{ scriptInfo.filename || (scriptInfo.platform === 'windows' ? 'start.bat' : 'start.sh') }}</span>
            </div>
            <pre class="ss-preview">{{ generatedScript }}</pre>
            <div class="ss-preview-footer">将保存至：{{ scriptInfo.path || '…' }}</div>
          </div>
        </div>

        <!-- ── 原始编辑模式 ── -->
        <div v-else class="ss-raw-wrap">
          <textarea class="ss-raw-editor" v-model="rawContent" spellcheck="false" @input="syncModified"/>
          <div class="ss-preview-footer">保存至：{{ scriptInfo.path || '…' }}</div>
        </div>

      </template>

      <!-- 未加载 -->
      <div v-else class="ss-empty">
        <p>点击刷新读取服务器启动脚本</p>
        <button class="ss-btn ss-btn-primary" @click="loadScript" :disabled="!agentOnline">读取脚本</button>
      </div>
    </template>

    </div><!-- /ss-content -->
  </div>
</template>

<script setup>
import { ref, computed, inject, onMounted, onUnmounted } from 'vue'

const activeServerKey       = inject('activeServerKey',       ref(''))
const canManageActiveServer = inject('canManageActiveServer', computed(() => false))

const props = defineProps({
  agentOnline: { type: Boolean, default: false },
  wsState:     { type: String,  default: 'disconnected' },
})

// ── 状态 ───────────────────────────────────────────────────────
const loading     = ref(false)
const saving      = ref(false)
const scriptLoaded = ref(false)
const loadError   = ref('')
const modified    = ref(false)
const mode        = ref('visual')  // 'visual' | 'raw'
const toast       = ref(null)

const scriptInfo = ref({
  found: null, platform: '', filename: '', path: '', content: ''
})

// 可视化参数
const params = ref({
  worldMode: 'direct',      // 'direct' | 'search' | 'manual'
  world: '', worldselectpath: '', worldname: '',
  port: '', maxplayers: '', ip: '',
  password: '', lang: '7', configpath: '', logpath: '',
  autocreate: '', difficulty: '', worldevil: '', extra: '',
  forceupdate: false, secure: false, ignoreversion: false,
  logclear: false, heaptile: false,
  autoRestart: true,
})

// 原始编辑内容
const rawContent = ref('')

// ── 脚本生成 ────────────────────────────────────────────────────
const generatedScript = computed(() => buildScript(params.value, scriptInfo.value.platform || 'windows'))

function buildScript(p, platform) {
  const isWin = platform === 'windows'
  const exe   = isWin ? 'TShock.Server.exe' : './TShock.Server'

  const args = []
  if (p.worldMode === 'direct' && p.world)       args.push(`-world "${p.world}"`)
  if (p.worldMode === 'search' && p.worldselectpath) args.push(`-worldselectpath "${p.worldselectpath}"`)
  if (p.worldMode === 'search' && p.worldname)   args.push(`-worldname "${p.worldname}"`)
  if (p.autocreate)   args.push(`-autocreate ${p.autocreate}`)
  if (p.port)         args.push(`-port ${p.port}`)
  if (p.maxplayers)   args.push(`-maxplayers ${p.maxplayers}`)
  if (p.ip)           args.push(`-ip ${p.ip}`)
  if (p.password)     args.push(`-password "${p.password}"`)
  if (p.lang)         args.push(`-lang ${p.lang}`)
  if (p.configpath)   args.push(`-configpath "${p.configpath}"`)
  if (p.logpath)      args.push(`-logpath "${p.logpath}"`)
  if (p.difficulty)   args.push(`-difficulty ${p.difficulty}`)
  if (p.worldevil && p.worldevil !== '')  args.push(`-worldevil ${p.worldevil}`)
  if (p.forceupdate)  args.push('-forceupdate')
  if (p.secure)       args.push('-secure')
  if (p.ignoreversion) args.push('-ignoreversion')
  if (p.logclear)     args.push('-logclear')
  if (p.heaptile)     args.push('-heaptile')
  if (p.extra)        args.push(p.extra)

  const cmd = `${exe} ${args.join(' ')}`

  if (isWin) {
    if (p.autoRestart) {
      // 有重启循环：任意退出后基本都会重启，由脚本控制
      return `@echo off\ncls\n:start\n${cmd}\n@echo.\n@echo Restarting server...\n@echo.\ngoto start`
    } else {
      return `@echo off\n${cmd}\npause`
    }
  } else {
    if (p.autoRestart) {
      return `#!/bin/bash\nwhile true; do\n    ${cmd}\n    echo "Server exited, restarting in 2s..."\n    sleep 2\ndone`
    } else {
      return `#!/bin/bash\n${cmd}`
    }
  }
}

// ── WebSocket ────────────────────────────────────────────────────
function sendWs(data) { window.__tshockSend?.(data) }

let _resolve = null

function sendAndWait(data, timeout = 15000) {
  return new Promise((resolve) => {
    if (props.wsState !== 'connected') {
      resolve({ success: false, msg: 'WebSocket 未连接，请稍后重试' })
      return
    }
    _resolve = resolve
    sendWs(data)
    setTimeout(() => { if (_resolve) { _resolve(null); _resolve = null } }, timeout)
  })
}

function onWsMessage(e) {
  const pkt = e.detail
  if (!_resolve) return
  // 过滤其他 Agent 的响应（含 metadata.agent_key 的才判断；后端直接发的错误包不含该字段，放行）
  if (pkt.metadata?.agent_key && pkt.metadata.agent_key !== activeServerKey.value) return
  if (pkt.type === 'read_startup_script_resp' || pkt.type === 'write_startup_script_resp') {
    const cb = _resolve
    _resolve = null
    cb(pkt.payload)
  }
}

// ── 加载 ─────────────────────────────────────────────────────────
async function loadScript() {
  if (!activeServerKey.value) return
  loading.value   = true
  loadError.value = ''
  const resp = await sendAndWait({
    type: 'read_startup_script', msg_id: Date.now().toString(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value }
  })
  loading.value = false
  if (!resp || !resp.success) {
    loadError.value = resp?.msg || '未知错误'
    return
  }
  scriptInfo.value = {
    found: resp.found, platform: resp.platform,
    filename: resp.filename, path: resp.path, content: resp.content
  }
  rawContent.value = resp.content
  parseScriptToParams(resp.content, resp.platform)
  scriptLoaded.value = true
  modified.value = false
}

// ── 解析脚本内容 → 填充可视化参数 ────────────────────────────────
function parseScriptToParams(content, platform) {
  if (!content) return
  const isWin = (platform || '').toLowerCase() !== 'linux'
  const exeRe = isWin ? /TShock\.Server\.exe\s+(.+)/i : /\.\/?TShock\.Server\s+(.+)/

  let cmdLine = ''
  for (const line of content.split(/\r?\n/)) {
    const m = line.trim().match(exeRe)
    if (m) { cmdLine = m[1].trim(); break }
  }
  if (!cmdLine) return

  // 解析参数（支持带引号的值）
  const tokens = []
  const re = /(-\w+)(?:\s+("([^"]*)"|([^\s-][^\s]*)))?/g
  let match
  while ((match = re.exec(cmdLine)) !== null) {
    tokens.push({ flag: match[1], val: match[3] ?? match[4] ?? '' })
  }

  const hasAutoRestart = isWin ? content.includes('goto start') : content.includes('while true')
  const p = {
    ...params.value,
    autoRestart: hasAutoRestart,
    worldMode: 'direct',
  }

  for (const { flag, val } of tokens) {
    switch (flag) {
      case '-world':           p.worldMode = 'direct'; p.world = val; break
      case '-worldselectpath': p.worldMode = 'search'; p.worldselectpath = val; break
      case '-worldname':       p.worldname = val; break
      case '-autocreate':      p.autocreate = val; break
      case '-port':            p.port = val; break
      case '-maxplayers':      p.maxplayers = val; break
      case '-ip':              p.ip = val; break
      case '-password':        p.password = val; break
      case '-lang':            p.lang = val; break
      case '-configpath':      p.configpath = val; break
      case '-logpath':         p.logpath = val; break
      case '-difficulty':      p.difficulty = val; break
      case '-worldevil':       p.worldevil = val; break
      case '-forceupdate':     p.forceupdate = true; break
      case '-secure':          p.secure = true; break
      case '-ignoreversion':   p.ignoreversion = true; break
      case '-logclear':        p.logclear = true; break
      case '-heaptile':        p.heaptile = true; break
    }
  }
  params.value = p
}

// ── 切换到原始模式（同步最新生成脚本） ──────────────────────────────
function switchToRaw() {
  if (mode.value === 'visual') {
    rawContent.value = generatedScript.value
    modified.value = true
  }
  mode.value = 'raw'
}

function syncModified() { modified.value = true }

// ── 保存 ─────────────────────────────────────────────────────────
async function saveScript() {
  if (!activeServerKey.value) return
  const content  = mode.value === 'visual' ? generatedScript.value : rawContent.value
  const filename = scriptInfo.value.filename || (scriptInfo.value.platform === 'windows' ? 'start.bat' : 'start.sh')

  saving.value = true
  const resp = await sendAndWait({
    type: 'write_startup_script', msg_id: Date.now().toString(), timestamp: Date.now(),
    payload: { agent_key: activeServerKey.value, content, filename }
  })
  saving.value = false

  if (resp?.success) {
    scriptInfo.value.path     = resp.path
    scriptInfo.value.filename = resp.filename
    scriptInfo.value.found    = true
    scriptInfo.value.content  = content
    rawContent.value = content
    modified.value = false
    showToast(true, `已保存至 ${resp.path}`)
  } else {
    showToast(false, resp?.msg || '保存失败')
  }
}

function showToast(ok, msg) {
  toast.value = { ok, msg }
  setTimeout(() => { toast.value = null }, 4000)
}

onMounted(() => {
  window.addEventListener('ws-message', onWsMessage)
  if (props.agentOnline && activeServerKey.value) loadScript()
})
onUnmounted(() => window.removeEventListener('ws-message', onWsMessage))
</script>

<style scoped>
.ss-page { display: flex; flex-direction: column; height: 100%; overflow: hidden; background: #f8fafc; }

/* 顶栏 */
.ss-header { display: flex; align-items: center; justify-content: space-between; padding: 20px 28px 16px; background: #fff; border-bottom: 1px solid #e2e8f0; flex-shrink: 0; flex-wrap: wrap; gap: 12px; }
.ss-header-left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.ss-title { margin: 0; font-size: 18px; font-weight: 700; color: #0f172a; }
.ss-header-right { display: flex; gap: 8px; }

/* 内容区 */
.ss-content { flex: 1; overflow-y: auto; padding: 24px 28px; box-sizing: border-box; }

/* 状态徽章 */
.ss-badge { font-size: 12px; font-weight: 500; padding: 2px 8px; border-radius: 20px; }
.ss-badge.win      { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; font-family: monospace; }
.ss-badge.linux    { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; font-family: monospace; }
.ss-badge.found    { background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; font-family: monospace; }
.ss-badge.notfound { background: #fef3c7; color: #92400e; border: 1px solid #fde68a; }
.ss-badge.unsaved  { font-size: 12px; color: #d97706; background: #fef3c7; border: 1px solid #fde68a; padding: 2px 8px; border-radius: 20px; animation: pulse-dot 1.5s ease-in-out infinite; }
@keyframes pulse-dot { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

/* 按钮 */
.ss-btn { display: inline-flex; align-items: center; gap: 6px; padding: 7px 16px; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; border: none; transition: all 0.15s; }
.ss-btn svg { width: 14px; height: 14px; flex-shrink: 0; }
.ss-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.ss-btn-outline { background: #fff; color: #374151; border: 1px solid #d1d5db; }
.ss-btn-outline:hover:not(:disabled) { background: #f9fafb; border-color: #9ca3af; }
.ss-btn-primary { background: #3b82f6; color: #fff; }
.ss-btn-primary:hover:not(:disabled) { background: #2563eb; }

/* 提示 */
.ss-offline { display: flex; align-items: center; gap: 12px; padding: 14px 18px; background: #fff7ed; border: 1px solid #fcd34d; border-radius: 10px; font-size: 14px; color: #92400e; }
.ss-offline svg { width: 20px; height: 20px; flex-shrink: 0; color: #94a3b8; }
.ss-loading { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 60px 24px; color: #64748b; font-size: 14px; flex-direction: row; }
.ss-spinner { width: 28px; height: 28px; border: 3px solid #e2e8f0; border-top-color: #3b82f6; border-radius: 50%; animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.ss-error { display: flex; flex-direction: column; gap: 8px; padding: 16px 20px; background: #fff1f2; border: 1px solid #fecdd3; border-radius: 10px; color: #9f1239; font-size: 14px; }
.ss-empty { display: flex; flex-direction: column; align-items: center; gap: 14px; padding: 60px 24px; color: #94a3b8; font-size: 14px; text-align: center; }

/* 提示条 */
.ss-toast { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 500; margin-bottom: 16px; }
.ss-toast.ok  { background: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
.ss-toast.err { background: #fee2e2; color: #991b1b; border: 1px solid #fecaca; }
.ss-toast-close { background: none; border: none; cursor: pointer; font-size: 14px; color: inherit; opacity: 0.6; padding: 0 0 0 12px; }
.ss-toast-close:hover { opacity: 1; }

/* 标签页 */
.ss-tabs { display: flex; gap: 2px; margin-bottom: 20px; border-bottom: 1px solid #e2e8f0; }
.ss-tab { padding: 8px 18px; font-size: 13px; font-weight: 600; background: none; border: none; border-bottom: 2px solid transparent; cursor: pointer; color: #94a3b8; margin-bottom: -1px; transition: all .15s; }
.ss-tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
.ss-tab:hover:not(.active) { color: #475569; }

/* 可视化布局 */
.ss-body { display: grid; grid-template-columns: 1fr 420px; gap: 20px; align-items: start; }
.ss-left { display: flex; flex-direction: column; gap: 16px; }

/* 区块 */
.ss-section { background: #fff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 18px 20px; }
.ss-section-title { font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: .06em; text-transform: uppercase; margin-bottom: 14px; }
.ss-field { display: flex; flex-direction: column; gap: 5px; flex: 1; }
.ss-field-row { display: flex; gap: 12px; }
.ss-label { font-size: 12px; font-weight: 600; color: #374151; display: flex; flex-direction: column; gap: 2px; }
.ss-hint { font-weight: 400; color: #94a3b8; font-size: 11px; }
.ss-input, .ss-select { width: 100%; padding: 7px 10px; border: 1px solid #e2e8f0; border-radius: 7px; font-size: 13px; color: #0f172a; background: #f8fafc; box-sizing: border-box; }
.ss-input:focus, .ss-select:focus { outline: none; border-color: #3b82f6; background: #fff; }

/* 单选组 */
.ss-radio-group { display: flex; flex-direction: column; gap: 8px; }
.ss-radio { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.ss-radio input { cursor: pointer; }
.ss-radio span { font-size: 13px; color: #1e293b; }
.ss-radio small { font-size: 11px; color: #94a3b8; font-family: monospace; margin-left: 4px; }
.ss-field-col { display: flex; flex-direction: column; }

/* 复选框 */
.ss-checkboxes { display: flex; flex-direction: column; gap: 10px; }
.ss-check { display: flex; align-items: flex-start; gap: 9px; cursor: pointer; }
.ss-check input { margin-top: 3px; flex-shrink: 0; cursor: pointer; }
.ss-check span { font-size: 13px; color: #1e293b; }
.ss-check small { display: block; font-size: 11px; color: #94a3b8; margin-top: 1px; }
.ss-check-lg span { font-size: 14px; font-weight: 600; }
.ss-check-lg small { font-size: 12px; }

/* 预览 */
.ss-right { position: sticky; top: 0; background: #0f172a; border-radius: 12px; overflow: hidden; }
.ss-preview-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: #1e293b; }
.ss-preview-header span { font-size: 12px; font-weight: 600; color: #94a3b8; }
.ss-preview-file { font-family: monospace; font-size: 12px; color: #60a5fa; }
.ss-preview { margin: 0; padding: 16px; font-family: 'Consolas', monospace; font-size: 12px; line-height: 1.7; color: #e2e8f0; white-space: pre-wrap; word-break: break-all; min-height: 200px; }
.ss-preview-footer { padding: 10px 16px; font-size: 11px; color: #475569; background: #1e293b; border-top: 1px solid #334155; font-family: monospace; }

/* 原始编辑 */
.ss-raw-wrap { display: flex; flex-direction: column; gap: 0; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; }
.ss-raw-editor { width: 100%; min-height: 500px; padding: 16px; font-family: 'Consolas', monospace; font-size: 13px; line-height: 1.7; color: #0f172a; border: none; resize: vertical; box-sizing: border-box; background: #f8fafc; }
.ss-raw-editor:focus { outline: none; background: #fff; }

@media (max-width: 1100px) {
  .ss-body { grid-template-columns: 1fr; }
  .ss-right { position: static; }
}
@media (max-width: 860px) {
  .ss-header { padding: 16px 20px 12px; }
  .ss-content { padding: 16px 20px; }
}
@media (max-width: 560px) {
  .ss-field-row { flex-direction: column; }
}
</style>
