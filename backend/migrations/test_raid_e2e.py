import sys
import os
import json

# Setup PYTHONPATH
sys.path.insert(0, "/home/joseph/ProjectAgentEnterprise/backend")
sys.path.insert(0, "/home/joseph/ProjectAgentEnterprise")

from app.graph.supervisor_graph import chat_graph
from app.graph.state import AgentState

query = (
    "Add a raid item for boston project - risk of delay in project kick off and onboarding. "
    "The reason is the SOW is not signed by customer. The customer has indicated there will be delay of two weeks to issue the signed PO"
)

state: AgentState = {
    "query": query,
    "project_id": "",  # Will be extracted by agent
    "history": [],
    "agent_outputs": [],
    "debug_log": "",
    "next_node": "",
}

print(f"Executing graph for query: '{query}'...")
final_state = chat_graph.invoke(state)

print("\n=== FINAL STATE ===")
print("Project ID Extracted:", final_state.get("project_id"))
print("Next Node Decision:", final_state.get("next_node"))
print("\n=== AGENT OUTPUTS ===")
for out in final_state.get("agent_outputs", []):
    print(out)

print("\n=== DEBUG LOG ===")
print(final_state.get("debug_log"))
