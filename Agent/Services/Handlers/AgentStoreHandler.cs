using System;
using System.Linq;
using System.Threading.Tasks;
using Newtonsoft.Json.Linq;
using TerrariaManagerAgent.Models;

namespace TerrariaManagerAgent.Services.Handlers
{
    public class AgentStoreHandler : HandlerBase
    {
        public AgentStoreHandler(WebSocketService wsService) : base(wsService) { }

        public async Task HandleCharacterExists(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var characterName = jobj["character_name"]?.ToString() ?? jobj["username"]?.ToString() ?? "";
            await SendAsync("agent_character_exists_resp", envelope.MsgId, new
            {
                success = true,
                exists = !string.IsNullOrWhiteSpace(characterName) && AgentLocalStore.CharacterExists(characterName),
                character_name = characterName
            });
        }

        public async Task HandleCharacterBind(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var panelUserId = jobj["panel_user_id"]?.Value<long>() ?? 0;
            var panelEmail = jobj["panel_email"]?.ToString() ?? "";
            var characterName = jobj["character_name"]?.ToString() ?? jobj["username"]?.ToString() ?? "";
            var source = jobj["source"]?.ToString() ?? "panel";

            if (panelUserId <= 0 || string.IsNullOrWhiteSpace(characterName))
            {
                await SendAsync("agent_character_bind_resp", envelope.MsgId, new
                {
                    success = false,
                    msg = "参数不完整",
                    character_name = characterName
                });
                return;
            }

            try
            {
                var existing = AgentLocalStore.FindCharacter(characterName);
                if (existing != null && existing.PanelUserId != panelUserId)
                    throw new Exception("该游戏账号已绑定到其他面板账号");

                var row = AgentLocalStore.UpsertCharacter(panelUserId, panelEmail, characterName, source);
                await SendCharacter("agent_character_bind_resp", envelope.MsgId, row, "绑定成功");
            }
            catch (Exception ex)
            {
                await SendAsync("agent_character_bind_resp", envelope.MsgId, new
                {
                    success = false,
                    msg = ex.Message,
                    character_name = characterName
                });
            }
        }

        public async Task HandleCharacterDelete(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var characterName = jobj["character_name"]?.ToString() ?? jobj["username"]?.ToString() ?? "";
            var hasUser = jobj["panel_user_id"] != null && jobj["panel_user_id"]!.Type != JTokenType.Null;
            var panelUserId = hasUser ? jobj["panel_user_id"]!.Value<long>() : (long?)null;

            if (string.IsNullOrWhiteSpace(characterName))
            {
                await SendAsync("agent_character_delete_resp", envelope.MsgId, new
                {
                    success = false,
                    msg = "character_name 不能为空",
                    character_name = characterName
                });
                return;
            }

            var row = AgentLocalStore.DeleteCharacter(characterName, panelUserId);
            await SendAsync("agent_character_delete_resp", envelope.MsgId, new
            {
                success = row != null,
                removed = row != null,
                msg = row != null ? "绑定已删除" : "角色绑定不存在",
                character_name = row?.CharacterName ?? characterName,
                previous_user_id = row?.PanelUserId,
                previous_email = row?.PanelEmail
            });
        }

        public async Task HandleCharacterAssign(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var characterName = jobj["character_name"]?.ToString() ?? "";
            var targetToken = jobj["target_user_id"];
            var targetUserId = targetToken == null || targetToken.Type == JTokenType.Null
                ? (long?)null
                : targetToken.Value<long>();
            var targetEmail = jobj["target_email"]?.ToString() ?? "";

            if (string.IsNullOrWhiteSpace(characterName))
            {
                await SendAsync("agent_character_assign_resp", envelope.MsgId, new
                {
                    success = false,
                    msg = "character_name 不能为空",
                    character_name = characterName
                });
                return;
            }

            var existing = AgentLocalStore.FindCharacter(characterName);
            if (targetUserId == null)
            {
                var deleted = AgentLocalStore.DeleteCharacter(characterName);
                await SendAsync("agent_character_assign_resp", envelope.MsgId, new
                {
                    success = true,
                    action = deleted != null ? "cleared" : "unchanged",
                    character_name = deleted?.CharacterName ?? characterName,
                    previous_user_id = deleted?.PanelUserId,
                    previous_email = deleted?.PanelEmail
                });
                return;
            }

            var row = AgentLocalStore.UpsertCharacter(targetUserId.Value, targetEmail, characterName, "manual_assign");
            await SendAsync("agent_character_assign_resp", envelope.MsgId, new
            {
                success = true,
                action = existing == null ? "created" : (existing.PanelUserId == targetUserId.Value ? "unchanged" : "reassigned"),
                character_name = row.CharacterName,
                target_user_id = row.PanelUserId,
                target_email = row.PanelEmail,
                previous_user_id = existing?.PanelUserId,
                previous_email = existing?.PanelEmail,
                registered_at = row.RegisteredAt
            });
        }

        public async Task HandleCharacterList(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var token = jobj["panel_user_id"];
            var panelUserId = token == null || token.Type == JTokenType.Null ? (long?)null : token.Value<long>();
            var rows = AgentLocalStore.ListCharacters(panelUserId)
                .Select(r => new
                {
                    panel_user_id = r.PanelUserId,
                    panel_email = r.PanelEmail,
                    character_name = r.CharacterName,
                    registered_at = r.RegisteredAt,
                    updated_at = r.UpdatedAt,
                    source = r.Source
                })
                .ToList();
            await SendAsync("agent_character_list_resp", envelope.MsgId, new { success = true, rows });
        }

        public async Task HandleBlacklistAdd(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var targetUserId = jobj["target_user_id"]?.Value<long>() ?? 0;
            var targetEmail = jobj["target_email"]?.ToString() ?? "";
            var reason = jobj["reason"]?.ToString() ?? "";
            var createdByUserId = jobj["created_by_user_id"]?.Value<long>() ?? 0;
            var createdByEmail = jobj["created_by_email"]?.ToString() ?? "";

            if (targetUserId <= 0 || createdByUserId <= 0)
            {
                await SendAsync("agent_blacklist_add_resp", envelope.MsgId, new { success = false, msg = "参数不完整" });
                return;
            }

            try
            {
                var row = AgentLocalStore.AddBlacklist(targetUserId, targetEmail, reason, createdByUserId, createdByEmail);
                await SendBlacklist("agent_blacklist_add_resp", envelope.MsgId, row, "已加入本服务器黑名单");
            }
            catch (Exception ex)
            {
                await SendAsync("agent_blacklist_add_resp", envelope.MsgId, new { success = false, msg = ex.Message });
            }
        }

        public async Task HandleBlacklistRemove(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var targetUserId = jobj["target_user_id"]?.Value<long>() ?? 0;
            var removedByUserId = jobj["removed_by_user_id"]?.Value<long>() ?? 0;
            var removedByEmail = jobj["removed_by_email"]?.ToString() ?? "";

            if (targetUserId <= 0 || removedByUserId <= 0)
            {
                await SendAsync("agent_blacklist_remove_resp", envelope.MsgId, new { success = false, msg = "参数不完整" });
                return;
            }

            var row = AgentLocalStore.RemoveBlacklist(targetUserId, removedByUserId, removedByEmail);
            if (row == null)
            {
                await SendAsync("agent_blacklist_remove_resp", envelope.MsgId, new { success = false, msg = "黑名单记录不存在" });
                return;
            }
            await SendBlacklist("agent_blacklist_remove_resp", envelope.MsgId, row, "已移除本服务器黑名单");
        }

        private Task SendCharacter(string type, string refId, CharacterBinding row, string msg)
        {
            return SendAsync(type, refId, new
            {
                success = true,
                msg,
                panel_user_id = row.PanelUserId,
                panel_email = row.PanelEmail,
                character_name = row.CharacterName,
                registered_at = row.RegisteredAt,
                updated_at = row.UpdatedAt,
                source = row.Source
            });
        }

        private Task SendBlacklist(string type, string refId, BlacklistEntry row, string msg)
        {
            return SendAsync(type, refId, new
            {
                success = true,
                msg,
                id = row.Id,
                target_user_id = row.TargetUserId,
                target_email = row.TargetEmail,
                reason = row.Reason,
                status = row.Status,
                created_by_user_id = row.CreatedByUserId,
                created_by_email = row.CreatedByEmail,
                created_at = row.CreatedAt,
                removed_by_user_id = row.RemovedByUserId,
                removed_by_email = row.RemovedByEmail,
                removed_at = row.RemovedAt
            });
        }

        private async Task SendAsync(string type, string refId, object payload)
        {
            await _wsService.SendAsync(new
            {
                type,
                msg_id = Guid.NewGuid().ToString("N"),
                timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                payload = MergeRef(payload, refId)
            });
        }

        private static object MergeRef(object payload, string refId)
        {
            var obj = JObject.FromObject(payload);
            obj["ref_id"] = refId;
            return obj;
        }
    }
}
