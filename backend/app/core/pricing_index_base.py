import json
import logging
import sqlite3
import os

logger = logging.getLogger(__name__)

class BasePricingIndex:
    """
    Base class for SQLite-backed Pricing Indexes.
    Provides robust SQL query building with pagination and filtering.
    """
    def __init__(self, service_name, allowed_filters: list):
        self.service_name = service_name
        self.table_name = f"pricing_{service_name}"
        self.allowed_filters = set(allowed_filters)
        self.db_path = self._get_db_path()
        
    def _get_db_path(self):
        try:
            from backend.app.core.paths import PRICING_DB
            return str(PRICING_DB)
        except ImportError:
            # Fallback for standardized structure
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
            return os.path.join(base_dir, 'data', 'pricing.db')

    def get_available_values(self, field: str) -> list:
        """
        Returns distinct values for a given field (column or JSON attribute).
        Useful for populating UI dropdowns.
        """
        if not os.path.exists(self.db_path):
             return []

        if field not in self.allowed_filters and field not in ['sku', 'price', 'location']:
             logger.warning(f"Field {field} not allowed for listing values")
             return []

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if field in ['sku', 'price', 'location']:
                query = f"SELECT DISTINCT {field} FROM {self.table_name} ORDER BY {field}"
            else:
                 query = f"SELECT DISTINCT json_extract(attributes, '$.{field}') FROM {self.table_name} ORDER BY 1"
            
            cursor.execute(query)
            return [row[0] for row in cursor.fetchall() if row[0] is not None]
            
        except Exception as e:
            logger.error(f"Failed to get values for {field}: {e}")
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def find_price(self, filters: dict):
        """Finds the first matching pricing record."""
        results, _ = self.query(filters, page=1, per_page=1)
        return results[0] if results else None

    def query(self, filters: dict, page: int = 1, per_page: int = 50, sort_by: str = None):
        """
        Queries the pricing database with pagination and filtering.
        
        Args:
            filters: Dictionary of filters. Keys must be in allowed_filters.
            page: Page number (1-based).
            per_page: Items per page.
            sort_by: Optional sort column (e.g. 'price desc').
            
        Returns:
            (items, total_count)
        """
        if not os.path.exists(self.db_path):
             logger.warning(f"{self.service_name} Pricing DB not found at {self.db_path}")
             return [], 0
             
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 1. Build WHERE Clause
            where_clauses = []
            params = []
            
            for key, value in filters.items():
                if key not in self.allowed_filters and key not in ['sku', 'location']:
                    logger.warning(f"Ignored unknown filter key: {key}")
                    continue
                
                # Check if it's a standard column or JSON attribute
                # We assume standard columns are 'sku', 'price', 'location'
                # All others are in 'attributes' JSON
                if key in ['sku', 'price', 'location']:
                    where_clauses.append(f"{key} = ?")
                else:
                    # SQLite JSON extraction for attributes
                    # optimization: json_extract(attributes, '$.key') = ?
                    where_clauses.append(f"json_extract(attributes, '$.{key}') = ?")
                
                params.append(value)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            
            # 2. Get Total Count
            count_sql = f"SELECT COUNT(*) FROM {self.table_name} WHERE {where_sql}"
            cursor.execute(count_sql, params)
            total = cursor.fetchone()[0]
            
            if total == 0:
                return [], 0
            
            # 3. Get Data with Pagination
            offset = (page - 1) * per_page
            
            # Sorting
            # Basic sanitization for sort_by to prevent SQLi
            order_sql = "ORDER BY price ASC" # Default
            if sort_by:
                # Expect "column asc" or "column desc"
                # Whitelist sortable columns + JSON fields
                parts = sort_by.lower().split()
                if len(parts) <= 2:
                    col = parts[0]
                    direction = parts[1] if len(parts) > 1 else 'asc'
                    if direction in ['asc', 'desc']:
                         if col in ['sku', 'price', 'location']:
                             order_sql = f"ORDER BY {col} {direction}"
                         elif col in self.allowed_filters:
                             order_sql = f"ORDER BY json_extract(attributes, '$.{col}') {direction}"

            data_sql = f"""
                SELECT sku, price, location, attributes 
                FROM {self.table_name} 
                WHERE {where_sql} 
                {order_sql}
                LIMIT ? OFFSET ?
            """
            cursor.execute(data_sql, params + [per_page, offset])
            
            items = []
            for row in cursor.fetchall():
                item = json.loads(row['attributes'])
                item['sku'] = row['sku']
                item['price'] = row['price']
                item['location'] = row['location']
                items.append(item)
                
            return items, total
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return [], 0
        finally:
            conn.close()
