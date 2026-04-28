using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using TShockAPI;

namespace TerrariaManagerAgent.Services
{
    /// <summary>
    /// 负责重启后启动脚本恢复与循环清理。
    /// </summary>
    public static class StartupScriptService
    {
        public static void CleanupRestartScript()
        {
            try
            {
                var serverDir = Path.GetDirectoryName(Process.GetCurrentProcess().MainModule?.FileName)
                                ?? Directory.GetCurrentDirectory();
                var flagPath = Path.Combine(serverDir, "restart_pending.flag");
                if (!File.Exists(flagPath)) return;

                var isWindows = Environment.OSVersion.Platform == PlatformID.Win32NT;
                var scriptNames = isWindows
                    ? new[] { "启动脚本(可修改).bat", "start.bat" }
                    : new[] { "启动脚本(可修改).sh", "start.sh" };

                foreach (var name in scriptNames)
                {
                    var path = Path.Combine(serverDir, name);
                    if (!File.Exists(path)) continue;

                    var content = File.ReadAllText(path, System.Text.Encoding.UTF8);
                    var cleaned = isWindows ? RemoveWinRestartLoop(content) : RemoveShRestartLoop(content);
                    File.WriteAllText(path, cleaned, new System.Text.UTF8Encoding(false));
                    AgentLog.Info("StartupScript", "restart_script_restored", ("path", path));
                    break;
                }

                File.Delete(flagPath);
            }
            catch (Exception ex)
            {
                AgentLog.Warn("StartupScript", "restore_failed", ("error", ex.Message));
            }
        }

        private static string RemoveWinRestartLoop(string content)
        {
            var lines = content.Split(new[] { "\r\n", "\n" }, StringSplitOptions.None);
            var result = new List<string>();
            foreach (var line in lines)
            {
                var t = line.Trim();
                if (t.Equals(":start", StringComparison.OrdinalIgnoreCase)) continue;
                if (t.StartsWith("goto start", StringComparison.OrdinalIgnoreCase)) continue;
                if (t.StartsWith("@echo Restarting", StringComparison.OrdinalIgnoreCase)) continue;
                result.Add(line);
            }

            int pauseIdx = -1;
            for (int i = 0; i < result.Count; i++)
            {
                var t = result[i].Trim();
                if (t.Equals("pause", StringComparison.OrdinalIgnoreCase) ||
                    t.StartsWith("pause ", StringComparison.OrdinalIgnoreCase))
                {
                    pauseIdx = i;
                    break;
                }
            }

            if (pauseIdx > 0)
            {
                int j = pauseIdx - 1;
                while (j >= 0 && result[j].Trim().Equals("@echo.", StringComparison.OrdinalIgnoreCase))
                {
                    result.RemoveAt(j);
                    pauseIdx--;
                    j--;
                }
            }

            while (result.Count > 0 && string.IsNullOrWhiteSpace(result[result.Count - 1]))
                result.RemoveAt(result.Count - 1);

            return string.Join("\r\n", result);
        }

        private static string RemoveShRestartLoop(string content)
        {
            var lines = content.Split(new[] { "\r\n", "\n" }, StringSplitOptions.None);
            var result = new List<string>();
            bool inLoop = false;

            foreach (var line in lines)
            {
                var t = line.Trim();
                if (t == "while true; do") { inLoop = true; continue; }
                if (t == "done") { inLoop = false; continue; }
                if (inLoop)
                {
                    if (t.StartsWith("./TShock.Server") || t.StartsWith("TShock.Server"))
                        result.Add(t);
                    continue;
                }
                result.Add(line);
            }

            while (result.Count > 0 && string.IsNullOrWhiteSpace(result[result.Count - 1]))
                result.RemoveAt(result.Count - 1);

            return string.Join("\n", result);
        }
    }
}
