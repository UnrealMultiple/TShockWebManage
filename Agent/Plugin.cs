using System;
using System.Threading;
using System.Threading.Tasks;
using TShockAPI;
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

        // 插件生命周期取消令牌（用于快速中断后台循环）
        private readonly CancellationTokenSource _pluginCts = new CancellationTokenSource();

        public override string Name => "RemoteManagerAgent";
        public override Version Version => new Version(1, 2, 0);
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
                _cmdHandler = new CommandHandler(_wsService);
                _runtimeService = new RuntimeBroadcastService(_wsService);
                CommandHandler.SetAuditLevel(config.AuditLevel);

                // 2. 注册消息接收回调：当 WS 收到消息时，交给 CommandHandler 处理
                _wsService.OnMessageReceived += _cmdHandler.ProcessRawMessage;

                // 3. 异步启动 WebSocket 连接循环
                _ = _wsService.StartAsync();

                // 4. 启动周期任务
                _ = Task.Run(() => _runtimeService.StatusBroadcastLoop(_pluginCts.Token));
                _ = Task.Run(() => _runtimeService.DeathDetectionLoop(_pluginCts.Token));

                // 5. 注册 TShock 钩子
                ServerApi.Hooks.ServerChat.Register(this, _runtimeService.OnChat);
                ServerApi.Hooks.ServerJoin.Register(this, _runtimeService.OnPlayerJoin);
                ServerApi.Hooks.ServerLeave.Register(this, _runtimeService.OnPlayerLeave);

                // 6. 初始化玩家统计追踪器
                StatsTracker.Init();

                // 7. 如果是重启后首次启动，还原启动脚本（移除临时循环）
                StartupScriptService.CleanupRestartScript();

                TShock.Log.Info("[Agent] 插件已初始化：WebSocket 服务与指令处理器已就绪");
            }
            catch (Exception ex)
            {
                TShock.Log.Error($"[Agent] 初始化异常: {ex.Message}");
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
                    }

                    // 取消后台循环（Task.Delay 立即中断）
                    _pluginCts.Cancel();

                    // 释放服务资源（关闭连接，取消 Token）
                    _wsService?.Dispose();
                    
                    TShock.Log.Info("[Agent] 插件已安全卸载，后台连接已关闭");
                }
                catch (Exception ex)
                {
                    TShock.Log.Error($"[Agent] 卸载时发生错误: {ex.Message}");
                }
            }
            base.Dispose(disposing);
        }
    }
}
