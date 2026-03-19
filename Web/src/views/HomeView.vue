<template>
  <div class="home-page">
    <section class="hero">
      <div>
        <h1>欢迎来到 TShock 平台主页</h1>
        <p>
          这里支持普通玩家、服主和受授权的平台管理员协作使用。
          先根据你的目标选择入口，再进入具体功能页面。
        </p>
      </div>
      <router-link to="/servers?tab=public" class="hero-action">进入服务器列表</router-link>
    </section>

    <section class="role-grid">
      <article class="role-card player">
        <h2>玩家</h2>
        <p class="role-desc">加入公开服务器或受邀服务器。</p>
        <ul>
          <li>浏览公共频道并加入服务器</li>
          <li>查看你已加入的服务器状态</li>
          <li>可使用玩家相关功能</li>
        </ul>
        <router-link to="/servers?tab=public" class="role-link">从“公共频道”开始</router-link>
      </article>

      <article class="role-card owner">
        <h2>服主</h2>
        <p class="role-desc">绑定你的 TShock，统一管理服务器并向成员授予权限。</p>
        <ul>
          <li>绑定 Agent Key 管理你的服务器</li>
          <li>在控制台执行运维指令</li>
          <li>向成员授予平台管理权限</li>
        </ul>
        <div class="role-actions">
          <router-link to="/servers" class="role-link">添加或管理服务器</router-link>
          <router-link to="/dashboard" class="role-link ghost">查看连接仪表盘</router-link>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup>
</script>

<style scoped>
.home-page {
  height: 100%;
  overflow-y: auto;
  box-sizing: border-box;
  padding: 28px 32px;
  color: #102a43;
}

.hero {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  align-items: center;
  background: linear-gradient(120deg, #e8f5e9 0%, #e0f2fe 100%);
  border: 1px solid #bae6fd;
  border-radius: 14px;
  padding: 24px 26px;
  margin-bottom: 22px;
}
.hero h1 {
  margin: 0 0 8px;
  font-size: 24px;
  color: #0f172a;
}
.hero p {
  margin: 0;
  max-width: 680px;
  line-height: 1.65;
  font-size: 14px;
  color: #334155;
}
.hero-action {
  flex-shrink: 0;
  background: #0f766e;
  color: #ffffff;
  text-decoration: none;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 700;
}
.hero-action:hover {
  background: #115e59;
}

.role-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 18px;
}

.role-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 20px;
}
.role-card h2 {
  margin: 0 0 8px;
  font-size: 20px;
  color: #0f172a;
}
.role-desc {
  margin: 0 0 10px;
  color: #475569;
  font-size: 14px;
  line-height: 1.6;
}
.role-card ul {
  margin: 0 0 14px;
  padding-left: 18px;
  color: #334155;
  line-height: 1.65;
  font-size: 13px;
}

.player {
  box-shadow: inset 0 0 0 1px #dbeafe;
}
.owner {
  box-shadow: inset 0 0 0 1px #bbf7d0;
}

.role-link {
  display: inline-block;
  color: #ffffff;
  background: #2563eb;
  text-decoration: none;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
}
.role-link:hover {
  background: #1d4ed8;
}

.role-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.role-link.ghost {
  background: #f8fafc;
  color: #0f172a;
  border: 1px solid #cbd5e1;
}
.role-link.ghost:hover {
  background: #f1f5f9;
}

.notice-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 16px 18px;
}
.notice-card h3 {
  margin: 0 0 6px;
  font-size: 16px;
  color: #0f172a;
}
.notice-card p {
  margin: 0;
  font-size: 13px;
  color: #475569;
  line-height: 1.7;
}

@media (max-width: 900px) {
  .home-page {
    padding: 18px;
  }
  .hero {
    flex-direction: column;
    align-items: flex-start;
  }
  .role-grid {
    grid-template-columns: 1fr;
  }
}
</style>
