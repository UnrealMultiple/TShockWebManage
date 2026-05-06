using Newtonsoft.Json;

namespace TerrariaManagerAgent.Models
{
    /// <summary>
    /// Agent 配置文件模型，对应 tshock/TerrariaManagerAgent.json
    /// </summary>
    public class AgentConfig
    {
        /// <summary>
        /// 后端 WebSocket 地址（不含 agent_key 参数）
        /// </summary>
        [JsonProperty("backend_url")]
        public string BackendUrl { get; set; } = "ws://127.0.0.1:8000/ws/agent";

        /// <summary>
        /// Agent 唯一标识，首次启动时自动生成并持久化到配置文件。
        /// 在面板“认领服务器”时填入此值。
        /// </summary>
        [JsonProperty("agent_key")]
        public string AgentKey { get; set; } = "";

        /// <summary>
        /// 审计日志级别：off / write / all
        /// - off: 关闭审计日志
        /// - write: 仅记录写操作与高风险操作（默认）
        /// - all: 记录所有操作（读写）
        /// </summary>
        [JsonProperty("audit_level")]
        public string AuditLevel { get; set; } = "write";

        /// <summary>
        /// 调试日志开关。默认关闭，仅排查 Agent 问题时临时开启。
        /// </summary>
        [JsonProperty("debug_enabled")]
        public bool DebugEnabled { get; set; } = false;
    }
}
