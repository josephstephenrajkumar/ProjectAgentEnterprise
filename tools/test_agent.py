import os
import sys

# Set up PYTHONPATH
sys.path.insert(0, "/home/joseph/ProjectAgentEnterprise/backend")
sys.path.insert(0, "/home/joseph/ProjectAgentEnterprise")

import sqlite3
from app.config.settings import get_settings

settings = get_settings()
print("Database path:", settings.db_abs_path)

# Verify projects
conn = sqlite3.connect(settings.db_abs_path)
conn.row_factory = sqlite3.Row
projects = conn.execute("SELECT project_id, ProjectNumber, customer FROM Project").fetchall()
print("Projects in DB:")
for p in projects:
    print(dict(p))
conn.close()

from app.graph.supervisor_graph import chat_graph

query = "What are the deliverables or milestones defined in the contract for BOSTON-001?"
print(f"\nInvoking chat_graph with query: {query}")

initial_state = {
    "query": query,
    "response": "",
    "next_node": "",
    "agent_outputs": [],
    "history": [],
    "debug_log": "",
    "project_id": "70c52032-82d6-4b1a-8cd6-81f96dfbc41a", # UUID for BOSTON-001
}

try:
    result = chat_graph.invoke(initial_state)
    print("\nResult response:")
    print(result.get("response"))
    print("\nResult debug log:")
    print(result.get("debug_log"))
    print("\nResult agent outputs:")
    for out in result.get("agent_outputs", []):
        print("---")
        print(out)
except Exception as e:
    import traceback
    traceback.print_exc()
