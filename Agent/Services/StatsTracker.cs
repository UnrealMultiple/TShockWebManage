using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using Microsoft.Data.Sqlite;
using TShockAPI;

namespace TerrariaManagerAgent.Services
{
    /// <summary>
    /// 静态追踪器：记录玩家死亡次数和在线时长，持久化到独立的 SQLite 文件。
    /// 需在 TShock.SavePath 初始化后调用 Init()。
    /// </summary>
    public static class StatsTracker
    {
        private static readonly ConcurrentDictionary<string, DateTime> _sessionStart
            = new(StringComparer.OrdinalIgnoreCase);

        private static string _dbPath = "";
        private static bool _inited;

        public static void Init()
        {
            if (_inited) return;
            _inited = true;
            _dbPath = Path.Combine(TShock.SavePath, "agent_stats.db");
            try
            {
                using var conn = OpenDb();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = @"
                    CREATE TABLE IF NOT EXISTS agent_player_stats (
                        name           TEXT NOT NULL COLLATE NOCASE,
                        deaths         INTEGER NOT NULL DEFAULT 0,
                        online_seconds INTEGER NOT NULL DEFAULT 0,
                        PRIMARY KEY (name)
                    )";
                cmd.ExecuteNonQuery();
            }
            catch (Exception ex)
            {
                TShock.Log.Warn($"[Agent] StatsTracker 表创建失败: {ex.Message}");
            }
        }

        private static SqliteConnection OpenDb()
        {
            var conn = new SqliteConnection($"Data Source={_dbPath}");
            conn.Open();
            return conn;
        }

        public static void OnJoin(string name)
        {
            if (string.IsNullOrWhiteSpace(name)) return;
            _sessionStart[name] = DateTime.UtcNow;
        }

        public static void OnLeave(string name)
        {
            if (string.IsNullOrWhiteSpace(name)) return;
            if (!_sessionStart.TryRemove(name, out var start)) return;

            long secs = Math.Max(0, (long)(DateTime.UtcNow - start).TotalSeconds);
            try
            {
                using var conn = OpenDb();
                EnsureRow(conn, name);
                using var cmd = conn.CreateCommand();
                cmd.CommandText = "UPDATE agent_player_stats SET online_seconds = online_seconds + @s WHERE name = @n COLLATE NOCASE";
                cmd.Parameters.AddWithValue("@n", name);
                cmd.Parameters.AddWithValue("@s", secs);
                cmd.ExecuteNonQuery();
            }
            catch { }
        }

        public static void OnDeath(string name)
        {
            if (string.IsNullOrWhiteSpace(name)) return;
            try
            {
                using var conn = OpenDb();
                EnsureRow(conn, name);
                using var cmd = conn.CreateCommand();
                cmd.CommandText = "UPDATE agent_player_stats SET deaths = deaths + 1 WHERE name = @n COLLATE NOCASE";
                cmd.Parameters.AddWithValue("@n", name);
                cmd.ExecuteNonQuery();
            }
            catch { }
        }

        private static void EnsureRow(SqliteConnection conn, string name)
        {
            using var cmd = conn.CreateCommand();
            cmd.CommandText = "INSERT OR IGNORE INTO agent_player_stats(name, deaths, online_seconds) VALUES(@n, 0, 0)";
            cmd.Parameters.AddWithValue("@n", name);
            cmd.ExecuteNonQuery();
        }

        /// <summary>返回所有玩家统计，当前在线会话时长实时累计。</summary>
        public static List<PlayerStatRow> GetAllStats()
        {
            var rows = new List<PlayerStatRow>();
            try
            {
                using var conn = OpenDb();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = "SELECT name, deaths, online_seconds FROM agent_player_stats ORDER BY online_seconds DESC LIMIT 100";
                using var reader = cmd.ExecuteReader();
                while (reader.Read())
                {
                    rows.Add(new PlayerStatRow
                    {
                        Name          = reader.GetString(0),
                        Deaths        = reader.GetInt32(1),
                        OnlineSeconds = reader.GetInt64(2),
                    });
                }
            }
            catch { }

            // 将当前在线会话时长合并
            foreach (var row in rows)
            {
                if (_sessionStart.TryGetValue(row.Name, out var start))
                    row.OnlineSeconds += (long)(DateTime.UtcNow - start).TotalSeconds;
            }

            // 补充在 DB 中没有记录但当前在线的玩家
            foreach (var kv in _sessionStart)
            {
                if (!rows.Exists(r => r.Name.Equals(kv.Key, StringComparison.OrdinalIgnoreCase)))
                {
                    rows.Add(new PlayerStatRow
                    {
                        Name          = kv.Key,
                        Deaths        = 0,
                        OnlineSeconds = (long)(DateTime.UtcNow - kv.Value).TotalSeconds,
                    });
                }
            }

            return rows;
        }
    }

    public class PlayerStatRow
    {
        public string Name          { get; set; } = "";
        public int    Deaths        { get; set; }
        public long   OnlineSeconds { get; set; }
    }
}
