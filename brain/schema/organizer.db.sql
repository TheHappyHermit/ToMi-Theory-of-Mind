CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'cancelled', 'blocked')),
    priority TEXT DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high', 'critical')),
    due_at TEXT,
    completed_at TEXT,
    project_id INTEGER,
    dependency_id INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL,
    FOREIGN KEY (dependency_id) REFERENCES tasks(id) ON DELETE SET NULL
);
CREATE TABLE sqlite_sequence(name,seq);
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'completed', 'archived')),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'USD',
    billing_cycle TEXT DEFAULT 'monthly',
    next_billing_date TEXT,
    status TEXT DEFAULT 'active' CHECK(status IN ('active', 'cancelled', 'paused')),
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE important_dates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    date TEXT NOT NULL,
    description TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE intentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    cue TEXT,
    action TEXT NOT NULL,
    status TEXT DEFAULT 'dormant' CHECK(status IN ('dormant', 'active', 'expired', 'completed')),
    created_at TEXT DEFAULT (datetime('now')),
    triggered_at TEXT
);
CREATE TABLE waiting_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    waiting_for TEXT,
    follow_up_date TEXT,
    status TEXT DEFAULT 'waiting' CHECK(status IN ('waiting', 'resolved', 'cancelled')),
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_due ON tasks(due_at);
CREATE INDEX idx_tasks_project ON tasks(project_id);
CREATE INDEX idx_subscriptions_next ON subscriptions(next_billing_date);
CREATE INDEX idx_dates ON important_dates(date);
CREATE INDEX idx_intentions_status ON intentions(status);
CREATE INDEX idx_waiting_status ON waiting_states(status);
CREATE TABLE reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    remind_at TEXT NOT NULL,
    channel TEXT DEFAULT 'all' CHECK(channel IN ('all', 'telegram', 'discord', 'email', 'sms', 'desktop', 'gui')),
    target_destination TEXT,
    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'sent', 'cancelled', 'snoozed')),
    recurring_rule TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    sent_at TEXT
);
CREATE INDEX idx_reminders_status_time ON reminders(status, remind_at);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_reminders_due ON reminders(remind_at) WHERE status = 'pending';
CREATE INDEX idx_intentions_dormant ON intentions(status, created_at);
CREATE INDEX idx_waiting_followup ON waiting_states(follow_up_date);
CREATE TABLE chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                bot_id TEXT NOT NULL,
                sender TEXT NOT NULL CHECK(sender IN ('user', 'bot', 'tool')),
                message TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
            );
CREATE INDEX idx_chat_bot_session ON chat_messages(bot_id, session_id);
