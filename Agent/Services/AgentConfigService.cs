using System;
using System.IO;
using Newtonsoft.Json;
using TShockAPI;
using TerrariaManagerAgent.Models;

namespace TerrariaManagerAgent.Services
{
    /// <summary>
    /// 负责 Agent 配置加载、初始化与回写。
    /// </summary>
    public static class AgentConfigService
    {
        private const string ConfigName = "TerrariaManagerAgent.json";

        public static AgentConfig LoadConfig(string savePath)
        {
            var configDir = ResolveSavePath(savePath);
            Directory.CreateDirectory(configDir);

            var path = Path.Combine(configDir, ConfigName);
            AgentConfig config;
            bool changed = false;

            if (!File.Exists(path))
            {
                config = new AgentConfig();
                changed = true;
            }
            else
            {
                try
                {
                    config = JsonConvert.DeserializeObject<AgentConfig>(File.ReadAllText(path)) ?? new AgentConfig();
                }
                catch (Exception ex)
                {
                    AgentLog.Error("Config", "load_failed_use_defaults",
                        ("path", path),
                        ("error", ex.Message));
                    config = new AgentConfig();
                    changed = true;
                }
            }

            if (string.IsNullOrWhiteSpace(config.AgentKey))
            {
                config.AgentKey = Guid.NewGuid().ToString("N");
                changed = true;
                AgentLog.Info("Config", "agent_key_generated", ("path", path));
            }

            var lvl = (config.AuditLevel ?? string.Empty).Trim().ToLowerInvariant();
            if (lvl != "off" && lvl != "write" && lvl != "all")
            {
                config.AuditLevel = "write";
                changed = true;
            }
            else
            {
                config.AuditLevel = lvl;
            }

            if (changed)
            {
                File.WriteAllText(path, JsonConvert.SerializeObject(config, Formatting.Indented));
            }

            AgentLog.Console("Config", "loaded",
                ("path", path),
                ("backend_url", config.BackendUrl),
                ("agent_key", config.AgentKey),
                ("audit_level", config.AuditLevel),
                ("debug_enabled", config.DebugEnabled));

            return config;
        }

        private static string ResolveSavePath(string savePath)
        {
            var raw = string.IsNullOrWhiteSpace(savePath) ? "tshock" : savePath;
            return Path.GetFullPath(raw);
        }

    }
}
