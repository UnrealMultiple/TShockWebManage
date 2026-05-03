using System;
using System.Collections.Generic;
using System.IO;
using Microsoft.Data.Sqlite;
using TShockAPI;

namespace TerrariaManagerAgent.Services
{
    public static class AgentLocalStore
    {
        private const string DbFileName = "TShockAgent.sqlite";
        private static string _dbPath = "";
        private static bool _inited;
        private static readonly object DbLock = new object();

        public static void Init()
        {
            if (_inited) return;
            _inited = true;
            _dbPath = Path.Combine(TShock.SavePath, DbFileName);

            lock (DbLock)
            {
                using var conn = OpenDb();
                ExecuteNonQuery(conn, @"
                    CREATE TABLE IF NOT EXISTS AgentCharacterBindings (
                        id             INTEGER PRIMARY KEY AUTOINCREMENT,
                        panel_user_id  INTEGER NOT NULL,
                        panel_email    TEXT NOT NULL DEFAULT '',
                        character_name TEXT NOT NULL COLLATE NOCASE,
                        registered_at  INTEGER NOT NULL,
                        updated_at     INTEGER NOT NULL,
                        source         TEXT NOT NULL DEFAULT '',
                        UNIQUE(character_name COLLATE NOCASE)
                    )");
                ExecuteNonQuery(conn, @"
                    CREATE INDEX IF NOT EXISTS ix_agent_character_bindings_user
                    ON AgentCharacterBindings(panel_user_id)");
                ExecuteNonQuery(conn, @"
                    CREATE TABLE IF NOT EXISTS AgentServerBlacklistEntries (
                        id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                        target_user_id     INTEGER NOT NULL,
                        target_email       TEXT NOT NULL DEFAULT '',
                        reason             TEXT NOT NULL DEFAULT '',
                        status             TEXT NOT NULL DEFAULT 'active',
                        created_by_user_id INTEGER NOT NULL,
                        created_by_email   TEXT NOT NULL DEFAULT '',
                        created_at         INTEGER NOT NULL,
                        removed_by_user_id INTEGER,
                        removed_by_email   TEXT NOT NULL DEFAULT '',
                        removed_at         INTEGER
                    )");
                ExecuteNonQuery(conn, @"
                    CREATE INDEX IF NOT EXISTS ix_agent_blacklist_status
                    ON AgentServerBlacklistEntries(status, created_at DESC)");
                ExecuteNonQuery(conn, @"
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_blacklist_active_user
                    ON AgentServerBlacklistEntries(target_user_id)
                    WHERE status='active'");
            }
        }

        private static SqliteConnection OpenDb()
        {
            if (string.IsNullOrWhiteSpace(_dbPath))
                _dbPath = Path.Combine(TShock.SavePath, DbFileName);
            var conn = new SqliteConnection($"Data Source={_dbPath}");
            conn.Open();
            return conn;
        }

        private static long Now() => DateTimeOffset.UtcNow.ToUnixTimeSeconds();

        private static void ExecuteNonQuery(SqliteConnection conn, string sql)
        {
            using var cmd = conn.CreateCommand();
            cmd.CommandText = sql;
            cmd.ExecuteNonQuery();
        }

        public static int CountCharacters(long panelUserId)
        {
            lock (DbLock)
            {
                using var conn = OpenDb();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = "SELECT COUNT(*) FROM AgentCharacterBindings WHERE panel_user_id=@uid";
                cmd.Parameters.AddWithValue("@uid", panelUserId);
                return Convert.ToInt32(cmd.ExecuteScalar() ?? 0);
            }
        }

        public static bool CharacterExists(string characterName)
        {
            lock (DbLock)
            {
                using var conn = OpenDb();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = "SELECT 1 FROM AgentCharacterBindings WHERE character_name=@name COLLATE NOCASE LIMIT 1";
                cmd.Parameters.AddWithValue("@name", characterName);
                return cmd.ExecuteScalar() != null;
            }
        }

        public static CharacterBinding? FindCharacter(string characterName)
        {
            lock (DbLock)
            {
                using var conn = OpenDb();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = @"
                    SELECT id, panel_user_id, panel_email, character_name, registered_at, updated_at, source
                    FROM AgentCharacterBindings
                    WHERE character_name=@name COLLATE NOCASE
                    LIMIT 1";
                cmd.Parameters.AddWithValue("@name", characterName);
                using var reader = cmd.ExecuteReader();
                return reader.Read() ? ReadCharacter(reader) : null;
            }
        }

        public static CharacterBinding UpsertCharacter(long panelUserId, string panelEmail, string characterName, string source)
        {
            var now = Now();
            lock (DbLock)
            {
                using var conn = OpenDb();
                using var tx = conn.BeginTransaction();
                using (var cmd = conn.CreateCommand())
                {
                    cmd.Transaction = tx;
                    cmd.CommandText = @"
                        INSERT INTO AgentCharacterBindings(
                            panel_user_id, panel_email, character_name, registered_at, updated_at, source
                        ) VALUES(@uid, @mail, @name, @now, @now, @source)
                        ON CONFLICT(character_name) DO UPDATE SET
                            panel_user_id=excluded.panel_user_id,
                            panel_email=excluded.panel_email,
                            updated_at=excluded.updated_at,
                            source=excluded.source";
                    cmd.Parameters.AddWithValue("@uid", panelUserId);
                    cmd.Parameters.AddWithValue("@mail", panelEmail ?? "");
                    cmd.Parameters.AddWithValue("@name", characterName);
                    cmd.Parameters.AddWithValue("@now", now);
                    cmd.Parameters.AddWithValue("@source", source ?? "");
                    cmd.ExecuteNonQuery();
                }
                tx.Commit();
                return FindCharacter(characterName)!;
            }
        }

        public static CharacterBinding? DeleteCharacter(string characterName, long? panelUserId = null)
        {
            lock (DbLock)
            {
                var existing = FindCharacter(characterName);
                if (existing == null) return null;
                if (panelUserId.HasValue && existing.PanelUserId != panelUserId.Value)
                    return null;

                using var conn = OpenDb();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = panelUserId.HasValue
                    ? "DELETE FROM AgentCharacterBindings WHERE character_name=@name COLLATE NOCASE AND panel_user_id=@uid"
                    : "DELETE FROM AgentCharacterBindings WHERE character_name=@name COLLATE NOCASE";
                cmd.Parameters.AddWithValue("@name", characterName);
                if (panelUserId.HasValue) cmd.Parameters.AddWithValue("@uid", panelUserId.Value);
                cmd.ExecuteNonQuery();
                return existing;
            }
        }

        public static List<CharacterBinding> ListCharacters(long? panelUserId = null)
        {
            lock (DbLock)
            {
                using var conn = OpenDb();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = panelUserId.HasValue
                    ? @"SELECT id, panel_user_id, panel_email, character_name, registered_at, updated_at, source
                        FROM AgentCharacterBindings WHERE panel_user_id=@uid ORDER BY registered_at DESC"
                    : @"SELECT id, panel_user_id, panel_email, character_name, registered_at, updated_at, source
                        FROM AgentCharacterBindings ORDER BY character_name COLLATE NOCASE";
                if (panelUserId.HasValue) cmd.Parameters.AddWithValue("@uid", panelUserId.Value);

                var rows = new List<CharacterBinding>();
                using var reader = cmd.ExecuteReader();
                while (reader.Read()) rows.Add(ReadCharacter(reader));
                return rows;
            }
        }

        private static CharacterBinding ReadCharacter(SqliteDataReader reader)
        {
            return new CharacterBinding
            {
                Id = reader.GetInt64(0),
                PanelUserId = reader.GetInt64(1),
                PanelEmail = reader.GetString(2),
                CharacterName = reader.GetString(3),
                RegisteredAt = reader.GetInt64(4),
                UpdatedAt = reader.GetInt64(5),
                Source = reader.GetString(6),
            };
        }

        public static BlacklistEntry AddBlacklist(
            long targetUserId,
            string targetEmail,
            string reason,
            long createdByUserId,
            string createdByEmail)
        {
            var now = Now();
            lock (DbLock)
            {
                using var conn = OpenDb();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = @"
                    INSERT INTO AgentServerBlacklistEntries(
                        target_user_id, target_email, reason, status,
                        created_by_user_id, created_by_email, created_at
                    ) VALUES(@target_uid, @target_email, @reason, 'active', @created_uid, @created_email, @now)";
                cmd.Parameters.AddWithValue("@target_uid", targetUserId);
                cmd.Parameters.AddWithValue("@target_email", targetEmail ?? "");
                cmd.Parameters.AddWithValue("@reason", reason ?? "");
                cmd.Parameters.AddWithValue("@created_uid", createdByUserId);
                cmd.Parameters.AddWithValue("@created_email", createdByEmail ?? "");
                cmd.Parameters.AddWithValue("@now", now);
                try
                {
                    cmd.ExecuteNonQuery();
                }
                catch (SqliteException ex) when (ex.SqliteErrorCode == 19)
                {
                }

                using var read = conn.CreateCommand();
                read.CommandText = @"
                    SELECT id, target_user_id, target_email, reason, status,
                           created_by_user_id, created_by_email, created_at,
                           removed_by_user_id, removed_by_email, removed_at
                    FROM AgentServerBlacklistEntries
                    WHERE target_user_id=@target_uid AND status='active'
                    LIMIT 1";
                read.Parameters.AddWithValue("@target_uid", targetUserId);
                using var reader = read.ExecuteReader();
                if (!reader.Read()) throw new Exception("黑名单写入失败");
                return ReadBlacklist(reader);
            }
        }

        public static BlacklistEntry? RemoveBlacklist(long targetUserId, long removedByUserId, string removedByEmail)
        {
            var now = Now();
            lock (DbLock)
            {
                using var conn = OpenDb();
                using var cmd = conn.CreateCommand();
                cmd.CommandText = @"
                    UPDATE AgentServerBlacklistEntries
                    SET status='removed', removed_by_user_id=@removed_uid,
                        removed_by_email=@removed_email, removed_at=@now
                    WHERE target_user_id=@target_uid AND status='active'";
                cmd.Parameters.AddWithValue("@removed_uid", removedByUserId);
                cmd.Parameters.AddWithValue("@removed_email", removedByEmail ?? "");
                cmd.Parameters.AddWithValue("@now", now);
                cmd.Parameters.AddWithValue("@target_uid", targetUserId);
                var affected = cmd.ExecuteNonQuery();
                if (affected <= 0) return null;

                using var read = conn.CreateCommand();
                read.CommandText = @"
                    SELECT id, target_user_id, target_email, reason, status,
                           created_by_user_id, created_by_email, created_at,
                           removed_by_user_id, removed_by_email, removed_at
                    FROM AgentServerBlacklistEntries
                    WHERE target_user_id=@target_uid
                    ORDER BY id DESC
                    LIMIT 1";
                read.Parameters.AddWithValue("@target_uid", targetUserId);
                using var reader = read.ExecuteReader();
                return reader.Read() ? ReadBlacklist(reader) : null;
            }
        }

        private static BlacklistEntry ReadBlacklist(SqliteDataReader reader)
        {
            return new BlacklistEntry
            {
                Id = reader.GetInt64(0),
                TargetUserId = reader.GetInt64(1),
                TargetEmail = reader.GetString(2),
                Reason = reader.GetString(3),
                Status = reader.GetString(4),
                CreatedByUserId = reader.GetInt64(5),
                CreatedByEmail = reader.GetString(6),
                CreatedAt = reader.GetInt64(7),
                RemovedByUserId = reader.IsDBNull(8) ? null : reader.GetInt64(8),
                RemovedByEmail = reader.GetString(9),
                RemovedAt = reader.IsDBNull(10) ? null : reader.GetInt64(10),
            };
        }
    }

    public class CharacterBinding
    {
        public long Id { get; set; }
        public long PanelUserId { get; set; }
        public string PanelEmail { get; set; } = "";
        public string CharacterName { get; set; } = "";
        public long RegisteredAt { get; set; }
        public long UpdatedAt { get; set; }
        public string Source { get; set; } = "";
    }

    public class BlacklistEntry
    {
        public long Id { get; set; }
        public long TargetUserId { get; set; }
        public string TargetEmail { get; set; } = "";
        public string Reason { get; set; } = "";
        public string Status { get; set; } = "";
        public long CreatedByUserId { get; set; }
        public string CreatedByEmail { get; set; } = "";
        public long CreatedAt { get; set; }
        public long? RemovedByUserId { get; set; }
        public string RemovedByEmail { get; set; } = "";
        public long? RemovedAt { get; set; }
    }
}
