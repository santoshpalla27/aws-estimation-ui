"""
SQLAlchemy models for pricing and job data.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import (
    Boolean, Column, Integer, String, Text, Numeric, DateTime,
    ForeignKey, CheckConstraint, Index, UniqueConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


# ============================================================================
# PRICING MODELS
# ============================================================================

class PricingVersion(Base):
    """Pricing data versions."""
    __tablename__ = "pricing_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    is_active = Column(Boolean, nullable=False, default=False)
    source = Column(String(100), nullable=False)
    metadata = Column(JSONB)
    
    # Relationships
    dimensions = relationship("PricingDimension", back_populates="version", cascade="all, delete-orphan")
    rules = relationship("PricingRule", back_populates="version", cascade="all, delete-orphan")
    free_tiers = relationship("PricingFreeTier", back_populates="version", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="pricing_version")
    
    __table_args__ = (
        Index("idx_pricing_versions_active", "is_active"),
        Index("idx_pricing_versions_created", "created_at"),
    )


class PricingService(Base):
    """AWS services catalog."""
    __tablename__ = "pricing_services"
    
    id = Column(Integer, primary_key=True, index=True)
    service_code = Column(String(100), unique=True, nullable=False)
    service_name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    dimensions = relationship("PricingDimension", back_populates="service")
    rules = relationship("PricingRule", back_populates="service")
    free_tiers = relationship("PricingFreeTier", back_populates="service")
    
    __table_args__ = (
        Index("idx_pricing_services_code", "service_code"),
    )


class PricingRegion(Base):
    """AWS regions catalog."""
    __tablename__ = "pricing_regions"
    
    id = Column(Integer, primary_key=True, index=True)
    region_code = Column(String(50), unique=True, nullable=False)
    region_name = Column(String(255), nullable=False)
    location = Column(String(255))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    dimensions = relationship("PricingDimension", back_populates="region")
    free_tiers = relationship("PricingFreeTier", back_populates="region")
    
    __table_args__ = (
        Index("idx_pricing_regions_code", "region_code"),
    )


class PricingDimension(Base):
    """Pricing SKUs with attributes."""
    __tablename__ = "pricing_dimensions"
    
    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("pricing_versions.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("pricing_services.id"), nullable=False)
    region_id = Column(Integer, ForeignKey("pricing_regions.id"))
    sku = Column(String(255), nullable=False)
    product_family = Column(String(100))
    attributes = Column(JSONB, nullable=False)
    unit = Column(String(50), nullable=False)
    price_per_unit = Column(Numeric(20, 10), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    effective_date = Column(DateTime)
    term_type = Column(String(50))
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    version = relationship("PricingVersion", back_populates="dimensions")
    service = relationship("PricingService", back_populates="dimensions")
    region = relationship("PricingRegion", back_populates="dimensions")
    
    __table_args__ = (
        UniqueConstraint("version_id", "sku", name="uq_version_sku"),
        Index("idx_pricing_dimensions_version", "version_id"),
        Index("idx_pricing_dimensions_service", "service_id"),
        Index("idx_pricing_dimensions_region", "region_id"),
        Index("idx_pricing_dimensions_sku", "sku"),
        Index("idx_pricing_dimensions_attributes", "attributes", postgresql_using="gin"),
        Index("idx_pricing_dimensions_product_family", "product_family"),
    )


class PricingRule(Base):
    """Complex pricing rules."""
    __tablename__ = "pricing_rules"
    
    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("pricing_versions.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("pricing_services.id"), nullable=False)
    rule_type = Column(String(50), nullable=False)
    rule_name = Column(String(255), nullable=False)
    conditions = Column(JSONB, nullable=False)
    formula = Column(JSONB, nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    version = relationship("PricingVersion", back_populates="rules")
    service = relationship("PricingService", back_populates="rules")
    
    __table_args__ = (
        Index("idx_pricing_rules_version", "version_id"),
        Index("idx_pricing_rules_service", "service_id"),
        Index("idx_pricing_rules_type", "rule_type"),
    )


class PricingFreeTier(Base):
    """AWS Free Tier definitions."""
    __tablename__ = "pricing_free_tiers"
    
    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("pricing_versions.id", ondelete="CASCADE"), nullable=False)
    service_id = Column(Integer, ForeignKey("pricing_services.id"), nullable=False)
    region_id = Column(Integer, ForeignKey("pricing_regions.id"))
    description = Column(Text, nullable=False)
    unit = Column(String(50), nullable=False)
    quantity = Column(Numeric(20, 10), nullable=False)
    period = Column(String(50), nullable=False)
    conditions = Column(JSONB)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    version = relationship("PricingVersion", back_populates="free_tiers")
    service = relationship("PricingService", back_populates="free_tiers")
    region = relationship("PricingRegion", back_populates="free_tiers")
    
    __table_args__ = (
        Index("idx_pricing_free_tiers_version", "version_id"),
        Index("idx_pricing_free_tiers_service", "service_id"),
    )


# ============================================================================
# JOB MODELS
# ============================================================================

class UploadJob(Base):
    """User Terraform file uploads."""
    __tablename__ = "upload_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(PGUUID(as_uuid=True), unique=True, nullable=False)
    upload_type = Column(String(20), nullable=False)
    file_path = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime)
    error_message = Column(Text)
    metadata = Column(JSONB)
    
    # Relationships
    analysis_result = relationship("AnalysisResult", back_populates="upload_job", uselist=False)
    
    __table_args__ = (
        CheckConstraint("upload_type IN ('file', 'folder', 'zip')", name="check_upload_type"),
        CheckConstraint(
            "status IN ('pending', 'parsing', 'calculating', 'completed', 'failed')",
            name="check_status"
        ),
        Index("idx_upload_jobs_job_id", "job_id"),
        Index("idx_upload_jobs_status", "status"),
        Index("idx_upload_jobs_created", "created_at"),
    )


class AnalysisResult(Base):
    """Cost analysis results."""
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(PGUUID(as_uuid=True), ForeignKey("upload_jobs.job_id", ondelete="CASCADE"), unique=True, nullable=False)
    pricing_version_id = Column(Integer, ForeignKey("pricing_versions.id"), nullable=False)
    total_monthly_cost = Column(Numeric(20, 2), nullable=False)
    total_resources = Column(Integer, nullable=False)
    total_supported_resources = Column(Integer, nullable=False)
    total_unsupported_resources = Column(Integer, nullable=False)
    breakdown_by_service = Column(JSONB, nullable=False)
    breakdown_by_region = Column(JSONB, nullable=False)
    warnings = Column(JSONB)
    errors = Column(JSONB)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    upload_job = relationship("UploadJob", back_populates="analysis_result")
    pricing_version = relationship("PricingVersion", back_populates="analysis_results")
    resource_costs = relationship("ResourceCost", back_populates="analysis", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("idx_analysis_results_job_id", "job_id"),
        Index("idx_analysis_results_pricing_version", "pricing_version_id"),
    )


class ResourceCost(Base):
    """Individual resource costs."""
    __tablename__ = "resource_costs"
    
    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analysis_results.id", ondelete="CASCADE"), nullable=False)
    resource_type = Column(String(255), nullable=False)
    resource_name = Column(String(255), nullable=False)
    service_code = Column(String(100), nullable=False)
    region_code = Column(String(50))
    monthly_cost = Column(Numeric(20, 2), nullable=False)
    attributes = Column(JSONB, nullable=False)
    pricing_details = Column(JSONB, nullable=False)
    warnings = Column(JSONB)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    # Relationships
    analysis = relationship("AnalysisResult", back_populates="resource_costs")
    
    __table_args__ = (
        Index("idx_resource_costs_analysis", "analysis_id"),
        Index("idx_resource_costs_service", "service_code"),
        Index("idx_resource_costs_region", "region_code"),
        Index("idx_resource_costs_type", "resource_type"),
    )


# ============================================================================
# AUDIT MODELS
# ============================================================================

class PricingIngestionLog(Base):
    """Pricing ingestion audit log."""
    __tablename__ = "pricing_ingestion_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    version_id = Column(Integer, ForeignKey("pricing_versions.id", ondelete="SET NULL"))
    status = Column(String(20), nullable=False)
    service_code = Column(String(100))
    records_processed = Column(Integer)
    error_message = Column(Text)
    started_at = Column(DateTime, nullable=False, server_default=func.now())
    completed_at = Column(DateTime)
    metadata = Column(JSONB)
    
    __table_args__ = (
        CheckConstraint("status IN ('started', 'completed', 'failed')", name="check_log_status"),
        Index("idx_pricing_ingestion_logs_version", "version_id"),
        Index("idx_pricing_ingestion_logs_status", "status"),
        Index("idx_pricing_ingestion_logs_started", "started_at"),
    )
