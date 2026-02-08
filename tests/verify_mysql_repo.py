
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load env
load_dotenv()

async def verify():
    print("Verifying MySQL Agent Repository...")
    
    # Check env
    print(f"ENV: type={os.getenv('AGENT_DB_TYPE')}")
    print(f"ENV: host={os.getenv('AGENT_DB_HOST')}")
    print(f"ENV: user={os.getenv('AGENT_DB_USER')}")
    print(f"ENV: db={os.getenv('AGENT_DB_NAME')}")
    
    try:
        from models import init_agent_repository
        from models.agent import Agent
        
        # 1. Initialize (should create DB and tables)
        repo = await init_agent_repository()
        
        if not repo:
            print("Failed to initialize repository")
            return
            
        print("Repository initialized and connected")
        
        # 2. Create Test Agent
        test_agent = Agent(name="MySQL Test Agent", description="Created by verification script")
        created = await repo.create(test_agent)
        print(f"Created agent: {created.id} - {created.name}")
        
        # 3. List Agents
        agents = await repo.list_all()
        print(f"Listed {len(agents)} agents")
        found = next((a for a in agents if a.id == created.id), None)
        if found:
            print("Found created agent in list")
        else:
            print("Created agent not found in list")
            
        # 4. Clean up
        deleted = await repo.hard_delete(created.id)
        if deleted:
            print("Cleaned up (hard deleted) test agent")
        else:
            print("Failed to delete test agent")
            
        await repo.disconnect()
        print("Disconnected")
        
    except Exception as e:
        print(f"Error during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify())
