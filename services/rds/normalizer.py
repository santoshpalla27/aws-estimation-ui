import json
import logging

logger = logging.getLogger(__name__)

def normalize(raw_file, output_file):
    logger.info(f"RDS: Normalizing {raw_file}...")
    normalized_data = { "products": [] }
    
    try:
        with open(raw_file, 'r') as f:
            raw = json.load(f)
            
        products = raw.get('products', {})
        terms = raw.get('terms', {})
        on_demand_terms = terms.get('OnDemand', {})
        
        for sku, product in products.items():
            attr = product.get('attributes', {})
            if attr.get('servicecode') != 'AmazonRDS':
                continue
                
            if attr.get('productFamily') != 'Database Instance':
                continue
            
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
                "instanceType": attr.get('instanceType'),
                "databaseEngine": attr.get('databaseEngine'),
                "databaseEdition": attr.get('databaseEdition'),
                "deploymentOption": attr.get('deploymentOption'),
                "location": attr.get('location'),
                "price": price
            }
            normalized_data["products"].append(normalized_item)
            
        with open(output_file, 'w') as f:
            json.dump(normalized_data, f, indent=2)
            
        logger.info(f"RDS: Normalization complete.")
    except Exception as e:
        logger.error(f"RDS: Normalization failed: {e}")
