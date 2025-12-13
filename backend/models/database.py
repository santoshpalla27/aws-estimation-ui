"""
Database models for projects, graphs, and estimates
"""

from sqlalchemy import Column, String, Text, DECIMAL, ForeignKey, Integer, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.sql import func
import uuid

from core.database import Base


class Project(Base):
    """Project model"""
    __tablename__ = "projects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    metadata = Column(JSONB, default={})
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class InfrastructureGraph(Base):
    """Infrastructure graph model"""
    __tablename__ = "infrastructure_graphs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    nodes = Column(JSONB, default=[])
    edges = Column(JSONB, default=[])
    metadata = Column(JSONB, default={})
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class CostEstimate(Base):
    """Cost estimate model"""
    __tablename__ = "cost_estimates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    graph_id = Column(UUID(as_uuid=True), ForeignKey("infrastructure_graphs.id", ondelete="SET NULL"))
    total_monthly_cost = Column(DECIMAL(12, 2), nullable=False)
    breakdown = Column(JSONB, nullable=False)
    warnings = Column(JSONB, default=[])
    assumptions = Column(JSONB, default=[])
    confidence = Column(DECIMAL(3, 2))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class PricingData(Base):
    """Pricing data cache model"""
    __tablename__ = "pricing_data"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service = Column(String(100), nullable=False)
    region = Column(String(50), nullable=False)
    sku = Column(String(255), nullable=False)
    attributes = Column(JSONB, nullable=False)
    pricing = Column(JSONB, nullable=False)
    effective_date = Column(Date, nullable=False)
    version = Column(String(50), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())


class PricingVersion(Base):
    """Pricing version tracking model"""
    __tablename__ = "pricing_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service = Column(String(100), nullable=False)
    region = Column(String(50), nullable=False)
    version = Column(String(50), nullable=False)
    sku_count = Column(Integer, nullable=False)
    synced_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
