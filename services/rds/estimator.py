from decimal import Decimal

def estimate(payload, pricing_index=None):
    """
    RDS Estimation.
    """
    instance_type = payload.get('instanceType')
    database_engine = payload.get('databaseEngine')
    deployment_option = payload.get('deploymentOption', 'Single-AZ') # or Multi-AZ
    location = payload.get('location')
    hours = payload.get('hours', 730)
    
    unit_price = 0.0
    
    if pricing_index:
        result = pricing_index.find_price({
            "instanceType": instance_type,
            "databaseEngine": database_engine,
            "location": location,
            "deploymentOption": deployment_option
        })
        if result:
            unit_price = result.get('price', 0.0)
            
    total_cost = Decimal(unit_price) * Decimal(hours)
    
    return {
        "service": "rds",
        "total_cost": float(total_cost),
        "breakdown": {
            "compute_cost": float(total_cost),
            "unit_price": unit_price
        }
    }
