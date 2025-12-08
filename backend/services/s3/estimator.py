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
    
    if pricing_index:
        result = pricing_index.find_price({
            "productFamily": "Storage",
            "storageClass": storage_class,
            "location": location
        })
        if result:
            unit_price = result.get('price', 0.023)
            
    total_cost = Decimal(unit_price) * Decimal(storage_gb)
    
    return {
        "service": "s3",
        "total_cost": float(total_cost),
        "breakdown": {
            "storage_cost": float(total_cost),
            "unit_price": unit_price
        }
    }
