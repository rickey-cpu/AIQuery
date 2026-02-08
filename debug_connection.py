from opensearchpy import OpenSearch
import os

def test_conn():
    # Hardcoded credentials from .env for debugging
    hosts = ["https://localhost:9200"] # Explicit HTTPS
    auth = ("admin", "OpenSearch@2026")
    
    print(f"Connecting to {hosts}...")
    
    client = OpenSearch(
        hosts=hosts,
        http_auth=auth,
        use_ssl=True,
        verify_certs=False,
        ssl_show_warn=False
    )
    
    try:
        info = client.info()
        print("Success!")
        print(info)
        return True
    except Exception as e:
        print(f"Connection failed: {e}")
        return False

if __name__ == "__main__":
    current_hosts = os.getenv("OS_HOSTS", "localhost:9200")
    print(f"Current OS_HOSTS env: {current_hosts}")
    test_conn()
