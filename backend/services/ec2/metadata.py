def extract_metadata(normalized_data):
    """
    Extracts EC2 metadata such as instance types types and regions (locations)
    from the normalized data.
    """
    products = normalized_data.get('products', [])
    
    instance_types = set()
    locations = set()
    operating_systems = set()
    
    for p in products:
        if p.get('instanceType'):
            instance_types.add(p['instanceType'])
        if p.get('location'):
            locations.add(p['location'])
        if p.get('operatingSystem'):
            operating_systems.add(p['operatingSystem'])
            
    return {
        "instanceTypes": sorted(list(instance_types)),
        "locations": sorted(list(locations)),
        "operatingSystems": sorted(list(operating_systems))
    }
