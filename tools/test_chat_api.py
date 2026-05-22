import requests
import json

url = "http://localhost:8000/api/chat"
payload = {
    "query": "What are the deliverables or milestones defined in the contract for BOSTON-001?",
    "session_id": "test-session",
    "project_id": "70c52032-82d6-4b1a-8cd6-81f96dfbc41a"
}
headers = {
    "Content-Type": "application/json"
}

try:
    response = requests.post(url, json=payload, headers=headers)
    print("Status Code:", response.status_code)
    print("Response JSON:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print("Error calling API:", e)
