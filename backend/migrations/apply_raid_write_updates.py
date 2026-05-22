import sqlite3
import json
import os

db_path = "/home/joseph/ProjectAgentEnterprise/data/openclaw.db"
if not os.path.exists(db_path):
    # Fallback to local path relative to script if needed
    db_path = os.path.join(os.path.dirname(__file__), "..", "data", "openclaw.db")

print(f"Connecting to database at {db_path}...")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 1. Update AgentConfigs
print("Updating AgentConfig tools...")
cursor.execute(
    """
    UPDATE AgentConfig
    SET tools = ?, tool_execution_order = ?
    WHERE agent_id = 'contract_sow_agent'
    """,
    (
        json.dumps(["create_raid_tool", "rag_search_tool", "summarize_tool"]),
        json.dumps(["create_raid_tool", "rag_search_tool", "summarize_tool"])
    )
)

cursor.execute(
    """
    UPDATE AgentConfig
    SET tools = ?, tool_execution_order = ?
    WHERE agent_id = 'raid_recommendation_agent'
    """,
    (
        json.dumps(["create_raid_tool", "raid_fetch_tool", "metrics_calculator_tool", "summarize_tool", "approval_gate_tool"]),
        json.dumps(["create_raid_tool", "raid_fetch_tool", "metrics_calculator_tool", "summarize_tool", "approval_gate_tool"])
    )
)

# 2. Update TriggerKeywords
new_keywords = [
    ('tkw_rad_08', 'add a raid'),
    ('tkw_rad_09', 'add raid'),
    ('tkw_rad_10', 'create raid'),
    ('tkw_rad_11', 'new raid'),
    ('tkw_rad_12', 'add risk'),
    ('tkw_rad_13', 'add issue'),
    ('tkw_rad_14', 'add dependency'),
    ('tkw_rad_15', 'add assumption'),
    ('tkw_rad_16', 'create dependency'),
    ('tkw_rad_17', 'create assumption'),
]

print("Inserting new TriggerKeywords...")
for kw_id, kw in new_keywords:
    cursor.execute(
        """
        INSERT OR IGNORE INTO TriggerKeyword (keyword_id, agent_id, keyword, match_type, priority)
        VALUES (?, 'raid_recommendation_agent', ?, 'contains', 1)
        """,
        (kw_id, kw)
    )

conn.commit()
conn.close()
print("Database updates successfully applied!")
