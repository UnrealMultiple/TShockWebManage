using Newtonsoft.Json;

namespace TerrariaManagerAgent.Models
{
    /// <summary>
    /// WebSocket 通信协议的外层包装类
    /// </summary>
    public class PacketEnvelope
    {
        [JsonProperty("type")]
        public string Type { get; set; }

        [JsonProperty("msg_id")]
        public string MsgId { get; set; }

        [JsonProperty("payload")]
        public object Payload { get; set; } // 动态载荷，后续根据 Type 转换
    }

    /// <summary>
    /// 远程指令的载荷结构
    /// </summary>
    public class CommandPayload
    {
        [JsonProperty("raw_cmd")]
        public string RawCmd { get; set; }

        [JsonProperty("executor")]
        public ExecutorInfo Executor { get; set; }
    }

    /// <summary>
    /// 执行者信息（权限控制用）
    /// </summary>
    public class ExecutorInfo
    {
        [JsonProperty("ts_user")]
        public string TsUser { get; set; }

        [JsonProperty("ts_group")]
        public string TsGroup { get; set; }

        [JsonProperty("is_console")]
        public bool IsConsole { get; set; }
    }

    /// <summary>
    /// 指令执行结果的回执载荷
    /// </summary>
    public class CommandResponsePayload
    {
        [JsonProperty("ref_id")]
        public string RefId { get; set; }

        [JsonProperty("success")]
        public bool Success { get; set; }

        [JsonProperty("output")]
        public string Output { get; set; }

        [JsonProperty("err_code")]
        public int ErrCode { get; set; }
    }
}
