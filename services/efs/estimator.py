from decimal import Decimal

def estimate(payload, pricing_index=None):
    storage_gb = payload.get('storageGB', 0)
    storage_class = payload.get('storageClass', 'Standard')
    location = payload.get('location')
    
    unit_price = 0.30 # Fallback
    
    if pricing_index:
        result = pricing_index.find_price({
            "storageClass": storage_class,
            "location": location
        })
        if result:
            unit_price = result.get('price', 0.30)
            
    total_cost = Decimal(unit_price) * Decimal(storage_gb)
    
    return {
        "service": "efs",
        "total_cost": float(total_cost),
        "breakdown": {
            "storage_cost": float(total_cost),
            "unit_price": unit_price
        }
    }
