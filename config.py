"""
AI Query Agent - Configuration Management v2
Enhanced with multi-database support
"""
import os
from dataclasses import dataclass, field
from typing import Literal, Optional
from pathlib import Path


@dataclass
class LLMConfig:
    """LLM Provider Configuration
    
    Supported Gemini models (2026) - from ai.google.dev:
    - gemini-3-pro-preview: Most intelligent, multimodal, agent model
    - gemini-3-flash-preview: Balanced speed/intelligence, scalable
    - gemini-2.5-pro: Advanced reasoning for code/math/STEM
    - gemini-2.5-flash: Best performance/price, large-scale processing
    - gemini-2.5-flash-lite: Lightweight version
    """
    provider: Literal["openai", "gemini", "ollama"] = "openai"
    model: str = "gpt-4"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 2000
    
    # Available models by provider (2026)
    GEMINI_MODELS = [
        "gemini-3-pro-preview",      # Most intelligent
        "gemini-3-flash-preview",    # Balanced speed/intelligence  
        "gemini-2.5-pro",            # Advanced reasoning (stable)
        "gemini-2.5-flash",          # Best performance/price (stable)
        "gemini-2.5-flash-lite",     # Lightweight
    ]
    OPENAI_MODELS = ["gpt-4o", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
    
    def __post_init__(self):
        if self.provider == "openai":
            self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")
        elif self.provider == "gemini":
            self.api_key = self.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            # Default to stable flash model if not specified
            if self.model == "gpt-4":
                self.model = "gemini-2.5-flash"  # Stable, best performance/price
        elif self.provider == "ollama":
            self.base_url = self.base_url or "http://localhost:11434"


@dataclass
class DatabaseConfig:
    """Database Configuration - Multi-database support"""
    type: Literal["sqlite", "postgresql", "mysql", "sqlserver", "elasticsearch", "opensearch"] = "sqlite"
    host: str = "localhost"
    port: int = 5432
    database: str = "aiquery.db"
    username: Optional[str] = None
    password: Optional[str] = None
    
    # SQL Server specific
    driver: str = "ODBC Driver 17 for SQL Server"
    
    # Elasticsearch specific
    use_ssl: bool = False
    verify_certs: bool = True
    
    def __post_init__(self):
        # Set default ports based on type
        default_ports = {
            "postgresql": 5432,
            "mysql": 3306,
            "sqlserver": 1433,
            "elasticsearch": 9200
        }
        if self.type in default_ports and self.port == 5432:
            self.port = default_ports[self.type]
    
    @property
    def connection_string(self) -> str:
        if self.type == "sqlite":
            return f"sqlite:///{self.database}"
        elif self.type == "postgresql":
            return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.type == "mysql":
            return f"mysql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.type == "sqlserver":
            return f"mssql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"
        elif self.type == "elasticsearch":
            protocol = "https" if self.use_ssl else "http"
            return f"{protocol}://{self.host}:{self.port}"
        return ""


@dataclass 
class ElasticsearchConfig:
    """Elasticsearch specific configuration"""
    hosts: list[str] = field(default_factory=lambda: ["http://localhost:9200"])
    username: str = ""
    password: str = ""
    use_ssl: bool = False
    verify_certs: bool = True
    use_opensearch: bool = False  # Set True for OpenSearch
    default_index: str = "*"


@dataclass
class OpenSearchConfig:
    """OpenSearch specific configuration"""
    hosts: list[str] = field(default_factory=lambda: ["http://localhost:9200"])
    username: str = ""
    password: str = ""
    use_ssl: bool = False
    verify_certs: bool = True
    default_index: str = "*"
    # AWS OpenSearch Service
    use_aws_auth: bool = False
    aws_region: str = ""
    aws_service: str = "es"  # 'es' or 'aoss' for Serverless
    timeout: int = 30


@dataclass
class VectorStoreConfig:
    """ChromaDB Vector Store Configuration"""
    persist_directory: str = "./data/chroma"
    collection_name: str = "sql_examples"
    embedding_model: str = "all-MiniLM-L6-v2"


@dataclass
class APIConfig:
    """API Server Configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    cors_origins: list = field(default_factory=lambda: ["*"])


@dataclass
class Config:
    """Main Configuration"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    elasticsearch: ElasticsearchConfig = field(default_factory=ElasticsearchConfig)
    opensearch: OpenSearchConfig = field(default_factory=OpenSearchConfig)
    vector_store: VectorStoreConfig = field(default_factory=VectorStoreConfig)
    api: APIConfig = field(default_factory=APIConfig)
    
    # Paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent)
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent / "data")
    
    def __post_init__(self):
        # Ensure data directory exists
        self.data_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
config = Config()


def load_config_from_env():
    """Load configuration from environment variables"""
    global config
    
    # LLM Config
    config.llm.provider = os.getenv("LLM_PROVIDER", config.llm.provider)
    config.llm.model = os.getenv("LLM_MODEL", config.llm.model)
    
    # Load API key based on provider
    if config.llm.provider == "gemini":
        config.llm.api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
    elif config.llm.provider == "openai":
        config.llm.api_key = os.getenv("OPENAI_API_KEY")
    
    # Database Config
    config.database.type = os.getenv("DB_TYPE", config.database.type)
    config.database.host = os.getenv("DB_HOST", config.database.host)
    config.database.port = int(os.getenv("DB_PORT", str(config.database.port)))
    config.database.database = os.getenv("DB_NAME", config.database.database)
    config.database.username = os.getenv("DB_USER", config.database.username)
    config.database.password = os.getenv("DB_PASSWORD", config.database.password)
    
    # SQL Server specific
    config.database.driver = os.getenv("DB_DRIVER", config.database.driver)
    
    # Elasticsearch Config
    es_hosts = os.getenv("ES_HOSTS")
    if es_hosts:
        config.elasticsearch.hosts = es_hosts.split(",")
    config.elasticsearch.username = os.getenv("ES_USER", config.elasticsearch.username)
    config.elasticsearch.password = os.getenv("ES_PASSWORD", config.elasticsearch.password)
    config.elasticsearch.use_opensearch = os.getenv("ES_USE_OPENSEARCH", "false").lower() == "true"
    
    # OpenSearch Config
    os_hosts = os.getenv("OS_HOSTS")
    if os_hosts:
        config.opensearch.hosts = os_hosts.split(",")
    config.opensearch.username = os.getenv("OS_USER", config.opensearch.username)
    config.opensearch.password = os.getenv("OS_PASSWORD", config.opensearch.password)
    config.opensearch.use_ssl = os.getenv("OS_USE_SSL", "false").lower() == "true"
    config.opensearch.verify_certs = os.getenv("OS_VERIFY_CERTS", "true").lower() == "true"
    config.opensearch.use_aws_auth = os.getenv("OS_USE_AWS_AUTH", "false").lower() == "true"
    config.opensearch.aws_region = os.getenv("OS_AWS_REGION", config.opensearch.aws_region)
    config.opensearch.aws_service = os.getenv("OS_AWS_SERVICE", config.opensearch.aws_service)
    
    return config


def get_database_connector():
    """Factory function to get appropriate database connector"""
    db_type = config.database.type
    
    if db_type == "sqlite":
        from database.connector import DatabaseConnector
        return DatabaseConnector(config.database.database)
    
    elif db_type == "mysql":
        from database.sources.mysql import MySQLConnector
        return MySQLConnector(
            host=config.database.host,
            port=config.database.port,
            database=config.database.database,
            user=config.database.username,
            password=config.database.password
        )
    
    elif db_type == "postgresql":
        from database.sources.postgresql import PostgreSQLConnector
        return PostgreSQLConnector(
            host=config.database.host,
            port=config.database.port,
            database=config.database.database,
            user=config.database.username,
            password=config.database.password
        )
    
    elif db_type == "sqlserver":
        from database.sources.sqlserver import SQLServerConnector
        return SQLServerConnector(
            host=config.database.host,
            port=config.database.port,
            database=config.database.database,
            user=config.database.username,
            password=config.database.password,
            driver=config.database.driver
        )
    
    elif db_type == "elasticsearch":
        from database.sources.elasticsearch import ElasticsearchConnector
        return ElasticsearchConnector(
            hosts=config.elasticsearch.hosts,
            username=config.elasticsearch.username,
            password=config.elasticsearch.password,
            use_ssl=config.elasticsearch.use_ssl,
            use_opensearch=config.elasticsearch.use_opensearch
        )
    
    elif db_type == "opensearch":
        from database.sources.opensearch import OpenSearchConnector
        return OpenSearchConnector(
            hosts=config.opensearch.hosts,
            username=config.opensearch.username,
            password=config.opensearch.password,
            use_ssl=config.opensearch.use_ssl,
            verify_certs=config.opensearch.verify_certs,
            use_aws_auth=config.opensearch.use_aws_auth,
            aws_region=config.opensearch.aws_region,
            aws_service=config.opensearch.aws_service,
            timeout=config.opensearch.timeout
        )
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

