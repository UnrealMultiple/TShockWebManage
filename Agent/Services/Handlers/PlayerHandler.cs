using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using Newtonsoft.Json.Linq;
using Terraria;
using Terraria.ID;
using TShockAPI;
using TerrariaManagerAgent.Models;
using TerrariaManagerAgent.Services;

namespace TerrariaManagerAgent.Services.Handlers
{
    public class PlayerHandler : HandlerBase
    {
        public PlayerHandler(WebSocketService wsService) : base(wsService) { }

        public async Task HandlePlayerStats(PacketEnvelope envelope)
        {
            try
            {
                // 统一输出为前端约定的 snake_case 字段，避免大小写序列化差异导致数据不可见。
                var stats = StatsTracker.GetAllStats()
                    .Select(s => new
                    {
                        name = s.Name,
                        deaths = s.Deaths,
                        online_seconds = s.OnlineSeconds,
                    })
                    .OrderByDescending(x => x.online_seconds)
                    .ThenByDescending(x => x.deaths)
                    .ToList();
                await _wsService.SendAsync(new
                {
                    type = "player_stats_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, stats }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "player_stats_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        private static string NormalizeBanlistType(string? raw)
        {
            return (raw ?? string.Empty).Trim().ToLowerInvariant() switch
            {
                "tile" or "tiles" => "tile",
                "item" or "items" => "item",
                "proj" or "projectile" or "projectiles" => "proj",
                _ => string.Empty
            };
        }

        private static List<string> ParseAllowedGroups(JObject jobj)
        {
            static IEnumerable<string> SplitGroups(string raw)
            {
                return (raw ?? string.Empty)
                    .Split(new[] { ',', ';', '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries)
                    .Select(x => x.Trim())
                    .Where(x => !string.IsNullOrWhiteSpace(x));
            }

            static IEnumerable<string> FromToken(JToken? token)
            {
                if (token == null) return Enumerable.Empty<string>();

                if (token.Type == JTokenType.String)
                    return SplitGroups(token.ToString());

                if (token.Type == JTokenType.Array)
                {
                    var list = new List<string>();
                    foreach (var item in token)
                    {
                        if (item == null) continue;
                        if (item.Type == JTokenType.String)
                        {
                            var value = item.ToString().Trim();
                            if (!string.IsNullOrWhiteSpace(value))
                                list.Add(value);
                        }
                    }
                    return list;
                }

                return Enumerable.Empty<string>();
            }

            var merged = new List<string>();
            foreach (var key in new[] { "allowedGroups", "allowed_groups", "allowedGroupsList", "allowed_groups_list", "groups" })
            {
                merged.AddRange(FromToken(jobj[key]));
            }

            return merged
                .Select(x => x.Trim())
                .Where(x => !string.IsNullOrWhiteSpace(x))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToList();
        }

        public async Task HandleListBanlists(PacketEnvelope envelope)
        {
            try
            {
                var tiles = TShock.TileBans.TileBans
                    .Select(b => new { id = b.ID, allowedGroups = b.AllowedGroups })
                    .OrderBy(x => x.id)
                    .ToList();

                var items = (TShock.ItemBans?.DataModel?.ItemBans ?? new List<TShockAPI.DB.ItemBan>())
                    .Select(b => new { name = b.Name, allowedGroups = b.AllowedGroups })
                    .OrderBy(x => x.name)
                    .Cast<object>()
                    .ToList();

                var projectiles = TShock.ProjectileBans.ProjectileBans
                    .Select(b => new { id = b.ID, allowedGroups = b.AllowedGroups })
                    .OrderBy(x => x.id)
                    .ToList();

                await _wsService.SendAsync(new
                {
                    type = "list_banlists_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = true,
                        tiles,
                        items,
                        projectiles
                    }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "list_banlists_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = false,
                        msg = ex.Message,
                        tiles = new object[0],
                        items = new object[0],
                        projectiles = new object[0]
                    }
                });
            }
        }
        public async Task HandleAddBanlist(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var banType = NormalizeBanlistType(jobj["ban_type"]?.ToString());
            var id = jobj["id"]?.Value<int>() ?? 0;
            var allowedGroups = ParseAllowedGroups(jobj);

            try
            {
                if (string.IsNullOrWhiteSpace(banType))
                    throw new Exception("封禁类型无效");

                if (id <= 0)
                    throw new Exception("ID 无效");

                var invalidGroups = allowedGroups
                    .Where(g => !TShock.Groups.GroupExists(g))
                    .ToList();
                if (invalidGroups.Count > 0)
                    throw new Exception($"无效组: {string.Join(", ", invalidGroups)}");

                switch (banType)
                {
                    case "tile":
                        if (id >= TileID.Count)
                            throw new Exception("图格 ID 无效");

                        TShock.TileBans.AddNewBan((short)id);
                        foreach (var group in allowedGroups)
                        {
                            TShock.TileBans.AllowGroup((short)id, group);
                        }
                        break;

                    case "item":
                        if (id >= ItemID.Count)
                            throw new Exception("物品 ID 无效");

                        string itemName = TShockAPI.Localization.EnglishLanguage.GetItemNameById(id);
                        if (string.IsNullOrWhiteSpace(itemName))
                            throw new Exception("物品 ID 无效");

                        if (TShock.ItemBans?.DataModel == null)
                            throw new Exception("物品封禁数据模型不可用");

                        TShock.ItemBans.DataModel.AddNewBan(itemName);
                        foreach (var group in allowedGroups)
                        {
                            TShock.ItemBans.DataModel.AllowGroup(itemName, group);
                        }
                        break;

                    case "proj":
                        if (id >= ProjectileID.Count)
                            throw new Exception("弹幕 ID 无效");

                        TShock.ProjectileBans.AddNewBan((short)id);
                        foreach (var group in allowedGroups)
                        {
                            TShock.ProjectileBans.AllowGroup((short)id, group);
                        }
                        break;

                    default:
                        throw new Exception("未知封禁类型");
                }
                await _wsService.SendAsync(new
                {
                    type = "add_banlist_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = true,
                        msg = $"已添加/更新 ID: {id}"
                    }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "add_banlist_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = false,
                        msg = ex.Message
                    }
                });
            }
        }
        public async Task HandleRemoveBanlist(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var banType = NormalizeBanlistType(jobj["ban_type"]?.ToString());
            var id = jobj["id"]?.Value<int>() ?? 0;

            try
            {
                if (string.IsNullOrWhiteSpace(banType))
                    throw new Exception("封禁类型无效");

                if (id <= 0)
                    throw new Exception("ID 无效");

                switch (banType)
                {
                    case "tile":
                        TShock.TileBans.RemoveBan((short)id);
                        break;

                    case "item":
                        string itemName = TShockAPI.Localization.EnglishLanguage.GetItemNameById(id);
                        if (string.IsNullOrWhiteSpace(itemName))
                            throw new Exception("物品 ID 无效");
                        if (TShock.ItemBans?.DataModel == null)
                            throw new Exception("物品封禁数据模型不可用");
                        TShock.ItemBans.DataModel.RemoveBan(itemName);
                        break;

                    case "proj":
                        TShock.ProjectileBans.RemoveBan((short)id);
                        break;

                    default:
                        throw new Exception("未知封禁类型");
                }

                await _wsService.SendAsync(new
                {
                    type = "remove_banlist_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = true,
                        msg = $"已移除 ID: {id}"
                    }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "remove_banlist_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = false,
                        msg = ex.Message
                    }
                });
            }
        }

        public async Task HandleUpdateBanlistGroups(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var banType = NormalizeBanlistType(jobj["ban_type"]?.ToString());
            var id = jobj["id"]?.Value<int>() ?? 0;
            var allowedGroups = ParseAllowedGroups(jobj);

            try
            {
                if (string.IsNullOrWhiteSpace(banType))
                    throw new Exception("封禁类型无效");

                if (id <= 0)
                    throw new Exception("ID 无效");

                var invalidGroups = allowedGroups
                    .Where(g => !TShock.Groups.GroupExists(g))
                    .ToList();
                if (invalidGroups.Count > 0)
                    throw new Exception($"无效组: {string.Join(", ", invalidGroups)}");

                switch (banType)
                {
                    case "tile":
                        if (id >= TileID.Count)
                            throw new Exception("图格 ID 无效");
                        TShock.TileBans.RemoveBan((short)id);
                        TShock.TileBans.AddNewBan((short)id);
                        foreach (var group in allowedGroups)
                            TShock.TileBans.AllowGroup((short)id, group);
                        break;

                    case "item":
                        if (id >= ItemID.Count)
                            throw new Exception("物品 ID 无效");
                        string itemName = TShockAPI.Localization.EnglishLanguage.GetItemNameById(id);
                        if (string.IsNullOrWhiteSpace(itemName))
                            throw new Exception("物品 ID 无效");
                        if (TShock.ItemBans?.DataModel == null)
                            throw new Exception("物品封禁数据模型不可用");

                        TShock.ItemBans.DataModel.RemoveBan(itemName);
                        TShock.ItemBans.DataModel.AddNewBan(itemName);
                        foreach (var group in allowedGroups)
                            TShock.ItemBans.DataModel.AllowGroup(itemName, group);
                        break;

                    case "proj":
                        if (id >= ProjectileID.Count)
                            throw new Exception("弹幕 ID 无效");
                        TShock.ProjectileBans.RemoveBan((short)id);
                        TShock.ProjectileBans.AddNewBan((short)id);
                        foreach (var group in allowedGroups)
                            TShock.ProjectileBans.AllowGroup((short)id, group);
                        break;

                    default:
                        throw new Exception("未知封禁类型");
                }

                await _wsService.SendAsync(new
                {
                    type = "update_banlist_groups_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = true,
                        msg = $"已更新 ID: {id} 的允许组"
                    }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "update_banlist_groups_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = false,
                        msg = ex.Message
                    }
                });
            }
        }

        public async Task HandlePlayerList(PacketEnvelope envelope)
        {
            try
            {
                var onlineNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (var p in TShock.Players)
                {
                    if (p != null && p.Active && !string.IsNullOrEmpty(p.Name))
                        onlineNames.Add(p.Name);
                }

                var allUsers = TShock.UserAccounts.GetUserAccounts();
                var regMap = allUsers.ToDictionary(u => u.Name, StringComparer.OrdinalIgnoreCase);

                // 先列所有当前在线玩家（含未注册账号），再补离线的注册账号
                var players = new System.Collections.Generic.List<object>();
                foreach (var n in onlineNames)
                {
                    regMap.TryGetValue(n, out var acc);
                    var tsp = TShock.Players.FirstOrDefault(p => p != null && p.Active &&
                                   string.Equals(p.Name, n, StringComparison.OrdinalIgnoreCase));
                    var onlineAcc = tsp?.Account;
                    if (acc == null && !string.IsNullOrWhiteSpace(onlineAcc?.Name))
                        regMap.TryGetValue(onlineAcc!.Name, out acc);

                    var resolvedAccountName = !string.IsNullOrWhiteSpace(acc?.Name)
                        ? acc!.Name
                        : (!string.IsNullOrWhiteSpace(onlineAcc?.Name) ? onlineAcc!.Name : n);
                    var resolvedUserId = acc?.ID ?? ((onlineAcc?.ID ?? -1) > 0 ? onlineAcc!.ID : -1);
                    var grp = acc?.Group ?? onlineAcc?.Group ?? tsp?.Group?.Name ?? "guest";

                    players.Add(new
                    {
                        name = n,
                        account_name = resolvedAccountName,
                        group = grp,
                        online = true,
                        user_id = resolvedUserId,
                    });
                }
                foreach (var u in allUsers)
                {
                    if (!onlineNames.Contains(u.Name))
                        players.Add(new { name = u.Name, account_name = u.Name, group = u.Group, online = false, user_id = u.ID });
                }

                await _wsService.SendAsync(new
                {
                    type = "player_list_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, players }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "player_list_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandlePlayerAction(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var action = jobj["action"]?.ToString() ?? "";
            var player = jobj["player"]?.ToString() ?? "";
            var group = jobj["group"]?.ToString() ?? "";
            var reason = jobj["reason"]?.ToString() ?? "由管理员操作";
            var duration = (jobj["duration"]?.ToString() ?? "").Trim();

            try
            {
                string EscapeQuoted(string text) => (text ?? string.Empty).Replace("\\", "\\\\").Replace("\"", "\\\"");

                void ExecuteAsServer(string cmd)
                {
                    Commands.HandleCommand(TSPlayer.Server, cmd);
                }

                bool IsOnlineExact(string name)
                {
                    return TShock.Players.Any(p =>
                        p != null && p.Active &&
                        string.Equals(p.Name, name, StringComparison.OrdinalIgnoreCase));
                }

                string NormalizeDurationOrThrow(string raw)
                {
                    var d = (raw ?? string.Empty).Trim();
                    if (string.IsNullOrEmpty(d)) return string.Empty;
                    if (!System.Text.RegularExpressions.Regex.IsMatch(d, @"^\d+d\d+m\d+s$", System.Text.RegularExpressions.RegexOptions.IgnoreCase))
                        throw new Exception("封禁时长格式错误，应为 0d0m0s，例如 10d30m0s");
                    return d.ToLowerInvariant();
                }

                string BuildBanAddCommand(string name, string why, string dur)
                {
                    var online = IsOnlineExact(name);
                    var target = online ? $"tsn:{name}" : $"acc:{name}";
                    var flags = online ? string.Empty : " -e";
                    var safeReason = string.IsNullOrWhiteSpace(why) ? "由管理员操作" : why.Trim();
                    var safeDuration = NormalizeDurationOrThrow(dur);
                    if (string.IsNullOrEmpty(safeDuration))
                        return $"/ban add \"{EscapeQuoted(target)}\" \"{EscapeQuoted(safeReason)}\"{flags}";
                    return $"/ban add \"{EscapeQuoted(target)}\" \"{EscapeQuoted(safeReason)}\" {safeDuration}{flags}";
                }

                bool IsBanActive(TShockAPI.DB.Ban ban)
                {
                    return ban.ExpirationDateTime == DateTime.MaxValue || ban.ExpirationDateTime > DateTime.UtcNow;
                }

                bool BanIdentifierMatchesPlayer(string identifier, string playerName)
                {
                    if (string.IsNullOrWhiteSpace(identifier) || string.IsNullOrWhiteSpace(playerName)) return false;
                    var target = playerName.Trim();
                    var idx = identifier.IndexOf(':');
                    if (idx <= 0) return string.Equals(identifier.Trim(), target, StringComparison.OrdinalIgnoreCase);

                    var prefix = identifier.Substring(0, idx).Trim().ToLowerInvariant();
                    var value = identifier[(idx + 1)..].Trim();
                    // 仅按名称/账号类标识匹配，避免误命中 ip/uuid
                    if (prefix is "acc" or "name" or "n" or "a" or "tsn")
                        return string.Equals(value, target, StringComparison.OrdinalIgnoreCase);
                    return false;
                }

                int? ResolveActiveBanTicketByPlayerName(string playerName)
                {
                    TShock.Bans.UpdateBans();
                    var match = TShock.Bans.Bans.Values
                        .Where(b => b != null && IsBanActive(b) && BanIdentifierMatchesPlayer(b.Identifier, playerName))
                        .OrderByDescending(b => b.BanDateTime)
                        .ThenByDescending(b => b.TicketNumber)
                        .FirstOrDefault();
                    return match?.TicketNumber;
                }

                string msg;
                switch (action)
                {
                    case "mute":
                        {
                            var online = TShock.Players.FirstOrDefault(
                                p => p != null && p.Active &&
                                string.Equals(p.Name, player, StringComparison.OrdinalIgnoreCase));
                            if (online != null)
                            {
                                online.mute = true;
                                msg = $"已禁言玩家 {player}";
                            }
                            else
                            {
                                msg = $"玩家 {player} 当前不在线，禁言仅对在线玩家有效";
                            }
                            break;
                        }
                    case "unmute":
                        {
                            var online = TShock.Players.FirstOrDefault(
                                p => p != null && p.Active &&
                                string.Equals(p.Name, player, StringComparison.OrdinalIgnoreCase));
                            if (online != null) online.mute = false;
                            msg = $"已解除禁言 {player}";
                            break;
                        }
                    case "ban":
                        {
                            ExecuteAsServer(BuildBanAddCommand(player, reason, duration));
                            msg = $"已提交封禁指令：{player}";
                            break;
                        }
                    case "ban_status":
                        {
                            var ticket = ResolveActiveBanTicketByPlayerName(player);
                            var banned = ticket != null;
                            msg = banned
                                ? $"玩家 {player} 当前处于封禁状态 (#{ticket})"
                                : $"玩家 {player} 当前未被封禁";
                            await _wsService.SendAsync(new
                            {
                                type = "player_action_resp",
                                msg_id = Guid.NewGuid().ToString("N"),
                                timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                                payload = new { ref_id = envelope.MsgId, action, success = true, msg, banned, ticket }
                            });
                            return;
                        }
                    case "unban":
                        {
                            int? ticket = null;
                            if (jobj["ticket"] != null && int.TryParse(jobj["ticket"]!.ToString(), out var tFromPayload))
                                ticket = tFromPayload;
                            ticket ??= ResolveActiveBanTicketByPlayerName(player);
                            if (ticket == null)
                                throw new Exception($"未找到 {player} 对应的有效封禁 Ticket");

                            ExecuteAsServer($"/ban del {ticket.Value}");
                            msg = $"已按 Ticket 解封：{player} (#{ticket.Value})";
                            break;
                        }
                    case "setgroup":
                        {
                            if (string.IsNullOrEmpty(group)) throw new Exception("必须指定目标组名");
                            var grp = TShock.Groups.GetGroupByName(group);
                            if (grp == null) throw new Exception($"组不存在: {group}");
                            var user = TShock.UserAccounts.GetUserAccountByName(player);
                            if (user == null) throw new Exception($"未找到玩家: {player}");
                            TShock.UserAccounts.SetUserGroup(user, group);
                            msg = $"已将 {player} 的组修改为 {group}";
                            break;
                        }
                    case "kick":
                        {
                            var online = TShock.Players.FirstOrDefault(
                                p => p != null && p.Active &&
                                string.Equals(p.Name, player, StringComparison.OrdinalIgnoreCase));
                            if (online == null) throw new Exception($"玩家 {player} 当前不在线");
                            online.Kick(reason, true);
                            msg = $"已踢出玩家 {player}";
                            break;
                        }
                    case "give_item":
                        {
                            var online = TShock.Players.FirstOrDefault(
                                p => p != null && p.Active &&
                                string.Equals(p.Name, player, StringComparison.OrdinalIgnoreCase));
                            if (online == null) throw new Exception($"玩家 {player} 当前不在线，给予物品仅限在线玩家");
                            int itemId = jobj["item_id"]?.Value<int>() ?? 0;
                            int stack = jobj["stack"]?.Value<int>() ?? 1;
                            int prefix = jobj["prefix"]?.Value<int>() ?? 0;
                            // 若未提供有效 item_id，尝试按名称查找
                            if (itemId <= 0)
                            {
                                var itemNameQuery = jobj["item_name"]?.ToString()?.Trim() ?? "";
                                if (string.IsNullOrEmpty(itemNameQuery)) throw new Exception("无效的物品 ID 或名称");
                                for (int i = 1; i < Terraria.ID.ItemID.Count; i++)
                                {
                                    var it = new Terraria.Item();
                                    it.SetDefaults(i);
                                    if (string.Equals(it.Name, itemNameQuery, StringComparison.OrdinalIgnoreCase))
                                    { itemId = i; break; }
                                }
                                if (itemId <= 0) throw new Exception($"未找到物品: {itemNameQuery}");
                            }
                            if (stack <= 0) stack = 1;
                            online.GiveItem(itemId, stack, prefix);
                            string itemName = "";
                            try { var it = new Terraria.Item(); it.SetDefaults(itemId); itemName = it.Name ?? ""; } catch { }
                            msg = $"已给予 {player} {stack}x {(string.IsNullOrEmpty(itemName) ? $"物品#{itemId}" : itemName)}";
                            break;
                        }
                    case "ban_all":
                        {
                            // 封禁指定列表中所有角色
                            var chars = jobj["chars"] as JArray;
                            if (chars == null || chars.Count == 0) throw new Exception("未指定角色列表");
                            var results = new List<string>();
                            foreach (var c in chars)
                            {
                                var name = c.ToString();
                                if (string.IsNullOrWhiteSpace(name)) continue;
                                ExecuteAsServer(BuildBanAddCommand(name, reason, duration));
                                results.Add($"已提交封禁：{name}");
                            }
                            msg = string.Join("；", results);
                            break;
                        }
                    case "unban_all":
                        {
                            // 解封指定列表中所有角色
                            var chars = jobj["chars"] as JArray;
                            if (chars == null || chars.Count == 0) throw new Exception("未指定角色列表");
                            var results = new List<string>();
                            foreach (var c in chars)
                            {
                                var name = c.ToString();
                                if (string.IsNullOrWhiteSpace(name)) continue;
                                var ticket = ResolveActiveBanTicketByPlayerName(name);
                                if (ticket == null)
                                {
                                    results.Add($"未找到 Ticket：{name}");
                                    continue;
                                }
                                ExecuteAsServer($"/ban del {ticket.Value}");
                                results.Add($"已按 Ticket 解封：{name} (#{ticket.Value})");
                            }
                            msg = string.Join("；", results);
                            break;
                        }
                    case "set_stats":
                        {
                            // 修改玩家 SSC 基础属性（需要 SSC 开启）
                            if (!Main.ServerSideCharacter) throw new Exception("服务器未启用 SSC，无法修改属性");
                            var account = TShock.UserAccounts.GetUserAccountByName(player);
                            if (account == null) throw new Exception($"未找到玩家账号: {player}");
                            int maxHp = jobj["max_hp"]?.Value<int>() ?? 0;
                            int maxMana = jobj["max_mana"]?.Value<int>() ?? 0;
                            if (maxHp <= 0 && maxMana <= 0) throw new Exception("必须指定 max_hp 或 max_mana");
                            var data = TShock.CharacterDB.GetPlayerData(new TSPlayer(-1), account.ID);
                            if (data == null) throw new Exception($"玩家 {player} 无 SSC 数据");
                            if (maxHp > 0) data.maxHealth = Math.Min(maxHp, 500);
                            if (maxMana > 0) data.maxMana = Math.Min(maxMana, 200);
                            // 若在线则同步内存并写库
                            var onlineP = TShock.Players.FirstOrDefault(
                                p => p != null && p.Active &&
                                string.Equals(p.Name, player, StringComparison.OrdinalIgnoreCase));
                            if (onlineP != null)
                            {
                                onlineP.TPlayer.statLifeMax = data.maxHealth;
                                onlineP.TPlayer.statManaMax = data.maxMana;
                                TShock.CharacterDB.InsertPlayerData(onlineP, true);
                            }
                            else
                            {
                                // 离线：直接更新数据库行
                                var dbPath = Path.Combine(TShock.SavePath, "tshock.sqlite");
                                using var conn2 = new SqliteConnection($"Data Source={dbPath}");
                                conn2.Open();
                                using var cmd2 = conn2.CreateCommand();
                                cmd2.CommandText = "UPDATE tsCharacter SET MaxHealth=@mh,MaxMana=@mm WHERE Account=@id";
                                cmd2.Parameters.AddWithValue("@mh", data.maxHealth);
                                cmd2.Parameters.AddWithValue("@mm", data.maxMana);
                                cmd2.Parameters.AddWithValue("@id", account.ID);
                                cmd2.ExecuteNonQuery();
                            }
                            msg = $"已更新 {player} 的属性（血量上限 {data.maxHealth}，魔力上限 {data.maxMana}）";
                            break;
                        }
                    default:
                        throw new Exception($"未知操作: {action}");
                }

                await _wsService.SendAsync(new
                {
                    type = "player_action_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, action, success = true, msg }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "player_action_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, action, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandleGetGroups(PacketEnvelope envelope)
        {
            try
            {
                var groups = TShock.Groups.groups.Select(g => g.Name).OrderBy(n => n).ToList();
                await _wsService.SendAsync(new
                {
                    type = "get_groups_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, groups }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "get_groups_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message, groups = new string[0] }
                });
            }
        }

        private static bool IsBanActiveRecord(TShockAPI.DB.Ban ban)
        {
            return ban.ExpirationDateTime == DateTime.MaxValue || ban.ExpirationDateTime > DateTime.UtcNow;
        }

        private static string ReadBanString(TShockAPI.DB.Ban ban, params string[] names)
        {
            var t = ban.GetType();
            foreach (var name in names)
            {
                var p = t.GetProperty(name);
                if (p != null)
                {
                    var v = p.GetValue(ban)?.ToString();
                    if (!string.IsNullOrWhiteSpace(v)) return v;
                }

                var f = t.GetField(name);
                if (f != null)
                {
                    var v = f.GetValue(ban)?.ToString();
                    if (!string.IsNullOrWhiteSpace(v)) return v;
                }
            }
            return string.Empty;
        }

        private static string ParseBanTarget(string identifier)
        {
            if (string.IsNullOrWhiteSpace(identifier)) return string.Empty;
            var raw = identifier.Trim();
            var idx = raw.IndexOf(':');
            if (idx <= 0) return raw;
            return raw[(idx + 1)..].Trim();
        }

        public async Task HandleListBans(PacketEnvelope envelope)
        {
            try
            {
                TShock.Bans.UpdateBans();

                var bans = TShock.Bans.Bans.Values
                    .Where(b => b != null)
                    .OrderByDescending(b => b.BanDateTime)
                    .ThenByDescending(b => b.TicketNumber)
                    .Select(b =>
                    {
                        var active = IsBanActiveRecord(b);
                        var expireAt = b.ExpirationDateTime == DateTime.MaxValue
                            ? string.Empty
                            : b.ExpirationDateTime.ToString("yyyy-MM-dd HH:mm:ss");
                        var remainingSeconds = b.ExpirationDateTime == DateTime.MaxValue
                            ? (long?)null
                            : Math.Max(0, (long)(b.ExpirationDateTime - DateTime.UtcNow).TotalSeconds);

                        return new
                        {
                            ticket = b.TicketNumber,
                            identifier = b.Identifier ?? string.Empty,
                            target = ParseBanTarget(b.Identifier ?? string.Empty),
                            reason = ReadBanString(b, "Reason", "reason", "BanReason", "banReason"),
                            banned_by = ReadBanString(b, "BanningUser", "BannedBy", "banner", "Banner"),
                            ban_time = b.BanDateTime.ToString("yyyy-MM-dd HH:mm:ss"),
                            expiration_time = expireAt,
                            active,
                            remaining_seconds = remainingSeconds
                        };
                    })
                    .ToList();

                await _wsService.SendAsync(new
                {
                    type = "list_bans_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = true,
                        bans
                    }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "list_bans_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = false,
                        msg = ex.Message,
                        bans = new object[0]
                    }
                });
            }
        }

        public async Task HandleUnbanByTicket(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            int ticket = jobj["ticket"]?.Value<int>() ?? 0;

            try
            {
                if (ticket <= 0) throw new Exception("Ticket 无效");

                TShock.Bans.UpdateBans();
                var exists = TShock.Bans.Bans.Values.Any(b => b != null && b.TicketNumber == ticket);
                if (!exists) throw new Exception($"未找到封禁 Ticket: {ticket}");

                Commands.HandleCommand(TSPlayer.Server, $"/ban del {ticket}");

                await _wsService.SendAsync(new
                {
                    type = "unban_by_ticket_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = true,
                        msg = $"已解除封禁 Ticket #{ticket}",
                        ticket
                    }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "unban_by_ticket_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = false,
                        msg = ex.Message,
                        ticket
                    }
                });
            }
        }

        public async Task HandleUpdateBanExpiration(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            int ticket = jobj["ticket"]?.Value<int>() ?? 0;
            var duration = (jobj["duration"]?.ToString() ?? string.Empty).Trim();
            var expirationText = (jobj["expiration_time"]?.ToString() ?? string.Empty).Trim();
            var permanent = jobj["permanent"]?.Value<bool>() ?? false;

            try
            {
                if (ticket <= 0) throw new Exception("Ticket 无效");

                string NormalizeDurationOrThrow(string raw)
                {
                    var d = (raw ?? string.Empty).Trim();
                    if (string.IsNullOrEmpty(d)) return string.Empty;
                    if (!System.Text.RegularExpressions.Regex.IsMatch(d, @"^\d+d\d+m\d+s$", System.Text.RegularExpressions.RegexOptions.IgnoreCase))
                        throw new Exception("封禁时长格式错误，应为 0d0m0s，例如 10d30m0s");
                    return d.ToLowerInvariant();
                }

                DateTime ParseExpireDateTime(string durationText, string expirationRaw, bool isPermanent)
                {
                    if (isPermanent) return DateTime.MaxValue;

                    var text = (expirationRaw ?? string.Empty).Trim();
                    if (!string.IsNullOrEmpty(text))
                    {
                        var formats = new[]
                        {
                            "yyyy-MM-dd'T'HH:mm",
                            "yyyy-MM-dd'T'HH:mm:ss",
                            "yyyy-MM-dd HH:mm:ss"
                        };

                        if (!DateTime.TryParseExact(
                                text,
                                formats,
                                CultureInfo.InvariantCulture,
                                DateTimeStyles.AssumeLocal,
                                out var parsedLocal))
                        {
                            throw new Exception("到期时间格式错误，请重新选择日期时间");
                        }

                        return parsedLocal.ToUniversalTime();
                    }

                    var d = NormalizeDurationOrThrow(durationText);
                    if (string.IsNullOrEmpty(d)) return DateTime.MaxValue;

                    var m = System.Text.RegularExpressions.Regex.Match(d, @"^(\d+)d(\d+)m(\d+)s$", System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                    var days = int.Parse(m.Groups[1].Value);
                    var minutes = int.Parse(m.Groups[2].Value);
                    var seconds = int.Parse(m.Groups[3].Value);
                    return DateTime.UtcNow
                        .AddDays(days)
                        .AddMinutes(minutes)
                        .AddSeconds(seconds);
                }

                TShock.Bans.UpdateBans();
                var oldBan = TShock.Bans.GetBanById(ticket);
                if (oldBan == null) throw new Exception($"未找到封禁 Ticket: {ticket}");

                var newExpire = ParseExpireDateTime(duration, expirationText, permanent);
                var id = oldBan.Identifier ?? string.Empty;
                if (string.IsNullOrWhiteSpace(id)) throw new Exception("封禁标识为空，无法更新到期时间");

                var reason = ReadBanString(oldBan, "Reason", "reason", "BanReason", "banReason");
                var bannedBy = ReadBanString(oldBan, "BanningUser", "BannedBy", "banner", "Banner");
                if (string.IsNullOrWhiteSpace(bannedBy)) bannedBy = "Panel";

                var oldBanTime = oldBan.BanDateTime;

                // 旧票据先删除再重建，以保证能按新到期时间落库。
                var removed = TShock.Bans.RemoveBan(ticket, true);
                if (!removed) throw new Exception($"更新失败，无法删除旧 Ticket: {ticket}");

                var inserted = TShock.Bans.InsertBan(id, reason, bannedBy, oldBanTime, newExpire);
                if (inserted?.Ban == null)
                    throw new Exception($"更新失败，重建封禁记录失败: {inserted?.Message ?? "未知错误"}");

                var newTicket = inserted.Ban.TicketNumber;

                await _wsService.SendAsync(new
                {
                    type = "update_ban_expiration_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = true,
                        old_ticket = ticket,
                        new_ticket = newTicket,
                        msg = newTicket == ticket
                            ? $"已更新 Ticket #{ticket} 的到期时间"
                            : $"已更新到期时间，Ticket #{ticket} 已重建为 #{newTicket}"
                    }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "update_ban_expiration_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = false,
                        msg = ex.Message,
                        ticket
                    }
                });
            }
        }

        public async Task HandleListGameGroups(PacketEnvelope envelope)
        {
            try
            {
                object? ReadMemberValue(object obj, params string[] names)
                {
                    var t = obj.GetType();
                    foreach (var name in names)
                    {
                        var p = t.GetProperty(name);
                        if (p != null)
                        {
                            var pv = p.GetValue(obj);
                            if (pv != null) return pv;
                        }

                        var f = t.GetField(name);
                        if (f != null)
                        {
                            var fv = f.GetValue(obj);
                            if (fv != null) return fv;
                        }
                    }
                    return null;
                }

                string ReadStringProp(object obj, params string[] names)
                {
                    var v = ReadMemberValue(obj, names);
                    return v?.ToString() ?? string.Empty;
                }

                List<string> ToPermissionList(object? raw)
                {
                    if (raw == null) return new List<string>();
                    if (raw is string s)
                    {
                        return s
                            .Split(new[] { ',', ';', '\n', '\r', '\t', ' ' }, StringSplitOptions.RemoveEmptyEntries)
                            .Select(x => x.Trim())
                            .Where(x => !string.IsNullOrWhiteSpace(x))
                            .Distinct(StringComparer.OrdinalIgnoreCase)
                            .OrderBy(x => x)
                            .ToList();
                    }
                    if (raw is IEnumerable<string> list)
                    {
                        return list
                            .Select(x => x?.Trim() ?? string.Empty)
                            .Where(x => !string.IsNullOrWhiteSpace(x))
                            .Distinct(StringComparer.OrdinalIgnoreCase)
                            .OrderBy(x => x)
                            .ToList();
                    }
                    if (raw is System.Collections.IEnumerable objList)
                    {
                        var result = new List<string>();
                        foreach (var item in objList)
                        {
                            var text = item?.ToString()?.Trim() ?? string.Empty;
                            if (!string.IsNullOrWhiteSpace(text)) result.Add(text);
                        }
                        return result
                            .Distinct(StringComparer.OrdinalIgnoreCase)
                            .OrderBy(x => x)
                            .ToList();
                    }
                    return new List<string>();
                }

                List<string> ReadPermissions(object obj)
                {
                    foreach (var name in new[] { "Permissions", "permissions", "Perms", "perms", "TotalPermissions", "totalPermissions" })
                    {
                        var val = ReadMemberValue(obj, name);
                        var parsed = ToPermissionList(val);
                        if (parsed.Count > 0) return parsed;
                    }
                    return new List<string>();
                }

                var groupDict = new Dictionary<string, (string parent, string prefix, string suffix, string chatColor, List<string> permissions)>(StringComparer.OrdinalIgnoreCase);

                // 优先从数据库读取（GroupList.Commands 为真实存储的权限列表）
                var dbPath = Path.Combine(TShock.SavePath, "tshock.sqlite");
                if (File.Exists(dbPath))
                {
                    using var conn = new SqliteConnection($"Data Source={dbPath}");
                    conn.Open();
                    using var cmd = conn.CreateCommand();
                    cmd.CommandText = "SELECT GroupName, Parent, Commands, Prefix, Suffix, ChatColor FROM GroupList";
                    using var reader = cmd.ExecuteReader();
                    while (reader.Read())
                    {
                        var name = reader["GroupName"]?.ToString() ?? string.Empty;
                        if (string.IsNullOrWhiteSpace(name)) continue;

                        var parent = reader["Parent"]?.ToString() ?? string.Empty;
                        var cmds = reader["Commands"]?.ToString() ?? string.Empty;
                        var prefix = reader["Prefix"]?.ToString() ?? string.Empty;
                        var suffix = reader["Suffix"]?.ToString() ?? string.Empty;
                        var chatColor = reader["ChatColor"]?.ToString() ?? string.Empty;

                        groupDict[name] = (parent, prefix, suffix, chatColor, ToPermissionList(cmds));
                    }
                }

                // 再从内存对象补齐（例如 superadmin 这类可能不在 GroupList 的组）
                foreach (var g in TShock.Groups.groups)
                {
                    var name = ReadStringProp(g, "Name");
                    if (string.IsNullOrWhiteSpace(name)) continue;
                    if (groupDict.ContainsKey(name)) continue;

                    var parent = ReadStringProp(g, "ParentName", "Parent");
                    var prefix = ReadStringProp(g, "Prefix");
                    var suffix = ReadStringProp(g, "Suffix");
                    var chatColor = ReadStringProp(g, "ChatColor");
                    var permissions = ReadPermissions(g);

                    groupDict[name] = (parent, prefix, suffix, chatColor, permissions);
                }

                var groups = groupDict
                    .Select(kv => new
                    {
                        name = kv.Key,
                        parent = kv.Value.parent,
                        prefix = kv.Value.prefix,
                        suffix = kv.Value.suffix,
                        chat_color = kv.Value.chatColor,
                        permissions = kv.Value.permissions,
                    })
                    .OrderBy(g => g.name)
                    .ToList();

                await _wsService.SendAsync(new
                {
                    type = "list_game_groups_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, groups }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "list_game_groups_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message, groups = new object[0] }
                });
            }
        }

        private static List<string> ParsePermissionsFromPayload(JToken? token)
        {
            if (token == null) return new List<string>();
            if (token is JArray arr)
            {
                return arr
                    .Select(x => x?.ToString()?.Trim() ?? string.Empty)
                    .Where(x => !string.IsNullOrWhiteSpace(x))
                    .Distinct(StringComparer.OrdinalIgnoreCase)
                    .OrderBy(x => x)
                    .ToList();
            }

            var raw = token.ToString();
            return raw
                .Split(new[] { ',', ';', '\n', '\r', '\t', ' ' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(x => x.Trim())
                .Where(x => !string.IsNullOrWhiteSpace(x))
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .OrderBy(x => x)
                .ToList();
        }

        private static string JoinPermissions(IEnumerable<string> permissions)
        {
            return string.Join(",", permissions
                .Select(x => x?.Trim() ?? string.Empty)
                .Where(x => !string.IsNullOrWhiteSpace(x))
                .Distinct(StringComparer.OrdinalIgnoreCase));
        }

        private static void ReloadGroupCache()
        {
            try
            {
                // TShock 原生方法名为 LoadPermisions（上游拼写如此）
                TShock.Groups.LoadPermisions();
            }
            catch
            {
                // 兜底：触发一次 reload
                Commands.HandleCommand(TSPlayer.Server, "/reload");
            }
        }

        public async Task HandleCreateGameGroup(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var name = (jobj["name"]?.ToString() ?? string.Empty).Trim();
            var parent = (jobj["parent"]?.ToString() ?? string.Empty).Trim();
            var prefix = (jobj["prefix"]?.ToString() ?? string.Empty).Trim();
            var suffix = (jobj["suffix"]?.ToString() ?? string.Empty).Trim();
            var chatColor = (jobj["chat_color"]?.ToString() ?? string.Empty).Trim();
            var permissions = ParsePermissionsFromPayload(jobj["permissions"]);

            try
            {
                if (string.IsNullOrWhiteSpace(name))
                    throw new Exception("组名不能为空");

                var dbPath = Path.Combine(TShock.SavePath, "tshock.sqlite");
                using var conn = new SqliteConnection($"Data Source={dbPath}");
                conn.Open();

                using (var chk = conn.CreateCommand())
                {
                    chk.CommandText = "SELECT 1 FROM GroupList WHERE GroupName=@name LIMIT 1";
                    chk.Parameters.AddWithValue("@name", name);
                    if (chk.ExecuteScalar() != null)
                        throw new Exception($"组已存在: {name}");
                }

                if (!string.IsNullOrWhiteSpace(parent))
                {
                    using var chkParent = conn.CreateCommand();
                    chkParent.CommandText = "SELECT 1 FROM GroupList WHERE GroupName=@parent LIMIT 1";
                    chkParent.Parameters.AddWithValue("@parent", parent);
                    if (chkParent.ExecuteScalar() == null)
                        throw new Exception($"父组不存在: {parent}");
                }

                using (var ins = conn.CreateCommand())
                {
                    ins.CommandText = @"
                        INSERT INTO GroupList (GroupName, Parent, Commands, ChatColor, Prefix, Suffix)
                        VALUES (@name, @parent, @cmds, @color, @prefix, @suffix)";
                    ins.Parameters.AddWithValue("@name", name);
                    ins.Parameters.AddWithValue("@parent", parent);
                    ins.Parameters.AddWithValue("@cmds", JoinPermissions(permissions));
                    ins.Parameters.AddWithValue("@color", string.IsNullOrWhiteSpace(chatColor) ? "255,255,255" : chatColor);
                    ins.Parameters.AddWithValue("@prefix", string.IsNullOrWhiteSpace(prefix) ? DBNull.Value : prefix);
                    ins.Parameters.AddWithValue("@suffix", string.IsNullOrWhiteSpace(suffix) ? DBNull.Value : suffix);
                    ins.ExecuteNonQuery();
                }

                ReloadGroupCache();

                await _wsService.SendAsync(new
                {
                    type = "create_game_group_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, msg = $"已创建组: {name}" }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "create_game_group_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandleUpdateGameGroup(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var name = (jobj["name"]?.ToString() ?? string.Empty).Trim();
            var oldName = (jobj["old_name"]?.ToString() ?? name).Trim();
            var parent = (jobj["parent"]?.ToString() ?? string.Empty).Trim();
            var prefix = (jobj["prefix"]?.ToString() ?? string.Empty).Trim();
            var suffix = (jobj["suffix"]?.ToString() ?? string.Empty).Trim();
            var chatColor = (jobj["chat_color"]?.ToString() ?? string.Empty).Trim();
            var permissions = ParsePermissionsFromPayload(jobj["permissions"]);

            try
            {
                if (string.IsNullOrWhiteSpace(name) || string.IsNullOrWhiteSpace(oldName))
                    throw new Exception("组名不能为空");

                if (!string.Equals(oldName, name, StringComparison.OrdinalIgnoreCase))
                {
                    if (string.Equals(oldName, "superadmin", StringComparison.OrdinalIgnoreCase) ||
                        string.Equals(oldName, "default", StringComparison.OrdinalIgnoreCase))
                        throw new Exception("内置组不允许重命名");
                }

                if (string.Equals(oldName, "superadmin", StringComparison.OrdinalIgnoreCase))
                {
                    throw new Exception("内置超级管理员组(superadmin)不允许被修改");
                }

                var dbPath = Path.Combine(TShock.SavePath, "tshock.sqlite");
                using var conn = new SqliteConnection($"Data Source={dbPath}");
                conn.Open();
                using var tx = conn.BeginTransaction();

                using (var chkOld = conn.CreateCommand())
                {
                    chkOld.Transaction = tx;
                    chkOld.CommandText = "SELECT ChatColor FROM GroupList WHERE GroupName=@old LIMIT 1";
                    chkOld.Parameters.AddWithValue("@old", oldName);
                    var chatColorObj = chkOld.ExecuteScalar();
                    if (chatColorObj == null)
                        throw new Exception($"组不存在: {oldName}");

                    if (!string.Equals(oldName, name, StringComparison.OrdinalIgnoreCase))
                    {
                        using var chkNew = conn.CreateCommand();
                        chkNew.Transaction = tx;
                        chkNew.CommandText = "SELECT 1 FROM GroupList WHERE GroupName=@name LIMIT 1";
                        chkNew.Parameters.AddWithValue("@name", name);
                        if (chkNew.ExecuteScalar() != null)
                            throw new Exception($"目标组名已存在: {name}");
                    }

                    if (!string.IsNullOrWhiteSpace(parent))
                    {
                        using var chkParent = conn.CreateCommand();
                        chkParent.Transaction = tx;
                        chkParent.CommandText = "SELECT 1 FROM GroupList WHERE GroupName=@parent LIMIT 1";
                        chkParent.Parameters.AddWithValue("@parent", parent);
                        if (chkParent.ExecuteScalar() == null)
                            throw new Exception($"父组不存在: {parent}");
                    }

                    var color = string.IsNullOrWhiteSpace(chatColor)
                        ? (chatColorObj?.ToString() ?? "255,255,255")
                        : chatColor;

                    using var upd = conn.CreateCommand();
                    upd.Transaction = tx;
                    upd.CommandText = @"
                        UPDATE GroupList
                           SET GroupName=@name,
                               Parent=@parent,
                               Commands=@cmds,
                               Prefix=@prefix,
                               Suffix=@suffix,
                               ChatColor=@color
                         WHERE GroupName=@old";
                    upd.Parameters.AddWithValue("@name", name);
                    upd.Parameters.AddWithValue("@parent", parent);
                    upd.Parameters.AddWithValue("@cmds", JoinPermissions(permissions));
                    upd.Parameters.AddWithValue("@prefix", string.IsNullOrWhiteSpace(prefix) ? DBNull.Value : prefix);
                    upd.Parameters.AddWithValue("@suffix", string.IsNullOrWhiteSpace(suffix) ? DBNull.Value : suffix);
                    upd.Parameters.AddWithValue("@color", color);
                    upd.Parameters.AddWithValue("@old", oldName);
                    upd.ExecuteNonQuery();

                    if (!string.Equals(oldName, name, StringComparison.OrdinalIgnoreCase))
                    {
                        using var updParent = conn.CreateCommand();
                        updParent.Transaction = tx;
                        updParent.CommandText = "UPDATE GroupList SET Parent=@new WHERE Parent=@old";
                        updParent.Parameters.AddWithValue("@new", name);
                        updParent.Parameters.AddWithValue("@old", oldName);
                        updParent.ExecuteNonQuery();

                        using var updUsers = conn.CreateCommand();
                        updUsers.Transaction = tx;
                        updUsers.CommandText = "UPDATE Users SET Usergroup=@new WHERE Usergroup=@old";
                        updUsers.Parameters.AddWithValue("@new", name);
                        updUsers.Parameters.AddWithValue("@old", oldName);
                        updUsers.ExecuteNonQuery();
                    }
                }

                tx.Commit();
                ReloadGroupCache();

                await _wsService.SendAsync(new
                {
                    type = "update_game_group_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, msg = $"已更新组: {oldName} -> {name}" }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "update_game_group_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandleDeleteGameGroup(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var name = (jobj["name"]?.ToString() ?? string.Empty).Trim();

            try
            {
                if (string.IsNullOrWhiteSpace(name))
                    throw new Exception("组名不能为空");

                if (string.Equals(name, "superadmin", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(name, "default", StringComparison.OrdinalIgnoreCase))
                    throw new Exception("内置组不可删除");

                var dbPath = Path.Combine(TShock.SavePath, "tshock.sqlite");
                using var conn = new SqliteConnection($"Data Source={dbPath}");
                conn.Open();
                using var tx = conn.BeginTransaction();

                using (var del = conn.CreateCommand())
                {
                    del.Transaction = tx;
                    del.CommandText = "DELETE FROM GroupList WHERE GroupName=@name";
                    del.Parameters.AddWithValue("@name", name);
                    var affected = del.ExecuteNonQuery();
                    if (affected == 0)
                        throw new Exception($"组不存在: {name}");
                }

                using (var updParent = conn.CreateCommand())
                {
                    updParent.Transaction = tx;
                    updParent.CommandText = "UPDATE GroupList SET Parent='' WHERE Parent=@name";
                    updParent.Parameters.AddWithValue("@name", name);
                    updParent.ExecuteNonQuery();
                }

                using (var updUsers = conn.CreateCommand())
                {
                    updUsers.Transaction = tx;
                    updUsers.CommandText = "UPDATE Users SET Usergroup='default' WHERE Usergroup=@name";
                    updUsers.Parameters.AddWithValue("@name", name);
                    updUsers.ExecuteNonQuery();
                }

                tx.Commit();
                ReloadGroupCache();

                await _wsService.SendAsync(new
                {
                    type = "delete_game_group_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, msg = $"已删除组: {name}" }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "delete_game_group_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandleRegisterUser(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var username = jobj["username"]?.ToString() ?? "";
            var password = jobj["password"]?.ToString() ?? "";
            var panelEmail = jobj["panel_user_email"]?.ToString() ?? "";
            var panelUserId = jobj["panel_user_id"]?.Value<long>() ?? 0;
            var registerLimit = jobj["register_limit"]?.Value<int>() ?? 1;

            if (string.IsNullOrWhiteSpace(username) || string.IsNullOrWhiteSpace(password))
            {
                await _wsService.SendAsync(new
                {
                    type = "register_user_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = false,
                        msg = "用户名或密码不能为空",
                        panel_user_email = panelEmail,
                        username
                    }
                });
                return;
            }

            try
            {
                if (TShock.UserAccounts.GetUserAccountByName(username) != null)
                    throw new Exception($"用户名 \"{username}\" 已存在");
                if (panelUserId <= 0)
                    throw new Exception("面板账号状态异常");
                if (AgentLocalStore.CharacterExists(username))
                    throw new Exception("该游戏账号已绑定到面板账号，无法重复注册");
                if (registerLimit > 0 && AgentLocalStore.CountCharacters(panelUserId) >= registerLimit)
                    throw new Exception($"当前账号可注册角色已达上限（{registerLimit}）");

                var account = new TShockAPI.DB.UserAccount();
                account.Name = username;
                account.Group = "default";
                account.CreateBCryptHash(password);
                TShock.UserAccounts.AddUserAccount(account);
                var binding = AgentLocalStore.UpsertCharacter(panelUserId, panelEmail, username, "register_user");

                await _wsService.SendAsync(new
                {
                    type = "register_user_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = true,
                        msg = $"角色 {username} 注册成功",
                        panel_user_email = panelEmail,
                        panel_user_id = panelUserId,
                        username,
                        registered_at = binding.RegisteredAt
                    }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "register_user_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = false,
                        msg = ex.Message,
                        panel_user_email = panelEmail,
                        username
                    }
                });
            }
        }

        public async Task HandleDeleteUser(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var username = jobj["username"]?.ToString() ?? "";
            var operatorEmail = jobj["operator_email"]?.ToString() ?? "unknown";

            if (string.IsNullOrWhiteSpace(username))
            {
                await _wsService.SendAsync(new
                {
                    type = "delete_user_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "用户名不能为空", username }
                });
                return;
            }

            try
            {
                var account = ResolveUserAccountLoose(username);
                if (account == null)
                    throw new Exception($"游戏账号 \"{CanonicalizeAccountName(username)}\" 不存在");

                TShock.UserAccounts.RemoveUserAccount(account);
                AgentLocalStore.DeleteCharacter(account.Name);

                string logEntry = $"[面板操作] 角色删除 — 请求账号: {username}, 实际账号: {account.Name}, 操作者: {operatorEmail}, 时间: {DateTime.Now:yyyy-MM-dd HH:mm:ss}";
                TShock.Log.Info(logEntry);

                await _wsService.SendAsync(new
                {
                    type = "delete_user_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = true,
                        msg = $"角色 {account.Name} 已删除",
                        username = account.Name,
                        operator_email = operatorEmail
                    }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "delete_user_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message, username }
                });
            }
        }

        private static string ExtractColorTaggedName(string raw)
        {
            var value = (raw ?? string.Empty).Trim();
            if (string.IsNullOrEmpty(value)) return value;

            if (!value.StartsWith("[c/", StringComparison.OrdinalIgnoreCase))
                return value;

            var colonIdx = value.IndexOf(':');
            var endIdx = value.LastIndexOf(']');
            if (colonIdx > 0 && endIdx > colonIdx)
            {
                var inner = value.Substring(colonIdx + 1, endIdx - colonIdx - 1).Trim();
                if (!string.IsNullOrWhiteSpace(inner)) return inner;
            }
            return value;
        }

        private static string TrimTailPunctuation(string raw)
        {
            var value = (raw ?? string.Empty).Trim();
            if (string.IsNullOrEmpty(value)) return value;

            while (value.Length > 0)
            {
                var ch = value[value.Length - 1];
                if (ch == '.' || ch == '。' || ch == ',' || ch == '，' ||
                    ch == '!' || ch == '！' || ch == '?' || ch == '？' ||
                    ch == ';' || ch == '；' || ch == ':' || ch == '：')
                {
                    value = value.Substring(0, value.Length - 1).TrimEnd();
                    continue;
                }
                break;
            }

            return value;
        }

        private static string CanonicalizeAccountName(string raw)
        {
            return TrimTailPunctuation(ExtractColorTaggedName(raw)).Trim();
        }

        private static TShockAPI.DB.UserAccount? ResolveUserAccountLoose(string username)
        {
            var canonical = CanonicalizeAccountName(username);
            if (string.IsNullOrWhiteSpace(canonical)) return null;

            var direct = TShock.UserAccounts.GetUserAccountByName(canonical);
            if (direct != null) return direct;

            var allUsers = TShock.UserAccounts.GetUserAccounts();

            var exact = allUsers.FirstOrDefault(u =>
                string.Equals((u?.Name ?? string.Empty).Trim(), canonical, StringComparison.OrdinalIgnoreCase));
            if (exact != null) return exact;

            // 兼容“传入在线显示名而非账号名”的场景：若在线玩家已登录账号，优先按其登录账号删除。
            var online = TShock.Players.FirstOrDefault(p =>
                p != null && p.Active &&
                string.Equals(CanonicalizeAccountName(p.Name), canonical, StringComparison.OrdinalIgnoreCase) &&
                p.Account != null && p.Account.ID > 0);
            if (online?.Account != null) return online.Account;

            var looseMatches = allUsers
                .Where(u => u != null &&
                            string.Equals(CanonicalizeAccountName(u.Name), canonical, StringComparison.OrdinalIgnoreCase))
                .ToList();

            if (looseMatches.Count == 1) return looseMatches[0];
            if (looseMatches.Count > 1)
            {
                throw new Exception($"找到多个可能账号，无法确定删除目标: {string.Join(", ", looseMatches.Select(u => u.Name).Take(5))}");
            }

            return null;
        }

        public async Task HandleChangePassword(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var username = jobj["username"]?.ToString() ?? "";
            var newPassword = jobj["new_password"]?.ToString() ?? "";

            bool success = false;
            string msg = "";
            try
            {
                if (string.IsNullOrWhiteSpace(username) || string.IsNullOrWhiteSpace(newPassword))
                    throw new Exception("用户名和新密码不能为空");

                var account = TShock.UserAccounts.GetUserAccountByName(username);
                if (account == null)
                    throw new Exception($"账号 \"{username}\" 不存在");

                TShock.UserAccounts.SetUserAccountPassword(account, newPassword);
                success = true;
                msg = $"账号 {username} 密码已更新";
            }
            catch (Exception ex)
            {
                msg = ex.Message;
            }

            await _wsService.SendAsync(new
            {
                type = "change_password_resp",
                msg_id = Guid.NewGuid().ToString("N"),
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                payload = new { ref_id = envelope.MsgId, success, msg, username }
            });
        }

        public async Task HandleSendBindCode(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var username = jobj["username"]?.ToString() ?? "";
            var code = jobj["code"]?.ToString() ?? "";

            if (string.IsNullOrWhiteSpace(username) || string.IsNullOrWhiteSpace(code))
            {
                await _wsService.SendAsync(new
                {
                    type = "send_bind_code_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "参数不完整" }
                });
                return;
            }

            if (AgentLocalStore.CharacterExists(username))
            {
                await _wsService.SendAsync(new
                {
                    type = "send_bind_code_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "该游戏账号已绑定到面板账号，无法重复绑定" }
                });
                return;
            }

            TSPlayer target = null;
            var foundOnline = false;
            foreach (var p in TShock.Players)
            {
                if (p == null || !p.Active) continue;
                if (p.Name.Equals(username, StringComparison.OrdinalIgnoreCase))
                {
                    foundOnline = true;
                    if (p.IsLoggedIn && p.Account != null)
                    {
                        target = p;
                    }
                    break;
                }
            }

            if (target == null)
            {
                var failMsg = foundOnline
                    ? $"角色 {username} 已在线，但尚未登录账号；必须该角色在线且完成登录后才能发送验证码"
                    : $"角色 {username} 当前不在线；必须该角色在线且完成登录后才能发送验证码";

                await _wsService.SendAsync(new
                {
                    type = "send_bind_code_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = false,
                        msg = failMsg
                    }
                });
                return;
            }

            target.SendInfoMessage($"[面板绑定] 您的绑定验证码为: {code}，有效期10分钟。请在面板中输入此验证码完成绑定。");

            await _wsService.SendAsync(new
            {
                type = "send_bind_code_resp",
                msg_id = Guid.NewGuid().ToString("N"),
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                payload = new
                {
                    ref_id = envelope.MsgId,
                    success = true,
                    msg = $"验证码已发送给玩家 {username}"
                }
            });
        }

        public async Task HandleGetCharInfo(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var username = jobj["username"]?.ToString() ?? "";

            if (string.IsNullOrWhiteSpace(username))
            {
                await _wsService.SendAsync(new
                {
                    type = "get_char_info_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "用户名不能为空" }
                });
                return;
            }

            try
            {
                var account = TShock.UserAccounts.GetUserAccountByName(username);
                string group = account?.Group ?? "guest";
                bool exists = account != null;

                var inventoryItems = new List<object>();
                bool hasSscData = false;

                if (Main.ServerSideCharacter && account != null)
                {
                    try
                    {
                        var dbPath = Path.Combine(TShock.SavePath, "tshock.sqlite");
                        if (File.Exists(dbPath))
                        {
                            using var conn = new SqliteConnection($"Data Source={dbPath};Mode=ReadOnly");
                            conn.Open();
                            using var cmd = conn.CreateCommand();
                            cmd.CommandText = "SELECT Inventory FROM tsCharacter WHERE Account=@id";
                            cmd.Parameters.AddWithValue("@id", account.ID);
                            using var reader = cmd.ExecuteReader();
                            if (reader.Read() && !reader.IsDBNull(0))
                            {
                                hasSscData = true;
                                inventoryItems = ParseTShockInventory(reader.GetString(0));
                            }
                        }
                    }
                    catch { /* SSC 数据不存在时静默忽略 */ }
                }

                await _wsService.SendAsync(new
                {
                    type = "get_char_info_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = true,
                        username,
                        group,
                        user_exists = exists,
                        ssc_enabled = Main.ServerSideCharacter,
                        has_ssc_data = hasSscData,
                        inventory = inventoryItems,
                    }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "get_char_info_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        /// <summary>解析所有背包槽位（含空槽），返回完整索引数组</summary>
        private static List<object> ParseAllInventorySlots(string raw)
        {
            var slots = new List<object>();
            if (string.IsNullOrEmpty(raw)) return slots;
            int idx = 0;
            foreach (var part in raw.Split('~'))
            {
                var p = part.Split(',');
                int netId = p.Length > 0 && int.TryParse(p[0].Trim(), out var n) ? n : 0;
                int prefix = p.Length > 1 && int.TryParse(p[1].Trim(), out var pr) ? pr : 0;
                int stack = p.Length > 2 && int.TryParse(p[2].Trim(), out var s) ? s : 0;
                int favorite = p.Length > 3 && int.TryParse(p[3].Trim(), out var f) ? (f != 0 ? 1 : 0) : 0;
                string name = "", prefixName = "";
                if (netId != 0)
                {
                    try { var i = new Item(); i.SetDefaults(netId); name = i.Name ?? ""; } catch { }
                }
                if (prefix > 0)
                {
                    try { prefixName = Lang.prefix[prefix].Value ?? ""; } catch { }
                }
                slots.Add(new { index = idx, net_id = netId, prefix, stack, favorite, name, prefix_name = prefixName });
                idx++;
            }
            return slots;
        }

        public async Task HandleGetInventory(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var username = jobj["username"]?.ToString() ?? "";
            try
            {
                if (string.IsNullOrWhiteSpace(username))
                    throw new Exception("必须指定玩家名");

                bool isOnline = false;
                int health = 0, maxHealth = 0, mana = 0, maxMana = 0;
                List<object> slots;

                // ① 优先从在线玩家内存读取（无需 SSC）
                var onlineTsp = TShock.Players.FirstOrDefault(p =>
                    p?.Active == true &&
                    string.Equals(p.Name, username, StringComparison.OrdinalIgnoreCase));

                if (onlineTsp != null)
                {
                    isOnline = true;
                    var tp = onlineTsp.TPlayer;
                    health = tp.statLife;
                    maxHealth = tp.statLifeMax;
                    mana = tp.statMana;
                    maxMana = tp.statManaMax;
                    slots = BuildSlotsFromTPlayer(tp);
                }
                else
                {
                    // ② 离线玩家通过 TShock CharacterDB API 读取
                    var account = TShock.UserAccounts.GetUserAccountByName(username);
                    if (account == null)
                        throw new Exception($"未找到玩家账号: {username}");

                    var data = TShock.CharacterDB.GetPlayerData(new TSPlayer(-1), account.ID);
                    if (data == null || data.inventory == null || data.inventory.Length == 0)
                        throw new Exception($"玩家 {username} 无角色数据（从未以 SSC 模式登录过，或服务器未启用 SSC）");

                    health = data.health;
                    maxHealth = data.maxHealth;
                    mana = data.mana;
                    maxMana = data.maxMana;
                    slots = BuildSlotsFromPlayerData(data);
                }

                await _wsService.SendAsync(new
                {
                    type = "get_inventory_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new
                    {
                        ref_id = envelope.MsgId,
                        success = true,
                        username,
                        is_online = isOnline,
                        ssc_enabled = Main.ServerSideCharacter,
                        health,
                        max_health = maxHealth,
                        mana,
                        max_mana = maxMana,
                        slots
                    }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "get_inventory_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        /// <summary>从在线玩家的 Terraria.Player 内存对象按 NetItem 线性索引构建槽位列表（无需 SSC）</summary>
        private static List<object> BuildSlotsFromTPlayer(Terraria.Player tp)
        {
            // TShock 6.0 NetItem 索引布局（MaxInventory = 350）：
            // 0-58:   inventory[0..58]       (59)
            // 59-78:  armor[0..19]           (20)
            // 79-88:  dye[0..9]              (10)
            // 89-93:  miscEquips[0..4]       (5)
            // 94-98:  miscDyes[0..4]         (5)
            // 99-138: bank/piggy[0..39]      (40)
            // 139-178:bank2/safe[0..39]      (40)
            // 179:    trash                  (1)
            // 180-219:bank3/forge[0..39]     (40)
            // 220-259:bank4/void[0..39]      (40)
            // 260-279:Loadout1 armor[0..19]  (20)
            // 280-289:Loadout1 dye[0..9]     (10)
            // 290-309:Loadout2 armor[0..19]  (20)
            // 310-319:Loadout2 dye[0..9]     (10)
            // 320-339:Loadout3 armor[0..19]  (20)
            // 340-349:Loadout3 dye[0..9]     (10)
            var slots = new List<object>(350);

            // 0-58: inventory[0..58]
            for (int i = 0; i < 59; i++)
                slots.Add(TerrariaItemToSlot(i, i < tp.inventory.Length ? tp.inventory[i] : null));
            // 59-78: armor[0..19]
            for (int i = 0; i < 20; i++)
                slots.Add(TerrariaItemToSlot(59 + i, i < tp.armor.Length ? tp.armor[i] : null));
            // 79-88: dye[0..9]
            for (int i = 0; i < 10; i++)
                slots.Add(TerrariaItemToSlot(79 + i, i < tp.dye.Length ? tp.dye[i] : null));
            // 89-93: miscEquips[0..4]
            for (int i = 0; i < 5; i++)
                slots.Add(TerrariaItemToSlot(89 + i, i < tp.miscEquips.Length ? tp.miscEquips[i] : null));
            // 94-98: miscDyes[0..4]
            for (int i = 0; i < 5; i++)
                slots.Add(TerrariaItemToSlot(94 + i, i < tp.miscDyes.Length ? tp.miscDyes[i] : null));
            // 99-138: piggy bank (bank.item[0..39])
            for (int i = 0; i < 40; i++)
                slots.Add(TerrariaItemToSlot(99 + i, i < tp.bank.item.Length ? tp.bank.item[i] : null));
            // 139-178: safe (bank2.item[0..39])
            for (int i = 0; i < 40; i++)
                slots.Add(TerrariaItemToSlot(139 + i, i < tp.bank2.item.Length ? tp.bank2.item[i] : null));
            // 179: trash item
            slots.Add(TerrariaItemToSlot(179, tp.trashItem));
            // 180-219: defender's forge (bank3.item[0..39])
            for (int i = 0; i < 40; i++)
                slots.Add(TerrariaItemToSlot(180 + i, i < tp.bank3.item.Length ? tp.bank3.item[i] : null));
            // 220-259: void vault (bank4.item[0..39])
            for (int i = 0; i < 40; i++)
                slots.Add(TerrariaItemToSlot(220 + i, i < tp.bank4.item.Length ? tp.bank4.item[i] : null));
            // 260-349: Loadouts（TShock 6.0 新增，Terraria 1.4.4+ 装备预设）
            if (tp.Loadouts != null)
            {
                int lBase = 260;
                for (int l = 0; l < Math.Min(tp.Loadouts.Length, 3); l++)
                {
                    var lo = tp.Loadouts[l];
                    // 护甲栏：20 个槽位
                    for (int i = 0; i < 20; i++)
                        slots.Add(TerrariaItemToSlot(lBase + i, lo?.Armor != null && i < lo.Armor.Length ? lo.Armor[i] : null));
                    lBase += 20;
                    // 染料栏：10 个槽位
                    for (int i = 0; i < 10; i++)
                        slots.Add(TerrariaItemToSlot(lBase + i, lo?.Dye != null && i < lo.Dye.Length ? lo.Dye[i] : null));
                    lBase += 10;
                }
                // 补足缺失的 loadout slots
                while (slots.Count < 350)
                    slots.Add(TerrariaItemToSlot(slots.Count, null));
            }

            return slots;
        }

        private static object TerrariaItemToSlot(int index, Terraria.Item? item)
        {
            if (item == null || item.type <= 0)
                return new { index, net_id = 0, prefix = 0, stack = 0, favorite = 0, name = "", prefix_name = "" };
            string name = item.Name ?? "";
            string prefixName = "";
            if (item.prefix > 0)
            {
                try { prefixName = Lang.prefix[item.prefix].Value ?? ""; } catch { }
            }
            return new { index, net_id = item.type, prefix = (int)item.prefix, stack = item.stack, favorite = item.favorited ? 1 : 0, name, prefix_name = prefixName };
        }

        private static Item CreateItemFromSlot(int netId, int prefix, int stack, int favorite)
        {
            var item = new Item();
            if (netId <= 0 || stack <= 0)
            {
                item.TurnToAir();
                return item;
            }

            try
            {
                item.SetDefaults(netId);
                item.stack = stack;
                item.prefix = (byte)prefix;
                item.favorited = favorite != 0;
            }
            catch
            {
                // 非法物品 ID 不应导致整次保存失败，降级为空槽位
                item.TurnToAir();
            }
            return item;
        }

        private static bool TryApplySlotToPlayer(Terraria.Player tp, int index, Item item)
        {
            if (index < 0) return false;

            // 0-58: inventory
            if (index <= 58)
            {
                if (index >= tp.inventory.Length) return false;
                tp.inventory[index] = item;
                return true;
            }
            // 59-78: armor
            if (index <= 78)
            {
                int i = index - 59;
                if (i >= tp.armor.Length) return false;
                tp.armor[i] = item;
                return true;
            }
            // 79-88: dye
            if (index <= 88)
            {
                int i = index - 79;
                if (i >= tp.dye.Length) return false;
                tp.dye[i] = item;
                return true;
            }
            // 89-93: misc equips
            if (index <= 93)
            {
                int i = index - 89;
                if (i >= tp.miscEquips.Length) return false;
                tp.miscEquips[i] = item;
                return true;
            }
            // 94-98: misc dyes
            if (index <= 98)
            {
                int i = index - 94;
                if (i >= tp.miscDyes.Length) return false;
                tp.miscDyes[i] = item;
                return true;
            }
            // 99-138: piggy bank
            if (index <= 138)
            {
                int i = index - 99;
                if (i >= tp.bank.item.Length) return false;
                tp.bank.item[i] = item;
                return true;
            }
            // 139-178: safe
            if (index <= 178)
            {
                int i = index - 139;
                if (i >= tp.bank2.item.Length) return false;
                tp.bank2.item[i] = item;
                return true;
            }
            // 179: trash
            if (index == 179)
            {
                tp.trashItem = item;
                return true;
            }
            // 180-219: forge
            if (index <= 219)
            {
                int i = index - 180;
                if (i >= tp.bank3.item.Length) return false;
                tp.bank3.item[i] = item;
                return true;
            }
            // 220-259: void vault
            if (index <= 259)
            {
                int i = index - 220;
                if (i >= tp.bank4.item.Length) return false;
                tp.bank4.item[i] = item;
                return true;
            }
            // 260-349: 3 套 loadout（每套 20 armor + 10 dye）
            if (index <= 349)
            {
                if (tp.Loadouts == null || tp.Loadouts.Length == 0) return false;
                int rel = index - 260;
                int loadoutIndex = rel / 30;
                int slotInLoadout = rel % 30;
                if (loadoutIndex < 0 || loadoutIndex >= tp.Loadouts.Length) return false;
                if (slotInLoadout < 20)
                {
                    if (tp.Loadouts[loadoutIndex].Armor == null || slotInLoadout >= tp.Loadouts[loadoutIndex].Armor.Length) return false;
                    tp.Loadouts[loadoutIndex].Armor[slotInLoadout] = item;
                }
                else
                {
                    int dyeIndex = slotInLoadout - 20;
                    if (tp.Loadouts[loadoutIndex].Dye == null || dyeIndex >= tp.Loadouts[loadoutIndex].Dye.Length) return false;
                    tp.Loadouts[loadoutIndex].Dye[dyeIndex] = item;
                }
                return true;
            }

            return false;
        }

        private enum InventoryTokenFormat
        {
            NetPrefixStack,
            NetStackPrefix,
        }

        private static InventoryTokenFormat DetectInventoryTokenFormat(
            string[] existingParts,
            TShockAPI.PlayerData? data)
        {
            if (data?.inventory == null || data.inventory.Length == 0)
                return InventoryTokenFormat.NetPrefixStack;

            int scoreNps = 0;
            int scoreNsp = 0;
            int n = Math.Min(existingParts.Length, data.inventory.Length);

            for (int i = 0; i < n; i++)
            {
                var p = existingParts[i].Split(',');
                if (p.Length < 3) continue;
                if (!int.TryParse(p[0].Trim(), out int a)) continue;
                if (!int.TryParse(p[1].Trim(), out int b)) continue;
                if (!int.TryParse(p[2].Trim(), out int c)) continue;

                var ni = data.inventory[i];
                if (ni.NetId == 0 && a == 0) continue;

                if (a == ni.NetId && b == ni.PrefixId && c == ni.Stack) scoreNps++;
                if (a == ni.NetId && b == ni.Stack && c == ni.PrefixId) scoreNsp++;
            }

            return scoreNsp > scoreNps
                ? InventoryTokenFormat.NetStackPrefix
                : InventoryTokenFormat.NetPrefixStack;
        }

        private static string SerializeInventoryToken(int netId, int prefix, int stack, InventoryTokenFormat format)
        {
            return format == InventoryTokenFormat.NetStackPrefix
                ? $"{netId},{stack},{prefix}"
                : $"{netId},{prefix},{stack}";
        }

        private static string SerializeInventoryTokenLikeTemplate(
            string templateToken,
            int netId,
            int prefix,
            int stack,
            int favorite,
            InventoryTokenFormat format)
        {
            var p = templateToken.Split(',');
            if (p.Length <= 0)
                return SerializeInventoryToken(netId, prefix, stack, format);

            var outParts = new string[p.Length];
            for (int i = 0; i < p.Length; i++)
                outParts[i] = p[i].Trim();

            outParts[0] = netId.ToString();

            // 四段格式固定为：id,stack,prefix,favorite
            if (outParts.Length >= 4)
            {
                outParts[1] = stack.ToString();
                outParts[2] = prefix.ToString();
                outParts[3] = favorite != 0 ? "1" : "0";
            }
            else
            {
                if (outParts.Length > 1)
                    outParts[1] = (format == InventoryTokenFormat.NetStackPrefix ? stack : prefix).ToString();
                if (outParts.Length > 2)
                    outParts[2] = (format == InventoryTokenFormat.NetStackPrefix ? prefix : stack).ToString();
            }

            // 第4段及其后字段（如 favorite/flags）保留原值；空物品时清零更安全
            if (netId == 0)
            {
                for (int i = 3; i < outParts.Length; i++)
                    outParts[i] = "0";
            }

            return string.Join(",", outParts);
        }

        /// <summary>从 TShock CharacterDB 返回的 PlayerData 按线性索引构建槽位列表</summary>
        private static List<object> BuildSlotsFromPlayerData(TShockAPI.PlayerData data)
        {
            var slots = new List<object>(data.inventory.Length);
            for (int i = 0; i < data.inventory.Length; i++)
            {
                var ni = data.inventory[i];
                int netId = ni.NetId, pfx = ni.PrefixId, stk = ni.Stack;
                string name = "", prefixName = "";
                if (netId != 0)
                {
                    try { var it = new Terraria.Item(); it.SetDefaults(netId); name = it.Name ?? ""; } catch { }
                }
                if (pfx > 0)
                {
                    try { prefixName = Lang.prefix[pfx].Value ?? ""; } catch { }
                }
                slots.Add(new { index = i, net_id = netId, prefix = pfx, stack = stk, favorite = 0, name, prefix_name = prefixName });
            }
            return slots;
        }

        public async Task HandleSaveInventory(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var username = jobj["username"]?.ToString() ?? "";
            var slotsArr = jobj["slots"] as JArray;
            var maxHpTok = jobj["max_hp"];
            var maxManaTok = jobj["max_mana"];
            // 永久加强物品字段
            var enhanceFields = new Dictionary<string, JToken> {
                    {"extraSlot", jobj["extraSlot"]},
                    {"unlockedBiomeTorches", jobj["unlockedBiomeTorches"]},
                    {"ateArtisanBread", jobj["ateArtisanBread"]},
                    {"usedAegisCrystal", jobj["usedAegisCrystal"]},
                    {"usedAegisFruit", jobj["usedAegisFruit"]},
                    {"usedArcaneCrystal", jobj["usedArcaneCrystal"]},
                    {"usedGalaxyPearl", jobj["usedGalaxyPearl"]},
                    {"usedGummyWorm", jobj["usedGummyWorm"]},
                    {"usedAmbrosia", jobj["usedAmbrosia"]},
                    {"unlockedSuperCart", jobj["unlockedSuperCart"]}
                };
            try
            {
                if (string.IsNullOrWhiteSpace(username) || slotsArr == null)
                    throw new Exception("参数无效");
                if (!Main.ServerSideCharacter)
                    throw new Exception("服务器未启用 SSC");
                var account = TShock.UserAccounts.GetUserAccountByName(username);
                if (account == null)
                    throw new Exception($"未找到玩家账号: {username}");

                var onlineTs = TShock.Players.FirstOrDefault(p =>
                    p?.Active == true &&
                    string.Equals(p.Name, username, StringComparison.OrdinalIgnoreCase));

                // 离线保存不再手写 tsCharacter.Inventory 字符串，直接走 CharacterDB API，规避格式差异导致清空
                var saveTarget = onlineTs ?? new TSPlayer(-1) { Account = account };
                var data = TShock.CharacterDB.GetPlayerData(saveTarget, account.ID);
                if (data == null || data.inventory == null || data.inventory.Length == 0)
                    throw new Exception("保存失败，角色数据不存在或库存为空");

                if (maxHpTok != null && maxHpTok.Type != JTokenType.Null)
                {
                    int mh = maxHpTok.Value<int>();
                    if (mh < 1) mh = 1;
                    if (mh > 500) mh = 500;
                    data.maxHealth = mh;
                    if (data.health > data.maxHealth) data.health = data.maxHealth;
                }
                if (maxManaTok != null && maxManaTok.Type != JTokenType.Null)
                {
                    int mm = maxManaTok.Value<int>();
                    if (mm < 0) mm = 0;
                    if (mm > 200) mm = 200;
                    data.maxMana = mm;
                    if (data.mana > data.maxMana) data.mana = data.maxMana;
                }
                // 永久加强物品字段赋值
                foreach (var kv in enhanceFields)
                {
                    if (kv.Value != null && kv.Value.Type != JTokenType.Null)
                    {
                        int v = kv.Value.Value<int>();
                        v = v != 0 ? 1 : 0;
                        switch (kv.Key)
                        {
                            case "extraSlot": data.extraSlot = v; break;
                            case "unlockedBiomeTorches": data.unlockedBiomeTorches = v; break;
                            case "ateArtisanBread": data.ateArtisanBread = v; break;
                            case "usedAegisCrystal": data.usedAegisCrystal = v; break;
                            case "usedAegisFruit": data.usedAegisFruit = v; break;
                            case "usedArcaneCrystal": data.usedArcaneCrystal = v; break;
                            case "usedGalaxyPearl": data.usedGalaxyPearl = v; break;
                            case "usedGummyWorm": data.usedGummyWorm = v; break;
                            case "usedAmbrosia": data.usedAmbrosia = v; break;
                            case "unlockedSuperCart": data.unlockedSuperCart = v; break;
                        }
                    }
                }

                int totalSlots = data.inventory.Length;
                var normalizedUpdates = new List<(int idx, int netId, int prefix, int stack, int favorite)>();

                // 3. 将前端传入的格子合并覆盖（只覆盖有改动的格子，不影响其他格子）
                foreach (var s in slotsArr)
                {
                    int idx = s["index"]?.Value<int>() ?? -1;
                    if (idx < 0 || idx >= totalSlots) continue;
                    int netId = s["net_id"]?.Value<int>() ?? 0;
                    int prefix = s["prefix"]?.Value<int>() ?? 0;
                    int stack = s["stack"]?.Value<int>() ?? 0;
                    int favorite = s["favorite"]?.Value<int>() ?? 0;
                    if (netId < 0) netId = 0;
                    if (prefix < 0 || prefix > 83) prefix = 0;
                    if (stack < 0) stack = 0;
                    favorite = favorite != 0 ? 1 : 0;
                    if (netId > 0 && stack == 0) stack = 1;
                    if (netId == 0) { prefix = 0; stack = 0; favorite = 0; }
                    normalizedUpdates.Add((idx, netId, prefix, stack, favorite));

                    data.inventory[idx] = new NetItem(netId, stack, (byte)prefix);

                    // 在线玩家：同步内存；PlayerSlot(5) 仅对 0-259 安全槽位下发
                    if (onlineTs != null)
                    {
                        try
                        {
                            var item = CreateItemFromSlot(netId, prefix, stack, favorite);
                            if (TryApplySlotToPlayer(onlineTs.TPlayer, idx, item))
                            {
                                // 向所有玩家广播装备改动(-1表示所有人)，让客户端和其他玩家均能看到更新。
                                // Terraria 原版 Packet 5 支持 0~349 所有槽位（含便携存储与预设装）。
                                NetMessage.SendData(5, -1, -1, null, onlineTs.Index, idx, item.prefix);
                            }
                        }
                        catch
                        {
                        }
                    }
                }

                // 4. 通过 TShock CharacterDB 写回，避免 Inventory 字符串序列化不一致
                bool writeOk = false;
                try
                {
                    writeOk = TShock.CharacterDB.InsertSpecificPlayerData(saveTarget, data);
                }
                catch
                {
                }
                // 在线玩家同步永久加强物品字段
                if (onlineTs != null)
                {
                    onlineTs.TPlayer.extraAccessory = data.extraSlot == 1;
                    onlineTs.TPlayer.unlockedBiomeTorches = data.unlockedBiomeTorches == 1;
                    onlineTs.TPlayer.ateArtisanBread = data.ateArtisanBread == 1;
                    onlineTs.TPlayer.usedAegisCrystal = data.usedAegisCrystal == 1;
                    onlineTs.TPlayer.usedAegisFruit = data.usedAegisFruit == 1;
                    onlineTs.TPlayer.usedArcaneCrystal = data.usedArcaneCrystal == 1;
                    onlineTs.TPlayer.usedGalaxyPearl = data.usedGalaxyPearl == 1;
                    onlineTs.TPlayer.usedGummyWorm = data.usedGummyWorm == 1;
                    onlineTs.TPlayer.usedAmbrosia = data.usedAmbrosia == 1;
                    onlineTs.TPlayer.unlockedSuperCart = data.unlockedSuperCart == 1;
                }

                if (!writeOk)
                {
                    // 回退：按数据库当前 Inventory 字符串格式与长度覆盖写入
                    var dbPath = Path.Combine(TShock.SavePath, "tshock.sqlite");
                    using var conn = new SqliteConnection($"Data Source={dbPath}");
                    conn.Open();

                    string existingInv = "";
                    using (var readCmd = conn.CreateCommand())
                    {
                        readCmd.CommandText = "SELECT Inventory FROM tsCharacter WHERE Account=@id";
                        readCmd.Parameters.AddWithValue("@id", account.ID);
                        var val = readCmd.ExecuteScalar();
                        if (val == null || val == DBNull.Value)
                            throw new Exception("保存失败：CharacterDB 写入失败，且未找到 tsCharacter 行");
                        existingInv = val.ToString() ?? "";
                    }

                    var existingParts = existingInv.Split('~');
                    if (existingParts.Length <= 0)
                        throw new Exception("保存失败：CharacterDB 写入失败，且 Inventory 为空");

                    // 用户确认四段语义固定为 id,stack,prefix,favorite，优先按该格式写回
                    var hasFourPartToken = existingParts.Any(t => t.Split(',').Length >= 4);
                    var tokenFormat = hasFourPartToken
                        ? InventoryTokenFormat.NetStackPrefix
                        : DetectInventoryTokenFormat(existingParts, data);
                    var parts = (string[])existingParts.Clone();
                    foreach (var u in normalizedUpdates)
                    {
                        if (u.idx < 0 || u.idx >= parts.Length) continue;
                        parts[u.idx] = SerializeInventoryTokenLikeTemplate(
                                parts[u.idx], u.netId, u.prefix, u.stack, u.favorite, tokenFormat);
                    }

                    using (var cmd = conn.CreateCommand())
                    {
                        cmd.CommandText = "UPDATE tsCharacter SET Inventory=@inv, MaxHealth=@mh, MaxMana=@mm, Health=@h, Mana=@m, " +
                            "extraSlot=@es, unlockedBiomeTorches=@ubt, ateArtisanBread=@aab, usedAegisCrystal=@uac, usedAegisFruit=@uaf, " +
                            "usedArcaneCrystal=@uarc, usedGalaxyPearl=@ugp, usedGummyWorm=@ugw, usedAmbrosia=@ua, unlockedSuperCart=@usc " +
                            "WHERE Account=@id";
                        cmd.Parameters.AddWithValue("@inv", string.Join("~", parts));
                        cmd.Parameters.AddWithValue("@mh", data.maxHealth);
                        cmd.Parameters.AddWithValue("@mm", data.maxMana);
                        cmd.Parameters.AddWithValue("@h", data.health);
                        cmd.Parameters.AddWithValue("@m", data.mana);
                        cmd.Parameters.AddWithValue("@es", data.extraSlot);
                        cmd.Parameters.AddWithValue("@ubt", data.unlockedBiomeTorches);
                        cmd.Parameters.AddWithValue("@aab", data.ateArtisanBread);
                        cmd.Parameters.AddWithValue("@uac", data.usedAegisCrystal);
                        cmd.Parameters.AddWithValue("@uaf", data.usedAegisFruit);
                        cmd.Parameters.AddWithValue("@uarc", data.usedArcaneCrystal);
                        cmd.Parameters.AddWithValue("@ugp", data.usedGalaxyPearl);
                        cmd.Parameters.AddWithValue("@ugw", data.usedGummyWorm);
                        cmd.Parameters.AddWithValue("@ua", data.usedAmbrosia);
                        cmd.Parameters.AddWithValue("@usc", data.unlockedSuperCart);
                        cmd.Parameters.AddWithValue("@id", account.ID);
                        cmd.ExecuteNonQuery();
                    }
                }

                bool reloaded = false;
                if (onlineTs == null)
                {
                    // 离线玩家：按需求在写库后触发 /reload，确保服务端配置/缓存刷新
                    try
                    {
                        TShockAPI.Commands.HandleCommand(TSPlayer.Server, "/reload");
                        reloaded = true;
                    }
                    catch
                    {
                        reloaded = false;
                    }
                }
                else
                {
                    // 在线玩家同步基础属性，保持面板修改即时可见
                    onlineTs.TPlayer.statLifeMax = data.maxHealth;
                    if (onlineTs.TPlayer.statLife > onlineTs.TPlayer.statLifeMax)
                        onlineTs.TPlayer.statLife = onlineTs.TPlayer.statLifeMax;
                    onlineTs.TPlayer.statManaMax = data.maxMana;
                    if (onlineTs.TPlayer.statMana > onlineTs.TPlayer.statManaMax)
                        onlineTs.TPlayer.statMana = onlineTs.TPlayer.statManaMax;
                    // 直接用常量同步，PlayerHp=13，PlayerMana=42
                    NetMessage.SendData(13, -1, -1, null, onlineTs.Index, 0f, 0f, 0f, 0);
                    NetMessage.SendData(42, -1, -1, null, onlineTs.Index, 0f, 0f, 0f, 0);
                    // 发送 Packet 4 同步玩家的全身装备/外观
                    NetMessage.SendData(4, -1, -1, null, onlineTs.Index);
                }

                bool isOnline = onlineTs != null;
                string msg = isOnline
                    ? $"已保存 {username} 的背包（SSC 在线同步已下发）"
                    : (reloaded
                        ? $"已保存 {username} 的背包，并已执行 /reload"
                        : $"已保存 {username} 的背包（/reload 执行失败）");

                await _wsService.SendAsync(new
                {
                    type = "save_inventory_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, msg, is_online = isOnline }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new
                {
                    type = "save_inventory_resp",
                    msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        /// <summary>解析 TShock SSC Inventory 字符串，兼容三段/四段；四段按 netId,stack,prefix,favorite 解析</summary>
        private static List<object> ParseTShockInventory(string raw)
        {
            var items = new List<object>();
            if (string.IsNullOrEmpty(raw)) return items;

            // 仅用于字符串解析兼容：根据第二/第三段取值分布推断是 net,prefix,stack 还是 net,stack,prefix
            bool maybeNetStackPrefix = true;
            {
                int scoreNsp = 0, scoreNps = 0;
                foreach (var token in raw.Split('~'))
                {
                    var p0 = token.Split(',');
                    if (p0.Length < 3) continue;
                    if (!int.TryParse(p0[1].Trim(), out int b)) continue;
                    if (!int.TryParse(p0[2].Trim(), out int c)) continue;
                    // 前缀值通常在 0-83，堆叠数通常明显更大
                    if (b > 83 && c <= 83) scoreNsp++;
                    if (c > 83 && b <= 83) scoreNps++;
                }
                maybeNetStackPrefix = scoreNsp > scoreNps;
            }

            int idx = 0;
            foreach (var slot in raw.Split('~'))
            {
                var p = slot.Split(',');
                if (p.Length >= 3
                    && int.TryParse(p[0].Trim(), out int netId)
                    && int.TryParse(p[1].Trim(), out int v1)
                    && int.TryParse(p[2].Trim(), out int v2)
                    && netId != 0)
                {
                    int stack;
                    int prefix;
                    int favorite = 0;
                    if (p.Length >= 4)
                    {
                        // 固定四段：id,stack,prefix,favorite
                        stack = v1;
                        prefix = v2;
                        if (int.TryParse(p[3].Trim(), out int fv)) favorite = fv != 0 ? 1 : 0;
                    }
                    else
                    {
                        stack = maybeNetStackPrefix ? v1 : v2;
                        prefix = maybeNetStackPrefix ? v2 : v1;
                    }
                    string itemName = "", prefixName = "";
                    try { var i = new Terraria.Item(); i.SetDefaults(netId); itemName = i.Name ?? ""; } catch { }
                    if (prefix > 0) { try { prefixName = Lang.prefix[prefix].Value ?? ""; } catch { } }
                    items.Add(new { index = idx, net_id = netId, prefix, stack, favorite, name = itemName, prefix_name = prefixName });
                }
                idx++;
            }
            return items;
        }
    }
}
