"""
Unit tests for pricing version state management.
Validates state transitions and single active version constraint.
"""
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.pricing.version_manager import (
    PricingVersionManager,
    VersionStatus,
    VersionTransitionError,
    ValidationIncompleteError,
    MultipleActiveVersionsError
)
from app.models.models import PricingVersion, PricingDimension


class TestVersionLifecycle:
    """Test version state machine."""
    
    def test_create_draft_version(self, db_session):
        """Test creating a DRAFT version."""
        manager = PricingVersionManager(db_session)
        
        version = manager.create_draft_version("2024-01-01", "AWS Bulk API")
        
        assert version.status == VersionStatus.DRAFT
        assert version.is_active is False
        assert version.validated_at is None
        assert version.activated_at is None
    
    def test_validate_draft_version(self, db_session):
        """Test validating a DRAFT version."""
        manager = PricingVersionManager(db_session)
        
        # Create draft
        version = manager.create_draft_version("2024-01-01", "AWS")
        
        # Add pricing dimensions
        for i in range(150):
            dimension = PricingDimension(
                version_id=version.id,
                service_code="AmazonEC2",
                region_code="us-east-1",
                sku=f"SKU{i}",
                price_per_unit=1.0,
                unit="Hrs",
                currency="USD",
                attributes={}
            )
            db_session.add(dimension)
        db_session.commit()
        
        # Validate
        validated = manager.validate_version(version.id, "system")
        
        assert validated.status == VersionStatus.VALIDATED
        assert validated.validated_at is not None
        assert validated.validated_by == "system"
        assert validated.validation_errors is None
    
    def test_validate_insufficient_dimensions_fails(self, db_session):
        """Test validation fails with insufficient dimensions."""
        manager = PricingVersionManager(db_session)
        
        version = manager.create_draft_version("2024-01-01", "AWS")
        
        # Add only 50 dimensions (less than minimum 100)
        for i in range(50):
            dimension = PricingDimension(
                version_id=version.id,
                service_code="AmazonEC2",
                region_code="us-east-1",
                sku=f"SKU{i}",
                price_per_unit=1.0,
                unit="Hrs",
                currency="USD",
                attributes={}
            )
            db_session.add(dimension)
        db_session.commit()
        
        with pytest.raises(ValidationIncompleteError, match="Insufficient pricing dimensions"):
            manager.validate_version(version.id, "system")
        
        # Check errors were recorded
        db_session.refresh(version)
        assert version.validation_errors is not None
    
    def test_validate_non_draft_fails(self, db_session):
        """Test cannot validate non-DRAFT version."""
        manager = PricingVersionManager(db_session)
        
        version = manager.create_draft_version("2024-01-01", "AWS")
        version.status = VersionStatus.VALIDATED
        db_session.commit()
        
        with pytest.raises(VersionTransitionError, match="Must be DRAFT"):
            manager.validate_version(version.id, "system")
    
    def test_activate_validated_version(self, db_session):
        """Test activating a VALIDATED version."""
        manager = PricingVersionManager(db_session)
        
        # Create and validate version
        version = manager.create_draft_version("2024-01-01", "AWS")
        
        # Add dimensions
        for i in range(150):
            db_session.add(PricingDimension(
                version_id=version.id,
                service_code="AmazonEC2",
                region_code="us-east-1",
                sku=f"SKU{i}",
                price_per_unit=1.0,
                unit="Hrs",
                currency="USD",
                attributes={}
            ))
        db_session.commit()
        
        validated = manager.validate_version(version.id, "system")
        
        # Activate
        active = manager.activate_version(validated.id, "admin")
        
        assert active.status == VersionStatus.ACTIVE
        assert active.is_active is True
        assert active.activated_at is not None
        assert active.activated_by == "admin"
    
    def test_activate_draft_without_force_fails(self, db_session):
        """Test cannot activate DRAFT without force."""
        manager = PricingVersionManager(db_session)
        
        version = manager.create_draft_version("2024-01-01", "AWS")
        
        with pytest.raises(ValidationIncompleteError, match="Must validate first"):
            manager.activate_version(version.id, "admin", force=False)
    
    def test_activate_draft_with_force(self, db_session):
        """Test can activate DRAFT with force=True."""
        manager = PricingVersionManager(db_session)
        
        version = manager.create_draft_version("2024-01-01", "AWS")
        
        active = manager.activate_version(version.id, "admin", force=True)
        
        assert active.status == VersionStatus.ACTIVE
        assert active.validated_at is not None  # Auto-validated
        assert active.validation_errors is not None  # Warning recorded
    
    def test_activate_archives_previous_active(self, db_session):
        """Test activating new version archives previous active."""
        manager = PricingVersionManager(db_session)
        
        # Create and activate first version
        v1 = manager.create_draft_version("2024-01-01", "AWS")
        manager.activate_version(v1.id, "admin", force=True)
        
        # Create and activate second version
        v2 = manager.create_draft_version("2024-01-02", "AWS")
        manager.activate_version(v2.id, "admin", force=True)
        
        # Check v1 is archived
        db_session.refresh(v1)
        assert v1.status == VersionStatus.ARCHIVED
        assert v1.archived_at is not None
        
        # Check v2 is active
        assert v2.status == VersionStatus.ACTIVE
    
    def test_only_one_active_version_allowed(self, db_session):
        """Test database constraint prevents multiple active versions."""
        manager = PricingVersionManager(db_session)
        
        # Create and activate first version
        v1 = manager.create_draft_version("2024-01-01", "AWS")
        manager.activate_version(v1.id, "admin", force=True)
        
        # Try to manually set another version as active (bypass manager)
        v2 = manager.create_draft_version("2024-01-02", "AWS")
        v2.status = VersionStatus.ACTIVE
        v2.is_active = True
        
        # This should fail due to unique constraint
        with pytest.raises(IntegrityError):
            db_session.commit()
        
        db_session.rollback()
    
    def test_archive_version(self, db_session):
        """Test archiving a version."""
        manager = PricingVersionManager(db_session)
        
        version = manager.create_draft_version("2024-01-01", "AWS")
        
        archived = manager.archive_version(version.id, "admin")
        
        assert archived.status == VersionStatus.ARCHIVED
        assert archived.archived_at is not None
        assert archived.archived_by == "admin"
    
    def test_cannot_archive_active_version(self, db_session):
        """Test cannot archive ACTIVE version directly."""
        manager = PricingVersionManager(db_session)
        
        version = manager.create_draft_version("2024-01-01", "AWS")
        manager.activate_version(version.id, "admin", force=True)
        
        with pytest.raises(VersionTransitionError, match="Cannot archive ACTIVE"):
            manager.archive_version(version.id, "admin")
    
    def test_get_active_version(self, db_session):
        """Test getting active version."""
        manager = PricingVersionManager(db_session)
        
        # No active version initially
        assert manager.get_active_version() is None
        
        # Create and activate version
        version = manager.create_draft_version("2024-01-01", "AWS")
        manager.activate_version(version.id, "admin", force=True)
        
        # Get active version
        active = manager.get_active_version()
        assert active is not None
        assert active.id == version.id
        assert active.status == VersionStatus.ACTIVE
    
    def test_get_version_by_status(self, db_session):
        """Test getting versions by status."""
        manager = PricingVersionManager(db_session)
        
        # Create versions in different states
        v1 = manager.create_draft_version("2024-01-01", "AWS")
        v2 = manager.create_draft_version("2024-01-02", "AWS")
        manager.activate_version(v2.id, "admin", force=True)
        v3 = manager.create_draft_version("2024-01-03", "AWS")
        
        # Get drafts
        drafts = manager.get_version_by_status(VersionStatus.DRAFT)
        assert len(drafts) == 2
        
        # Get active
        active = manager.get_version_by_status(VersionStatus.ACTIVE)
        assert len(active) == 1
        assert active[0].id == v2.id
    
    def test_version_history(self, db_session):
        """Test getting version history."""
        manager = PricingVersionManager(db_session)
        
        # Create multiple versions
        for i in range(5):
            v = manager.create_draft_version(f"2024-01-0{i+1}", "AWS")
            if i == 2:
                manager.activate_version(v.id, "admin", force=True)
        
        history = manager.get_version_history(limit=10)
        
        assert len(history) == 5
        assert all("status" in h for h in history)
        assert all("created_at" in h for h in history)


# Fixtures for testing
@pytest.fixture
def db_session():
    """Create test database session."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.models import Base
    
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session
    
    session.close()
