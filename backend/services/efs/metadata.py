from services.efs.pricing_index import PricingIndex

def extract_metadata(normalized_data=None):
    """
    Extracts EFS metadata.
    """
    index = PricingIndex()
    
    return {
        "storageClasses": index.get_available_values("storageClass"),
        "locations": index.get_available_values("location")
    }
