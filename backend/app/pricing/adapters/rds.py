"""
RDS pricing adapter.
Calculates costs for RDS database instances.
"""
from typing import Dict
from decimal import Decimal
import logging

from app.pricing.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class RDSAdapter(BaseAdapter):
    """RDS database instance pricing adapter."""
    
    def calculate_cost(self, resource: Dict) -> Dict:
        """
        Calculate monthly cost for an RDS instance.
        
        Args:
            resource: Normalized resource with attributes:
                - instance_class: RDS instance class (e.g., 'db.t3.micro')
                - engine: Database engine (mysql, postgres, etc.)
                - region: AWS region
                - deployment_option: Single-AZ or Multi-AZ
                - allocated_storage: Storage in GB
                - storage_type: Storage type (gp2, gp3, io1)
        
        Returns:
            Cost calculation result
        """
        warnings = []
        
        # Extract attributes
        instance_class = resource.get("instance_class")
        engine = resource.get("engine", "mysql")
        region = resource.get("region", "us-east-1")
        deployment_option = resource.get("deployment_option", "Single-AZ")
        allocated_storage = resource.get("allocated_storage", 20)
        storage_type = resource.get("storage_type", "gp2")
        
        if not instance_class:
            return self.format_cost_result(
                Decimal("0"),
                {"error": "Missing instance_class"},
                ["Missing instance_class attribute"]
            )
        
        # Map engine names
        engine_map = {
            "mysql": "MySQL",
            "postgres": "PostgreSQL",
            "mariadb": "MariaDB",
            "oracle-se2": "Oracle",
            "sqlserver-ex": "SQL Server"
        }
        database_engine = engine_map.get(engine, "MySQL")
        
        # Calculate instance cost
        instance_pricing = self.query_pricing(
            service_code="AmazonRDS",
            region_code=region,
            filters={
                "instanceType": instance_class,
                "databaseEngine": database_engine,
                "deploymentOption": deployment_option
            }
        )
        
        instance_cost = Decimal("0")
        if instance_pricing:
            price_per_hour = instance_pricing.price_per_unit
            instance_cost = price_per_hour * self.hours_per_month()
        else:
            warnings.append(f"No instance pricing found for {instance_class}")
        
        # Calculate storage cost
        storage_pricing = self.query_pricing(
            service_code="AmazonRDS",
            region_code=region,
            filters={
                "volumeType": storage_type.upper(),
                "databaseEngine": database_engine
            }
        )
        
        storage_cost = Decimal("0")
        if storage_pricing:
            price_per_gb_month = storage_pricing.price_per_unit
            storage_cost = price_per_gb_month * Decimal(str(allocated_storage))
        else:
            warnings.append(f"No storage pricing found for {storage_type}")
        
        # Total cost
        monthly_cost = instance_cost + storage_cost
        
        pricing_details = {
            "instance_class": instance_class,
            "engine": engine,
            "region": region,
            "deployment_option": deployment_option,
            "instance_cost": float(instance_cost),
            "storage_cost": float(storage_cost),
            "allocated_storage_gb": allocated_storage,
            "storage_type": storage_type
        }
        
        return self.format_cost_result(monthly_cost, pricing_details, warnings)
