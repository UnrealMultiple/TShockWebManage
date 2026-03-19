using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.Data.Sqlite;
using Newtonsoft.Json.Linq;
using TerrariaManagerAgent.Models;

namespace TerrariaManagerAgent.Services.Handlers
{
    public class DatabaseHandler : HandlerBase
    {
        public DatabaseHandler(WebSocketService wsService) : base(wsService) { }

        private static string EscIdent(string s) => s.Replace("\"", "\"\"");

        public async Task HandleDbQuery(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var path = jobj["path"]?.ToString() ?? "";
            var sql  = jobj["sql"]?.ToString()  ?? "";
            if (!IsPathSafe(path))
            {
                await _wsService.SendAsync(new {
                    type = "db_query_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "路径不合法" }
                });
                return;
            }
            try
            {
                if (!File.Exists(path)) throw new FileNotFoundException("数据库文件不存在");
                using var conn = new SqliteConnection($"Data Source={path};Mode=ReadOnly");
                conn.Open();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = sql;
                cmd.CommandTimeout = 10;
                using var reader = cmd.ExecuteReader();

                var columns = new List<string>();
                for (int i = 0; i < reader.FieldCount; i++)
                    columns.Add(reader.GetName(i));

                var rows = new List<List<object?>>();
                int rowLimit = 500;
                while (reader.Read() && rows.Count < rowLimit)
                {
                    var row = new List<object?>();
                    for (int i = 0; i < reader.FieldCount; i++)
                        row.Add(reader.IsDBNull(i) ? null : reader.GetValue(i));
                    rows.Add(row);
                }
                bool truncated = rows.Count >= rowLimit;

                await _wsService.SendAsync(new {
                    type = "db_query_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, columns, rows, truncated }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type = "db_query_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandleDbExec(PacketEnvelope envelope)
        {
            var jobj = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var path = jobj["path"]?.ToString() ?? "";
            var sql  = jobj["sql"]?.ToString()  ?? "";
            if (!IsPathSafe(path))
            {
                await _wsService.SendAsync(new {
                    type = "db_exec_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "路径不合法" }
                });
                return;
            }
            try
            {
                if (!File.Exists(path)) throw new FileNotFoundException("数据库文件不存在");
                using var conn = new SqliteConnection($"Data Source={path}");
                conn.Open();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = sql;
                cmd.CommandTimeout = 10;
                int affected = cmd.ExecuteNonQuery();
                await _wsService.SendAsync(new {
                    type = "db_exec_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, affected }
                });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new {
                    type = "db_exec_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message }
                });
            }
        }

        public async Task HandleDbUpdateRow(PacketEnvelope envelope)
        {
            var jobj  = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var path  = jobj["path"]?.ToString()  ?? "";
            var tbl   = jobj["table"]?.ToString() ?? "";
            var col   = jobj["col"]?.ToString()   ?? "";
            var rowid = jobj["rowid"]?.ToObject<long>() ?? 0;
            var val   = jobj["value"];
            if (!IsPathSafe(path) || string.IsNullOrEmpty(tbl) || string.IsNullOrEmpty(col))
            {
                await _wsService.SendAsync(new { type = "db_update_row_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "参数不合法" } });
                return;
            }
            try
            {
                using var conn = new SqliteConnection($"Data Source={path}");
                conn.Open();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = $"UPDATE \"{EscIdent(tbl)}\" SET \"{EscIdent(col)}\" = @val WHERE rowid = @rowid";
                cmd.Parameters.AddWithValue("@val", val == null || val.Type == JTokenType.Null
                    ? (object)DBNull.Value : val.ToString()!);
                cmd.Parameters.AddWithValue("@rowid", rowid);
                int affected = cmd.ExecuteNonQuery();
                await _wsService.SendAsync(new { type = "db_update_row_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, affected } });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new { type = "db_update_row_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message } });
            }
        }

        public async Task HandleDbDeleteRow(PacketEnvelope envelope)
        {
            var jobj  = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var path  = jobj["path"]?.ToString()  ?? "";
            var tbl   = jobj["table"]?.ToString() ?? "";
            var rowid = jobj["rowid"]?.ToObject<long>() ?? 0;
            if (!IsPathSafe(path) || string.IsNullOrEmpty(tbl))
            {
                await _wsService.SendAsync(new { type = "db_delete_row_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "参数不合法" } });
                return;
            }
            try
            {
                using var conn = new SqliteConnection($"Data Source={path}");
                conn.Open();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = $"DELETE FROM \"{EscIdent(tbl)}\" WHERE rowid = @rowid";
                cmd.Parameters.AddWithValue("@rowid", rowid);
                int affected = cmd.ExecuteNonQuery();
                await _wsService.SendAsync(new { type = "db_delete_row_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, affected, rowid } });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new { type = "db_delete_row_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message } });
            }
        }

        public async Task HandleDbInsertRow(PacketEnvelope envelope)
        {
            var jobj    = JObject.Parse(envelope.Payload?.ToString() ?? "{}");
            var path    = jobj["path"]?.ToString()  ?? "";
            var tbl     = jobj["table"]?.ToString() ?? "";
            var colsArr = jobj["cols"]   as JArray;
            var valsArr = jobj["values"] as JArray;
            if (!IsPathSafe(path) || string.IsNullOrEmpty(tbl) || colsArr == null || valsArr == null)
            {
                await _wsService.SendAsync(new { type = "db_insert_row_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = "参数不合法" } });
                return;
            }
            try
            {
                var cols    = colsArr.Select(c => c.ToString()).ToList();
                var colPart = string.Join(", ", cols.Select(c => $"\"{EscIdent(c)}\""));
                var parPart = string.Join(", ", cols.Select((_, i) => $"@p{i}"));
                using var conn = new SqliteConnection($"Data Source={path}");
                conn.Open();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = $"INSERT INTO \"{EscIdent(tbl)}\" ({colPart}) VALUES ({parPart})";
                for (int i = 0; i < cols.Count; i++)
                {
                    var v = i < valsArr.Count ? valsArr[i] : JValue.CreateNull();
                    cmd.Parameters.AddWithValue($"@p{i}", v == null || v.Type == JTokenType.Null
                        ? (object)DBNull.Value : v.ToString()!);
                }
                cmd.ExecuteNonQuery();
                using var lastCmd = conn.CreateCommand();
                lastCmd.CommandText = "SELECT last_insert_rowid()";
                var newRowid = (long)lastCmd.ExecuteScalar()!;
                await _wsService.SendAsync(new { type = "db_insert_row_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = true, rowid = newRowid } });
            }
            catch (Exception ex)
            {
                await _wsService.SendAsync(new { type = "db_insert_row_resp", msg_id = Guid.NewGuid().ToString("N"),
                    timestamp = DateTimeOffset.UtcNow.ToUnixTimeSeconds(),
                    payload = new { ref_id = envelope.MsgId, success = false, msg = ex.Message } });
            }
        }
    }
}
