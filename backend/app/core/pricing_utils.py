from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Union

def calculate_tiered_cost(quantity: Union[str, float, int, Decimal], tiers: List[Dict]) -> Decimal:
    """
    Calculates cost based on tiered pricing.
    
    Args:
        quantity: The usage amount (e.g., GB).
        tiers: A list of dicts defining tiers.
               Format: [{"limit": <float|None>, "price": <float>}, ...]
               'limit' is the upper bound of usage for that tier (cumulative or incremental? Usually incremental usage within tier).
               
               Standard AWS format interpretation:
               Tier 1: 0 - 50 TB (limit 51200 GB)
               Tier 2: Next 450 TB (limit 460800 GB)
               Tier 3: Over 500 TB (limit None)
               
               We assume 'limit' is the amount of usage allowed IN THIS TIER (incremental).
               If 'limit' is None, it means infinite (last tier).
               
    Returns:
        Total cost as Decimal.
    """
    qty = Decimal(str(quantity))
    total_cost = Decimal('0.0')
    remaining_qty = qty
    
    # Ensure tiers are processed in order. 
    # We assume the list passed is already ordered (First tier, Next tier, ...).
    
    for tier in tiers:
        if remaining_qty <= 0:
            break
            
        limit = tier.get('limit')
        price = Decimal(str(tier.get('price', 0.0)))
        
        if limit is None:
            # Infinite tier
            tier_usage = remaining_qty
        else:
            tier_limit = Decimal(str(limit))
            tier_usage = min(remaining_qty, tier_limit)
            
        cost_for_tier = tier_usage * price
        total_cost += cost_for_tier
        
        remaining_qty -= tier_usage
        
    return total_cost.quantize(Decimal('0.0000000001')) # High precision return, round at UI layer if needed
