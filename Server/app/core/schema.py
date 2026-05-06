import sqlite3

from app.core.config import AUTH_DB_PATH


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(str(row[1]).lower() == column.lower() for row in rows)


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not _column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def init_auth_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT    UNIQUE NOT NULL,
            pw_hash    TEXT    NOT NULL,
            salt       TEXT    NOT NULL,
            access_group_id INTEGER,
            created_at INTEGER NOT NULL
        )
    """)
    _ensure_column(conn, "Users", "access_group_id", "INTEGER")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS AccountAccessGroups (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    UNIQUE NOT NULL,
            parent_group_id INTEGER,
            description TEXT,
            permissions TEXT NOT NULL DEFAULT '[]',
            is_builtin INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (parent_group_id) REFERENCES AccountAccessGroups(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS AgentCharacterBindingsCache (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            agent_key      TEXT    NOT NULL,
            character_name TEXT    NOT NULL,
            registered_at  INTEGER NOT NULL,
            UNIQUE(agent_key, character_name),
            FOREIGN KEY (user_id) REFERENCES Users(id) ON DELETE CASCADE
        )
    """)

    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO AccountAccessGroups(name, description, permissions, is_builtin) VALUES('superadmin', '超级管理员，拥有所有权限', '[\"*\"]', 1)")
    cursor.execute("INSERT OR IGNORE INTO AccountAccessGroups(name, description, permissions, is_builtin) VALUES('admin', '管理员', '[\"rbac.manage\"]', 1)")
    cursor.execute("INSERT OR IGNORE INTO AccountAccessGroups(name, description, permissions, is_builtin) VALUES('default', '普通用户', '[]', 1)")


def init_auth_db() -> None:
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        init_auth_schema(conn)
        conn.commit()


def init_server_workflow_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ServerMemberRequests (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id           INTEGER NOT NULL,
            request_type        TEXT    NOT NULL,
            from_user_id        INTEGER NOT NULL,
            to_user_id          INTEGER,
            message             TEXT    NOT NULL DEFAULT '',
            status              TEXT    NOT NULL DEFAULT 'pending',
            reviewed_by_user_id INTEGER,
            reviewed_at         INTEGER,
            review_note         TEXT    NOT NULL DEFAULT '',
            withdrawn_at        INTEGER,
            expires_at          INTEGER,
            acted_at            INTEGER,
            created_at          INTEGER NOT NULL,
            updated_at          INTEGER NOT NULL,
            CHECK(request_type IN ('join', 'invite')),
            CHECK(status IN ('pending', 'approved', 'rejected', 'withdrawn', 'accepted', 'canceled', 'expired')),
            FOREIGN KEY(server_id) REFERENCES Servers(id) ON DELETE CASCADE,
            FOREIGN KEY(from_user_id) REFERENCES Users(id) ON DELETE CASCADE,
            FOREIGN KEY(to_user_id) REFERENCES Users(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_member_requests_server_type_status ON ServerMemberRequests(server_id, request_type, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_member_requests_from_type_status ON ServerMemberRequests(from_user_id, request_type, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_member_requests_to_type_status ON ServerMemberRequests(to_user_id, request_type, status)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_member_join_pending ON ServerMemberRequests(server_id, from_user_id) WHERE request_type='join' AND status='pending'"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_member_invite_pending ON ServerMemberRequests(server_id, to_user_id) WHERE request_type='invite' AND status='pending'"
    )


def init_blacklist_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS AgentServerBlacklistCache (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id          INTEGER NOT NULL,
            target_user_id     INTEGER NOT NULL,
            target_email       TEXT    NOT NULL DEFAULT '',
            reason             TEXT    NOT NULL DEFAULT '',
            status             TEXT    NOT NULL DEFAULT 'active',
            created_by_user_id INTEGER NOT NULL,
            created_at         INTEGER NOT NULL,
            removed_by_user_id INTEGER,
            removed_at         INTEGER,
            FOREIGN KEY(server_id) REFERENCES Servers(id) ON DELETE CASCADE,
            FOREIGN KEY(target_user_id) REFERENCES Users(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_agent_blacklist_server_status ON AgentServerBlacklistCache(server_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_agent_blacklist_target ON AgentServerBlacklistCache(target_user_id, status)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_blacklist_active ON AgentServerBlacklistCache(server_id, target_user_id) WHERE status='active'"
    )

    conn.execute("""
        CREATE TABLE IF NOT EXISTS CloudBlacklistEntries (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            target_user_id       INTEGER NOT NULL,
            target_email         TEXT    NOT NULL DEFAULT '',
            source_server_id     INTEGER NOT NULL,
            reason               TEXT    NOT NULL,
            status               TEXT    NOT NULL DEFAULT 'pending',
            submitted_by_user_id INTEGER NOT NULL,
            submitted_at         INTEGER NOT NULL,
            reviewed_by_user_id  INTEGER,
            reviewed_at          INTEGER,
            review_note          TEXT    NOT NULL DEFAULT '',
            FOREIGN KEY(target_user_id) REFERENCES Users(id) ON DELETE CASCADE,
            FOREIGN KEY(source_server_id) REFERENCES Servers(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_cloud_blacklist_target_status ON CloudBlacklistEntries(target_user_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_cloud_blacklist_status ON CloudBlacklistEntries(status, submitted_at DESC)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_cloud_blacklist_open_source ON CloudBlacklistEntries(source_server_id, target_user_id) WHERE status IN ('pending','approved')"
    )


def init_message_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Messages (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            receiver_user_id INTEGER NOT NULL,
            sender_user_id   INTEGER,
            server_id        INTEGER,
            type             TEXT    NOT NULL,
            ref_type         TEXT,
            ref_id           INTEGER,
            title            TEXT    NOT NULL,
            content          TEXT    NOT NULL,
            payload_json     TEXT    NOT NULL DEFAULT '{}',
            created_at       INTEGER NOT NULL,
            read_at          INTEGER,
            FOREIGN KEY(receiver_user_id) REFERENCES Users(id) ON DELETE CASCADE,
            FOREIGN KEY(sender_user_id) REFERENCES Users(id) ON DELETE SET NULL,
            FOREIGN KEY(server_id) REFERENCES Servers(id) ON DELETE SET NULL
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_messages_receiver_read_created ON Messages(receiver_user_id, read_at, created_at DESC)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_messages_ref ON Messages(ref_type, ref_id)")


def init_server_access_group_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ServerAccessGroups (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id   INTEGER NOT NULL,
            name        TEXT    NOT NULL,
            description TEXT,
            parent_group_id INTEGER,
            is_builtin  INTEGER NOT NULL DEFAULT 0,
            permissions TEXT NOT NULL DEFAULT '[]',
            UNIQUE(server_id, name),
            FOREIGN KEY(server_id) REFERENCES Servers(id) ON DELETE CASCADE
        )
    """)


def init_platform_admin_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS AccountRestrictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            restriction_type TEXT NOT NULL,
            value TEXT,
            reason TEXT,
            created_by INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1,
            CHECK(restriction_type IN ('qq_limit', 'ban', 'role_limit'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_account_restrictions_user ON AccountRestrictions(user_id)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS UserReports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_id INTEGER NOT NULL,
            reported_user_id INTEGER NOT NULL,
            reported_server_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL,
            resolved_at INTEGER,
            resolved_by INTEGER,
            resolution TEXT,
            CHECK(status IN ('pending', 'processing', 'resolved', 'ignored'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_user_reports_status ON UserReports(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_user_reports_reported_user ON UserReports(reported_user_id)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS AuditLogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operator_id INTEGER NOT NULL,
            operation_type TEXT NOT NULL,
            target_type TEXT NOT NULL,
            target_id INTEGER NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at INTEGER NOT NULL,
            CHECK(operation_type IN ('server_create', 'server_delete', 'server_update', 'account_ban', 'account_unban', 'announcement_create', 'announcement_update', 'announcement_delete', 'audit_approve', 'audit_reject', 'permission_grant', 'permission_revoke'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_operator ON AuditLogs(operator_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_created ON AuditLogs(created_at DESC)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS PlatformSettings (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT,
            updated_at INTEGER NOT NULL
        )
    """)


def init_announcement_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS Announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            target_type TEXT NOT NULL DEFAULT 'all',
            server_id INTEGER,
            target_account_id INTEGER,
            is_important INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            created_by INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            updated_at INTEGER,
            expires_at INTEGER,
            CHECK(status IN ('active', 'archived')),
            CHECK(target_type IN ('server', 'account', 'all'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_announcements_status ON Announcements(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_announcements_server ON Announcements(server_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_announcements_target_type ON Announcements(target_type)")


def init_platform_schema(conn: sqlite3.Connection) -> None:
    init_server_workflow_schema(conn)
    init_blacklist_schema(conn)
    init_message_schema(conn)
    init_server_access_group_schema(conn)
    init_platform_admin_schema(conn)
    init_announcement_schema(conn)


def init_platform_db() -> None:
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        init_auth_schema(conn)
        init_platform_schema(conn)
        conn.commit()
