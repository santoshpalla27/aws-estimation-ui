import logging
import os
try:
    from backend.app.core.pricing_index_base import BasePricingIndex
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    from backend.app.core.pricing_index_base import BasePricingIndex

logger = logging.getLogger(__name__)

class PricingIndex(BasePricingIndex):
    def __init__(self):
        super().__init__('ec2', allowed_filters=[
            'instanceType', 'vcpu', 'memory', 'operatingSystem', 'networkPerformance', 
        ])

    def get_instance_type_details(self):
        """
        Returns a list of dicts with instance type details:
        [{ "instanceType": "t3.micro", "vcpu": "2", "memory": "1 GiB", ... }]
        """
        if not os.path.exists(self.db_path):
             return []
             
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # We want unique combinations of specs for each instance type
            # Since an instance type might have different prices (regions), specs should be constant.
            query = """
                SELECT DISTINCT 
                    json_extract(attributes, '$.instanceType') as instanceType,
                    json_extract(attributes, '$.vcpu') as vcpu,
                    json_extract(attributes, '$.memory') as memory,
                    json_extract(attributes, '$.storage') as storage,
                    json_extract(attributes, '$.networkPerformance') as networkPerformance
                FROM pricing_ec2
                WHERE instanceType IS NOT NULL
                ORDER BY instanceType
            """
            cursor.execute(query)
            cols = ['instanceType', 'vcpu', 'memory', 'storage', 'networkPerformance']
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(cols, row)))
            return results
        except Exception as e:
            logger.error(f"Failed to get instance details: {e}")
            return []
        finally:
            conn.close()

    def get_all_storage_prices(self):
        """
        Returns EBS storage prices for all regions.
        { "US East (N. Virginia)": { "General Purpose": 0.08, ... } }
        """
        if not os.path.exists(self.db_path):
             return {}
             
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            query = """
                SELECT 
                    location,
                    json_extract(attributes, '$.volumeType') as volumeType,
                    price
                FROM pricing_ec2
                WHERE json_extract(attributes, '$.productFamily') = 'Storage'
                  AND json_extract(attributes, '$.usagetype') LIKE '%VolumeUsage%'
            """
            cursor.execute(query)
            
            results = {}
            for row in cursor.fetchall():
                loc = row[0]
                v_type = row[1]
                price = row[2]
                
                if loc and v_type:
                    if loc not in results:
                        results[loc] = {}
                    results[loc][v_type] = price
            return results
        except Exception as e:
            logger.error(f"Failed to get storage prices: {e}")
            return {}
        finally:
            conn.close()
