"""
Pricing version state management.
Enforces strict state transitions and single active version constraint.
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.models.models import PricingVersion, PricingDimension

logger = logging.getLogger(__name__)


class VersionStatus(str, Enum):
    """Pricing version lifecycle states."""
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class VersionTransitionError(Exception):
    """Raised when version state transition is invalid."""
    pass


class ValidationIncompleteError(Exception):
    """Raised when attempting to activate unvalidated version."""
    pass


class MultipleActiveVersionsError(Exception):
    """Raised when database constraint is violated (should never happen)."""
    pass


class PricingVersionManager:
    """
    Manages pricing version lifecycle with atomic state transitions.
    
    State Machine:
        DRAFT → VALIDATED → ACTIVE → ARCHIVED
    
    Rules:
    - Only one ACTIVE version allowed (enforced by DB constraint)
    - Activation requires validation
    - All transitions are atomic
    - State changes are audited
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_draft_version(self, version_name: str, source: str) -> PricingVersion:
        """
        Create a new DRAFT pricing version.
        
        Args:
            version_name: Version identifier
            source: Data source (e.g., "AWS Bulk API")
        
        Returns:
            New DRAFT version
        """
        version = PricingVersion(
            version=version_name,
            source=source,
            status=VersionStatus.DRAFT,
            is_active=False
        )
        
        self.db.add(version)
        self.db.commit()
        self.db.refresh(version)
        
        logger.info(f"Created DRAFT version {version.id}: {version_name}")
        return version
    
    def validate_version(
        self,
        version_id: int,
        validated_by: str,
        min_dimensions: int = 100
    ) -> PricingVersion:
        """
        Validate a DRAFT version and transition to VALIDATED.
        
        Validation checks:
        - Version is in DRAFT state
        - Has minimum number of pricing dimensions
        - No critical errors in data
        
        Args:
            version_id: Version to validate
            validated_by: User/system performing validation
            min_dimensions: Minimum required pricing dimensions
        
        Returns:
            VALIDATED version
        
        Raises:
            VersionTransitionError: If version is not in DRAFT state
            ValidationIncompleteError: If validation checks fail
        """
        version = self._get_version(version_id)
        
        # Check current state
        if version.status != VersionStatus.DRAFT:
            raise VersionTransitionError(
                f"Cannot validate version {version_id} in state {version.status}. "
                f"Must be DRAFT."
            )
        
        # Perform validation checks
        errors = []
        
        # Check dimension count
        dimension_count = self.db.execute(
            select(func.count(PricingDimension.id))
            .where(PricingDimension.version_id == version_id)
        ).scalar()
        
        if dimension_count < min_dimensions:
            errors.append(
                f"Insufficient pricing dimensions: {dimension_count} < {min_dimensions}"
            )
        
        # Check for required services
        service_count = self.db.execute(
            select(func.count(func.distinct(PricingDimension.service_code)))
            .where(PricingDimension.version_id == version_id)
        ).scalar()
        
        if service_count == 0:
            errors.append("No services found in pricing data")
        
        # If validation failed, update version with errors
        if errors:
            version.validation_errors = {"errors": errors}
            self.db.commit()
            
            raise ValidationIncompleteError(
                f"Version {version_id} validation failed: {'; '.join(errors)}"
            )
        
        # Transition to VALIDATED
        version.status = VersionStatus.VALIDATED
        version.validated_at = datetime.utcnow()
        version.validated_by = validated_by
        version.validation_errors = None
        
        self.db.commit()
        self.db.refresh(version)
        
        logger.info(
            f"Validated version {version_id} with {dimension_count} dimensions, "
            f"{service_count} services"
        )
        return version
    
    def activate_version(
        self,
        version_id: int,
        activated_by: str,
        force: bool = False
    ) -> PricingVersion:
        """
        Activate a VALIDATED version atomically.
        
        This is the CRITICAL operation that ensures exactly one active version.
        
        Process:
        1. Verify version is VALIDATED (or force from DRAFT)
        2. Archive current ACTIVE version (if exists)
        3. Activate new version
        4. All in single transaction (atomic)
        
        Args:
            version_id: Version to activate
            activated_by: User/system performing activation
            force: Allow activation of DRAFT version (dangerous!)
        
        Returns:
            ACTIVE version
        
        Raises:
            VersionTransitionError: If version state is invalid
            ValidationIncompleteError: If version not validated and force=False
            MultipleActiveVersionsError: If DB constraint violated
        """
        version = self._get_version(version_id)
        
        # Check current state
        if version.status == VersionStatus.ACTIVE:
            logger.warning(f"Version {version_id} is already ACTIVE")
            return version
        
        if version.status == VersionStatus.ARCHIVED:
            raise VersionTransitionError(
                f"Cannot activate ARCHIVED version {version_id}"
            )
        
        if version.status == VersionStatus.DRAFT and not force:
            raise ValidationIncompleteError(
                f"Cannot activate DRAFT version {version_id}. "
                f"Must validate first or use force=True"
            )
        
        # ATOMIC TRANSACTION: Archive old + Activate new
        try:
            # Find current active version
            current_active = self.db.execute(
                select(PricingVersion)
                .where(PricingVersion.status == VersionStatus.ACTIVE)
            ).scalar_one_or_none()
            
            # Archive current active version
            if current_active:
                logger.info(f"Archiving current active version {current_active.id}")
                current_active.status = VersionStatus.ARCHIVED
                current_active.archived_at = datetime.utcnow()
                current_active.archived_by = activated_by
            
            # Activate new version
            version.status = VersionStatus.ACTIVE
            version.activated_at = datetime.utcnow()
            version.activated_by = activated_by
            
            # If forcing from DRAFT, mark as validated
            if version.validated_at is None:
                version.validated_at = datetime.utcnow()
                version.validated_by = activated_by
                version.validation_errors = {"warning": "Activated without validation"}
            
            # Commit transaction
            self.db.commit()
            self.db.refresh(version)
            
            logger.info(f"Activated version {version_id}")
            return version
        
        except IntegrityError as e:
            self.db.rollback()
            
            # This should never happen due to our logic, but check anyway
            if "idx_pricing_versions_single_active" in str(e):
                raise MultipleActiveVersionsError(
                    f"Database constraint violation: multiple ACTIVE versions detected. "
                    f"This indicates a critical bug."
                )
            raise
    
    def archive_version(self, version_id: int, archived_by: str) -> PricingVersion:
        """
        Archive a version.
        
        Args:
            version_id: Version to archive
            archived_by: User/system performing archival
        
        Returns:
            ARCHIVED version
        
        Raises:
            VersionTransitionError: If version is ACTIVE
        """
        version = self._get_version(version_id)
        
        # Cannot archive ACTIVE version directly
        if version.status == VersionStatus.ACTIVE:
            raise VersionTransitionError(
                f"Cannot archive ACTIVE version {version_id}. "
                f"Activate another version first."
            )
        
        if version.status == VersionStatus.ARCHIVED:
            logger.warning(f"Version {version_id} is already ARCHIVED")
            return version
        
        version.status = VersionStatus.ARCHIVED
        version.archived_at = datetime.utcnow()
        version.archived_by = archived_by
        
        self.db.commit()
        self.db.refresh(version)
        
        logger.info(f"Archived version {version_id}")
        return version
    
    def get_active_version(self) -> Optional[PricingVersion]:
        """
        Get the current ACTIVE pricing version.
        
        This is the ONLY version that should be used for cost calculations.
        
        Returns:
            Active version or None if no active version exists
        """
        version = self.db.execute(
            select(PricingVersion)
            .where(PricingVersion.status == VersionStatus.ACTIVE)
        ).scalar_one_or_none()
        
        if version:
            logger.debug(f"Active version: {version.id} ({version.version})")
        else:
            logger.warning("No active pricing version found")
        
        return version
    
    def get_version_by_status(self, status: VersionStatus) -> List[PricingVersion]:
        """
        Get all versions with given status.
        
        Args:
            status: Status to filter by
        
        Returns:
            List of versions
        """
        versions = self.db.execute(
            select(PricingVersion)
            .where(PricingVersion.status == status)
            .order_by(PricingVersion.created_at.desc())
        ).scalars().all()
        
        return list(versions)
    
    def get_version_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get version history with state transitions.
        
        Args:
            limit: Maximum versions to return
        
        Returns:
            List of version summaries
        """
        versions = self.db.execute(
            select(PricingVersion)
            .order_by(PricingVersion.created_at.desc())
            .limit(limit)
        ).scalars().all()
        
        history = []
        for v in versions:
            history.append({
                "id": v.id,
                "version": v.version,
                "status": v.status,
                "created_at": v.created_at.isoformat() if v.created_at else None,
                "validated_at": v.validated_at.isoformat() if v.validated_at else None,
                "activated_at": v.activated_at.isoformat() if v.activated_at else None,
                "archived_at": v.archived_at.isoformat() if v.archived_at else None,
                "source": v.source
            })
        
        return history
    
    def _get_version(self, version_id: int) -> PricingVersion:
        """
        Get version by ID.
        
        Args:
            version_id: Version ID
        
        Returns:
            Version
        
        Raises:
            ValueError: If version not found
        """
        version = self.db.execute(
            select(PricingVersion)
            .where(PricingVersion.id == version_id)
        ).scalar_one_or_none()
        
        if not version:
            raise ValueError(f"Version {version_id} not found")
        
        return version
