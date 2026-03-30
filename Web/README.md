# Web 前端部署说明

本目录是 Vue 3 + Vite 前端，可部署到任意静态托管平台。

## 1. 本地开发

1. 安装依赖

```bash
npm ci
```

2. 启动开发服务器

```bash
npm run dev
```

默认会通过 Vite 代理把 /api 转发到 VITE_API_PROXY_TARGET。

## 2. 环境变量

可参考 .env.example。

- VITE_API_PROXY_TARGET: 本地开发代理目标，仅开发时生效
- VITE_API_BASE: 生产环境后端基础地址，例如 https://api.example.com
- VITE_WS_BASE: WebSocket 基地址，例如 wss://api.example.com
- VITE_PUBLIC_BASE: 前端发布子路径，默认 /

说明：

- 如果是根路径部署（例如 https://example.com/），VITE_PUBLIC_BASE 用 /
- 如果是子路径部署（例如 https://user.github.io/repo/），VITE_PUBLIC_BASE 用 /repo/

## 3. 构建

```bash
npm run build
```

产物在 dist 目录。

## 4. GitHub Pages（GitHub Actions）

仓库内已提供工作流：

- .github/workflows/deploy-web-pages.yml

建议按下面步骤配置：

1. 打开仓库 Settings -> Pages
2. Build and deployment -> Source 选择 GitHub Actions
3. 打开 Settings -> Environments -> github-pages
4. Deployment branches and tags 里允许分支
5. Environment secrets 通常不用填（本项目前端构建不需要敏感值）
6. Environment variables 里新增：

- VITE_API_BASE = 你的后端 HTTPS 地址（示例：https://api.example.com）
- VITE_WS_BASE = 你的后端 WSS 地址（示例：wss://api.example.com）

触发方式：

1. 向 master 推送一次 Web 目录相关改动，或
2. 在 Actions 页手动运行 Deploy Web To Pages（workflow_dispatch）

首次部署成功后，访问地址一般是：

- https://<你的用户名>.github.io/<仓库名>/

## 5. 其他平台部署

### 5.1 Vercel

1. 导入仓库
2. Root Directory 选择 Web
3. Build Command: npm run build
4. Output Directory: dist
5. 环境变量配置：VITE_API_BASE、VITE_WS_BASE、VITE_PUBLIC_BASE

推荐：VITE_PUBLIC_BASE 设置为 /

### 5.2 Netlify

1. Base directory: Web
2. Build command: npm run build
3. Publish directory: Web/dist
4. 环境变量配置：VITE_API_BASE、VITE_WS_BASE、VITE_PUBLIC_BASE

### 5.3 自托管（Nginx/Caddy/静态文件服务器）

1. 本地构建得到 dist
2. 把 dist 全量上传到站点目录
3. 确保前端域名能访问后端 API 和 WS
4. 若开启了后端 CORS 白名单，需要把前端域名加入白名单

## 6. 常见问题

### 6.1 页面能打开但接口全部失败

通常是 VITE_API_BASE 没配置或配置错了。浏览器 Network 里若请求打到 github.io 域名下的 /api，就是这个问题。

### 6.2 实时状态不更新

检查 VITE_WS_BASE 是否是正确的 ws/wss 地址，并确认反向代理已放行 WebSocket 升级连接。

### 6.3 刷新后 404

本项目使用 hash 路由（#/path），一般不会因刷新导致 404；若你改成 history 路由，需要在服务器配置回退到 index.html。
