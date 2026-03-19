using System;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using TShockAPI;
using TerrariaManagerAgent.Models;

namespace TerrariaManagerAgent.Services.Handlers
{
    public class ServerHandler : HandlerBase
    {
        // 主流面板生成的启动脚本名（优先检测），其次是通用名
        private static readonly string[] WinScriptNames   = { "启动脚本(可修改).bat", "start.bat" };
        private static readonly string[] LinuxScriptNames = { "启动脚本(可修改).sh",  "start.sh"  };

        public ServerHandler(WebSocketService wsService) : base(wsService) { }

        public async Task HandleServerControl(PacketEnvelope envelope)
        {
            string action   = "";
            string operatorId = "unknown";
            try
            {
                var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
                action     = jobj["action"]?.ToString()   ?? "";
                operatorId = jobj["operator"]?.ToString() ?? "unknown";
            }
            catch { }

            var actionLabel = action switch {
                "stop"       => "正常关闭",
                "stop_nosave"=> "不保存关闭",
                "force_kill" => "强制终止",
                "restart"    => "重启",
                _            => action
            };
            TShock.Log.ConsoleInfo($"[Agent] 面板操作: {operatorId} 执行了「{actionLabel}」");

            switch (action)
            {
                case "stop":
                    await _wsService.SendAsync(new {
                        type = "server_ctrl_resp", msg_id = Guid.NewGuid().ToString("N"),
                        timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                        payload = new { ref_id = envelope.MsgId, action, success = true, msg = "服务器正在关闭…" }
                    });
                    await Task.Delay(1200);
                    _wsService.SignalShutdown();
                    // 调用 TShock /off 命令：保存地图后正常退出，是否重启由外部脚本决定
                    TShockAPI.Commands.HandleCommand(TSPlayer.Server, "/off");
                    break;

                case "stop_nosave":
                    await _wsService.SendAsync(new {
                        type = "server_ctrl_resp", msg_id = Guid.NewGuid().ToString("N"),
                        timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                        payload = new { ref_id = envelope.MsgId, action, success = true, msg = "服务器正在关闭（不保存）…" }
                    });
                    await Task.Delay(300);
                    _wsService.SignalShutdown();
                    // 调用 TShock /off-nosave 命令：不保存地图直接退出
                    TShockAPI.Commands.HandleCommand(TSPlayer.Server, "/off-nosave");
                    break;

                case "restart":
                    await _wsService.SendAsync(new {
                        type = "server_ctrl_resp", msg_id = Guid.NewGuid().ToString("N"),
                        timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                        payload = new { ref_id = envelope.MsgId, action, success = true, msg = "服务器正在重启…" }
                    });
                    // 临时向启动脚本注入重启循环 + 写 flag，重启后嘿动时自动还原
                    InjectRestartLoop();
                    await Task.Delay(1200);
                    _wsService.SignalShutdown();
                    TShockAPI.Commands.HandleCommand(TSPlayer.Server, "/off");
                    break;
            }
        }

        /// <summary>
        /// 在启动脚本中临时注入重启循环，并写 restart_pending.flag。
        /// 如果脚本已有循环则仅写 flag。
        /// </summary>
        private void InjectRestartLoop()
        {
            try
            {
                var serverDir   = GetServerDir();
                var isWindows   = Environment.OSVersion.Platform == PlatformID.Win32NT;
                var scriptNames = isWindows ? WinScriptNames : LinuxScriptNames;

                string? foundPath = null;
                foreach (var n in scriptNames)
                {
                    var p = Path.Combine(serverDir, n);
                    if (File.Exists(p)) { foundPath = p; break; }
                }

                if (foundPath != null)
                {
                    var content = File.ReadAllText(foundPath, System.Text.Encoding.UTF8);
                    if (isWindows && !content.Contains("goto start"))
                    {
                        var lines = new System.Collections.Generic.List<string>(
                            content.Split(new[] { "\r\n", "\n" }, StringSplitOptions.None));
                        int idx = lines.FindIndex(l =>
                            l.Trim().StartsWith("TShock.Server", StringComparison.OrdinalIgnoreCase));
                        if (idx >= 0)
                        {
                            lines.Insert(idx, ":start");
                            idx++; // TShock.Server 行现在 idx+1
                            lines.Insert(idx + 1, "goto start");
                            File.WriteAllText(foundPath, string.Join("\r\n", lines),
                                new System.Text.UTF8Encoding(false));
                        }
                    }
                    else if (!isWindows && !content.Contains("while true"))
                    {
                        var lines = new System.Collections.Generic.List<string>(
                            content.Split(new[] { "\r\n", "\n" }, StringSplitOptions.None));
                        int idx = lines.FindIndex(l =>
                            l.Trim().StartsWith("./TShock.Server") || l.Trim().StartsWith("TShock.Server"));
                        if (idx >= 0)
                        {
                            var cmd = lines[idx].Trim();
                            lines[idx] = "while true; do";
                            lines.Insert(idx + 1, $"    {cmd}");
                            lines.Insert(idx + 2, "    echo \"Server exited, restarting in 2s...\"");
                            lines.Insert(idx + 3, "    sleep 2");
                            lines.Insert(idx + 4, "done");
                            File.WriteAllText(foundPath, string.Join("\n", lines),
                                new System.Text.UTF8Encoding(false));
                        }
                    }
                }

                File.WriteAllText(Path.Combine(serverDir, "restart_pending.flag"),
                    DateTime.UtcNow.ToString("o"), System.Text.Encoding.UTF8);
            }
            catch (Exception ex)
            {
                TShock.Log.Warn($"[Agent] 注入重启循环失败: {ex.Message}");
            }
        }

        public async Task HandleReadMotd(PacketEnvelope envelope)
        {
            var motdPath = GetMotdPath();
            try
            {
                var content = File.Exists(motdPath)
                    ? File.ReadAllText(motdPath, System.Text.Encoding.UTF8)
                    : "";
                await _wsService.SendAsync(new {
                    type      = "read_motd_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = true, content, path = motdPath }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type      = "read_motd_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandleWriteMotd(PacketEnvelope envelope)
        {
            var jobj    = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var content = jobj["content"]?.ToString() ?? "";
            var motdPath = GetMotdPath();
            try
            {
                File.WriteAllText(motdPath, content, new System.Text.UTF8Encoding(false));
                await _wsService.SendAsync(new {
                    type      = "write_motd_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = true, path = motdPath }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type      = "write_motd_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandleReload(PacketEnvelope envelope)
        {
            try
            {
                TShockAPI.Commands.HandleCommand(TSPlayer.Server, "/reload");
                await _wsService.SendAsync(new {
                    type      = "reload_tshock_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = true, msg = "已执行 /reload" }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type      = "reload_tshock_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload   = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        private string GetMotdPath()
        {
            var rawSave  = TShock.SavePath ?? "tshock";
            var saveDir  = Path.IsPathRooted(rawSave) ? rawSave : Path.Combine(GetServerDir(), rawSave);
            return Path.Combine(saveDir, "motd.txt");
        }

        public async Task HandleReadStartupScript(PacketEnvelope envelope)
        {
            var serverDir  = GetServerDir();
            var isWindows  = Environment.OSVersion.Platform == PlatformID.Win32NT;
            var names      = isWindows ? WinScriptNames : LinuxScriptNames;
            var platform   = isWindows ? "windows" : "linux";
            var defaultName = isWindows ? "start.bat" : "start.sh";

            string? foundPath = null;
            string? foundName = null;
            foreach (var n in names)
            {
                var p = Path.Combine(serverDir, n);
                if (File.Exists(p)) { foundPath = p; foundName = n; break; }
            }

            if (foundPath != null)
            {
                var content = File.ReadAllText(foundPath, System.Text.Encoding.UTF8);
                await _wsService.SendAsync(new {
                    type = "read_startup_script_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, found = true,
                        path = foundPath, filename = foundName, platform, content }
                });
            }
            else
            {
                await _wsService.SendAsync(new {
                    type = "read_startup_script_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, found = false,
                        path = Path.Combine(serverDir, defaultName), filename = defaultName,
                        platform, content = "" }
                });
            }
        }

        public async Task HandleWriteStartupScript(PacketEnvelope envelope)
        {
            var jobj     = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var content  = jobj["content"]?.ToString()  ?? "";
            var filename = jobj["filename"]?.ToString() ?? "";

            var serverDir = GetServerDir();
            if (string.IsNullOrEmpty(filename))
                filename = Environment.OSVersion.Platform == PlatformID.Win32NT ? "start.bat" : "start.sh";

            var filePath = Path.Combine(serverDir, filename);
            if (!IsPathSafe(filePath))
            {
                await _wsService.SendAsync(new {
                    type = "write_startup_script_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "路径不合法" }
                });
                return;
            }

            try
            {
                // 无 BOM 写入，兼容 bash 脚本
                File.WriteAllText(filePath, content, new System.Text.UTF8Encoding(false));

                // Linux 下自动赋予可执行权限
                if (Environment.OSVersion.Platform != PlatformID.Win32NT && filename.EndsWith(".sh"))
                {
                    try
                    {
                        var chmod = new Process {
                            StartInfo = new ProcessStartInfo("chmod", $"+x \"{filePath}\"")
                            { UseShellExecute = false, CreateNoWindow = true }
                        };
                        chmod.Start();
                        chmod.WaitForExit();
                    }
                    catch { /* chmod 失败不影响写入结果 */ }
                }

                await _wsService.SendAsync(new {
                    type = "write_startup_script_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, path = filePath, filename }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type = "write_startup_script_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandleReadTShockConfig(PacketEnvelope envelope)
        {
            var jobj    = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var fileKey = jobj["file"]?.ToString() ?? "config";

            var serverDir = GetServerDir();
            var rawSave   = TShock.SavePath ?? "tshock";
            var savePath  = Path.IsPathRooted(rawSave) ? rawSave : Path.Combine(serverDir, rawSave);
            var fileName  = fileKey == "ssc" ? "sscconfig.json" : "config.json";
            var filePath  = Path.Combine(savePath, fileName);

            try
            {
                if (!File.Exists(filePath))
                {
                    await _wsService.SendAsync(new {
                        type = "read_tshock_config_resp", msg_id = Guid.NewGuid().ToString("N"),
                        timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                        payload = new { ref_id = envelope.MsgId, success = false,
                            msg = $"配置文件不存在: {filePath}" }
                    });
                    return;
                }
                var content = File.ReadAllText(filePath, System.Text.Encoding.UTF8);
                await _wsService.SendAsync(new {
                    type = "read_tshock_config_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true,
                        file = fileKey, path = filePath, content }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type = "read_tshock_config_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandleWriteTShockConfig(PacketEnvelope envelope)
        {
            var jobj    = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var fileKey = jobj["file"]?.ToString()    ?? "config";
            var content = jobj["content"]?.ToString() ?? "";

            var serverDir = GetServerDir();
            var rawSave   = TShock.SavePath ?? "tshock";
            var savePath  = Path.IsPathRooted(rawSave) ? rawSave : Path.Combine(serverDir, rawSave);
            var fileName  = fileKey == "ssc" ? "sscconfig.json" : "config.json";
            var filePath  = Path.Combine(savePath, fileName);

            if (!IsPathSafe(filePath))
            {
                await _wsService.SendAsync(new {
                    type = "write_tshock_config_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "路径不合法" }
                });
                return;
            }
            try
            {
                // 写入前验证 JSON 有效性
                JToken.Parse(content);
                File.WriteAllText(filePath, content, System.Text.Encoding.UTF8);
                await _wsService.SendAsync(new {
                    type = "write_tshock_config_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, file = fileKey }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type = "write_tshock_config_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }
    }
}
