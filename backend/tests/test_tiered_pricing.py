import pytest
from decimal import Decimal
from backend.app.core.pricing_utils import calculate_tiered_cost

def test_tiered_cost_single_tier():
    # 0.023 per GB, infinite
    tiers = [{"limit": None, "price": 0.023}]
    cost = calculate_tiered_cost(100, tiers)
    assert cost == Decimal('2.3000000000')

def test_tiered_cost_two_tiers_within_first():
    # First 50 GB at 0.023, Next at 0.022
    tiers = [
        {"limit": 50, "price": 0.023},
        {"limit": None, "price": 0.022}
    ]
    # Usage 40 GB -> All in tier 1
    cost = calculate_tiered_cost(40, tiers)
    assert cost == Decimal('0.9200000000') # 40 * 0.023

def test_tiered_cost_two_tiers_spanning():
    # First 50 GB at 0.023, Next at 0.022
    tiers = [
        {"limit": 50, "price": 0.023},
        {"limit": None, "price": 0.022}
    ]
    # Usage 60 GB -> 50 * 0.023 + 10 * 0.022
    # 1.15 + 0.22 = 1.37
    cost = calculate_tiered_cost(60, tiers)
    assert cost == Decimal('1.3700000000')

def test_tiered_cost_multiple_tiers():
    # T1: 10 @ 1.00
    # T2: 10 @ 0.50
    # T3: Inf @ 0.10
    tiers = [
        {"limit": 10, "price": 1.00},
        {"limit": 10, "price": 0.50},
        {"limit": None, "price": 0.10}
    ]
    
    # Usage 25 -> 10@1 + 10@0.5 + 5@0.1 = 10 + 5 + 0.5 = 15.5
    cost = calculate_tiered_cost(25, tiers)
    assert cost == Decimal('15.5000000000')

def test_zero_usage():
    tiers = [{"limit": None, "price": 1.0}]
    cost = calculate_tiered_cost(0, tiers)
    assert cost == Decimal('0.0000000000')
