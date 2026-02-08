"""
Agent Models - Multi-Database Agent System
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid
import json


@dataclass
class DatabaseSource:
    """
    A database source configuration for an agent.
    
    Each agent can have multiple database sources to query from.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""                           # Display name (e.g., "Sales DB")
    db_type: str = "sqlite"                  # sqlite, mysql, postgresql, sqlserver, elasticsearch, opensearch
    
    # Connection config (stored as dict for flexibility)
    host: str = "localhost"
    port: int = 0                            # 0 = use default for db_type
    database: str = ""
    username: str = ""
    password: str = ""
    
    # Type-specific options
    options: dict = field(default_factory=dict)
    
    # Metadata
    is_default: bool = False                 # Primary database for this agent
    description: str = ""
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "db_type": self.db_type,
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "password": "***" if self.password else "",  # Mask password
            "options": self.options,
            "is_default": self.is_default,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "DatabaseSource":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            db_type=data.get("db_type", "sqlite"),
            host=data.get("host", "localhost"),
            port=data.get("port", 0),
            database=data.get("database", ""),
            username=data.get("username", ""),
            password=data.get("password", ""),
            options=data.get("options", {}),
            is_default=data.get("is_default", False),
            description=data.get("description", "")
        )
    
    def get_default_port(self) -> int:
        """Get default port for database type"""
        ports = {
            "mysql": 3306,
            "postgresql": 5432,
            "sqlserver": 1433,
            "elasticsearch": 9200,
            "opensearch": 9200
        }
        return ports.get(self.db_type, 0)


@dataclass
class Agent:
    """
    Agent configuration with multiple database sources.
    
    Each agent represents a specialized query assistant that can
    access specific databases and has its own context.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    
    # Database sources
    databases: list[DatabaseSource] = field(default_factory=list)
    
    # Agent behavior settings
    default_database_id: Optional[str] = None
    auto_route: bool = True                  # Auto-select database based on query
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "databases": [db.to_dict() for db in self.databases],
            "default_database_id": self.default_database_id,
            "auto_route": self.auto_route,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_active": self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Agent":
        databases = [DatabaseSource.from_dict(db) for db in data.get("databases", [])]
        
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        else:
            created_at = datetime.now()
            
        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        else:
            updated_at = datetime.now()
        
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            databases=databases,
            default_database_id=data.get("default_database_id"),
            auto_route=data.get("auto_route", True),
            created_at=created_at,
            updated_at=updated_at,
            is_active=data.get("is_active", True)
        )
    
    def get_default_database(self) -> Optional[DatabaseSource]:
        """Get the default database source"""
        if self.default_database_id:
            for db in self.databases:
                if db.id == self.default_database_id:
                    return db
        
        # Fallback to first marked as default or first in list
        for db in self.databases:
            if db.is_default:
                return db
        
        return self.databases[0] if self.databases else None
    
    def get_database_by_id(self, db_id: str) -> Optional[DatabaseSource]:
        """Get database source by ID"""
        for db in self.databases:
            if db.id == db_id:
                return db
        return None
    
    def get_database_by_name(self, name: str) -> Optional[DatabaseSource]:
        """Get database source by name"""
        for db in self.databases:
            if db.name.lower() == name.lower():
                return db
        return None
    
    def add_database(self, db: DatabaseSource) -> None:
        """Add a database source"""
        self.databases.append(db)
        if len(self.databases) == 1:
            self.default_database_id = db.id
        self.updated_at = datetime.now()
    
    def remove_database(self, db_id: str) -> bool:
        """Remove a database source by ID"""
        for i, db in enumerate(self.databases):
            if db.id == db_id:
                self.databases.pop(i)
                if self.default_database_id == db_id:
                    self.default_database_id = self.databases[0].id if self.databases else None
                self.updated_at = datetime.now()
                return True
        return False
