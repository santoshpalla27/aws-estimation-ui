def extract_metadata(normalized_data):
    products = normalized_data.get('products', [])
    storage_classes = set()
    locations = set()
    
    for p in products:
        if p.get('storageClass'):
            storage_classes.add(p['storageClass'])
        if p.get('location'):
            locations.add(p['location'])
            
    return {
        "storageClasses": sorted(list(storage_classes)),
        "locations": sorted(list(locations))
    }
