import json
import logging

logger = logging.getLogger(__name__)

def normalize(raw_file, output_file):
    logger.info(f"EFS: Normalizing {raw_file}...")
    normalized_data = { "products": [] }
    
    try:
        with open(raw_file, 'r') as f:
            raw = json.load(f)
            
        products = raw.get('products', {})
        terms = raw.get('terms', {})
        on_demand_terms = terms.get('OnDemand', {})
        
        for sku, product in products.items():
            attr = product.get('attributes', {})
            if attr.get('servicecode') != 'AmazonEFS':
                continue
            
            # Focus on Storage
            if attr.get('productFamily') != 'Storage':
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
                "storageClass": attr.get('storageClass'),
                "location": attr.get('location'),
                "price": price
            }
            normalized_data["products"].append(normalized_item)
            
        with open(output_file, 'w') as f:
            json.dump(normalized_data, f, indent=2)
            
        logger.info(f"EFS: Normalization complete.")
    except Exception as e:
        logger.error(f"EFS: Normalization failed: {e}")
