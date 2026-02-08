
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load env
load_dotenv()

async def verify():
    print("Verifying Agent List (500 Error Reproduction)...")
    
    try:
        from models import init_agent_repository, get_agent_repository
        
        # Initialize repo (picks up MySQL from env)
        await init_agent_repository()
        repo = get_agent_repository()
        
        print(f"Repo type: {type(repo)}")
        
        print("\nAttempting to list agents...")
        agents = await repo.list_all(active_only=True)
        print(f"Successfully listed {len(agents)} agents")
        
        for a in agents:
            print(f" - Agent: {a.name}")
            print(f"   created_at type: {type(a.created_at)} Value: {a.created_at}")
            print(f"   updated_at type: {type(a.updated_at)} Value: {a.updated_at}")
            
            # Test serialization
            try:
                d = a.to_dict()
                print("   to_dict() success")
                # print(f"   Dict: {d}")
                
                from api.routes.agents import AgentResponse
                resp = AgentResponse(**d)
                print(f"   AgentResponse valid: {resp.id}")
            except Exception as e:
                print(f"   SERIALIZATION FAILED: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"\nError listing agents:")
        print(f"{type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify())
