import os
import sys
import time
import requests
import json

BASE_URL = "http://localhost:8000/api"

# Ingestion files location in WSL
DOCS_DIR = "/home/joseph/ProjectAgentEnterprise/data/docs/projects/202021"
contract_path = os.path.join(DOCS_DIR, "Boston_Property_SMAX_Migration_SOW_v0.4.docx")
estimation_path = os.path.join(DOCS_DIR, "Boston Property SMAX Implementation - estimations with milestones.xlsx")
erp_path = os.path.join(DOCS_DIR, "Boston property Project Data - ERP.xlsx")

def run_test(use_json=False):
    results = {
        "passed": True,
        "steps": [],
        "routing_tests": []
    }
    
    def log_step(name, status, details):
        results["steps"].append({
            "name": name,
            "status": "passed" if status else "failed",
            "details": details
        })
        if not status:
            results["passed"] = False
            
    # --- Step 1: Create and Ingest ---
    if not use_json:
        print("=== Step 1: Creating and Ingesting project INTEG-TEST-999 ===")
    
    if not os.path.exists(contract_path) or not os.path.exists(estimation_path):
        err = f"Ingestion files do not exist at {DOCS_DIR}."
        if not use_json:
            print(f"Error: {err}")
        log_step("Project Creation & Ingestion", False, err)
        return results

    data = {
        "project_name": "Integration Test Project",
        "project_code": "INTEG-TEST-999",
        "opportunity_id": "O-1932849"
    }

    try:
        files = {
            "contract_file": open(contract_path, "rb"),
            "estimation_file": open(estimation_path, "rb"),
            "project_file": open(erp_path, "rb")
        }
        res = requests.post(f"{BASE_URL}/projects", data=data, files=files)
        # Close file handles
        for f in files.values():
            f.close()
    except Exception as e:
        if not use_json:
            print("Failed to contact FastAPI server:", e)
        log_step("Project Creation & Ingestion", False, f"Server contact failed: {e}")
        return results

    if not use_json:
        print("Creation response:", res.status_code)
        
    if res.status_code != 201:
        err_msg = f"Failed to create project (HTTP {res.status_code}): {res.text}"
        if not use_json:
            print(err_msg)
        log_step("Project Creation & Ingestion", False, err_msg)
        return results

    project_id = res.json()["project_id"]
    log_step("Project Creation & Ingestion", True, f"Project created successfully with ID: {project_id}")

    # --- Step 2: Poll Ingestion Status ---
    if not use_json:
        print("\n=== Step 2: Polling Ingestion Status ===")
    status = "processing"
    elapsed = 0
    while status == "processing" and elapsed < 120:
        time.sleep(3)
        elapsed += 3
        try:
            proj_res = requests.get(f"{BASE_URL}/projects/{project_id}")
            if proj_res.status_code == 200:
                proj_data = proj_res.json()
                status = proj_data.get("vectorization_status", "idle")
                if not use_json:
                    print(f"[{elapsed}s] Vectorization status: {status}")
            else:
                if not use_json:
                    print(f"Error fetching status: {proj_res.status_code}")
                status = "error"
        except Exception as e:
            if not use_json:
                print(f"Error polling: {e}")
            status = "error"

    if status != "completed":
        log_step("Ingestion Polling", False, f"Ingestion finished with non-complete status: {status}")
    else:
        log_step("Ingestion Polling", True, "Ingestion pipeline finished successfully!")

    # Let the DB settle for a brief moment
    time.sleep(2)

    # --- Step 3: Verify KuzuDB ---
    if not use_json:
        print("\n=== Step 3: Verifying KuzuDB Status ===")
    try:
        kuzu_res = requests.get(f"{BASE_URL}/projects/kuzudb/status")
        kuzu_data = kuzu_res.json()
        if not use_json:
            print("KuzuDB Status:", json.dumps(kuzu_data, indent=2))
        log_step("KuzuDB Status Check", kuzu_res.status_code == 200, kuzu_data)
    except Exception as e:
        if not use_json:
            print(f"Failed to check KuzuDB: {e}")
        log_step("KuzuDB Status Check", False, str(e))

    # --- Step 4: Chat Routing ---
    if not use_json:
        print("\n=== Step 4: Executing Chat Routing Tests ===")
    
    queries = [
        {
            "type": "SQL (Structured)",
            "query": "What are the milestones and their amounts defined for this project?",
            "expected_agent": "sql_agent",
            "avoid_agent": "contract_sow_agent"
        },
        {
            "type": "SQL (Structured)",
            "query": "List the resource roles and their total hours allocated.",
            "expected_agent": "sql_agent",
            "avoid_agent": "contract_sow_agent"
        },
        {
            "type": "RAG (Unstructured)",
            "query": "What is the key business driver or scope background mentioned in the SOW?",
            "expected_agent": "contract_sow_agent",
            "avoid_agent": "sql_agent"
        },
        {
            "type": "RAG (Unstructured)",
            "query": "What are the project exclusions or assumptions defined in the contract?",
            "expected_agent": "contract_sow_agent",
            "avoid_agent": "sql_agent"
        },
        {
            "type": "General / Fallback",
            "query": "Explain the general difference between a Project Manager (PM) and a Delivery Manager (DM).",
            "expected_agent": "general_agent",
            "avoid_agent": None
        }
    ]

    all_routing_passed = True
    for q in queries:
        if not use_json:
            print("-" * 60)
            print(f"Query Type: {q['type']}")
            print(f"Query: \"{q['query']}\"")
        
        chat_payload = {
            "query": q["query"],
            "session_id": f"test-session-{project_id}",
            "project_id": project_id
        }
        
        try:
            chat_res = requests.post(f"{BASE_URL}/chat", json=chat_payload)
            if chat_res.status_code == 200:
                chat_data = chat_res.json()
                ans = chat_data["response"]
                route = chat_data["route"]
                agents_used = chat_data["agents_used"]
                
                if not use_json:
                    print(f"Answer snippet: {ans[:250]}...")
                    print(f"Route Selected: {route}")
                    print(f"Agents Used: {agents_used}")
                
                # Validation logic
                passed = True
                if q["expected_agent"] and q["expected_agent"] not in agents_used:
                    passed = False
                if q["avoid_agent"] and q["avoid_agent"] in agents_used:
                    passed = False
                
                if not passed:
                    all_routing_passed = False
                    
                if not use_json:
                    print("✅ Validation: PASS" if passed else "❌ Validation: FAIL (Incorrect routing)")
                
                results["routing_tests"].append({
                    "query": q["query"],
                    "type": q["type"],
                    "expected_agent": q["expected_agent"],
                    "avoid_agent": q["avoid_agent"],
                    "route_selected": route,
                    "agents_used": agents_used,
                    "passed": passed,
                    "answer_snippet": ans[:200]
                })
            else:
                if not use_json:
                    print(f"Error calling Chat API: {chat_res.status_code}")
                all_routing_passed = False
                results["routing_tests"].append({
                    "query": q["query"],
                    "type": q["type"],
                    "passed": False,
                    "error": f"HTTP {chat_res.status_code}: {chat_res.text}"
                })
        except Exception as e:
            if not use_json:
                print(f"Exception during chat call: {e}")
            all_routing_passed = False
            results["routing_tests"].append({
                "query": q["query"],
                "type": q["type"],
                "passed": False,
                "error": str(e)
            })

    log_step("Chat Routing Verification", all_routing_passed, f"Routing check: {'PASS' if all_routing_passed else 'FAIL'}")

    # --- Step 5: Teardown ---
    if not use_json:
        print("\n=== Step 5: Cleaning up test project (Teardown) ===")
    try:
        del_res = requests.delete(f"{BASE_URL}/projects/{project_id}")
        if not use_json:
            print("Delete response:", del_res.status_code, del_res.json())
        log_step("Project Teardown", del_res.status_code == 200, del_res.json())
    except Exception as e:
        if not use_json:
            print("Teardown failed:", e)
        log_step("Project Teardown", False, str(e))

    # Double check KuzuDB status after deletion
    try:
        kuzu_post_del = requests.get(f"{BASE_URL}/projects/kuzudb/status")
        if not use_json:
            print("KuzuDB Post-Delete Status:", json.dumps(kuzu_post_del.json(), indent=2))
    except Exception:
        pass

    return results

if __name__ == "__main__":
    use_json = "--json" in sys.argv
    res = run_test(use_json=use_json)
    if use_json:
        print(json.dumps(res, indent=2))
    
    # Exit with code based on overall success
    sys.exit(0 if res["passed"] else 1)
