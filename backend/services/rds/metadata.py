def extract_metadata(normalized_data):
    products = normalized_data.get('products', [])
    instance_types = set()
    engines = set()
    locations = set()
    
    for p in products:
        if p.get('instanceType'):
            instance_types.add(p['instanceType'])
        if p.get('databaseEngine'):
            engines.add(p['databaseEngine'])
        if p.get('location'):
            locations.add(p['location'])
            
    return {
        "instanceTypes": sorted(list(instance_types)),
        "databaseEngines": sorted(list(engines)),
        "locations": sorted(list(locations))
    }
