from decimal import Decimal

def estimate(payload, pricing_index=None):
    """
    Estimates EC2 cost.
    Payload: {
        "instanceType": "t3.micro",
        "location": "US East (N. Virginia)",
        "operatingSystem": "Linux",
        "hours": 730,
        "count": 1
    }
    """
    instance_type = payload.get('instanceType')
    location = payload.get('location')
    operating_system = payload.get('operatingSystem', 'Linux')
    hours = payload.get('hours', 730)
    count = payload.get('count', 1)
    
    # In a real system, we use the pricing_index to look up the price.
    # For now, we'll assume pricing_index provides a lookup method 
    # OR we'll mock the lookup if the index isn't fully implemented yet.
    
    unit_price = 0.0
    
    if pricing_index:
        # Proposed interface for pricing_index
        # pricing_index.find_price(filters={...})
        result = pricing_index.find_price({
            "instanceType": instance_type,
            "location": location,
            "operatingSystem": operating_system
        })
        if result:
            unit_price = result.get('price', 0.0)
    else:
        # Fallback for testing without index
        # (This shouldn't happen in prod, but for robustness)
        unit_price = 0.0

    total_cost = Decimal(unit_price) * Decimal(hours) * Decimal(count)
    
    return {
        "service": "ec2",
        "total_cost": float(total_cost),
        "breakdown": {
            "unit_price": unit_price,
            "hours": hours,
            "count": count
        }
    }
