from services.rds.pricing_index import PricingIndex

def extract_metadata(normalized_data=None):
    """
    Extracts RDS metadata.
    """
    index = PricingIndex()
    
    return {
        "instanceTypes": index.get_available_values("instanceType"),
        "databaseEngines": index.get_available_values("databaseEngine"),
        "databaseEditions": index.get_available_values("databaseEdition"),
        "deploymentOptions": index.get_available_values("deploymentOption"),
        "locations": index.get_available_values("location")
    }
