
import os
import sys
from fastapi.testclient import TestClient
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load env
load_dotenv()

# Set env to force MySQL usage for test
os.environ["AGENT_DB_TYPE"] = "mysql"
# Assuming other env vars are set in .env or system

def test_api():
    print("Testing API /agents locally...")
    
    try:
        from main import app
        # Trigger startup event manually if TestClient doesn't? 
        # TestClient runs lifespan events by default.
        
        with TestClient(app) as client:
            print("Client created. Sending request...")
            response = client.get("/api/agents")
            
            print(f"Status Code: {response.status_code}")
            if response.status_code == 200:
                print("Success!")
                print(f"Response: {response.json()}")
            else:
                print(f"Failed: {response.text}")
                
    except Exception as e:
        print(f"\nException during test:")
        print(f"{type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_api()
