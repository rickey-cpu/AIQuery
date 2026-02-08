import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

import asyncio
import httpx
from config import load_config_from_env

# Load config to ensure env vars are set
load_config_from_env()

BASE_URL = "http://localhost:8000/api"
AGENT_ID = "test-agent-edit-delete"

async def test_flow():
    async with httpx.AsyncClient(timeout=10.0) as client:
        print(f"Testing with Agent ID: {AGENT_ID}")
        
        # 0. Create Agent (if not exists, or just ensure we can use this ID)
        # We don't strictly need to create the agent in DB for semantic layer to work 
        # as per current implementation (it just uses agent_id string), 
        # but let's assume valid agent_id is passed.
        
        # 1. Create Entity
        print("\n[1] Creating Entity 'TestUser'...")
        ent_payload = {
            "name": "TestUser",
            "table_name": "users",
            "primary_key": "id",
            "description": "A user of the system.",
            "synonyms": ["Client"]
        }
        res = await client.post(f"{BASE_URL}/agents/{AGENT_ID}/semantic/entities", json=ent_payload)
        print(f"Result: {res.status_code} {res.text}")
        if res.status_code != 200:
            print("[FAIL] Failed to create entity")
            return

        # 2. Update Entity (PUT)
        print("\n[2] Updating Entity 'TestUser' (description and synonyms)...")
        ent_payload["description"] = "A registered user of the platform."
        ent_payload["synonyms"] = ["Client", "Member"]
        
        res = await client.put(f"{BASE_URL}/agents/{AGENT_ID}/semantic/entities", json=ent_payload)
        print(f"Result: {res.status_code} {res.text}")
        if res.status_code != 200:
            print("[FAIL] Failed to update entity")
            return

        # 3. Verify Update (Get List)
        print("\n[3] Verifying Update...")
        res = await client.get(f"{BASE_URL}/agents/{AGENT_ID}/semantic/entities")
        entities = res.json()
        target = next((e for e in entities if e["name"] == "TestUser"), None)
        if target:
            print(f"Found: {target}")
            if "Member" in target["synonyms"] and "registered" in target["description"]:
                 print("[OK] Update verified!")
            else:
                 print("[FAIL] Update content mismatch")
        else:
            print("[FAIL] Entity not found after update")

        # 4. Delete Entity
        print("\n[4] Deleting Entity 'TestUser'...")
        res = await client.delete(f"{BASE_URL}/agents/{AGENT_ID}/semantic/entities/TestUser")
        print(f"Result: {res.status_code} {res.text}")
        if res.status_code != 200:
             print("[FAIL] Failed to delete entity")
             return

        # 5. Verify Deletion
        print("\n[5] Verifying Deletion...")
        res = await client.get(f"{BASE_URL}/agents/{AGENT_ID}/semantic/entities")
        entities = res.json()
        target = next((e for e in entities if e["name"] == "TestUser"), None)
        if not target:
            print("[OK] Deletion verified! Entity is gone.")
        else:
            print("[FAIL] Entity still exists after deletion.")

if __name__ == "__main__":
    asyncio.run(test_flow())
