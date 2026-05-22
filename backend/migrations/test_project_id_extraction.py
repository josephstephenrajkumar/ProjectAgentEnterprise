import sys
sys.path.insert(0, "/home/joseph/ProjectAgentEnterprise/backend")
sys.path.insert(0, "/home/joseph/ProjectAgentEnterprise")

from langchain_core.messages import SystemMessage, HumanMessage
from app.agents.llm_factory import get_llm

llm = get_llm()
prompt = (
    "You are a strict data extractor. Your job is to extract the project identifier (Project Number, Opportunity ID, project code, or customer/project name) from the user's query. "
    "Output ONLY the raw identifier string (e.g., 'boston' or 'boston-001') and absolutely nothing else. No explanation, no filler, no markdown. "
    "Strip generic trailing nouns like 'project', 'sow', 'contract', 'opportunity' (e.g., for 'boston project', extract 'boston'). "
    "If not found, output exactly: NONE"
)
query = (
    "Add a raid item for boston project - risk of delay in project kick off and onboarding. "
    "The reason is the SOW is not signed by customer. The customer has indicated there will be delay of two weeks to issue the signed PO"
)

response = llm.invoke([
    SystemMessage(content=prompt),
    HumanMessage(content=query)
])
print("Extracted identifier:", response.content.strip())
