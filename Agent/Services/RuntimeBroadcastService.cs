using System;
using System.Diagnostics;
using System.Linq;
using System.Net.NetworkInformation;
using System.Threading;
using System.Threading.Tasks;
using TShockAPI;
using Terraria;
using TerrariaApi.Server;

namespace TerrariaManagerAgent.Services
{
    /// <summary>
    /// 负责玩家事件采集、死亡轮询与服务器状态上报。
    /// </summary>
    public class RuntimeBroadcastService
    {
        private readonly WebSocketService _wsService;
        private readonly bool[] _wasDead = new bool[256];

        private Process? _thisProcess;
        private TimeSpan _lastCpuTime = TimeSpan.Zero;
        private DateTime _lastCpuMeasure = DateTime.MinValue;

        private long _lastNetSent = -1;
        private long _lastNetRecv = -1;
        private DateTime _lastNetMeasure = DateTime.MinValue;

        public RuntimeBroadcastService(WebSocketService wsService)
        {
            _wsService = wsService;
        }

        public void OnChat(ServerChatEventArgs args)
        {
            if (args == null || args.Handled) return;

            var player = Main.player[args.Who];
            if (player == null) return;

            var logEntry = new
            {
                type = "chat",
                player = player.name,
                text = args.Text,
                time = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")
            };

            _ = _wsService.SendAsync(logEntry);
        }

        public void OnPlayerJoin(JoinEventArgs args)
        {
            if (args == null) return;
            var player = TShock.Players?[args.Who];
            if (player != null && !string.IsNullOrEmpty(player.Name))
                StatsTracker.OnJoin(player.Name);
        }

        public void OnPlayerLeave(LeaveEventArgs args)
        {
            if (args == null) return;
            var player = TShock.Players?[args.Who];
            if (player != null && !string.IsNullOrEmpty(player.Name))
                StatsTracker.OnLeave(player.Name);
        }

        public async Task DeathDetectionLoop(CancellationToken token)
        {
            try { await Task.Delay(5000, token); }
            catch (OperationCanceledException) { return; }

            while (!token.IsCancellationRequested)
            {
                try
                {
                    for (var i = 0; i < 255; i++)
                    {
                        var p = TShock.Players?[i];
                        if (p == null || !p.Active)
                        {
                            _wasDead[i] = false;
                            continue;
                        }

                        var isDead = p.TPlayer?.dead ?? false;
                        if (isDead && !_wasDead[i] && !string.IsNullOrEmpty(p.Name))
                            StatsTracker.OnDeath(p.Name);
                        _wasDead[i] = isDead;
                    }
                }
                catch
                {
                    // 忽略单次采集异常，下一轮继续
                }

                try { await Task.Delay(1000, token); }
                catch (OperationCanceledException) { break; }
            }
        }

        public async Task StatusBroadcastLoop(CancellationToken token)
        {
            _thisProcess = Process.GetCurrentProcess();

            try { await Task.Delay(5000, token); }
            catch (OperationCanceledException) { return; }

            while (!token.IsCancellationRequested)
            {
                try
                {
                    var now = DateTime.UtcNow;
                    _thisProcess?.Refresh();

                    double cpuPercent = 0;
                    if (_lastCpuMeasure != DateTime.MinValue)
                    {
                        var wallMs = (now - _lastCpuMeasure).TotalMilliseconds;
                        var cpuMs = ((_thisProcess?.TotalProcessorTime ?? TimeSpan.Zero) - _lastCpuTime).TotalMilliseconds;
                        cpuPercent = wallMs > 0
                            ? Math.Round(Math.Min(100, cpuMs / wallMs / Environment.ProcessorCount * 100), 1)
                            : 0;
                    }
                    _lastCpuTime = _thisProcess?.TotalProcessorTime ?? TimeSpan.Zero;
                    _lastCpuMeasure = now;
                    var memMb = (_thisProcess?.WorkingSet64 ?? 0) / 1024 / 1024;

                    long totalSent = 0;
                    long totalRecv = 0;
                    foreach (var ni in NetworkInterface.GetAllNetworkInterfaces())
                    {
                        if (ni.OperationalStatus != OperationalStatus.Up) continue;
                        var s = ni.GetIPv4Statistics();
                        totalSent += s.BytesSent;
                        totalRecv += s.BytesReceived;
                    }

                    double netSendKbps = 0;
                    double netRecvKbps = 0;
                    if (_lastNetSent >= 0 && _lastNetMeasure != DateTime.MinValue)
                    {
                        var elapsedSec = (now - _lastNetMeasure).TotalSeconds;
                        if (elapsedSec > 0)
                        {
                            netSendKbps = Math.Round(Math.Max(0, totalSent - _lastNetSent) / 1024.0 / elapsedSec, 1);
                            netRecvKbps = Math.Round(Math.Max(0, totalRecv - _lastNetRecv) / 1024.0 / elapsedSec, 1);
                        }
                    }
                    _lastNetSent = totalSent;
                    _lastNetRecv = totalRecv;
                    _lastNetMeasure = now;

                    var players = TShock.Players
                        ?.Where(p => p != null && p.Active && !string.IsNullOrEmpty(p.Name))
                        .Select(p => new
                        {
                            name = p.Name,
                            hp = p.TPlayer?.statLife ?? 0,
                            max_hp = p.TPlayer?.statLifeMax2 ?? 0,
                            mana = p.TPlayer?.statMana ?? 0,
                            max_mana = p.TPlayer?.statManaMax2 ?? 0,
                            tile_x = p.TileX,
                            tile_y = p.TileY,
                        }).ToArray() ?? Array.Empty<object>();

                    await _wsService.SendAsync(new
                    {
                        type = "status",
                        msg_id = Guid.NewGuid().ToString("N"),
                        timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                        payload = new
                        {
                            online_players = players.Length,
                            max_players = TShock.Config.Settings.MaxSlots,
                            world_name = Main.worldName ?? string.Empty,
                            game_version = Main.versionNumber ?? string.Empty,
                            players,
                            world = new
                            {
                                is_day = Main.dayTime,
                                time = (int)Main.time,
                                moon_phase = Main.moonPhase,
                                is_hardmode = Main.hardMode,
                                width = Main.maxTilesX,
                                height = Main.maxTilesY,
                            },
                            resources = new
                            {
                                mem_mb = memMb,
                                cpu_percent = cpuPercent,
                                net_send_kbps = netSendKbps,
                                net_recv_kbps = netRecvKbps,
                            }
                        }
                    });
                }
                catch
                {
                    // 连接断开或瞬时异常时静默忽略，等待下一轮
                }

                try { await Task.Delay(15000, token); }
                catch (OperationCanceledException) { break; }
            }
        }
    }
}
