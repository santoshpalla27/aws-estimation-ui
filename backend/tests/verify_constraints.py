"""
Verification script for pricing unique constraints.
Tests that duplicate SKUs are prevented by database constraints.
"""
import asyncio
import sys
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.database import get_async_session
from app.models.models import PricingVersion


async def verify_unique_constraints():
    """Verify that unique constraints prevent duplicate SKUs."""
    
    print("=" * 60)
    print("PRICING UNIQUE CONSTRAINT VERIFICATION")
    print("=" * 60)
    
    async with get_async_session() as db:
        # Create test pricing version
        version = PricingVersion(
            version="test_constraint_verification",
            source="test",
            status="DRAFT"
        )
        db.add(version)
        await db.commit()
        await db.refresh(version)
        
        print(f"\n✓ Created test version: {version.id}")
        
        # Test 1: EC2 unique constraint
        print("\n" + "-" * 60)
        print("TEST 1: EC2 Unique Constraint")
        print("-" * 60)
        
        try:
            # Insert first EC2 SKU
            await db.execute(text("""
                INSERT INTO pricing_ec2 
                (version_id, sku, instance_type, operating_system, tenancy, region, capacity_status, price_per_unit, unit)
                VALUES 
                (:version_id, 'TEST-SKU-1', 't3.micro', 'Linux', 'Shared', 'us-east-1', 'Used', 0.0104, 'Hrs')
            """), {"version_id": version.id})
            await db.commit()
            print("✓ First EC2 SKU inserted successfully")
            
            # Try to insert duplicate (should fail)
            try:
                await db.execute(text("""
                    INSERT INTO pricing_ec2 
                    (version_id, sku, instance_type, operating_system, tenancy, region, capacity_status, price_per_unit, unit)
                    VALUES 
                    (:version_id, 'TEST-SKU-2', 't3.micro', 'Linux', 'Shared', 'us-east-1', 'Used', 0.0104, 'Hrs')
                """), {"version_id": version.id})
                await db.commit()
                print("❌ FAIL: Duplicate EC2 SKU was allowed!")
                return False
            except IntegrityError as e:
                await db.rollback()
                if "uq_pricing_ec2_sku" in str(e):
                    print("✓ PASS: Duplicate EC2 SKU correctly rejected")
                else:
                    print(f"❌ FAIL: Wrong constraint violated: {e}")
                    return False
        
        except Exception as e:
            print(f"❌ ERROR: {e}")
            await db.rollback()
            return False
        
        # Test 2: RDS unique constraint
        print("\n" + "-" * 60)
        print("TEST 2: RDS Unique Constraint")
        print("-" * 60)
        
        try:
            await db.execute(text("""
                INSERT INTO pricing_rds 
                (version_id, sku, instance_class, engine, region, deployment_option, price_per_unit, unit)
                VALUES 
                (:version_id, 'TEST-RDS-1', 'db.t3.micro', 'mysql', 'us-east-1', 'Single-AZ', 0.017, 'Hrs')
            """), {"version_id": version.id})
            await db.commit()
            print("✓ First RDS SKU inserted successfully")
            
            try:
                await db.execute(text("""
                    INSERT INTO pricing_rds 
                    (version_id, sku, instance_class, engine, region, deployment_option, price_per_unit, unit)
                    VALUES 
                    (:version_id, 'TEST-RDS-2', 'db.t3.micro', 'mysql', 'us-east-1', 'Single-AZ', 0.017, 'Hrs')
                """), {"version_id": version.id})
                await db.commit()
                print("❌ FAIL: Duplicate RDS SKU was allowed!")
                return False
            except IntegrityError as e:
                await db.rollback()
                if "uq_pricing_rds_sku" in str(e):
                    print("✓ PASS: Duplicate RDS SKU correctly rejected")
                else:
                    print(f"❌ FAIL: Wrong constraint violated: {e}")
                    return False
        
        except Exception as e:
            print(f"❌ ERROR: {e}")
            await db.rollback()
            return False
        
        # Test 3: Single ACTIVE version constraint
        print("\n" + "-" * 60)
        print("TEST 3: Single ACTIVE Version Constraint")
        print("-" * 60)
        
        try:
            # Create first ACTIVE version
            version1 = PricingVersion(
                version="active_test_1",
                source="test",
                status="ACTIVE"
            )
            db.add(version1)
            await db.commit()
            print("✓ First ACTIVE version created")
            
            # Try to create second ACTIVE version (should fail)
            try:
                version2 = PricingVersion(
                    version="active_test_2",
                    source="test",
                    status="ACTIVE"
                )
                db.add(version2)
                await db.commit()
                print("❌ FAIL: Multiple ACTIVE versions allowed!")
                return False
            except IntegrityError as e:
                await db.rollback()
                if "idx_pricing_versions_single_active" in str(e):
                    print("✓ PASS: Multiple ACTIVE versions correctly rejected")
                else:
                    print(f"❌ FAIL: Wrong constraint violated: {e}")
                    return False
        
        except Exception as e:
            print(f"❌ ERROR: {e}")
            await db.rollback()
            return False
        
        # Cleanup
        print("\n" + "-" * 60)
        print("Cleaning up test data...")
        print("-" * 60)
        
        await db.execute(text("DELETE FROM pricing_ec2 WHERE version_id = :version_id"), {"version_id": version.id})
        await db.execute(text("DELETE FROM pricing_rds WHERE version_id = :version_id"), {"version_id": version.id})
        await db.execute(text("DELETE FROM pricing_versions WHERE version LIKE 'test%' OR version LIKE 'active_test%'"))
        await db.commit()
        print("✓ Test data cleaned up")
    
    print("\n" + "=" * 60)
    print("✓ ALL CONSTRAINTS VERIFIED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    result = asyncio.run(verify_unique_constraints())
    sys.exit(0 if result else 1)
