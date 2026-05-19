# SQL Learning Layer Design

## Purpose

Preserve the previous behavior where the agent reuses successful SQL patterns from short-term and long-term memory.

## Flow

```text
User Query
→ Normalize query
→ Resolve context from short-term memory
→ Apply SemanticMap
→ Search SqlQueryMemory / QueryFeedback
→ If high confidence, reuse SQL template
→ Fill parameters
→ Validate SQL safety
→ Execute
→ Record success/failure
```

## Short-term Memory

Stored in LangGraph state:
- project_id
- project_number
- plan_version_id
- reporting_month
- last_route
- last_sql_intent
- last_sql_result

## Long-term Memory

Stored in DB:
- QueryFeedback
- SemanticMap
- SqlQueryMemory

## SQL Safety Rules

- SELECT only from chat.
- No DELETE, UPDATE, INSERT, DROP, ALTER from chat.
- Writes go through approved service methods.
- Parameter binding mandatory.
- Reject raw string interpolation.
