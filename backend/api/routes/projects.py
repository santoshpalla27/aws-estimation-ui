"""
Project management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
import structlog

from core.database import get_db
from models.database import Project as DBProject
from models.schemas import Project, ProjectCreate, ProjectUpdate

router = APIRouter()
logger = structlog.get_logger()


@router.get("", response_model=List[Project])
async def list_projects(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """List all projects"""
    result = await db.execute(
        select(DBProject)
        .offset(skip)
        .limit(limit)
        .order_by(DBProject.created_at.desc())
    )
    projects = result.scalars().all()
    return projects


@router.post("", response_model=Project, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new project"""
    db_project = DBProject(**project.model_dump())
    db.add(db_project)
    await db.commit()
    await db.refresh(db_project)
    
    logger.info("project_created", project_id=str(db_project.id), name=db_project.name)
    return db_project


@router.get("/{project_id}", response_model=Project)
async def get_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get project by ID"""
    result = await db.execute(
        select(DBProject).where(DBProject.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    return project


@router.put("/{project_id}", response_model=Project)
async def update_project(
    project_id: UUID,
    project_update: ProjectUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update project"""
    result = await db.execute(
        select(DBProject).where(DBProject.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    # Update fields
    update_data = project_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)
    
    await db.commit()
    await db.refresh(project)
    
    logger.info("project_updated", project_id=str(project_id))
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete project"""
    result = await db.execute(
        select(DBProject).where(DBProject.id == project_id)
    )
    project = result.scalar_one_or_none()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    await db.delete(project)
    await db.commit()
    
    logger.info("project_deleted", project_id=str(project_id))
    return None
