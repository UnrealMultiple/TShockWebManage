using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
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
        private static readonly string[] WinStartupExecutables = { "TShock.Installer.exe", "TShock.Server.exe" };
        private static readonly string[] LinuxStartupExecutables = { "TShock.Installer", "TShock.Server" };

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
            AgentLog.Audit("server_control_requested",
                ("msg_id", envelope.MsgId),
                ("operator", operatorId),
                ("action", action),
                ("action_label", actionLabel));

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
                bool injected = false;
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
                            IsWindowsStartupCommand(l.Trim(), out _));
                        if (idx >= 0)
                        {
                            lines.Insert(idx, ":start");
                            idx++;
                            lines.Insert(idx + 1, "goto start");
                            File.WriteAllText(foundPath, string.Join("\r\n", lines),
                                new System.Text.UTF8Encoding(false));
                            injected = true;
                        }
                    }
                    else if (!isWindows && !content.Contains("while true"))
                    {
                        var lines = new System.Collections.Generic.List<string>(
                            content.Split(new[] { "\r\n", "\n" }, StringSplitOptions.None));
                        int idx = lines.FindIndex(l =>
                            IsLinuxStartupCommand(l.Trim(), out _));
                        if (idx >= 0)
                        {
                            var cmd = lines[idx].Trim();
                            lines[idx] = "while true; do";
                            lines.Insert(idx + 1, $"    {cmd}");
                            lines.Insert(idx + 2, "    echo \"Server exited, restarting in 2s...\"");
                            lines.Insert(idx + 3, "    sleep 2");
                            lines.Insert(idx + 4, "    exec \"$0\" \"$@\"");
                            lines.Insert(idx + 5, "done");
                            File.WriteAllText(foundPath, string.Join("\n", lines),
                                new System.Text.UTF8Encoding(false));
                            injected = true;
                        }
                    }
                }

                if (injected)
                    File.WriteAllText(Path.Combine(serverDir, "restart_pending.flag"),
                        DateTime.UtcNow.ToString("o"), System.Text.Encoding.UTF8);
            }
            catch (Exception ex)
            {
                AgentLog.Warn("ServerControl", "inject_restart_loop_failed", ("error", ex.Message));
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
            return Path.Combine(TShock.SavePath, "motd.txt");
        }

        public async Task HandleReadStartupScript(PacketEnvelope envelope)
        {
            var serverDir  = GetServerDir();
            var isWindows  = Environment.OSVersion.Platform == PlatformID.Win32NT;
            var names      = isWindows ? WinScriptNames : LinuxScriptNames;
            var platform   = isWindows ? "windows" : "linux";
            var defaultName = isWindows ? "start.bat" : "start.sh";
            var executable = GetPreferredStartupExecutable(serverDir, isWindows);
            var executableExists = StartupExecutableExists(serverDir, executable);

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
                var scriptExecutable = GetStartupExecutableFromScript(content, isWindows) ?? executable;
                var scriptExecutableExists = StartupExecutableExists(serverDir, scriptExecutable);
                await _wsService.SendAsync(new {
                    type = "read_startup_script_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, found = true,
                        path = foundPath, filename = foundName, platform, path_exists = true, content,
                        executable = scriptExecutable, executable_exists = scriptExecutableExists }
                });
            }
            else
            {
                await _wsService.SendAsync(new {
                    type = "read_startup_script_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, found = false,
                        path = Path.Combine(serverDir, defaultName), filename = defaultName,
                        platform, path_exists = false, content = "",
                        executable, executable_exists = executableExists }
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

            var isWindows = Environment.OSVersion.Platform == PlatformID.Win32NT;
            if (!IsAllowedStartupScriptName(filename, isWindows))
            {
                var allowedNames = string.Join(" / ", isWindows ? WinScriptNames : LinuxScriptNames);
                await _wsService.SendAsync(new {
                    type = "write_startup_script_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = $"启动脚本只能保存为 {allowedNames}" }
                });
                return;
            }

            if (!ValidateStartupScriptContent(content, isWindows, serverDir, out var validationMsg))
            {
                await _wsService.SendAsync(new {
                    type = "write_startup_script_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = validationMsg }
                });
                return;
            }

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

                // Linux 环境下自动赋予可执行权限
                if (!isWindows && filename.EndsWith(".sh"))
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
                    catch { /* chmod 失败不影响文件写入 */ }
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

        private static bool IsAllowedStartupScriptName(string filename, bool isWindows)
        {
            if (string.IsNullOrWhiteSpace(filename)) return false;
            if (Path.GetFileName(filename) != filename) return false;
            var allowed = isWindows ? WinScriptNames : LinuxScriptNames;
            return allowed.Contains(filename, StringComparer.OrdinalIgnoreCase);
        }

        private static bool ValidateStartupScriptContent(string content, bool isWindows, string serverDir, out string msg)
        {
            msg = "";
            if (string.IsNullOrWhiteSpace(content))
            {
                msg = "启动脚本内容不能为空";
                return false;
            }

            var lines = content
                .Replace("\r\n", "\n")
                .Replace('\r', '\n')
                .Split('\n')
                .Select(x => x.Trim())
                .Where(x => !string.IsNullOrWhiteSpace(x))
                .ToList();

            if (lines.Count == 0)
            {
                msg = "启动脚本内容不能为空";
                return false;
            }

            return isWindows
                ? ValidateWindowsStartupScript(lines, serverDir, out msg)
                : ValidateLinuxStartupScript(lines, serverDir, out msg);
        }

        private static bool ValidateWindowsStartupScript(List<string> lines, string serverDir, out string msg)
        {
            msg = "";
            var commandCount = 0;
            var allowedLines = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                "@echo off",
                "cls",
                ":start",
                "@echo.",
                "@echo Restarting server...",
                "goto start",
                "pause",
            };

            foreach (var line in lines)
            {
                if (IsWindowsStartupCommand(line, out var exe))
                {
                    commandCount++;
                    if (commandCount > 1)
                    {
                        msg = "启动脚本只能包含一条 TShock 启动命令";
                        return false;
                    }
                    if (line.Length > exe.Length && !char.IsWhiteSpace(line[exe.Length]))
                    {
                        msg = "启动命令必须直接调用 TShock.Installer.exe 或 TShock.Server.exe";
                        return false;
                    }
                    if (ContainsWindowsShellOperator(line))
                    {
                        msg = "启动参数包含不允许的命令连接符或环境变量符号";
                        return false;
                    }
                    if (!File.Exists(Path.Combine(serverDir, exe)))
                    {
                        msg = $"{exe} 不存在，请确认脚本位于 TShock 根目录";
                        return false;
                    }
                    continue;
                }

                if (!allowedLines.Contains(line))
                {
                    msg = $"启动脚本包含不允许的命令: {line}";
                    return false;
                }
            }

            if (commandCount == 0)
            {
                msg = "启动脚本必须包含 TShock.Installer.exe 或 TShock.Server.exe 启动命令";
                return false;
            }
            return true;
        }

        private static bool ValidateLinuxStartupScript(List<string> lines, string serverDir, out string msg)
        {
            msg = "";
            var commandCount = 0;
            var allowedLines = new HashSet<string>(StringComparer.Ordinal)
            {
                "#!/bin/bash",
                "while true; do",
                "echo \"Server exited, restarting in 2s...\"",
                "sleep 2",
                "exec \"$0\" \"$@\"",
                "done",
            };

            foreach (var line in lines)
            {
                var isCommand = IsLinuxStartupCommand(line, out var exe);
                if (isCommand)
                {
                    commandCount++;
                    if (commandCount > 1)
                    {
                        msg = "启动脚本只能包含一条 TShock 启动命令";
                        return false;
                    }
                    if (line.Length > exe.Length && !char.IsWhiteSpace(line[exe.Length]))
                    {
                        msg = "启动命令必须直接调用 TShock.Installer 或 TShock.Server";
                        return false;
                    }
                    if (ContainsLinuxShellOperator(line))
                    {
                        msg = "启动参数包含不允许的 Shell 控制符";
                        return false;
                    }
                    var exeName = exe.StartsWith("./", StringComparison.Ordinal) ? exe.Substring(2) : exe;
                    if (!File.Exists(Path.Combine(serverDir, exeName)))
                    {
                        msg = $"{exeName} 不存在，请确认脚本位于 TShock 根目录";
                        return false;
                    }
                    continue;
                }

                if (!allowedLines.Contains(line))
                {
                    msg = $"启动脚本包含不允许的命令: {line}";
                    return false;
                }
            }

            if (commandCount == 0)
            {
                msg = "启动脚本必须包含 TShock.Installer 或 TShock.Server 启动命令";
                return false;
            }
            return true;
        }

        private static string GetPreferredStartupExecutable(string serverDir, bool isWindows)
        {
            var candidates = isWindows ? WinStartupExecutables : LinuxStartupExecutables;
            foreach (var exe in candidates)
            {
                if (File.Exists(Path.Combine(serverDir, exe)))
                    return isWindows ? exe : "./" + exe;
            }
            var fallback = candidates.Last();
            return isWindows ? fallback : "./" + fallback;
        }

        private static string? GetStartupExecutableFromScript(string content, bool isWindows)
        {
            foreach (var line in content
                .Replace("\r\n", "\n")
                .Replace('\r', '\n')
                .Split('\n')
                .Select(x => x.Trim()))
            {
                if (isWindows)
                {
                    if (IsWindowsStartupCommand(line, out var exe))
                        return exe;
                }
                else if (IsLinuxStartupCommand(line, out var exe))
                {
                    return exe.StartsWith("./", StringComparison.Ordinal) ? exe : "./" + exe;
                }
            }
            return null;
        }

        private static bool StartupExecutableExists(string serverDir, string executable)
        {
            var exeName = executable.StartsWith("./", StringComparison.Ordinal)
                ? executable.Substring(2)
                : executable;
            return File.Exists(Path.Combine(serverDir, exeName));
        }

        private static bool IsWindowsStartupCommand(string line, out string exe)
        {
            exe = "";
            foreach (var candidate in WinStartupExecutables)
            {
                if (line.Equals(candidate, StringComparison.OrdinalIgnoreCase)
                    || line.StartsWith(candidate + " ", StringComparison.OrdinalIgnoreCase))
                {
                    exe = candidate;
                    return true;
                }
            }
            return false;
        }

        private static bool IsLinuxStartupCommand(string line, out string exe)
        {
            exe = "";
            foreach (var candidate in LinuxStartupExecutables)
            {
                var relativeCandidate = "./" + candidate;
                if (line.Equals(relativeCandidate, StringComparison.OrdinalIgnoreCase)
                    || line.StartsWith(relativeCandidate + " ", StringComparison.OrdinalIgnoreCase))
                {
                    exe = relativeCandidate;
                    return true;
                }
                if (line.Equals(candidate, StringComparison.OrdinalIgnoreCase)
                    || line.StartsWith(candidate + " ", StringComparison.OrdinalIgnoreCase))
                {
                    exe = candidate;
                    return true;
                }
            }
            return false;
        }

        private static bool ContainsWindowsShellOperator(string line)
        {
            return line.IndexOfAny(new[] { '&', '|', '<', '>', '^', '%' }) >= 0;
        }

        private static bool ContainsLinuxShellOperator(string line)
        {
            return line.IndexOfAny(new[] { ';', '&', '|', '<', '>', '`', '$' }) >= 0;
        }

        public async Task HandleReadTShockConfig(PacketEnvelope envelope)
        {
            var jobj    = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var fileKey = jobj["file"]?.ToString() ?? "config";

            var fileName  = fileKey == "ssc" ? "sscconfig.json" : "config.json";
            var filePath  = Path.Combine(TShock.SavePath, fileName);

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

            var fileName  = fileKey == "ssc" ? "sscconfig.json" : "config.json";
            var filePath  = Path.Combine(TShock.SavePath, fileName);

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
