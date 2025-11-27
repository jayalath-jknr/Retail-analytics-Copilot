"""SQLite database access and schema introspection for Northwind."""
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Dict, Optional


@dataclass
class QueryResult:
    """Result of a SQL query execution."""
    success: bool
    columns: List[str]
    rows: List[tuple]
    error: Optional[str] = None
    tables_used: List[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "success": self.success,
            "columns": self.columns,
            "rows": self.rows,
            "error": self.error,
            "row_count": len(self.rows) if self.rows else 0
        }


class NorthwindDB:
    """SQLite interface for Northwind database."""
    
    def __init__(self, db_path: str = "data/northwind.sqlite"):
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {self.db_path}")
        
        self.schema_cache = None
        self._load_schema()
    
    def _load_schema(self):
        """Load and cache database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' 
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            schema = {}
            for table in tables:
                # Handle table names with spaces
                table_name = f'"{table}"' if ' ' in table else table
                try:
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    schema[table] = [
                        {
                            "name": col[1],
                            "type": col[2],
                            "notnull": col[3],
                            "pk": col[5]
                        }
                        for col in columns
                    ]
                except Exception as e:
                    print(f"Warning: Could not load schema for {table}: {e}")
            
            self.schema_cache = schema
    
    def get_schema_description(self) -> str:
        """Get a human-readable schema description."""
        if not self.schema_cache:
            return "No schema available."
        
        lines = ["# Northwind Database Schema\n"]
        
        # Key tables first
        key_tables = ["Orders", "Order Details", "Products", "Customers", "Categories"]
        other_tables = [t for t in self.schema_cache.keys() if t not in key_tables]
        
        for table in key_tables + other_tables:
            if table not in self.schema_cache:
                continue
            
            cols = self.schema_cache[table]
            lines.append(f"\n## {table}")
            for col in cols:
                pk_marker = " [PK]" if col["pk"] else ""
                lines.append(f"  - {col['name']}: {col['type']}{pk_marker}")
        
        return "\n".join(lines)
    
    def get_compact_schema(self) -> str:
        """Get a compact schema for prompts."""
        if not self.schema_cache:
            return ""
        
        lines = []
        key_tables = ["Orders", "Order Details", "Products", "Customers", "Categories"]
        
        for table in key_tables:
            if table not in self.schema_cache:
                continue
            cols = self.schema_cache[table]
            col_names = [c["name"] for c in cols]
            lines.append(f"{table}({', '.join(col_names)})")
        
        return "\n".join(lines)
    
    def execute_query(self, sql: str) -> QueryResult:
        """Execute a SQL query and return structured result."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                
                # Get column names
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                
                # Fetch all rows
                rows = cursor.fetchall()
                
                # Extract table names used (simple heuristic)
                tables_used = self._extract_tables_from_sql(sql)
                
                return QueryResult(
                    success=True,
                    columns=columns,
                    rows=rows,
                    tables_used=tables_used
                )
        
        except Exception as e:
            return QueryResult(
                success=False,
                columns=[],
                rows=[],
                error=str(e),
                tables_used=[]
            )
    
    def _extract_tables_from_sql(self, sql: str) -> List[str]:
        """Extract table names from SQL query (simple regex-based)."""
        import re
        
        # Normalize SQL
        sql_upper = sql.upper()
        
        tables = []
        if not self.schema_cache:
            return tables
        
        # Check for each known table in the SQL
        for table in self.schema_cache.keys():
            # Look for table name with word boundaries
            pattern = r'\b' + re.escape(table.upper()) + r'\b'
            if re.search(pattern, sql_upper):
                tables.append(table)
        
        return sorted(set(tables))
    
    def test_connection(self) -> bool:
        """Test database connection."""
        try:
            result = self.execute_query("SELECT 1")
            return result.success
        except:
            return False


def create_lowercase_views(db_path: str = "data/northwind.sqlite"):
    """Create lowercase compatibility views for easier querying."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            views = [
                'CREATE VIEW IF NOT EXISTS orders AS SELECT * FROM Orders',
                'CREATE VIEW IF NOT EXISTS order_items AS SELECT * FROM [Order Details]',
                'CREATE VIEW IF NOT EXISTS products AS SELECT * FROM Products',
                'CREATE VIEW IF NOT EXISTS customers AS SELECT * FROM Customers',
                'CREATE VIEW IF NOT EXISTS categories AS SELECT * FROM Categories'
            ]
            
            for view_sql in views:
                try:
                    cursor.execute(view_sql)
                except Exception as e:
                    print(f"Warning creating view: {e}")
            
            conn.commit()
    except Exception as e:
        print(f"Warning: Could not create views: {e}")


def test_db():
    """Test database connectivity and schema."""
    db = NorthwindDB()
    
    print("Schema loaded successfully!")
    print(f"Tables found: {len(db.schema_cache)}")
    print("\nCompact Schema:")
    print(db.get_compact_schema())
    
    print("\n" + "="*50)
    print("Test Query: Count orders")
    result = db.execute_query("SELECT COUNT(*) as order_count FROM Orders")
    
    if result.success:
        print(f"Columns: {result.columns}")
        print(f"Rows: {result.rows}")
        print(f"Tables used: {result.tables_used}")
    else:
        print(f"Error: {result.error}")


if __name__ == "__main__":
    # Create views first
    create_lowercase_views()
    test_db()
