from decimal import Decimal

def estimate(payload, pricing_index=None):
    """
    S3 Estimation.
    Payload: { "storageGB": 100, "storageClass": "General Purpose", "location": "..." }
    """
    storage_gb = payload.get('storageGB', 0)
    storage_class = payload.get('storageClass', 'General Purpose')
    location = payload.get('location')
    
    unit_price = 0.023 # Fallback
    tiers = []
    
    if pricing_index:
        result = pricing_index.find_price({
            "productFamily": "Storage",
            "storageClass": storage_class,
            "location": location
        })
        if result:
            # Check for tiers structure in attributes or result
            # Expected format in result: 'tiers': [{'limit': X, 'price': Y}, ...]
            # Current DB only has 'price'.
            if 'tiers' in result:
                tiers = result['tiers']
            else:
                unit_price = result.get('price', 0.023)
                tiers = [{"limit": None, "price": unit_price}]
        else:
             tiers = [{"limit": None, "price": unit_price}]
    else:
         tiers = [{"limit": None, "price": unit_price}]
            
    # Calculate using helper
    from backend.app.core.pricing_utils import calculate_tiered_cost
    total_cost = calculate_tiered_cost(storage_gb, tiers)
    
    return {
        "service": "s3",
        "total_cost": float(total_cost),
        "breakdown": {
            "storage_cost": float(total_cost),
            "unit_price": unit_price, # Representative price logic could be complex for tiers
            "tiers_used": tiers
        }
    }
