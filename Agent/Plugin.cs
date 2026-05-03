using System;
using System.Threading;
using System.Threading.Tasks;
using TShockAPI;
using TShockAPI.Hooks;
using Terraria;
using TerrariaApi.Server;
using TerrariaManagerAgent.Services;

namespace TerrariaManagerAgent
{
    [ApiVersion(2, 1)]
    public class ManagerAgent : TerrariaPlugin
    {
        private WebSocketService _wsService;
        private CommandHandler _cmdHandler;
        private RuntimeBroadcastService _runtimeService;
        private string _currentBackendUrl = string.Empty;
        private string _currentAgentKey = string.Empty;

        // 插件生命周期取消令牌（用于快速中断后台循环）
        private readonly CancellationTokenSource _pluginCts = new CancellationTokenSource();

        public override string Name => "TerrariaManagerAgent";
        public override Version Version => new Version(1, 2, 3);
        public override string Author => "熙恩";
        public override string Description => "TShock 远程管理代理插件";

        public ManagerAgent(Main game) : base(game) { }

        /// <summary>
        /// 插件初始化：注册钩子并启动后台服务
        /// </summary>
        public override void Initialize()
        {
            try
            {
                // 0. 加载配置文件
                var config = AgentConfigService.LoadConfig(TShock.SavePath);

                // 1. 初始化模块
                _wsService = new WebSocketService(config.BackendUrl, config.AgentKey);
                _runtimeService = new RuntimeBroadcastService(_wsService);
                _cmdHandler = new CommandHandler(_wsService, _runtimeService);
                AgentLog.SetDebugEnabled(config.DebugEnabled);
                CommandHandler.SetAuditLevel(config.AuditLevel);
                _currentBackendUrl = config.BackendUrl ?? string.Empty;
                _currentAgentKey = config.AgentKey ?? string.Empty;

                // 2. 初始化 Agent 本地数据库
                AgentLocalStore.Init();
                StatsTracker.Init();

                // 3. 注册消息接收回调：当 WS 收到消息时，交给 CommandHandler 处理
                _wsService.OnMessageReceived += _cmdHandler.ProcessRawMessage;

                // 4. 异步启动 WebSocket 连接循环
                _ = _wsService.StartAsync();

                // 5. 启动周期任务
                _ = Task.Run(() => _runtimeService.StatusBroadcastLoop(_pluginCts.Token));
                _ = Task.Run(() => _runtimeService.DeathDetectionLoop(_pluginCts.Token));

                // 6. 注册 TShock 钩子
                ServerApi.Hooks.ServerChat.Register(this, _runtimeService.OnChat);
                ServerApi.Hooks.ServerJoin.Register(this, _runtimeService.OnPlayerJoin);
                ServerApi.Hooks.ServerLeave.Register(this, _runtimeService.OnPlayerLeave);
                PlayerHooks.PlayerPostLogin += _runtimeService.OnPlayerPostLogin;
                PlayerHooks.PlayerLogout += _runtimeService.OnPlayerLogout;
                GeneralHooks.ReloadEvent += OnReload;

                // 7. 如果是重启后首次启动，还原启动脚本（移除临时循环）
                StartupScriptService.CleanupRestartScript();

                AgentLog.Info("Lifecycle", "plugin_initialized",
                    ("backend_url", _currentBackendUrl),
                    ("audit_level", config.AuditLevel));
            }
            catch (Exception ex)
            {
                AgentLog.Error("Lifecycle", "plugin_initialize_failed", ("error", ex.Message));
            }
        }

        /// <summary>
        /// 插件卸载：清理资源，关闭连接
        /// </summary>
        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                try
                {
                    // 注销钩子
                    if (_runtimeService != null)
                    {
                        ServerApi.Hooks.ServerChat.Deregister(this, _runtimeService.OnChat);
                        ServerApi.Hooks.ServerJoin.Deregister(this, _runtimeService.OnPlayerJoin);
                        ServerApi.Hooks.ServerLeave.Deregister(this, _runtimeService.OnPlayerLeave);
                        PlayerHooks.PlayerPostLogin -= _runtimeService.OnPlayerPostLogin;
                        PlayerHooks.PlayerLogout -= _runtimeService.OnPlayerLogout;
                    }
                    GeneralHooks.ReloadEvent -= OnReload;

                    // 取消后台循环（Task.Delay 立即中断）
                    _pluginCts.Cancel();

                    // 刷盘当前在线会话时长，避免重载/停服丢失在线统计
                    StatsTracker.FlushAllOnlineSessions();

                    // 释放服务资源（关闭连接，取消 Token）
                    _wsService?.Dispose();
                    
                    AgentLog.Info("Lifecycle", "plugin_disposed");
                }
                catch (Exception ex)
                {
                    AgentLog.Error("Lifecycle", "plugin_dispose_failed", ("error", ex.Message));
                }
            }
            base.Dispose(disposing);
        }

        private void OnReload(ReloadEventArgs args)
        {
            try
            {
                var config = AgentConfigService.LoadConfig(TShock.SavePath);
                AgentLog.SetDebugEnabled(config.DebugEnabled);
                CommandHandler.SetAuditLevel(config.AuditLevel);

                var backendChanged = !string.Equals(_currentBackendUrl, config.BackendUrl ?? string.Empty, StringComparison.OrdinalIgnoreCase);
                var agentKeyChanged = !string.Equals(_currentAgentKey, config.AgentKey ?? string.Empty, StringComparison.OrdinalIgnoreCase);

                _currentBackendUrl = config.BackendUrl ?? string.Empty;
                _currentAgentKey = config.AgentKey ?? string.Empty;

                if (backendChanged || agentKeyChanged)
                {
                    args.Player?.SendWarningMessage("[Agent] 配置已重读，但 BackendUrl/AgentKey 变更需重启服务器后生效");
                    AgentLog.Warn("Config", "reload_requires_restart",
                        ("backend_changed", backendChanged),
                        ("agent_key_changed", agentKeyChanged),
                        ("audit_level", config.AuditLevel),
                        ("debug_enabled", config.DebugEnabled));
                }
                else
                {
                    args.Player?.SendSuccessMessage("[Agent] 配置已重读并生效（AuditLevel 已更新）");
                    AgentLog.Info("Config", "reload_applied",
                        ("audit_level", config.AuditLevel),
                        ("debug_enabled", config.DebugEnabled));
                }
            }
            catch (Exception ex)
            {
                args.Player?.SendErrorMessage($"[Agent] 重读配置失败: {ex.Message}");
                AgentLog.Error("Config", "reload_failed", ("error", ex.Message));
            }
        }
    }
}
