"""
Pydantic schemas for API request/response validation
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID


# Project schemas
class ProjectBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    meta_data: Dict[str, Any] = Field(default_factory=dict)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None


class Project(ProjectBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Service Node schemas
class ServiceNode(BaseModel):
    id: str
    service_type: str
    config: Dict[str, Any]
    region: str
    availability_zone: Optional[str] = None
    meta_data: Dict[str, Any] = Field(default_factory=dict)


# Dependency Edge schemas
class DependencyEdge(BaseModel):
    source: str
    target: str
    type: str  # mandatory, conditional, implicit, cost_only
    reason: str
    cost_impact: Optional[Dict[str, Any]] = None
    meta_data: Dict[str, Any] = Field(default_factory=dict)


# Infrastructure Graph schemas
class InfrastructureGraphCreate(BaseModel):
    project_id: UUID
    nodes: List[ServiceNode]
    edges: List[DependencyEdge]
    meta_data: Dict[str, Any] = Field(default_factory=dict)


class InfrastructureGraph(BaseModel):
    id: UUID
    project_id: UUID
    nodes: List[ServiceNode]
    edges: List[DependencyEdge]
    meta_data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Cost Estimate schemas
class CostBreakdown(BaseModel):
    dimension: str  # service, region, category
    key: str
    value: Decimal
    details: Optional[Dict[str, Any]] = None


class EstimateRequest(BaseModel):
    services: List[ServiceNode]
    dependencies: Optional[List[DependencyEdge]] = Field(default_factory=list)


class Estimate(BaseModel):
    id: UUID
    project_id: UUID
    graph_id: Optional[UUID]
    total_monthly_cost: Decimal
    breakdown: List[CostBreakdown]
    warnings: List[str]
    assumptions: List[str]
    confidence: Optional[Decimal]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# Service Catalog schemas
class ServiceMetadata(BaseModel):
    service_id: str
    display_name: str
    description: str
    category: str
    icon_url: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class ServiceDefinition(BaseModel):
    service_id: str
    version: str
    category: str
    metadata: ServiceMetadata
    dependencies: Dict[str, Any]
    cost_formula: Dict[str, Any]
    validation_rules: List[Dict[str, Any]]
    ui_schema: Dict[str, Any]
