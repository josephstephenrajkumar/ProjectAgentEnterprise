"""
Email Agent — extracts recipients and content, simulates sending.
Ported from agents/email_agent.py.
"""
import json
from app.graph.state import AgentState
from app.agents.llm_factory import get_llm
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage


EMAIL_EXTRACTION_PROMPT = """You are an AI assistant that prepares emails based on chat summaries.

Your task is to:
1. Identify the list of recipient email addresses from the user's current query.
2. Identify the content to be emailed.
   - If the user says "this" or "the summary", use the MOST RECENT comprehensive report from the assistant in conversation history.
   - If the user provides specific text, use that.
3. Generate a professional subject line.

Return ONLY a JSON object:
{
  "recipients": ["email1@example.com"],
  "subject": "string",
  "body": "string"
}

If no recipients are found, return: {"error": "No recipients found"}"""


def email_agent_node(state: AgentState) -> dict:
    query = state["query"]
    history = state.get("history", [])
    debug = state.get("debug_log", "")
    llm = get_llm()

    messages = [SystemMessage(content=EMAIL_EXTRACTION_PROMPT)]
    for msg in history[-6:]:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg.get("content", "")))
    messages.append(HumanMessage(content=f"Current Instruction: {query}"))

    try:
        response = llm.invoke(messages)
        content = response.content.strip()

        if "```json" in content:
            content = content.split("```json")[-1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[-2].strip()

        data = json.loads(content)

        if "error" in data:
            return {
                "response": f"❌ Email Error: {data['error']}",
                "debug_log": debug + f"\n❌ Email Agent: {data['error']}",
            }

        recipients = data.get("recipients", [])
        subject = data.get("subject", "Project Intelligence Summary")
        body = data.get("body", "")

        if not recipients:
            return {
                "response": "❌ No email addresses found in your request.",
                "debug_log": debug + "\n❌ Email Agent: No recipients.",
            }

        from_addr = "joseph.stephenr@gmail.com"
        debug += f"\n📧 Email Agent simulating send to {', '.join(recipients)}"

        success_msg = "✅ **Email Sent Successfully!**\n\n"
        success_msg += f"- **From:** `{from_addr}`\n"
        success_msg += f"- **To:** {', '.join([f'`{r}`' for r in recipients])}\n"
        success_msg += f"- **Subject:** {subject}\n\n---\n"
        success_msg += f"**Content Sent:**\n\n{body[:500]}{'...' if len(body) > 500 else ''}"

        return {
            "response": success_msg,
            "debug_log": debug + "\n✅ Email Agent: simulated send.",
            "next_node": "END",
        }
    except Exception as e:
        return {
            "response": f"❌ Failed to process email request: {e}",
            "debug_log": debug + f"\n❌ Email Agent error: {e}",
        }
