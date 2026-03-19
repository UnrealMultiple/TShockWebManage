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
        public static AgentConfig LoadConfig(string savePath)
        {
            var path = Path.Combine(savePath, "agent_config.json");
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
                    TShock.Log.Error($"[Agent] 读取配置失败，使用默认值: {ex.Message}");
                    config = new AgentConfig();
                }
            }

            if (string.IsNullOrWhiteSpace(config.AgentKey))
            {
                config.AgentKey = Guid.NewGuid().ToString("N");
                changed = true;
                TShock.Log.Info("[Agent] 首次启动，已自动生成 agent_key");
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

            TShock.Log.ConsoleInfo($"| Agent Key : {config.AgentKey,-36} |");
            TShock.Log.ConsoleInfo($"| Audit Lv  : {config.AuditLevel,-36} |");

            return config;
        }
    }
}
