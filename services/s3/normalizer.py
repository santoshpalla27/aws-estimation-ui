import json
import logging

logger = logging.getLogger(__name__)

def normalize(raw_file, output_file):
    logger.info(f"S3: Normalizing {raw_file}...")
    
    normalized_data = { "products": [] }
    
    try:
        with open(raw_file, 'r') as f:
            raw = json.load(f)
            
        products = raw.get('products', {})
        terms = raw.get('terms', {})
        on_demand_terms = terms.get('OnDemand', {})
        
        for sku, product in products.items():
            attr = product.get('attributes', {})
            if attr.get('servicecode') != 'AmazonS3':
                continue
            
            # Extract relevant S3 attributes
            # We care about storage, requests, data transfer
            
            family = attr.get('productFamily')
            
            # Price
            price = 0.0
            term = on_demand_terms.get(sku)
            if term:
                term_key = list(term.keys())[0]
                price_dimensions = term[term_key].get('priceDimensions', {})
                if price_dimensions:
                    pd_key = list(price_dimensions.keys())[0]
                    price_str = price_dimensions[pd_key].get('pricePerUnit', {}).get('USD', '0')
                    price = float(price_str)
            
            normalized_item = {
                "sku": sku,
                "productFamily": family,
                "storageClass": attr.get('storageClass'),
                "location": attr.get('location'),
                "volumeType": attr.get('volumeType'),
                "price": price
            }
            
            normalized_data["products"].append(normalized_item)
            
        with open(output_file, 'w') as f:
            json.dump(normalized_data, f, indent=2)
            
        logger.info(f"S3: Normalization complete.")
        
    except Exception as e:
        logger.error(f"S3: Normalization failed: {e}")
