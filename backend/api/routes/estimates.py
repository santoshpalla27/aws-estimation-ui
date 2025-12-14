"""
Cost estimation endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
import structlog

from core.database import get_db
from models.database import CostEstimate as DBEstimate, InfrastructureGraph as DBGraph
from models.schemas import Estimate, EstimateRequest
from services.graph_engine import GraphEngine
from services.cost_calculator import CostCalculator

router = APIRouter()
logger = structlog.get_logger()


@router.post("", response_model=Estimate, status_code=status.HTTP_201_CREATED)
async def create_estimate(
    request: EstimateRequest,
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Create cost estimate from infrastructure design
    
    This endpoint:
    1. Builds dependency graph from services
    2. Injects implicit dependencies
    3. Validates graph
    4. Calculates costs
    5. Returns estimate with warnings and assumptions
    """
    try:
        # Build and validate graph
        graph_engine = GraphEngine()
        graph = await graph_engine.build_graph(
            services=request.services,
            explicit_edges=request.dependencies
        )
        
        # Calculate costs
        cost_calculator = CostCalculator()
        estimate_result = await cost_calculator.calculate_estimate(graph)
        
        # Save graph
        db_graph = DBGraph(
            project_id=project_id,
            nodes=[node.model_dump() for node in graph.nodes.values()],
            edges=[edge.model_dump() for edge in graph.edges],
            meta_data=graph.meta_data
        )
        db.add(db_graph)
        await db.flush()
        
        # Save estimate
        db_estimate = DBEstimate(
            project_id=project_id,
            graph_id=db_graph.id,
            total_monthly_cost=estimate_result.total_monthly_cost,
            breakdown=[b.model_dump() for b in estimate_result.breakdown],
            warnings=estimate_result.warnings,
            assumptions=estimate_result.assumptions,
            confidence=estimate_result.confidence
        )
        db.add(db_estimate)
        await db.commit()
        await db.refresh(db_estimate)
        
        logger.info(
            "estimate_created",
            estimate_id=str(db_estimate.id),
            project_id=str(project_id),
            total_cost=float(estimate_result.total_monthly_cost),
            node_count=len(graph.nodes),
            confidence=float(estimate_result.confidence) if estimate_result.confidence else None
        )
        
        return db_estimate
        
    except Exception as e:
        logger.error("estimate_creation_failed", error=str(e), project_id=str(project_id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create estimate: {str(e)}"
        )


@router.get("/{estimate_id}", response_model=Estimate)
async def get_estimate(
    estimate_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get estimate by ID"""
    result = await db.execute(
        select(DBEstimate).where(DBEstimate.id == estimate_id)
    )
    estimate = result.scalar_one_or_none()
    
    if not estimate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Estimate {estimate_id} not found"
        )
    
    return estimate


@router.get("", response_model=List[Estimate])
async def list_estimates(
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all estimates for a project (query parameter version)"""
    result = await db.execute(
        select(DBEstimate)
        .where(DBEstimate.project_id == project_id)
        .offset(skip)
        .limit(limit)
        .order_by(DBEstimate.created_at.desc())
    )
    estimates = result.scalars().all()
    return estimates


@router.get("/project/{project_id}", response_model=List[Estimate])
async def list_project_estimates(
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all estimates for a project"""
    result = await db.execute(
        select(DBEstimate)
        .where(DBEstimate.project_id == project_id)
        .offset(skip)
        .limit(limit)
        .order_by(DBEstimate.created_at.desc())
    )
    estimates = result.scalars().all()
    return estimates
