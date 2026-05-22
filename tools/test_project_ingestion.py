import requests
import time
import json
import os

url = "http://localhost:8000/api/projects"

# Files to upload
contract_file_path = "/home/joseph/ProjectAgentEnterprise/data/docs/projects/202021/Boston_Property_SMAX_Migration_SOW_v0.4.docx"
estimation_file_path = "/home/joseph/ProjectAgentEnterprise/data/docs/projects/202021/Boston Property SMAX Implementation - estimations with milestones.xlsx"

# Prepare payload
data = {
    "project_name": "Boston Test Ingest Project",
    "project_code": "BOSTON-TEST-INGEST",
    "opportunity_id": "O-TEST-12345"
}

# Open files
files = {}
if os.path.exists(contract_file_path):
    files["contract_file"] = ("Boston_Property_SMAX_Migration_SOW_v0.4.docx", open(contract_file_path, "rb"), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
else:
    print("Contract file not found!")
    exit(1)

if os.path.exists(estimation_file_path):
    files["estimation_file"] = ("Boston Property SMAX Implementation - estimations with milestones.xlsx", open(estimation_file_path, "rb"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    print("Estimation file not found!")
    exit(1)

print("Sending POST request to create project...")
try:
    response = requests.post(url, data=data, files=files)
    print("Response Status Code:", response.status_code)
    
    if response.status_code != 201:
        print("Failed to create project:", response.text)
        exit(1)
        
    res_json = response.json()
    print("Response JSON:")
    print(json.dumps(res_json, indent=2))
    
    project_id = res_json["project_id"]
    print(f"\nProject created successfully with ID: {project_id}")
    
    # Poll project status
    status_url = f"http://localhost:8000/api/projects/{project_id}"
    print(f"Polling status endpoint {status_url}...")
    
    for i in range(20):
        time.sleep(2)
        status_res = requests.get(status_url)
        if status_res.status_code == 200:
            status_data = status_res.json()
            status = status_data.get("vectorization_status")
            error = status_data.get("vectorization_error")
            print(f"Poll #{i+1}: status={status}, error={error}")
            if status in ["completed", "failed"]:
                print(f"\nFinished polling. Vectorization status: {status}")
                if status == "failed":
                    print("Error details:", error)
                break
        else:
            print(f"Poll #{i+1}: HTTP error {status_res.status_code}")
            
except Exception as e:
    print("Error:", e)
finally:
    # Close files
    for key, val in files.items():
        val[1].close()
