"""
Pricing Database Models - Versioned pricing storage
"""

from sqlalchemy import Column, String, Numeric, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from core.database import Base


class PricingVersion(Base):
    """Pricing version table - tracks pricing data versions"""
    __tablename__ = "pricing_versions"
    __table_args__ = (
        Index('idx_pricing_versions_active', 'is_active'),
        {'extend_existing': True}  # Allow table redefinition
    )
    
    version = Column(String(20), primary_key=True)  # "2024-12"
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    source_type = Column(String(50), nullable=False, default="aws_pricing_api")
    is_active = Column(Boolean, default=True, index=True)
    pricing_metadata = Column(JSONB, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    
    # Relationships
    rates = relationship("PricingRate", back_populates="version_rel", cascade="all, delete-orphan")


class PricingRate(Base):
    """Pricing rates table - versioned, immutable pricing data"""
    __tablename__ = "pricing_rates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(20), ForeignKey("pricing_versions.version"), nullable=False, index=True)
    service = Column(String(100), nullable=False, index=True)
    region = Column(String(50), nullable=False, index=True)
    pricing_key = Column(String(200), nullable=False, index=True)
    rate = Column(Numeric(20, 10), nullable=False)
    unit = Column(String(50), nullable=True)
    source_sku = Column(String(200), nullable=True)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    version_rel = relationship("PricingVersion", back_populates="rates")
    
    # Composite unique constraint
    __table_args__ = (
        Index('idx_pricing_lookup', 'version', 'service', 'region', 'pricing_key'),
        Index('idx_pricing_service_region', 'service', 'region'),
        {'extend_existing': True}  # Allow table redefinition
    )


class PricingMetadata(Base):
    """Pricing metadata table - free tier, multipliers, etc."""
    __tablename__ = "pricing_metadata"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version = Column(String(20), ForeignKey("pricing_versions.version"), nullable=False)
    service = Column(String(100), nullable=False)
    region = Column(String(50), nullable=False)
    free_tier = Column(JSONB, nullable=True)
    tier_boundaries = Column(JSONB, nullable=True)
    multipliers = Column(JSONB, nullable=True)
    source_url = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_pricing_metadata_lookup', 'version', 'service', 'region', unique=True),
        {'extend_existing': True}  # Allow table redefinition
    )


class PricingChange(Base):
    """Pricing change log - audit trail for pricing changes"""
    __tablename__ = "pricing_changes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    old_version = Column(String(20), nullable=True)
    new_version = Column(String(20), nullable=False)
    service = Column(String(100), nullable=False)
    region = Column(String(50), nullable=False)
    pricing_key = Column(String(200), nullable=False)
    old_rate = Column(Numeric(20, 10), nullable=True)
    new_rate = Column(Numeric(20, 10), nullable=False)
    change_percent = Column(Numeric(10, 4), nullable=True)
    detected_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_pricing_changes_version', 'new_version'),
        Index('idx_pricing_changes_service', 'service', 'region'),
        {'extend_existing': True}  # Allow table redefinition
    )
