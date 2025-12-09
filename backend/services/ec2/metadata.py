from services.ec2.pricing_index import PricingIndex

def extract_metadata(normalized_data=None):
    """
    Extracts EC2 metadata such as instance types and regions (locations)
    from the pricing database.
    """
    index = PricingIndex()
    
    return {
        "instanceTypes": index.get_available_values("instanceType"),
        "locations": index.get_available_values("location"),
        "operatingSystems": index.get_available_values("operatingSystem")
    }
