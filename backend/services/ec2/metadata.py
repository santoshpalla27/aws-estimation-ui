try:
    from services.ec2.pricing_index import PricingIndex
except ImportError:
    from backend.services.ec2.pricing_index import PricingIndex

def extract_metadata(normalized_data=None):
    """
    Extracts EC2 metadata such as instance types and regions (locations)
    from the pricing database.
    """
    index = PricingIndex()
    
    return {
        "instanceTypes": index.get_available_values("instanceType"),
        "instanceTypeDetails": index.get_instance_type_details(),
        "storagePrices": index.get_all_storage_prices(),
        "locations": index.get_available_values("location"),
        "operatingSystems": index.get_available_values("operatingSystem")
    }
