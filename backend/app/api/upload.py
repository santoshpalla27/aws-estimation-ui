"""
Upload API endpoints with secure file handling.
"""
import logging
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_async_session
from app.models.models import UploadJob
from app.security.file_validation import FileValidator, SecurityError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload")
async def upload_terraform(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Upload Terraform file or zip.
    
    Args:
        file: Uploaded file
        db: Database session
    
    Returns:
        Job ID for tracking
    """
    # Validate file size
    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB"
        )
    
    # Create upload directory
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate job ID
    job_id = uuid.uuid4()
    job_dir = upload_dir / str(job_id)
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine upload type
    filename = file.filename or "upload"
    is_zip = filename.endswith(".zip")
    
    try:
        if is_zip:
            # Save zip temporarily
            zip_path = job_dir / filename
            zip_path.write_bytes(content)
            
            # Extract safely with validation
            try:
                extracted_files = FileValidator.safe_extract_zip(
                    str(zip_path),
                    str(job_dir)
                )
                logger.info(f"Safely extracted {len(extracted_files)} files")
            except SecurityError as e:
                logger.error(f"Security validation failed: {e}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Security validation failed: {str(e)}"
                )
            
            upload_type = "zip"
            file_path = str(job_dir)
        
        else:
            # Validate single file
            try:
                FileValidator.validate_file_extension(filename)
            except SecurityError as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid file type: {str(e)}"
                )
            
            # Save single file
            file_path = job_dir / filename
            file_path.write_bytes(content)
            
            # Validate file size
            try:
                FileValidator.validate_file_size(str(file_path))
            except SecurityError as e:
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large: {str(e)}"
                )
            
            upload_type = "file"
            file_path = str(file_path)
        
        # Create upload job record
        upload_job = UploadJob(
            job_id=job_id,
            upload_type=upload_type,
            file_path=file_path,
            status="pending",
            metadata={"filename": filename}
        )
        
        db.add(upload_job)
        await db.commit()
        await db.refresh(upload_job)
        
        logger.info(f"Created upload job: {job_id}")
        
        return {
            "job_id": str(job_id),
            "status": "pending",
            "message": "Upload successful. Use /api/analyze to start cost calculation."
        }
    
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        
        # Cleanup
        if job_dir.exists():
            shutil.rmtree(job_dir)
        
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
