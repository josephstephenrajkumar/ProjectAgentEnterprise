# Router Agent Design

## Purpose

Replace OpenClaw routing with a controlled LangGraph router.

## Routing Layers

1. Rule-based routing
2. Embedding-based intent matching
3. LLM fallback classifier
4. Mixed route synthesizer

## Routes

SQL route:
- ETC
- EAC
- GM
- margin
- forecast
- revenue
- invoice
- cost
- hours
- actuals
- backlog

RAG route:
- SOW
- contract
- clause
- acceptance
- obligation
- deliverable

Summary route:
- MBR
- weekly summary
- executive summary

Mixed route example:
"Why did July revenue move and what does the SOW say?"

Flow:
```text
Router
→ SQL Agent: July revenue movement
→ RAG Agent: SOW acceptance terms
→ Synthesizer
```
