# Implementation Plan: Persist RAID Items from Chat Request

This plan outlines the changes needed to support adding RAID (Risk, Assumption, Issue, Dependency) items directly from the Chat Console into the SQLite `RAIDitems` database table.

## User Review Required

> [!NOTE]
> - A new agent tool `create_raid_tool` will be introduced to extract RAID item details from the user's query and insert/queue them.
> - If the active agent does not require human approval (e.g. `contract_sow_agent`), it will insert the RAID item directly into the `RAIDitems` table.
> - If the agent requires human approval (e.g. `raid_recommendation_agent`), it will create a pending `RaidItemCreation` request in `HumanApprovalQueue` which will write to the database upon approval.

## Proposed Changes

---

### Component: Backend Services

#### [MODIFY] [raid_service.py](file:///home/joseph/ProjectAgentEnterprise/backend/app/services/raid_service.py)
- Update `create_raid_item` function signature to accept `roam: str = ""`.
- Update the SQL insert statement in `create_raid_item` to include the `ROAM` column.

#### [MODIFY] [approval_service.py](file:///home/joseph/ProjectAgentEnterprise/backend/app/services/approval_service.py)
- Update `resolve_approval` to support `approval_type == "RaidItemCreation"`.
- Retrieve the proposed payload, parse it, and call `create_raid_item` to persist the approved RAID item in the database.

---

### Component: Agent Framework

#### [MODIFY] [generic_agent_runner.py](file:///home/joseph/ProjectAgentEnterprise/backend/app/agents/generic_agent_runner.py)
- Define a new tool `_tool_create_raid` that uses the LLM to extract RAID item parameters (type, category, description, mitigating action, due date, status, roam, impact area, financial impact, schedule impact days) from the user query.
- Register `create_raid_tool` in the `TOOL_REGISTRY`.
- Update the tool execution loop in `GenericAgentRunner.run` to dynamically pass `query`, `agent_id`, and `requires_approval` to any tool functions that accept them.

#### [MODIFY] [router.py](file:///home/joseph/ProjectAgentEnterprise/backend/app/graph/router.py)
- Add keywords to `RULE_KEYWORDS` for `raid_recommendation_agent` to catch explicit write intents:
  - `"add a raid"`, `"add raid"`, `"create raid"`, `"new raid"`, `"add risk"`, `"add issue"`, `"add dependency"`, `"add assumption"`, `"create dependency"`, `"create assumption"`

---

### Component: Database Migrations and Seeding

#### [MODIFY] [002_agent_platform_tables.sql](file:///home/joseph/ProjectAgentEnterprise/backend/migrations/002_agent_platform_tables.sql)
- Add `create_raid_tool` to the tools lists for `contract_sow_agent` and `raid_recommendation_agent` in the seed data.
- Update `TriggerKeyword` seeds to include the new RAID creation keywords.

#### [NEW] [apply_raid_write_updates.py](file:///home/joseph/ProjectAgentEnterprise/backend/migrations/apply_raid_write_updates.py)
- Write a one-time migration runner script to update `AgentConfig` and `TriggerKeyword` in the existing `data/openclaw.db` database file.

---

## Verification Plan

### Automated Tests
- Run backend verification scripts or a python test script to simulate a chat message and verify database insertion.

### Manual Verification
1. Open the Chat Console and query:
   `Add a raid item for boston project - risk of delay in project kick off and onboarding. The reason is the SOW is not signed by customer. The customer has indicated there will be delay of two weeks to issue the signed PO`
2. Verify that the system routes properly and logs the creation or proposal in the backend.
3. Check the `RAIDitems` table in SQLite to ensure the new row exists and has all correct attributes populated.
4. If routed to an agent requiring approval, verify the item appears in the **Approval Center**, and then authorize it and verify it populates `RAIDitems`.
