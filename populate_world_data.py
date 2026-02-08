import asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from config import load_config_from_env
from models import init_agent_repository

# Load config
load_config_from_env()

AGENT_KEY = "world-explorer"
AGENT_NAME = "World Explorer"
AGENT_DB = "world" # Looking for a DB named 'world'

async def populate():
    # Ensure repo is initialized
    await init_agent_repository()
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        
        # 1. Create or Get Agent
        print(f"Checking for agent '{AGENT_NAME}'...")
        agents_res = await client.get("/api/agents")
        
        agent_id = None
        if agents_res.status_code == 200:
            agents = agents_res.json()
            for a in agents:
                if isinstance(a, dict) and a.get("name") == AGENT_NAME:
                    agent_id = a.get("id")
                    print(f"Found existing agent: {agent_id}")
                    break
        else:
            print(f"List agents failed: {agents_res.status_code}. Proceeding to create...")
        
        if not agent_id:
            print("Creating new agent...")
            create_res = await client.post("/api/agents", json={
                "name": AGENT_NAME,
                "description": "Expert on world geography, population, and economics.",
                "auto_route": True,
                "databases": [{
                    "name": "MySQL World DB",
                    "db_type": "mysql",
                    "host": "localhost",
                    "port": 3306,
                    "database": AGENT_DB,
                    "username": "ntquyen", # Example placeholder
                    "password": "12345678@Abc"      # Example placeholder
                }]
            })
            if create_res.status_code == 200:
                agent_id = create_res.json()["id"]
                print(f"Created agent: {agent_id}")
            else:
                print(f"Failed to create agent: {create_res.text}")
                return

        # 2. Define Entities
        entities = [
            {
                "name": "Country",
                "table_name": "country",
                "primary_key": "Code",
                "description": "Represents a nation or state. Contains data on population, GNP, government, and geography.",
                "synonyms": ["Nation", "State", "Republic", "Kingdom"]
            },
            {
                "name": "City",
                "table_name": "city",
                "primary_key": "ID",
                "description": "A city or town within a country. Contains population data.",
                "synonyms": ["Town", "Municipality", "Urban Area"]
            },
            {
                "name": "CountryLanguage",
                "table_name": "countrylanguage",
                "primary_key": "CountryCode,Language", # Composite PK
                "description": "Languages spoken in each country, including official status and percentage of speakers.",
                "synonyms": ["Language", "Dialect", "Tongue"]
            }
        ]

        # 3. Define Metrics
        metrics = [
            {
                "name": "TotalPopulation",
                "definition": "SUM(Population)",
                "description": "The total number of people.",
                "condition": None,
                "synonyms": ["Population", "Inhabitants", "Citizens"]
            },
            {
                "name": "TotalGNP",
                "definition": "SUM(GNP)",
                "description": "Total Gross National Product.",
                "condition": None,
                "synonyms": ["Gross National Product", "Economic Output"]
            },
            {
                "name": "AvgLifeExpectancy",
                "definition": "AVG(LifeExpectancy)",
                "description": "Average life expectancy in years.",
                "condition": "LifeExpectancy IS NOT NULL",
                "synonyms": ["Life Span", "Longevity"]
            },
            {
                "name": "CityCount",
                "definition": "COUNT(ID)",
                "description": "Total number of cities registered.",
                "condition": None,
                "synonyms": ["Number of Cities"]
            },
             {
                "name": "OfficialLanguageCount",
                "definition": "COUNT(*)",
                "description": "Number of official languages.",
                "condition": "IsOfficial = 'T'",
                "synonyms": ["Number of Official Languages"]
            }
        ]

        # 4. Add Entities using API
        print("\nAdding Entities...")
        for ent in entities:
            res = await client.post(f"/api/agents/{agent_id}/semantic/entities", json=ent)
            if res.status_code == 200:
                print(f" [x] Entity '{ent['name']}' added.")
            else:
                print(f" [!] Failed to add entity '{ent['name']}': {res.text}")

        # 5. Add Metrics using API
        print("\nAdding Metrics...")
        for met in metrics:
            res = await client.post(f"/api/agents/{agent_id}/semantic/metrics", json=met)
            if res.status_code == 200:
                print(f" [x] Metric '{met['name']}' added.")
            else:
                print(f" [!] Failed to add metric '{met['name']}': {res.text}")

        print(f"\n✅ Population complete for agent: {AGENT_NAME} ({agent_id})")

if __name__ == "__main__":
    asyncio.run(populate())
