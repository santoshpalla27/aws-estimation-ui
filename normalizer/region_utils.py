import logging

# Standard AWS Location to Region Code Mapping
# Sourced from AWS Price List API documentation and standard mappings
LOCATION_TO_REGION = {
    "US East (N. Virginia)": "us-east-1",
    "US East (Ohio)": "us-east-2",
    "US West (N. California)": "us-west-1",
    "US West (Oregon)": "us-west-2",
    "Asia Pacific (Mumbai)": "ap-south-1",
    "Asia Pacific (Osaka)": "ap-northeast-3",
    "Asia Pacific (Seoul)": "ap-northeast-2",
    "Asia Pacific (Singapore)": "ap-southeast-1",
    "Asia Pacific (Sydney)": "ap-southeast-2",
    "Asia Pacific (Tokyo)": "ap-northeast-1",
    "Canada (Central)": "ca-central-1",
    "Europe (Frankfurt)": "eu-central-1",
    "Europe (Ireland)": "eu-west-1",
    "Europe (London)": "eu-west-2",
    "Europe (Paris)": "eu-west-3",
    "Europe (Stockholm)": "eu-north-1",
    "South America (Sao Paulo)": "sa-east-1",
    "Middle East (Bahrain)": "me-south-1",
    "Africa (Cape Town)": "af-south-1",
    "EU (Milan)": "eu-south-1",
    "Middle East (UAE)": "me-central-1",
    "Asia Pacific (Hong Kong)": "ap-east-1",
    "Asia Pacific (Hyderabad)": "ap-south-2",
    "Asia Pacific (Jakarta)": "ap-southeast-3",
    "Asia Pacific (Melbourne)": "ap-southeast-4",
    "Canada West (Calgary)": "ca-west-1",
    "Europe (Spain)": "eu-south-2",
    "Europe (Zurich)": "eu-central-2",
    "Israel (Tel Aviv)": "il-central-1",
    "US West (Los Angeles)": "us-west-2-lax-1", # Local Zone usually maps to parent region for pricing, but specific locations exist
    "Any": "global" # Global services
}

def resolve_region(attributes):
    """
    Derive the region code from attributes.
    1. Try 'regionCode'
    2. Try mapping 'location'
    3. Return None if failures
    """
    # 1. Direct Region Code (Most reliable)
    if 'regionCode' in attributes and attributes['regionCode']:
        return attributes['regionCode']
    
    # 2. Map Location
    if 'location' in attributes:
        loc = attributes['location']
        if loc in LOCATION_TO_REGION:
            return LOCATION_TO_REGION[loc]
            
    # 3. Special cases usually not needed if mapping is complete
    return None
