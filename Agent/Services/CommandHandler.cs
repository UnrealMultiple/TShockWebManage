using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using TShockAPI;
using TerrariaManagerAgent.Models;
using TerrariaManagerAgent.Services.Handlers;

namespace TerrariaManagerAgent.Services
{
    /// <summary>
    /// 消息调度器：解析消息类型并分发给对应的 Handler。
    /// </summary>
    public class CommandHandler
    {
        private readonly WebSocketService _wsService;
        private readonly FileHandler      _file;
        private readonly DatabaseHandler  _db;
        private readonly PlayerHandler    _player;
        private readonly PluginHandler    _plugin;
        private readonly ServerHandler    _server;
        private readonly WorldHandler     _world;

        private static readonly HashSet<string> NoisyReadOps = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "read_tshock_config",
            "read_startup_script",
            "read_motd",
            "plugin_list_configs",
            "plugin_local_list",
            "plugin_cloud_list",
            "plugin_check_updates",
            "file_list",
            "file_read",
            "db_query",
            "player_list",
            "get_char_info",
            "world_progress",
            "player_stats",
            "get_groups",
            "list_bans",
            "list_game_groups",
            "create_game_group",
            "update_game_group",
            "delete_game_group",
            "get_inventory",
            "get_minimap",
            "get_player_positions",
            "list_banlists",
        };

        private sealed class AuditWindowState
        {
            public DateTime Last = DateTime.MinValue;
            public int Suppressed = 0;
        }

        private static readonly Dictionary<string, AuditWindowState> AuditWindows =
            new Dictionary<string, AuditWindowState>(StringComparer.OrdinalIgnoreCase);
        private static readonly object AuditLock = new object();
        private static readonly TimeSpan AuditWindow = TimeSpan.FromSeconds(8);
        private static string _auditLevel = "write";

        private static readonly HashSet<string> WriteOps = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
        {
            "cmd",
            "server_ctrl",
            "reload_tshock",
            "file_write", "file_create", "file_mkdir", "file_move", "file_copy", "file_upload", "file_delete",
            "db_exec", "db_update_row", "db_delete_row", "db_insert_row",
            "write_tshock_config", "write_startup_script", "write_motd",
            "plugin_install", "plugin_uninstall", "plugin_update", "plugin_disable", "plugin_enable", "plugin_blacklist", "plugin_install_apm",
            "player_action", "register_user", "change_password", "delete_user", "send_bind_code",
            "unban_by_ticket",
            "update_ban_expiration",
            "create_game_group", "update_game_group", "delete_game_group",
            "save_inventory",
            "add_banlist",
            "remove_banlist",
            "update_banlist_groups",
        };

        public static void SetAuditLevel(string? level)
        {
            var v = (level ?? "").Trim().ToLowerInvariant();
            if (v != "off" && v != "write" && v != "all") v = "write";
            lock (AuditLock)
            {
                _auditLevel = v;
                AuditWindows.Clear();
            }
        }

        public CommandHandler(WebSocketService wsService)
        {
            _wsService = wsService;
            _file      = new FileHandler(wsService);
            _db        = new DatabaseHandler(wsService);
            _player    = new PlayerHandler(wsService);
            _plugin    = new PluginHandler(wsService);
            _server    = new ServerHandler(wsService);
            _world     = new WorldHandler(wsService);
        }

        public async Task ProcessRawMessage(string json)
        {
            try
            {
                var envelope = JsonConvert.DeserializeObject<PacketEnvelope>(json);
                if (envelope == null) return;

                AuditPanelOperation(envelope);

                Console.WriteLine($"[Agent DEBUG] 收到消息类型: {envelope.Type}, MsgId: {envelope.MsgId}");

                switch (envelope.Type)
                {
                    case "cmd":                  await HandleCommand(envelope);                       break;
                    case "file_list":            await _file.HandleFileList(envelope);               break;
                    case "file_read":            await _file.HandleFileRead(envelope);               break;
                    case "file_write":           await _file.HandleFileWrite(envelope);              break;
                    case "file_create":          await _file.HandleFileCreate(envelope);             break;
                    case "file_mkdir":           await _file.HandleFileMkdir(envelope);              break;
                    case "file_move":            await _file.HandleFileMove(envelope);               break;
                    case "file_copy":            await _file.HandleFileCopy(envelope);               break;
                    case "file_upload":          await _file.HandleFileUpload(envelope);             break;
                    case "file_delete":          await _file.HandleFileDelete(envelope);             break;
                    case "db_query":             await _db.HandleDbQuery(envelope);                  break;
                    case "db_exec":              await _db.HandleDbExec(envelope);                   break;
                    case "db_update_row":        await _db.HandleDbUpdateRow(envelope);              break;
                    case "db_delete_row":        await _db.HandleDbDeleteRow(envelope);              break;
                    case "db_insert_row":        await _db.HandleDbInsertRow(envelope);              break;
                    case "server_ctrl":          await _server.HandleServerControl(envelope);        break;
                    case "player_list":          await _player.HandlePlayerList(envelope);           break;
                    case "player_action":        await _player.HandlePlayerAction(envelope);         break;
                    case "register_user":        await _player.HandleRegisterUser(envelope);         break;
                    case "change_password":      await _player.HandleChangePassword(envelope);       break;
                    case "delete_user":          await _player.HandleDeleteUser(envelope);           break;
                    case "get_char_info":        await _player.HandleGetCharInfo(envelope);          break;
                    case "send_bind_code":       await _player.HandleSendBindCode(envelope);         break;
                    case "reload_tshock":         await _server.HandleReload(envelope);               break;
                    case "read_tshock_config":   await _server.HandleReadTShockConfig(envelope);     break;
                    case "write_tshock_config":  await _server.HandleWriteTShockConfig(envelope);    break;
                    case "read_startup_script":  await _server.HandleReadStartupScript(envelope);    break;
                    case "write_startup_script": await _server.HandleWriteStartupScript(envelope);   break;
                    case "read_motd":            await _server.HandleReadMotd(envelope);             break;
                    case "write_motd":           await _server.HandleWriteMotd(envelope);            break;
                    case "plugin_list_configs":  await _plugin.HandlePluginListConfigs(envelope);    break;
                    case "plugin_cloud_list":    await _plugin.HandlePluginCloudList(envelope);      break;
                    case "plugin_local_list":    await _plugin.HandlePluginLocalList(envelope);      break;
                    case "plugin_install":       await _plugin.HandlePluginInstall(envelope);        break;
                    case "plugin_uninstall":     await _plugin.HandlePluginUninstall(envelope);      break;
                    case "plugin_check_updates": await _plugin.HandlePluginCheckUpdates(envelope);   break;
                    case "plugin_update":        await _plugin.HandlePluginUpdate(envelope);         break;
                    case "plugin_disable":       await _plugin.HandlePluginDisable(envelope);        break;
                    case "plugin_enable":        await _plugin.HandlePluginEnable(envelope);         break;
                    case "plugin_blacklist":     await _plugin.HandlePluginBlacklist(envelope);      break;
                    case "plugin_install_apm":   await _plugin.HandleApmInstall(envelope);           break;
                    case "plugin_check_apm":     await _plugin.HandleCheckApm(envelope);             break;                    case "world_progress":         await _world.HandleWorldProgress(envelope);          break;
                    case "player_stats":           await _player.HandlePlayerStats(envelope);           break;
                    case "list_bans":              await _player.HandleListBans(envelope);             break;
                    case "unban_by_ticket":        await _player.HandleUnbanByTicket(envelope);        break;
                    case "update_ban_expiration":  await _player.HandleUpdateBanExpiration(envelope); break;
                    case "get_minimap":            await _world.HandleMinimap(envelope);                break;
                    case "get_player_positions":   await _world.HandlePlayerPositions(envelope);        break;
                    case "get_inventory":          await _player.HandleGetInventory(envelope);          break;
                    case "save_inventory":         await _player.HandleSaveInventory(envelope);         break;
                    case "list_banlists":         await _player.HandleListBanlists(envelope);          break;
                    case "add_banlist":           await _player.HandleAddBanlist(envelope);            break;
                    case "remove_banlist":        await _player.HandleRemoveBanlist(envelope);         break;
                    case "update_banlist_groups": await _player.HandleUpdateBanlistGroups(envelope);   break;
                    case "get_groups":             await _player.HandleGetGroups(envelope);             break;
                    case "list_game_groups":       await _player.HandleListGameGroups(envelope);        break;
                    case "create_game_group":      await _player.HandleCreateGameGroup(envelope);       break;
                    case "update_game_group":      await _player.HandleUpdateGameGroup(envelope);       break;
                    case "delete_game_group":      await _player.HandleDeleteGameGroup(envelope);       break;
                }
            }
            catch (Exception ex)
            {
                TShock.Log.Error($"[Agent] 处理 JSON 失败: {ex.Message}");
            }
        }

        private async Task HandleCommand(PacketEnvelope envelope)
        {
            var payload = JsonConvert.DeserializeObject<CommandPayload>(envelope.Payload?.ToString() ?? "{}");
            if (payload == null) return;

            var resp = new CommandResponsePayload
            {
                RefId   = envelope.MsgId,
                Success = false,
                Output  = "",
                ErrCode = 0
            };

            var runner = new AgentCommandRunner(payload.Executor.TsUser);

            if (payload.Executor.IsConsole)
            {
                runner.Group = TShock.Groups.GetGroupByName("superadmin") ?? new Group("console");
            }
            else
            {
                var group = TShock.Groups.GetGroupByName(payload.Executor.TsGroup);
                if (group == null)
                {
                    resp.Output = $"[Agent] 未找到角色组: {payload.Executor.TsGroup}";
                    await SendBack(resp);
                    return;
                }
                runner.Group = group;
            }

            string cmdText = payload.RawCmd.StartsWith("/") ? payload.RawCmd.Substring(1) : payload.RawCmd;
            var cmdParts   = cmdText.Split(' ');
            var commands   = Commands.ChatCommands.FindAll(c => c.Names.Contains(cmdParts[0]));

            if (commands.Count == 0)
            {
                resp.Output = "无效指令";
            }
            else if (commands[0].Permissions.Count > 0 && !commands[0].Permissions.Any(p => runner.HasPermission(p)))
            {
                resp.Output = "权限不足";
            }
            else
            {
                runner.OutputLines.Clear();
                resp.Success = Commands.HandleCommand(runner, payload.RawCmd);
                resp.Output  = string.Join("\n", runner.OutputLines);
            }

            await SendBack(resp);
        }

        private async Task SendBack(CommandResponsePayload payload)
        {
            await _wsService.SendAsync(new
            {
                type      = "cmd_resp",
                msg_id    = Guid.NewGuid().ToString("N"),
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                payload   = payload
            });
        }

        private static void AuditPanelOperation(PacketEnvelope envelope)
        {
            try
            {
                var payload = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
                var operatorEmail = payload["operator_email"]?.ToString();
                if (string.IsNullOrWhiteSpace(operatorEmail)) return;

                var opType = envelope.Type ?? "unknown";
                if (!ShouldAudit(opType)) return;
                var detail = DescribeOperation(opType, payload);
                if (string.Equals(opType, "list_banlists_resp", StringComparison.OrdinalIgnoreCase))
                {
                    detail = DescribeReadResult(payload);
                }

                if (NoisyReadOps.Contains(opType))
                {
                    var key = $"{operatorEmail}|{opType}|{detail}";
                    var now = DateTime.UtcNow;
                    lock (AuditLock)
                    {
                        if (!AuditWindows.TryGetValue(key, out var state))
                        {
                            state = new AuditWindowState();
                            AuditWindows[key] = state;
                        }

                        if (state.Last != DateTime.MinValue && now - state.Last < AuditWindow)
                        {
                            state.Suppressed++;
                            return;
                        }

                        if (state.Suppressed > 0)
                        {
                            TShock.Log.ConsoleInfo($"[Agent审计] 账号={operatorEmail} | 操作={detail} | 已合并 {state.Suppressed} 次重复请求");
                            state.Suppressed = 0;
                        }

                        state.Last = now;
                    }
                }

                TShock.Log.ConsoleInfo($"[Agent审计] 账号={operatorEmail} | 操作={detail}");
            }
            catch
            {
                // 审计日志失败不影响主流程
            }
        }

        private static bool ShouldAudit(string opType)
        {
            var level = _auditLevel;
            if (level == "off") return false;
            if (level == "all") return true;
            // 写入模式仅记录写操作与高风险操作
            return WriteOps.Contains(opType);
        }

        private static string DescribeOperation(string opType, JObject payload)
        {
            switch (opType)
            {
                case "cmd":
                    {
                        var cmd = payload["raw_cmd"]?.ToString() ?? "(空命令)";
                        return $"执行命令 {cmd}";
                    }
                case "server_ctrl":
                    {
                        var action = payload["action"]?.ToString() ?? "unknown";
                        return action switch
                        {
                            "stop" => "关闭服务器(保存)",
                            "stop_nosave" => "关闭服务器(不保存)",
                            "restart" => "重启服务器",
                            "force_kill" => "强制终止服务器",
                            _ => $"服务器控制:{action}",
                        };
                    }
                case "file_read":
                case "file_write":
                case "file_delete":
                case "file_create":
                case "file_move":
                case "file_copy":
                    {
                        var p = payload["path"]?.ToString() ?? payload["src"]?.ToString() ?? "(未提供路径)";
                        return $"{opType} {p}";
                    }
                case "db_query":
                    return "查询数据库";
                case "db_exec":
                    return "执行数据库变更";
                case "write_tshock_config":
                    return "修改 TShock 配置";
                case "read_tshock_config":
                    return "读取 TShock 配置";
                case "write_startup_script":
                    return "修改启动脚本";
                case "read_startup_script":
                    return "读取启动脚本";
                case "write_motd":
                    return "修改 MOTD";
                case "read_motd":
                    return "读取 MOTD";
                case "plugin_install":
                    return "安装插件";
                case "plugin_uninstall":
                    return "卸载插件";
                case "plugin_update":
                    return "更新插件";
                case "plugin_disable":
                    return "禁用插件";
                case "plugin_enable":
                    return "启用插件";
                case "player_action":
                    {
                        var action = payload["action"]?.ToString() ?? "unknown";
                        var player = payload["player"]?.ToString() ?? payload["username"]?.ToString() ?? "(未知玩家)";
                        return $"玩家操作:{action} 目标={player}";
                    }
                default:
                    return opType;
            }
        }

        private static string DescribeReadResult(JObject payload)
        {
            static int CountArray(JToken token)
            {
                return token is JArray arr ? arr.Count : 0;
            }

            var tiles = CountArray(payload["tiles"]);
            var items = CountArray(payload["items"]);
            var projectiles = CountArray(payload["projectiles"]);
            var success = payload["success"]?.Value<bool?>();
            var msg = payload["msg"]?.ToString();

            if (success == false)
                return $"读取图格/物品/弹幕封禁列表失败: {msg}";

            return $"读取图格/物品/弹幕封禁列表 tiles={tiles}, items={items}, projectiles={projectiles}";
        }
    }
}