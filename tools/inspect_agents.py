import sqlite3
from app.config.settings import get_settings
import sys

sys.path.insert(0, "/home/joseph/ProjectAgentEnterprise/backend")
sys.path.insert(0, "/home/joseph/ProjectAgentEnterprise")

settings = get_settings()
conn = sqlite3.connect(settings.db_abs_path)
conn.row_factory = sqlite3.Row

print("--- AGENTS ---")
for row in conn.execute("SELECT agent_id, name, is_active, tools, requires_approval FROM AgentConfig").fetchall():
    print(dict(row))

print("\n--- TRIGGER KEYWORDS ---")
for row in conn.execute("SELECT agent_id, keyword, priority, is_active FROM TriggerKeyword").fetchall():
    print(dict(row))

conn.close()
