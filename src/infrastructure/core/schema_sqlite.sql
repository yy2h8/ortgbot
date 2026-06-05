CREATE TABLE IF NOT EXISTS telegram_groups (
    telegram_group_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tg_id INTEGER UNIQUE NOT NULL,
    title TEXT NOT NULL,
    language TEXT,
    trigger_word TEXT,
    persona TEXT,
    bot_added_at INTEGER NOT NULL,
    is_active INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

-- find_active_groups(), _cleanup_inactive_groups()
CREATE INDEX IF NOT EXISTS idx_telegram_groups_is_active ON telegram_groups (is_active);

CREATE TABLE IF NOT EXISTS telegram_group_members (
    telegram_group_member_id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_group_id INTEGER REFERENCES telegram_groups(telegram_group_id) ON DELETE SET NULL,
    tg_id INTEGER NOT NULL,
    first_name TEXT NOT NULL,
    username TEXT,
    is_bot INTEGER NOT NULL DEFAULT 0,
    has_left_group INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE(telegram_group_id, tg_id)
);

-- _cleanup_inactive_members() join + date filter
CREATE INDEX IF NOT EXISTS idx_telegram_group_members_cleanup ON telegram_group_members (telegram_group_id, has_left_group, updated_at);

CREATE TABLE IF NOT EXISTS telegram_messages (
    telegram_message_id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_group_id INTEGER REFERENCES telegram_groups(telegram_group_id) ON DELETE SET NULL,
    telegram_group_member_id INTEGER REFERENCES telegram_group_members(telegram_group_member_id) ON DELETE SET NULL,
    reply_to_message_id INTEGER REFERENCES telegram_messages(telegram_message_id) ON DELETE SET NULL,
    tg_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
    is_reply_to_bot_message INTEGER NOT NULL,
    is_generated INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);

-- find_by_tg_id() — resolves reply-to message on every incoming reply
CREATE INDEX IF NOT EXISTS idx_telegram_messages_tg_id ON telegram_messages (tg_id);

-- delete_all_for_group(), get_all_messages_for_group_excluding_generated() ordering, cleanup deletes
CREATE INDEX IF NOT EXISTS idx_telegram_messages_group_timestamp ON telegram_messages (telegram_group_id, timestamp);

-- count_non_generated_for_groups(), get_all_messages_for_group_excluding_generated() filter
CREATE INDEX IF NOT EXISTS idx_telegram_messages_group_generated ON telegram_messages (telegram_group_id, is_generated);

-- _cleanup_inactive_members() delete, _cleanup_orphaned_member_messages()
CREATE INDEX IF NOT EXISTS idx_telegram_messages_member_id ON telegram_messages (telegram_group_member_id);

-- FK ON DELETE SET NULL cascade when messages are deleted (reply chain integrity)
CREATE INDEX IF NOT EXISTS idx_telegram_messages_reply_to ON telegram_messages (reply_to_message_id);

CREATE TABLE IF NOT EXISTS openrouter_requests (
    openrouter_request_id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_openrouter_id TEXT,
    telegram_group_id INTEGER REFERENCES telegram_groups(telegram_group_id) ON DELETE SET NULL,
    prompt_tokens_usage INTEGER,
    completion_tokens_usage INTEGER,
    cost_estimate_usd REAL,
    request_payload TEXT,  -- JSON stored as TEXT
    response_content TEXT,  -- JSON stored as TEXT
    processing_time_ms INTEGER,
    success INTEGER,
    error_message TEXT,
    created_at INTEGER NOT NULL
);

-- FK ON DELETE SET NULL cascade when groups are deleted (append-only analytics log)
CREATE INDEX IF NOT EXISTS idx_openrouter_requests_group_id ON openrouter_requests (telegram_group_id);

CREATE TABLE IF NOT EXISTS ai_group_contexts (
    ai_group_context_id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_group_id INTEGER REFERENCES telegram_groups(telegram_group_id) ON DELETE SET NULL,
    context_text TEXT NOT NULL,
    analysis_trends_count INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);

-- find_for_group(), find_for_groups()
CREATE INDEX IF NOT EXISTS idx_ai_group_contexts_group_created ON ai_group_contexts (telegram_group_id, created_at DESC);

CREATE TABLE IF NOT EXISTS ai_group_trends (
    ai_group_trend_id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_group_id INTEGER REFERENCES telegram_groups(telegram_group_id) ON DELETE SET NULL,
    recent_trends_text TEXT NOT NULL,
    analysis_message_count INTEGER NOT NULL DEFAULT 0,
    created_at INTEGER NOT NULL
);

-- find_latest_for_group(), find_all_for_group(), count_for_groups(), delete queries
CREATE INDEX IF NOT EXISTS idx_ai_group_trends_group_created ON ai_group_trends (telegram_group_id, created_at);

CREATE TABLE IF NOT EXISTS rate_limit_entries (
    rate_limit_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT NOT NULL,
    timestamp REAL NOT NULL
);

-- check() sliding window COUNT
CREATE INDEX IF NOT EXISTS idx_rate_limit_entries_key_timestamp ON rate_limit_entries (key, timestamp);

-- cleanup_expired_entries() WHERE timestamp < ?
CREATE INDEX IF NOT EXISTS idx_rate_limit_entries_timestamp ON rate_limit_entries (timestamp);
