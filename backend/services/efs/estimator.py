from decimal import Decimal

def estimate(payload, pricing_index=None):
    storage_gb = payload.get('storageGB', 0)
    storage_class = payload.get('storageClass', 'Standard')
    location = payload.get('location')
    
    unit_price = 0.30 # Fallback
    tiers = []
    
    if pricing_index:
        result = pricing_index.find_price({
            "storageClass": storage_class,
            "location": location
        })
        if result:
            if 'tiers' in result:
                tiers = result['tiers']
            else:
                unit_price = result.get('price', 0.30)
                tiers = [{"limit": None, "price": unit_price}]
        else:
            tiers = [{"limit": None, "price": unit_price}]
    else:
        tiers = [{"limit": None, "price": unit_price}]
            
    # Calculate using helper
    from backend.app.core.pricing_utils import calculate_tiered_cost
    total_cost = calculate_tiered_cost(storage_gb, tiers)
    
    return {
        "service": "efs",
        "total_cost": float(total_cost),
        "breakdown": {
            "storage_cost": float(total_cost),
            "unit_price": unit_price,
            "tiers_used": tiers
        }
    }
