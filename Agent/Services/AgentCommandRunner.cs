using System.Collections.Generic;
using Microsoft.Xna.Framework;
using TShockAPI;
using TShockAPI.DB;

namespace TerrariaManagerAgent.Services
{
    /// <summary>
    /// 虚拟指令执行者，用于捕获 TShock 指令输出
    /// </summary>
    public class AgentCommandRunner : TSPlayer
    {
        public List<string> OutputLines { get; } = new List<string>();

        public AgentCommandRunner(string name) : base(255) // 使用 255 位作为服务器/虚拟标识
        {
            IsLoggedIn = true;
            var runnerName = string.IsNullOrWhiteSpace(name) ? "PanelUser" : name;
            Account = new UserAccount { Name = runnerName, Group = "superadmin" };
        }

        public override void SendMessage(string msg, byte red, byte green, byte blue) => OutputLines.Add(msg);
        public override void SendMessage(string msg, Color color) => OutputLines.Add(msg);
        public override void SendSuccessMessage(string msg) => OutputLines.Add(msg);
        public override void SendErrorMessage(string msg) => OutputLines.Add(msg);
        public override void SendInfoMessage(string msg) => OutputLines.Add(msg);
        public override void SendWarningMessage(string msg) => OutputLines.Add(msg);
    }
}
