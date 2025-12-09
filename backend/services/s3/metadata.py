from services.s3.pricing_index import PricingIndex

def extract_metadata(normalized_data=None):
    """
    Extracts S3 metadata.
    """
    index = PricingIndex()
    
    return {
        "storageClasses": index.get_available_values("storageClass"),
        "locations": index.get_available_values("location"),
        # Add other filters deemed necessary for UI
        "volumeTypes": index.get_available_values("volumeType")
    }
