import sqlite3

from app.core.config import AUTH_DB_PATH


def init_auth_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            email      TEXT    UNIQUE NOT NULL,
            pw_hash    TEXT    NOT NULL,
            salt       TEXT    NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS account_roles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    UNIQUE NOT NULL,
            parent_id   INTEGER,
            description TEXT,
            FOREIGN KEY (parent_id) REFERENCES account_roles(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS account_role_permissions (
            group_id   INTEGER NOT NULL,
            permission TEXT    NOT NULL,
            PRIMARY KEY (group_id, permission),
            FOREIGN KEY (group_id) REFERENCES account_roles(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS account_role_members (
            user_id    INTEGER NOT NULL,
            group_id   INTEGER NOT NULL,
            PRIMARY KEY (user_id, group_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (group_id) REFERENCES account_roles(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_character_bindings_cache (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id        INTEGER NOT NULL,
            agent_key      TEXT    NOT NULL,
            character_name TEXT    NOT NULL,
            registered_at  INTEGER NOT NULL,
            UNIQUE(agent_key, character_name),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM account_roles WHERE name='superadmin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO account_roles(name, description) VALUES('superadmin', '超级管理员，拥有所有权限')")
        cursor.execute("INSERT INTO account_roles(name, description) VALUES('admin', '管理员')")
        cursor.execute("INSERT INTO account_roles(name, description) VALUES('default', '普通用户')")
        cursor.execute("SELECT id FROM account_roles WHERE name='superadmin'")
        sid = cursor.fetchone()[0]
        cursor.execute("INSERT INTO account_role_permissions(group_id, permission) VALUES(?, '*')", (sid,))


def init_auth_db() -> None:
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        init_auth_schema(conn)
        conn.commit()


def init_server_workflow_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS server_member_requests (
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
            FOREIGN KEY(server_id) REFERENCES servers(id) ON DELETE CASCADE,
            FOREIGN KEY(from_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(to_user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_member_requests_server_type_status ON server_member_requests(server_id, request_type, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_member_requests_from_type_status ON server_member_requests(from_user_id, request_type, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_member_requests_to_type_status ON server_member_requests(to_user_id, request_type, status)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_member_join_pending ON server_member_requests(server_id, from_user_id) WHERE request_type='join' AND status='pending'"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_member_invite_pending ON server_member_requests(server_id, to_user_id) WHERE request_type='invite' AND status='pending'"
    )


def init_blacklist_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_server_blacklist_cache (
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
            FOREIGN KEY(server_id) REFERENCES servers(id) ON DELETE CASCADE,
            FOREIGN KEY(target_user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_agent_blacklist_server_status ON agent_server_blacklist_cache(server_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_agent_blacklist_target ON agent_server_blacklist_cache(target_user_id, status)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_agent_blacklist_active ON agent_server_blacklist_cache(server_id, target_user_id) WHERE status='active'"
    )

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cloud_blacklist_entries (
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
            FOREIGN KEY(target_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(source_server_id) REFERENCES servers(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_cloud_blacklist_target_status ON cloud_blacklist_entries(target_user_id, status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_cloud_blacklist_status ON cloud_blacklist_entries(status, submitted_at DESC)")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_cloud_blacklist_open_source ON cloud_blacklist_entries(source_server_id, target_user_id) WHERE status IN ('pending','approved')"
    )


def init_message_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
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
            FOREIGN KEY(receiver_user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(sender_user_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY(server_id) REFERENCES servers(id) ON DELETE SET NULL
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS ix_messages_receiver_read_created ON messages(receiver_user_id, read_at, created_at DESC)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS ix_messages_ref ON messages(ref_type, ref_id)")


def init_server_role_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS server_roles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            server_id   INTEGER NOT NULL,
            name        TEXT    NOT NULL,
            description TEXT,
            parent_group_id INTEGER,
            is_builtin  INTEGER NOT NULL DEFAULT 0,
            UNIQUE(server_id, name),
            FOREIGN KEY(server_id) REFERENCES servers(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS server_role_permissions (
            group_id    INTEGER NOT NULL,
            permission  TEXT    NOT NULL,
            PRIMARY KEY(group_id, permission),
            FOREIGN KEY(group_id) REFERENCES server_roles(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS server_member_roles (
            server_id   INTEGER NOT NULL,
            user_id     INTEGER NOT NULL,
            group_id    INTEGER NOT NULL,
            PRIMARY KEY(server_id, user_id),
            FOREIGN KEY(server_id) REFERENCES servers(id) ON DELETE CASCADE,
            FOREIGN KEY(group_id) REFERENCES server_roles(id) ON DELETE CASCADE
        )
    """)


def init_platform_admin_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS account_restrictions (
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
    conn.execute("CREATE INDEX IF NOT EXISTS ix_account_restrictions_user ON account_restrictions(user_id)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_reports (
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
    conn.execute("CREATE INDEX IF NOT EXISTS ix_user_reports_status ON user_reports(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_user_reports_reported_user ON user_reports(reported_user_id)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
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
    conn.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_operator ON audit_logs(operator_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_created ON audit_logs(created_at DESC)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS platform_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT,
            updated_at INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS platform_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            is_platform_admin INTEGER NOT NULL DEFAULT 0,
            permissions TEXT,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS ix_platform_members_user ON platform_members(user_id)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS platform_roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            permissions TEXT NOT NULL DEFAULT '[]',
            is_builtin INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS platform_member_roles (
            user_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            assigned_at INTEGER NOT NULL,
            PRIMARY KEY(user_id, group_id)
        )
    """)


def init_announcement_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS announcements (
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
    conn.execute("CREATE INDEX IF NOT EXISTS ix_announcements_status ON announcements(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_announcements_server ON announcements(server_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS ix_announcements_target_type ON announcements(target_type)")


def init_platform_schema(conn: sqlite3.Connection) -> None:
    init_server_workflow_schema(conn)
    init_blacklist_schema(conn)
    init_message_schema(conn)
    init_server_role_schema(conn)
    init_platform_admin_schema(conn)
    init_announcement_schema(conn)


def init_platform_db() -> None:
    with sqlite3.connect(AUTH_DB_PATH) as conn:
        init_auth_schema(conn)
        init_platform_schema(conn)
        conn.commit()
