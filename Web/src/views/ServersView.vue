<template>
  <div class="servers-page">
    <!-- 页头 -->
    <div class="page-header">
      <h1 class="page-title">服务器</h1>
      <button v-if="activeTab === 'mine'" class="btn btn-primary" @click="openClaimModal">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
        添加服务器
      </button>
    </div>

    <!-- Tab 导航 -->
    <div class="tab-bar">
      <button :class="['tab-btn', activeTab === 'public' && 'active']" @click="activeTab = 'public'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
        公共频道
        <span class="tab-count" v-if="publicServers.length">{{ publicServers.length }}</span>
      </button>
      <button :class="['tab-btn', activeTab === 'mine' && 'active']" @click="activeTab = 'mine'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
        我的服务器
        <span class="tab-count" v-if="myOwnedServers.length">{{ myOwnedServers.length }}</span>
      </button>
      <button :class="['tab-btn', activeTab === 'joined' && 'active']" @click="activeTab = 'joined'">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
        我加入的
        <span class="tab-count" v-if="myJoinedServers.length">{{ myJoinedServers.length }}</span>
      </button>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-state">加载中...</div>

    <template v-else>
      <!-- ═══ 公共频道 ═══ -->
      <div v-if="activeTab === 'public'">
        <!-- 搜索栏 -->
        <div class="search-bar">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input v-model="publicSearch" placeholder="搜索服务器名称或描述…" class="search-input" />
          <button v-if="publicSearch" class="search-clear" @click="publicSearch = ''">&#x2715;</button>
        </div>
        <div v-if="filteredPublicServers.length" class="server-grid">
          <div v-for="s in filteredPublicServers" :key="s.id" class="server-card public-card">
            <div class="card-header-row">
              <span class="server-name">{{ s.name }}</span>
              <span :class="['online-badge', s.online ? 'online' : 'offline']">
                {{ s.online ? '在线' : '离线' }}
              </span>
            </div>
            <div class="server-desc">{{ s.description || '暂无描述' }}</div>
            <div class="card-meta-row">
              <span class="meta-chip" v-if="s.game_version">{{ s.game_version }}</span>
              <span class="meta-chip">{{ s.member_count }} 名成员</span>
            </div>
            <div class="card-footer-row">
              <button class="btn btn-sm btn-outline" @click="openInfoModal(s)">详情</button>
              <button
                class="btn btn-sm btn-primary"
                :disabled="isAlreadyMember(s.id)"
                @click="joinPublicServer(s)"
              >{{ isAlreadyMember(s.id) ? '已加入' : '加入' }}</button>
            </div>
          </div>
        </div>
        <div v-else-if="publicSearch" class="empty-tab">
          <p>没有匹配「{{ publicSearch }}」的服务器</p>
        </div>
        <div v-else class="empty-tab">
          <div class="empty-icon-wrap">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
          </div>
          <p>暂无公开服务器</p>
          <p class="empty-hint">服主可在添加服务器时开启「公开」选项，让其他玩家能在这里找到并加入。</p>
        </div>
      </div>

      <!-- ═══ 我的服务器 ═══ -->
      <div v-else-if="activeTab === 'mine'">
        <!-- 引导空白页 -->
        <div v-if="!myOwnedServers.length" class="onboarding-empty">
          <div class="onboard-hero">
            <div class="onboard-icon-wrap">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
            </div>
            <h2>开始你的第一台服务器</h2>
            <p class="onboard-sub">将 TShock Agent 插件安装到你的服务器，就可以在这里远程管理了。</p>
          </div>
          <div class="steps">
            <div class="step">
              <div class="step-num">1</div>
              <div class="step-body">
                <strong>安装并启动 Agent 插件</strong>
                <p>将 <code>TerrariaAgent.dll</code> 放入 TShock 的 <code>ServerPlugins/</code> 目录，启动服务器。</p>
              </div>
            </div>
            <div class="step step-arrow">→</div>
            <div class="step">
              <div class="step-num">2</div>
              <div class="step-body">
                <strong>复制控制台中的 Agent Key</strong>
                <p>插件首次运行会在控制台输出密钥框，复制其中的 <code>Agent Key</code>。</p>
              </div>
            </div>
            <div class="step step-arrow">→</div>
            <div class="step">
              <div class="step-num">3</div>
              <div class="step-body">
                <strong>填写表单完成绑定</strong>
                <p>点击上方「添加服务器」，填入密钥和名称，即成为该服务器的管理员。</p>
              </div>
            </div>
          </div>
          <button class="btn btn-primary btn-lg" @click="openClaimModal">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            添加我的第一台服务器
          </button>
        </div>

        <!-- 已有服务器列表 -->
        <div v-else>
          <div class="search-bar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input v-model="mineSearch" placeholder="搜索服务器名称…" class="search-input" />
            <button v-if="mineSearch" class="search-clear" @click="mineSearch = ''">&#x2715;</button>
          </div>
          <div v-if="!filteredMineServers.length && mineSearch" class="empty-tab" style="padding:40px 0">
            <p>没有匹配「{{ mineSearch }}」的服务器</p>
          </div>
          <div v-else class="server-grid">
            <div
              v-for="s in filteredMineServers" :key="s.id"
              class="server-card"
              @click="selectServer(s)"
            >
              <div class="card-header-row">
                <span class="server-name">{{ s.name }}</span>
                <div class="card-badges">
                  <span class="role-tag">Owner</span>
                  <span :class="['online-badge', s.online ? 'online' : 'offline']">
                    {{ s.online ? '在线' : '离线' }}
                  </span>
                  <span v-if="s.is_public" class="badge-public">公开</span>
                </div>
              </div>
              <div class="server-desc">{{ s.description || '暂无描述' }}</div>
              <div class="card-footer-row">
                <span class="meta-text">{{ s.member_count }} 名成员</span>
                <div style="display:flex;gap:6px;">
                  <button
                    v-if="s.agent_key && activeServerKey !== s.agent_key"
                    class="btn btn-sm btn-primary"
                    @click.stop="switchToServer(s)"
                  >切换</button>
                  <span v-else-if="s.agent_key && activeServerKey === s.agent_key" class="badge-active">当前</span>
                  <button class="btn btn-sm btn-outline" @click.stop="openEditModal(s)">设置</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══ 我加入的 ═══ -->
      <div v-else-if="activeTab === 'joined'">
        <div v-if="!myJoinedServers.length" class="empty-tab">
          <div class="empty-icon-wrap">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <p>还没有加入任何服务器</p>
          <p class="empty-hint">去「公共频道」找找看，或让服主将服务器设为公开。</p>
          <button class="btn btn-secondary" style="margin-top:14px" @click="activeTab = 'public'">
            浏览公共频道
          </button>
        </div>
        <div v-else>
          <div class="search-bar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input v-model="joinedSearch" placeholder="搜索服务器名称…" class="search-input" />
            <button v-if="joinedSearch" class="search-clear" @click="joinedSearch = ''">&#x2715;</button>
          </div>
          <div v-if="!filteredJoinedServers.length && joinedSearch" class="empty-tab" style="padding:40px 0">
            <p>没有匹配「{{ joinedSearch }}」的服务器</p>
          </div>
          <div v-else class="server-grid">
            <div
              v-for="s in filteredJoinedServers" :key="s.id"
              class="server-card"
              @click="selectServer(s)"
            >
              <div class="card-header-row">
                <span class="server-name">{{ s.name }}</span>
                <div class="card-badges">
                  <span class="role-tag member">Member</span>
                  <span :class="['online-badge', s.online ? 'online' : 'offline']">
                    {{ s.online ? '在线' : '离线' }}
                  </span>
                </div>
              </div>
              <div class="server-desc">{{ s.description || '暂无描述' }}</div>
              <div class="card-footer-row">
                <span class="meta-text">{{ s.member_count }} 名成员</span>
                <div style="display:flex;gap:6px;">
                  <button
                    v-if="s.agent_key && activeServerKey !== s.agent_key"
                    class="btn btn-sm btn-primary"
                    @click.stop="switchToServer(s)"
                  >切换</button>
                  <span v-else-if="s.agent_key && activeServerKey === s.agent_key" class="badge-active">当前</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 服务器详情弹窗 -->
    <div v-if="detailModal.open" class="modal-overlay" @click.self="detailModal.open = false">
      <div class="modal modal-detail">
        <div class="modal-info-header">
          <h3 class="modal-title">{{ detailModal.data?.name }}</h3>
          <div style="display:flex;gap:6px;align-items:center">
            <span v-if="detailModal.data?.is_public" class="badge-public">公开</span>
            <span :class="['online-badge', detailModal.data?.online ? 'online' : 'offline']">
              {{ detailModal.data?.online ? '在线' : '离线' }}
            </span>
          </div>
        </div>
        <p class="modal-info-desc">{{ detailModal.data?.description || '该服务器暂无介绍。' }}</p>
        <div class="modal-info-meta">
          <span>{{ detailModal.data?.members?.length ?? 0 }} 名成员</span>
          <span v-if="detailModal.data?.game_version" class="meta-chip">{{ detailModal.data.game_version }}</span>
        </div>
        <template v-if="detailModal.data?.game_ip && (detailModal.isOwner || detailModal.data?.show_ip)">
          <div class="info-connect-block">
            <div class="info-connect-title">连接信息</div>
            <div class="info-connect-row">
              <span class="info-connect-label">地址</span>
              <code class="info-connect-val">{{ detailModal.data.game_ip }}{{ detailModal.data.game_port ? ':' + detailModal.data.game_port : '' }}</code>
              <button class="copy-btn" @click="copyText(detailModal.data.game_ip + (detailModal.data.game_port ? ':' + detailModal.data.game_port : ''), 'det-ip')">
                <span v-if="copied === 'det-ip'">✓</span><span v-else>复制</span>
              </button>
            </div>
            <div v-if="detailModal.data.qq_group" class="info-connect-row">
              <span class="info-connect-label">QQ 群</span>
              <code class="info-connect-val">{{ detailModal.data.qq_group }}</code>
              <button class="copy-btn" @click="copyText(detailModal.data.qq_group, 'det-qq')">
                <span v-if="copied === 'det-qq'">✓</span><span v-else>复制</span>
              </button>
            </div>
          </div>
        </template>
        <template v-else-if="detailModal.data?.qq_group">
          <div class="info-connect-block">
            <div class="info-connect-title">联系方式</div>
            <div class="info-connect-row">
              <span class="info-connect-label">QQ 群</span>
              <code class="info-connect-val">{{ detailModal.data.qq_group }}</code>
              <button class="copy-btn" @click="copyText(detailModal.data.qq_group, 'det-qq')">
                <span v-if="copied === 'det-qq'">✓</span><span v-else>复制</span>
              </button>
            </div>
          </div>
        </template>
        <p v-if="detailModal.isOwner" class="detail-hint" style="margin:8px 0 16px">成员管理请前往「用户管理」</p>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="detailModal.open = false">关闭</button>
          <template v-if="detailModal.isOwner">
            <button class="btn btn-outline" @click="openEditFromDetail">设置</button>
            <button class="btn btn-danger" @click="handleDissolve">解散</button>
          </template>
          <button v-else class="btn btn-outline" @click="handleLeave">离开</button>
        </div>
      </div>
    </div>

    <!-- 添加服务器弹窗（认领） -->
    <div v-if="claimModal.open" class="modal-overlay" @click.self="claimModal.open = false">
      <div class="modal modal-wide">
        <h3 class="modal-title">添加服务器</h3>
        <p class="modal-tip">将控制台中显示的 <code>Agent Key</code> 填入下方，即可绑定并成为服务器管理员。</p>
        <label class="modal-label">Agent Key <span class="required">*</span></label>
        <input v-model="claimModal.key" class="modal-input" placeholder="粘贴来自控制台的 key" maxlength="100" />
        <label class="modal-label">服务器名称 <span class="required">*</span></label>
        <input v-model="claimModal.name" class="modal-input" placeholder="给服务器起个名字" maxlength="50" />
        <label class="modal-label">描述（可选）</label>
        <textarea v-model="claimModal.desc" class="modal-input modal-textarea" placeholder="服务器介绍（可留空）" maxlength="200" />
        <div class="modal-row-2">
          <div>
            <label class="modal-label">游戏 IP</label>
            <input v-model="claimModal.game_ip" class="modal-input" placeholder="如 play.example.com" maxlength="100" />
          </div>
          <div>
            <label class="modal-label">端口</label>
            <input v-model.number="claimModal.game_port" class="modal-input" type="number" min="1" max="65535" placeholder="7777" />
          </div>
        </div>
        <div>
          <label class="modal-label">QQ 群号</label>
          <input v-model="claimModal.qq_group" class="modal-input" placeholder="可选" maxlength="20" />
        </div>
        <div class="modal-toggle-row">
          <label class="srv-toggle-wrap">
            <label class="srv-toggle">
              <input type="checkbox" v-model="claimModal.isPublic" />
              <span class="srv-toggle-track"><span class="srv-toggle-thumb"></span></span>
            </label>
            <span class="srv-toggle-text">公开此服务器（显示在公共频道，其他玩家可自由加入）</span>
          </label>
        </div>
        <div class="modal-toggle-row">
          <label class="srv-toggle-wrap">
            <label class="srv-toggle">
              <input type="checkbox" v-model="claimModal.showIp" />
              <span class="srv-toggle-track"><span class="srv-toggle-thumb"></span></span>
            </label>
            <span class="srv-toggle-text">在公开介绍中显示 IP 地址</span>
          </label>
        </div>
        <p v-if="claimModal.error" class="modal-error">{{ claimModal.error }}</p>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="claimModal.open = false">取消</button>
          <button class="btn btn-primary" :disabled="claimModal.loading" @click="submitClaim">
            {{ claimModal.loading ? '绑定中...' : '确认绑定' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 点看介绍弹窗 -->
    <div v-if="infoModal.open" class="modal-overlay" @click.self="infoModal.open = false">
      <div class="modal modal-info">
        <div class="modal-info-header">
          <h3 class="modal-title">{{ infoModal.server?.name }}</h3>
          <span :class="['online-badge', infoModal.server?.online ? 'online' : 'offline']">
            {{ infoModal.server?.online ? '在线' : '离线' }}
          </span>
        </div>
        <p class="modal-info-desc">{{ infoModal.server?.description || '该服务器暂无介绍。' }}</p>
        <div class="modal-info-meta">
          <span>{{ infoModal.server?.member_count }} 名成员</span>
          <span v-if="infoModal.server?.game_version">{{ infoModal.server.game_version }}</span>
        </div>
        <div v-if="infoModal.server?.game_ip && infoModal.server?.show_ip" class="info-connect-block">
          <div class="info-connect-title">连接信息</div>
          <div class="info-connect-row">
            <span class="info-connect-label">地址</span>
            <code class="info-connect-val">{{ infoModal.server.game_ip }}{{ infoModal.server.game_port ? ':' + infoModal.server.game_port : '' }}</code>
            <button class="copy-btn" @click="copyText(infoModal.server.game_ip + (infoModal.server.game_port ? ':' + infoModal.server.game_port : ''), 'ip')">
              <span v-if="copied === 'ip'">✓</span><span v-else>复制</span>
            </button>
          </div>
          <div v-if="infoModal.server?.qq_group" class="info-connect-row">
            <span class="info-connect-label">QQ 群</span>
            <code class="info-connect-val">{{ infoModal.server.qq_group }}</code>
            <button class="copy-btn" @click="copyText(infoModal.server.qq_group, 'qq')">
              <span v-if="copied === 'qq'">✓</span><span v-else>复制</span>
            </button>
          </div>
        </div>
        <div v-else-if="infoModal.server?.qq_group" class="info-connect-block">
          <div class="info-connect-title">联系方式</div>
          <div class="info-connect-row">
            <span class="info-connect-label">QQ 群</span>
            <code class="info-connect-val">{{ infoModal.server.qq_group }}</code>
            <button class="copy-btn" @click="copyText(infoModal.server.qq_group, 'qq')">
              <span v-if="copied === 'qq'">✓</span><span v-else>复制</span>
            </button>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="infoModal.open = false">关闭</button>
          <button
            class="btn btn-primary"
            :disabled="isAlreadyMember(infoModal.server?.id)"
            @click="joinFromInfo">
            {{ isAlreadyMember(infoModal.server?.id) ? '已加入' : '加入服务器' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 编辑服务器弹窗 -->
    <div v-if="editModal.open" class="modal-overlay" @click.self="editModal.open = false">
      <div class="modal modal-wide">
        <h3 class="modal-title">项目设置</h3>
        <label class="modal-label">服务器名称 <span class="required">*</span></label>
        <input v-model="editModal.name" class="modal-input" placeholder="服务器名称" maxlength="50" />
        <label class="modal-label">介绍</label>
        <textarea v-model="editModal.desc" class="modal-input modal-textarea" placeholder="服务器介绍（可留空）" maxlength="200" />
        <div class="modal-row-2">
          <div>
            <label class="modal-label">游戏 IP</label>
            <input v-model="editModal.game_ip" class="modal-input" placeholder="如 play.example.com" maxlength="100" />
          </div>
          <div>
            <label class="modal-label">端口</label>
            <input v-model.number="editModal.game_port" class="modal-input" type="number" min="1" max="65535" placeholder="7777" />
          </div>
        </div>
        <div>
          <label class="modal-label">QQ 群号</label>
          <input v-model="editModal.qq_group" class="modal-input" placeholder="可选" maxlength="20" />
        </div>
        <div class="modal-toggle-row">
          <label class="srv-toggle-wrap">
            <label class="srv-toggle">
              <input type="checkbox" v-model="editModal.isPublic" />
              <span class="srv-toggle-track"><span class="srv-toggle-thumb"></span></span>
            </label>
            <span class="srv-toggle-text">公开此服务器（显示在公共频道，其他玩家可加入）</span>
          </label>
        </div>
        <div class="modal-toggle-row">
          <label class="srv-toggle-wrap">
            <label class="srv-toggle">
              <input type="checkbox" v-model="editModal.showIp" />
              <span class="srv-toggle-track"><span class="srv-toggle-thumb"></span></span>
            </label>
            <span class="srv-toggle-text">在公开介绍中显示 IP 地址</span>
          </label>
        </div>
        <p v-if="editModal.error" class="modal-error">{{ editModal.error }}</p>
        <div class="modal-footer">
          <button class="btn btn-secondary" @click="editModal.open = false">取消</button>
          <button class="btn btn-primary" :disabled="editModal.loading" @click="submitEdit">
            {{ editModal.loading ? '保存中...' : '保存修改' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, inject, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getEmail } from '@/api/auth'
import {
  claimServer, joinServer, listServers, listPublicServers,
  getServer, leaveServer, kickMember, dissolveServer, updateServer
} from '@/api/servers'

// 全局服务器列表刷新（MainLayout 提供）
const globalReloadServers = inject('reloadServers', null)
const layoutServers       = inject('myServers', ref([]))
const activeServerKey     = inject('activeServerKey', ref(''))
const route  = useRoute()
const router = useRouter()

function normalizeAgentKey(v) {
  return String(v || '').trim()
}

function getLayoutOnlineMap() {
  const m = new Map()
  for (const s of layoutServers.value || []) {
    m.set(normalizeAgentKey(s.agent_key), !!s.online)
  }
  return m
}

function syncOnlineBadgesFromLayout() {
  const onlineMap = getLayoutOnlineMap()
  myServers.value = myServers.value.map(s => {
    const key = normalizeAgentKey(s.agent_key)
    if (!onlineMap.has(key)) return s
    return { ...s, online: onlineMap.get(key) }
  })
  publicServers.value = publicServers.value.map(s => {
    const key = normalizeAgentKey(s.agent_key)
    if (!onlineMap.has(key)) return s
    return { ...s, online: onlineMap.get(key) }
  })
}

// ── Tab ──────────────────────────────────────────────────────
function normalizeTab(tab) {
  return ['public', 'mine', 'joined'].includes(tab) ? tab : 'mine'
}

const activeTab = ref(normalizeTab(route.query.tab))

// ── 基础状态 ─────────────────────────────────────────────────
const myServers     = ref([])   // 我参与的服务器（owner + member）
const publicServers = ref([])   // 公共服务器列表
const loading       = ref(true)
const currentUserId = ref(null)
const mineSearch    = ref('')
const joinedSearch  = ref('')
const detailModal   = ref({ open: false, data: null, isOwner: false })
// 分组计算
const myOwnedServers  = computed(() => myServers.value.filter(s => s.owner_id === currentUserId.value))
const myJoinedServers = computed(() => myServers.value.filter(s => s.owner_id !== currentUserId.value))
const filteredMineServers = computed(() => {
  const q = mineSearch.value.trim().toLowerCase()
  if (!q) return myOwnedServers.value
  return myOwnedServers.value.filter(s => s.name.toLowerCase().includes(q))
})
const filteredJoinedServers = computed(() => {
  const q = joinedSearch.value.trim().toLowerCase()
  if (!q) return myJoinedServers.value
  return myJoinedServers.value.filter(s => s.name.toLowerCase().includes(q))
})

const claimModal = ref({ open: false, key: '', name: '', desc: '', isPublic: false, showIp: true, game_ip: '', game_port: null, qq_group: '', error: '', loading: false })
const infoModal  = ref({ open: false, server: null })
const editModal  = ref({ open: false, id: null, name: '', desc: '', isPublic: false, showIp: true, game_ip: '', game_port: null, qq_group: '', error: '', loading: false })

// 公共频道搜索
const publicSearch = ref('')
const filteredPublicServers = computed(() => {
  const q = publicSearch.value.trim().toLowerCase()
  if (!q) return publicServers.value
  return publicServers.value.filter(s =>
    s.name.toLowerCase().includes(q) ||
    (s.description && s.description.toLowerCase().includes(q))
  )
})

// ── 工具 ─────────────────────────────────────────────────────
function formatTime(ts) {
  return new Date(ts * 1000).toLocaleDateString('zh-CN')
}

function isAlreadyMember(serverId) {
  return myServers.value.some(s => s.id === serverId)
}

// ── 数据加载 ─────────────────────────────────────────────────
async function loadAll() {
  loading.value = true
  try {
    const [mine, pub] = await Promise.all([listServers(), listPublicServers()])
    myServers.value     = mine
    publicServers.value = pub
    syncOnlineBadgesFromLayout()
    // 用 email 反查当前用户 id（通过第一条含成员信息的服务器详情）
    if (!currentUserId.value && mine.length) {
      const d = await getServer(mine[0].id).catch(() => null)
      if (d) {
        const myEmail = getEmail()
        const me = d.members.find(m => m.email === myEmail)
        if (me) currentUserId.value = me.user_id
      }
    }
  } catch(e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function selectServer(s) {
  try {
    const data = await getServer(s.id)
    if (!currentUserId.value) {
      const myEmail = getEmail()
      const me = data.members.find(m => m.email === myEmail)
      if (me) currentUserId.value = me.user_id
    }
    detailModal.value = { open: true, data, isOwner: data.owner_id === currentUserId.value }
  } catch(e) {
    console.error(e)
  }
}

function openEditFromDetail() {
  openEditModal(detailModal.value.data)
  detailModal.value.open = false
}

// ── 查看介绍弹窗 ─────────────────────────────────────────────
function openInfoModal(s) {
  infoModal.value = { open: true, server: s }
}

async function joinFromInfo() {
  const s = infoModal.value.server
  if (!s || isAlreadyMember(s.id)) return
  infoModal.value.open = false
  await joinPublicServer(s)
}

// ── 编辑服务器弹窗 ────────────────────────────────────────────
function openEditModal(s) {
  editModal.value = {
    open: true, id: s.id,
    name: s.name, desc: s.description || '',
    isPublic: s.is_public, showIp: s.show_ip ?? true,
    game_ip: s.game_ip || '', game_port: s.game_port || null,
    qq_group: s.qq_group || '',
    error: '', loading: false,
  }
}

async function submitEdit() {
  if (!editModal.value.name.trim()) { editModal.value.error = '服务器名称不能为空'; return }
  editModal.value.loading = true
  editModal.value.error = ''
  try {
    await updateServer(editModal.value.id, {
      name:         editModal.value.name.trim(),
      description:  editModal.value.desc,
      is_public:    editModal.value.isPublic,
      show_ip:      editModal.value.showIp,
      game_ip:      editModal.value.game_ip,
      game_port:    editModal.value.game_port || null,
      qq_group:     editModal.value.qq_group,
    })
    editModal.value.open = false
    await loadAll()
    if (globalReloadServers) await globalReloadServers()
  } catch(e) {
    editModal.value.error = e.message
  } finally {
    editModal.value.loading = false
  }
}

// ── 切换当前服务器 ────────────────────────────────────────────
function switchToServer(s) {
  activeServerKey.value = s.agent_key
  localStorage.setItem('active_agent_key', s.agent_key)
}
// ── 复制到剪贴板 ─────────────────────────────────
const copied = ref('')
let _copyTimer = null
function copyText(text, key) {
  navigator.clipboard.writeText(text).catch(() => {
    const ta = document.createElement('textarea')
    ta.value = text
    ta.style.cssText = 'position:fixed;opacity:0;pointer-events:none'
    document.body.appendChild(ta); ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
  })
  copied.value = key
  clearTimeout(_copyTimer)
  _copyTimer = setTimeout(() => { copied.value = '' }, 1500)
}
// ── 认领 ─────────────────────────────────────────────────────
function openClaimModal() {
  Object.assign(claimModal.value, { open: true, key: '', name: '', desc: '', isPublic: false, showIp: true, game_ip: '', game_port: null, qq_group: '', error: '', loading: false })
}

async function submitClaim() {
  if (!claimModal.value.key || !claimModal.value.name) {
    claimModal.value.error = 'Agent Key 和名称为必填项'
    return
  }
  claimModal.value.loading = true
  claimModal.value.error = ''
  try {
    await claimServer(
      claimModal.value.key, claimModal.value.name,
      claimModal.value.desc, claimModal.value.isPublic,
      {
        game_ip:  claimModal.value.game_ip,
        game_port: claimModal.value.game_port || null,
        qq_group: claimModal.value.qq_group,
        show_ip:  claimModal.value.showIp,
      }
    )
    claimModal.value.open = false
    await loadAll()
    if (globalReloadServers) await globalReloadServers()
  } catch(e) {
    claimModal.value.error = e.message
  } finally {
    claimModal.value.loading = false
  }
}

// ── 加入公共服务器 ────────────────────────────────────────────
async function joinPublicServer(s) {
  if (isAlreadyMember(s.id)) return
  if (!confirm(`确定加入「${s.name}」吗？`)) return
  try {
    await joinServer(s.id)
    await loadAll()
    if (globalReloadServers) await globalReloadServers()
    activeTab.value = 'joined'
  } catch(e) {
    alert(e.message)
  }
}

// ── 离开 / 解散 / 踢人 ───────────────────────────────────────
async function handleLeave() {
  if (!confirm('确定要离开该服务器吗？')) return
  try {
    await leaveServer(detailModal.value.data.id)
    detailModal.value.open = false
    await loadAll()
    if (globalReloadServers) await globalReloadServers()
  } catch(e) { alert(e.message) }
}

async function handleDissolve() {
  if (!confirm('确定要解散该服务器吗？此操作不可撤销')) return
  try {
    await dissolveServer(detailModal.value.data.id)
    detailModal.value.open = false
    await loadAll()
    if (globalReloadServers) await globalReloadServers()
  } catch(e) { alert(e.message) }
}

async function handleKick(userId) {
  if (!confirm('确定踢出该用户吗？')) return
  try {
    await kickMember(detailModal.value.data.id, userId)
    detailModal.value.data = await getServer(detailModal.value.data.id)
  } catch(e) { alert(e.message) }
}

onMounted(loadAll)

watch(layoutServers, () => {
  syncOnlineBadgesFromLayout()
}, { deep: true })

watch(
  () => route.query.tab,
  (tab) => {
    const normalized = normalizeTab(tab)
    if (normalized !== activeTab.value) activeTab.value = normalized
  }
)

watch(activeTab, (tab) => {
  if (route.query.tab === tab) return
  router.replace({ query: { ...route.query, tab } })
})
</script>

<style scoped>
.servers-page {
  padding: 28px 32px;
  min-height: 100%;
  box-sizing: border-box;
  overflow-y: auto;
}

/* ── 页头 ── */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 18px;
}
.page-title { font-size: 1.4rem; font-weight: 700; color: #1e293b; margin: 0; }

/* ── Tab 导航 ── */
.tab-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 22px;
  border-bottom: 2px solid #e2e8f0;
  padding-bottom: 0;
}
.tab-btn {
  padding: 8px 18px;
  border: none;
  background: none;
  font-size: 0.9rem;
  color: #64748b;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  border-radius: 4px 4px 0 0;
  transition: color .15s;
  display: flex; align-items: center; gap: 6px;
}
.tab-btn:hover { color: #3b82f6; }
.tab-btn.active { color: #3b82f6; border-bottom-color: #3b82f6; font-weight: 600; }
.tab-count {
  background: #eff6ff; color: #3b82f6;
  font-size: 11px; font-weight: 700;
  padding: 1px 6px; border-radius: 10px;
}

/* ── 按钮 ── */
.btn {
  padding: 8px 18px;
  border-radius: 7px;
  border: none;
  cursor: pointer;
  font-size: 0.88rem;
  font-weight: 500;
  transition: opacity .15s, background .15s;
  display: inline-flex; align-items: center; gap: 6px;
}
.btn svg { width: 14px; height: 14px; flex-shrink: 0; }
.btn:disabled { opacity: .55; cursor: default; }
.tab-btn svg { width: 16px; height: 16px; flex-shrink: 0; }
.btn-primary   { background: #3b82f6; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #2563eb; }
.btn-secondary { background: #e2e8f0; color: #374151; }
.btn-secondary:hover { background: #cbd5e1; }
.btn-outline   { background: transparent; border: 1px solid #cbd5e1; color: #374151; }
.btn-outline:hover { background: #f1f5f9; }
.btn-danger    { background: #ef4444; color: #fff; }
.btn-danger:hover { background: #dc2626; }
.btn-sm        { padding: 4px 12px; font-size: 0.8rem; }
.btn-lg        { padding: 12px 32px; font-size: 0.95rem; border-radius: 8px; margin-bottom: 14px; }

/* ── 卡片网格 ── */
.server-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.server-card {
  background: #fff;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  padding: 18px 20px;
  cursor: pointer;
  transition: border-color .15s, box-shadow .15s;
}
.server-card:hover    { border-color: #93c5fd; box-shadow: 0 2px 8px rgba(59,130,246,.12); }
.server-card.selected { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.15); }
.public-card { cursor: default; }
.public-card:hover { border-color: #a5b4fc; box-shadow: none; }

.card-header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
}
.card-badges { display: flex; gap: 5px; flex-wrap: wrap; justify-content: flex-end; }
.server-name { font-weight: 600; color: #1e293b; font-size: 1rem; }
.server-desc {
  font-size: 0.84rem; color: #64748b; margin-bottom: 10px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.server-meta { font-size: 0.8rem; color: #94a3b8; }

.card-footer-row {
  display: flex; align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}
.meta-text { font-size: 0.8rem; color: #94a3b8; }

.card-meta-row {
  display: flex; gap: 8px; flex-wrap: wrap;
  margin: 6px 0 0;
}
.meta-chip {
  font-size: 0.78rem; color: #64748b;
  background: #f1f5f9; padding: 2px 8px;
  border-radius: 20px;
}

.online-badge {
  font-size: 0.72rem; padding: 2px 7px;
  border-radius: 20px; font-weight: 500;
}
.online-badge.online  { background: #dcfce7; color: #16a34a; }
.online-badge.offline { background: #f1f5f9; color: #94a3b8; }

.role-tag {
  padding: 2px 8px; border-radius: 20px;
  font-size: 0.72rem; font-weight: 500;
  background: #eff6ff; color: #2563eb;
}
.role-tag.member { background: #f1f5f9; color: #64748b; }

.badge-public {
  padding: 2px 7px; border-radius: 20px;
  font-size: 0.72rem; font-weight: 500;
  background: #fef3c7; color: #d97706;
}

/* ── 空状态 ── */
.empty-tab {
  text-align: center; padding: 70px 0; color: #94a3b8;
}
.empty-icon { font-size: 2.5rem; margin-bottom: 10px; }
.empty-icon-wrap {
  display: flex; align-items: center; justify-content: center;
  width: 64px; height: 64px; margin: 0 auto 14px;
  background: #f1f5f9; border-radius: 16px;
}
.empty-icon-wrap svg { width: 32px; height: 32px; stroke: #94a3b8; }
.empty-tab p { margin: 4px 0; }
.empty-hint { font-size: 0.84rem; }

/* ── 引导空白页 ── */
.onboarding-empty {
  display: flex; flex-direction: column;
  align-items: center; padding: 50px 0 30px;
  text-align: center;
}
.onboard-hero { margin-bottom: 36px; }
.onboard-icon { font-size: 3rem; margin-bottom: 12px; }
.onboard-icon-wrap {
  display: flex; align-items: center; justify-content: center;
  width: 72px; height: 72px; margin: 0 auto 16px;
  background: #eff6ff; border-radius: 18px;
}
.onboard-icon-wrap svg { width: 38px; height: 38px; stroke: #3b82f6; }
.onboard-hero h2 { font-size: 1.4rem; font-weight: 700; color: #1e293b; margin: 0 0 6px; }
.onboard-sub  { font-size: 0.88rem; color: #64748b; margin: 0; }
.steps { display: flex; align-items: flex-start; gap: 14px; margin-bottom: 32px; flex-wrap: wrap; justify-content: center; }
.step {
  display: flex; align-items: flex-start; gap: 10px;
  background: #fff; border: 1px solid #e2e8f0;
  border-radius: 10px; padding: 16px 18px;
  max-width: 200px; text-align: left;
}
.step-arrow { align-self: center; font-size: 1.2rem; color: #cbd5e1; }
.step-num {
  width: 26px; height: 26px; border-radius: 50%;
  background: #3b82f6; color: #fff;
  font-size: 0.8rem; font-weight: 700;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
}
.step-body strong { display: block; font-size: 0.84rem; color: #1e293b; margin-bottom: 3px; }
.step-body p      { font-size: 0.76rem; color: #64748b; margin: 0; line-height: 1.5; }
.step-body code   { background: #f1f5f9; padding: 1px 4px; border-radius: 4px; font-size: .74rem; }

/* ── 详情面板 ── */
.detail-panel {
  background: #fff; border: 1.5px solid #e2e8f0;
  border-radius: 10px; padding: 22px 26px; margin-top: 4px;
}
.detail-header {
  display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 12px;
}
.detail-header h2 { margin: 0; font-size: 1.1rem; color: #1e293b; }
.detail-meta {
  display: flex; gap: 20px; flex-wrap: wrap; align-items: center;
  font-size: 0.84rem; color: #64748b; margin-bottom: 16px;
}
.detail-hint {
  font-size: 0.82rem; color: #94a3b8;
  background: #f1f5f9; padding: 2px 10px; border-radius: 20px;
}

/* ── 成员表格 ── */
.members-table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
.members-table th {
  text-align: left; padding: 8px 12px;
  background: #f8fafc; border-bottom: 1px solid #e2e8f0;
  color: #475569; font-weight: 500;
}
.members-table td { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; color: #374151; }
.members-table tr:last-child td { border-bottom: none; }

/* ── 加载 ── */
.loading-state { text-align: center; padding: 60px; color: #94a3b8; }

/* ── 弹窗 ── */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.35);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
  z-index: 1000;
  overflow-y: auto;
}
.modal {
  background: #fff; border-radius: 12px;
  padding: 28px 32px; width: 420px;
  max-width: 100%; max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 8px 32px rgba(0,0,0,.15);
  box-sizing: border-box;
}
.modal-wide {
  width: 560px;
}
.modal-row-2 {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
}
.modal-row-2 .modal-input { margin-bottom: 14px; }
.modal-title  { font-size: 1.1rem; font-weight: 600; color: #1e293b; margin: 0 0 10px; }
.modal-tip    { font-size: 0.82rem; color: #64748b; margin: 0 0 16px; }
.modal-tip code { background: #f1f5f9; padding: 1px 4px; border-radius: 4px; }
.modal-label  { display: block; font-size: 0.84rem; color: #475569; margin-bottom: 5px; }
.required     { color: #ef4444; }
.modal-input  {
  width: 100%; box-sizing: border-box;
  padding: 9px 12px; border: 1.5px solid #e2e8f0;
  border-radius: 7px; font-size: 0.9rem;
  outline: none; margin-bottom: 14px;
  transition: border-color .15s;
}
.modal-input:focus { border-color: #3b82f6; }
.modal-toggle-row { margin-bottom: 14px; }
.srv-toggle-wrap { display: flex; align-items: flex-start; gap: 10px; cursor: pointer; font-size: 0.85rem; color: #475569; }
.srv-toggle-text { padding-top: 3px; line-height: 1.5; }
.srv-toggle { display: inline-flex; align-items: center; cursor: pointer; user-select: none; flex-shrink: 0; }
.srv-toggle input { position: absolute; opacity: 0; width: 0; height: 0; }
.srv-toggle-track { position: relative; width: 40px; height: 22px; background: #e2e8f0; border-radius: 11px; transition: background 0.2s; }
.srv-toggle input:checked + .srv-toggle-track { background: #3b82f6; }
.srv-toggle-thumb { position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; background: #fff; border-radius: 50%; transition: transform 0.2s; box-shadow: 0 1px 3px rgba(0,0,0,0.15); }
.srv-toggle input:checked + .srv-toggle-track .srv-toggle-thumb { transform: translateX(18px); }
.modal-error  { font-size: 0.84rem; color: #ef4444; margin: -8px 0 10px; }
.modal-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 4px; }
.modal-textarea { resize: vertical; min-height: 80px; font-family: inherit; }

/* ── 查看介绍弹窗 ── */
.modal-info { max-width: 400px; }
.modal-info-header { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.modal-info-header .modal-title { margin: 0; flex: 1; }
.modal-info-desc { font-size: 0.9rem; color: #374151; line-height: 1.6; margin: 0 0 14px; white-space: pre-wrap; word-break: break-word; overflow-wrap: break-word; }
.modal-info-meta { font-size: 0.84rem; color: #64748b; margin-bottom: 12px; display: flex; gap: 14px; }

.info-connect-block {
  background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 8px; padding: 12px 14px; margin-bottom: 14px;
}
.info-connect-title { font-size: 0.78rem; font-weight: 600; color: #475569; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .05em; }
.info-connect-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.info-connect-row:last-child { margin-bottom: 0; }
.info-connect-label { font-size: 0.8rem; color: #94a3b8; min-width: 44px; flex-shrink: 0; }
.info-connect-val { font-size: 0.88rem; color: #1e293b; background: #fff; padding: 2px 7px; border-radius: 5px; border: 1px solid #e2e8f0; flex: 1; min-width: 0; word-break: break-all; }
.copy-btn {
  flex-shrink: 0;
  padding: 2px 9px; border-radius: 5px;
  border: 1px solid #e2e8f0; background: #f8fafc;
  color: #475569; font-size: 0.78rem; cursor: pointer;
  transition: background .12s, color .12s;
  white-space: nowrap;
}
.copy-btn:hover { background: #eff6ff; color: #2563eb; border-color: #bfdbfe; }
.info-connect-label { font-size: 0.8rem; color: #94a3b8; min-width: 44px; flex-shrink: 0; }
.info-connect-val { font-size: 0.88rem; color: #1e293b; background: #fff; padding: 2px 7px; border-radius: 5px; border: 1px solid #e2e8f0; flex: 1; min-width: 0; word-break: break-all; }
.copy-btn {
  flex-shrink: 0;
  padding: 2px 9px; border-radius: 5px;
  border: 1px solid #e2e8f0; background: #f8fafc;
  color: #475569; font-size: 0.78rem; cursor: pointer;
  transition: background .12s, color .12s;
  white-space: nowrap;
}
.copy-btn:hover { background: #eff6ff; color: #2563eb; border-color: #bfdbfe; }

/* ── 搜索栏 ── */
.search-bar {
  display: flex; align-items: center; gap: 8px;
  background: #fff; border: 1.5px solid #e2e8f0;
  border-radius: 8px; padding: 7px 12px;
  margin-bottom: 16px;
}
.search-bar svg { width: 16px; height: 16px; stroke: #94a3b8; flex-shrink: 0; }
.search-input { flex: 1; border: none; outline: none; font-size: 0.9rem; color: #374151; background: none; }
.search-clear { background: none; border: none; cursor: pointer; color: #94a3b8; font-size: 14px; padding: 0 2px; line-height: 1; }
.search-clear:hover { color: #64748b; }

/* ── 已加入的"当前"标记 ── */
.badge-active {
  padding: 2px 7px; border-radius: 20px;
  font-size: 0.72rem; font-weight: 600;
  background: #dcfce7; color: #16a34a;
}
.server-card.active-server { border-color: #86efac; }

/* ── 服务器详情弹窗 ── */
.modal-detail { width: 480px; }
</style>
