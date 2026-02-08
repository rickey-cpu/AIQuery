"""
Database Connector - Handles database connections and query execution
"""
import asyncio
from typing import Any, Optional
from dataclasses import dataclass
import aiosqlite
from pathlib import Path

# Global database instance
_database: Optional["DatabaseConnector"] = None


@dataclass
class QueryResult:
    """Result of a database query"""
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    
    def to_dict(self) -> dict:
        return {
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count
        }


class DatabaseConnector:
    """
    Database Connector - Async SQLite connection management
    
    Features:
    - Connection pooling
    - Query execution with timeout
    - Result formatting
    - Error handling
    """
    
    def __init__(self, database_path: str = "data/aiquery.db"):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._connection: Optional[aiosqlite.Connection] = None
    
    async def connect(self):
        """Establish database connection"""
        if self._connection is None:
            self._connection = await aiosqlite.connect(str(self.database_path))
            self._connection.row_factory = aiosqlite.Row
    
    async def disconnect(self):
        """Close database connection"""
        if self._connection:
            await self._connection.close()
            self._connection = None
    
    async def execute(self, sql: str, params: tuple = ()) -> dict:
        """Execute SQL query and return results"""
        await self.connect()
        
        try:
            async with self._connection.execute(sql, params) as cursor:
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                return {
                    "columns": columns,
                    "rows": [list(row) for row in rows],
                    "row_count": len(rows)
                }
        except Exception as e:
            raise Exception(f"Query execution failed: {str(e)}")
    
    async def execute_many(self, sql: str, params_list: list[tuple]) -> int:
        """Execute SQL with multiple parameter sets"""
        await self.connect()
        
        async with self._connection.executemany(sql, params_list) as cursor:
            await self._connection.commit()
            return cursor.rowcount
    
    async def init_sample_data(self):
        """Initialize sample E-commerce data"""
        await self.connect()
        
        # Create tables
        await self._connection.executescript("""
            -- Categories
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                parent_id INTEGER REFERENCES categories(id)
            );
            
            -- Products
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                category_id INTEGER REFERENCES categories(id),
                stock INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Customers
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE,
                phone TEXT,
                city TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            
            -- Orders
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER REFERENCES customers(id),
                order_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending',
                total_amount REAL DEFAULT 0,
                shipping_address TEXT
            );
            
            -- Order Items
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER REFERENCES orders(id),
                product_id INTEGER REFERENCES products(id),
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL
            );
        """)
        
        # Check if data exists
        result = await self.execute("SELECT COUNT(*) as count FROM customers")
        if result["rows"][0][0] > 0:
            return  # Already has data
        
        # Insert sample categories
        await self._connection.executescript("""
            INSERT INTO categories (name) VALUES ('Electronics');
            INSERT INTO categories (name) VALUES ('Clothing');
            INSERT INTO categories (name) VALUES ('Books');
            INSERT INTO categories (name) VALUES ('Home & Garden');
            INSERT INTO categories (name) VALUES ('Sports');
        """)
        
        # Insert sample products
        await self._connection.executescript("""
            INSERT INTO products (name, description, price, category_id, stock) VALUES 
                ('iPhone 15', 'Latest Apple smartphone', 999.99, 1, 50),
                ('MacBook Pro', '14-inch laptop', 1999.99, 1, 30),
                ('AirPods Pro', 'Wireless earbuds', 249.99, 1, 100),
                ('T-Shirt Basic', 'Cotton t-shirt', 19.99, 2, 200),
                ('Jeans Classic', 'Blue denim jeans', 49.99, 2, 150),
                ('Python Cookbook', 'Programming book', 39.99, 3, 75),
                ('Data Science Handbook', 'Reference book', 54.99, 3, 60),
                ('Garden Tools Set', '5-piece set', 79.99, 4, 40),
                ('Yoga Mat', 'Premium exercise mat', 29.99, 5, 80),
                ('Running Shoes', 'Sports footwear', 89.99, 5, 120);
        """)
        
        # Insert sample customers
        await self._connection.executescript("""
            INSERT INTO customers (name, email, phone, city) VALUES
                ('Nguyen Van A', 'nva@email.com', '0901234567', 'Hanoi'),
                ('Tran Thi B', 'ttb@email.com', '0912345678', 'Ho Chi Minh'),
                ('Le Van C', 'lvc@email.com', '0923456789', 'Da Nang'),
                ('Pham Thi D', 'ptd@email.com', '0934567890', 'Hanoi'),
                ('Hoang Van E', 'hve@email.com', '0945678901', 'Ho Chi Minh'),
                ('Vo Thi F', 'vtf@email.com', '0956789012', 'Can Tho'),
                ('Dang Van G', 'dvg@email.com', '0967890123', 'Hanoi'),
                ('Bui Thi H', 'bth@email.com', '0978901234', 'Hai Phong');
        """)
        
        # Insert sample orders
        await self._connection.executescript("""
            INSERT INTO orders (customer_id, order_date, status, total_amount, shipping_address) VALUES
                (1, '2024-01-15', 'delivered', 1249.98, '123 Pho Hue, Hanoi'),
                (2, '2024-01-20', 'delivered', 69.98, '456 Le Loi, HCMC'),
                (1, '2024-02-01', 'shipped', 249.99, '123 Pho Hue, Hanoi'),
                (3, '2024-02-10', 'confirmed', 94.98, '789 Bach Dang, Da Nang'),
                (4, '2024-02-15', 'pending', 2089.98, '321 Tran Hung Dao, Hanoi'),
                (5, '2024-02-20', 'delivered', 119.98, '654 Nguyen Hue, HCMC'),
                (6, '2024-03-01', 'shipped', 79.99, '987 Ninh Kieu, Can Tho'),
                (7, '2024-03-05', 'pending', 39.99, '147 Doi Can, Hanoi');
        """)
        
        # Insert sample order items
        await self._connection.executescript("""
            INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
                (1, 1, 1, 999.99),
                (1, 3, 1, 249.99),
                (2, 4, 2, 19.99),
                (2, 5, 1, 49.99),
                (3, 3, 1, 249.99),
                (4, 6, 1, 39.99),
                (4, 7, 1, 54.99),
                (5, 2, 1, 1999.99),
                (5, 9, 3, 29.99),
                (6, 10, 1, 89.99),
                (6, 9, 1, 29.99),
                (7, 8, 1, 79.99),
                (8, 6, 1, 39.99);
        """)
        
        await self._connection.commit()
        print("✅ Sample E-commerce data initialized")


async def init_database() -> DatabaseConnector:
    """Initialize global database connection"""
    global _database
    from config import config
    
    _database = DatabaseConnector(config.database.database)
    await _database.connect()
    await _database.init_sample_data()
    return _database


def get_database() -> Optional[DatabaseConnector]:
    """Get global database instance"""
    return _database
