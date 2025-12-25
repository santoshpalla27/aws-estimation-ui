"""
Secure file handling and validation.
Prevents Zip Slip and other file-based attacks.
"""
import os
import zipfile
import logging
from pathlib import Path
from typing import Set, List

logger = logging.getLogger(__name__)


class SecurityError(Exception):
    """Raised when security validation fails."""
    pass


class FileValidator:
    """
    Validates uploaded files for security.
    
    Prevents:
    - Zip Slip (path traversal)
    - Absolute paths
    - Malicious file types
    - Excessive file counts
    - Excessive file sizes
    """
    
    # Allowed file extensions
    ALLOWED_EXTENSIONS: Set[str] = {
        '.tf',
        '.tfvars',
        '.json',
        '.hcl'
    }
    
    # Security limits
    MAX_FILES = 1000
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
    MAX_TOTAL_SIZE = 100 * 1024 * 1024  # 100MB total
    MAX_PATH_LENGTH = 255
    
    @classmethod
    def validate_filename(cls, filename: str) -> None:
        """
        Validate a single filename.
        
        Args:
            filename: Filename to validate
        
        Raises:
            SecurityError: If validation fails
        """
        # Reject absolute paths
        if os.path.isabs(filename):
            raise SecurityError(f"Absolute paths not allowed: {filename}")
        
        # Reject path traversal
        if '..' in filename:
            raise SecurityError(f"Path traversal not allowed: {filename}")
        
        # Reject hidden files (starting with .)
        parts = Path(filename).parts
        if any(part.startswith('.') for part in parts):
            raise SecurityError(f"Hidden files not allowed: {filename}")
        
        # Check path length
        if len(filename) > cls.MAX_PATH_LENGTH:
            raise SecurityError(f"Path too long: {filename}")
        
        # Validate extension
        ext = os.path.splitext(filename)[1].lower()
        if ext and ext not in cls.ALLOWED_EXTENSIONS:
            raise SecurityError(f"File type not allowed: {ext}")
    
    @classmethod
    def validate_extraction_path(cls, member_path: str, extract_root: str) -> str:
        """
        Validate that extraction path is safe.
        
        Args:
            member_path: Path from zip member
            extract_root: Root extraction directory
        
        Returns:
            Validated absolute path
        
        Raises:
            SecurityError: If path escapes extraction root
        """
        # Normalize paths
        extract_root = os.path.abspath(extract_root)
        target_path = os.path.abspath(os.path.join(extract_root, member_path))
        
        # Ensure target is within extraction root
        if not target_path.startswith(extract_root):
            raise SecurityError(
                f"Path traversal detected: {member_path} would extract to {target_path}"
            )
        
        return target_path
    
    @classmethod
    def safe_extract_zip(cls, zip_path: str, extract_to: str) -> List[str]:
        """
        Safely extract zip file with validation.
        
        Args:
            zip_path: Path to zip file
            extract_to: Directory to extract to
        
        Returns:
            List of extracted file paths
        
        Raises:
            SecurityError: If validation fails
        """
        extracted_files = []
        total_size = 0
        
        with zipfile.ZipFile(zip_path, 'r') as zf:
            members = zf.namelist()
            
            # Check file count
            if len(members) > cls.MAX_FILES:
                raise SecurityError(
                    f"Too many files in archive: {len(members)} > {cls.MAX_FILES}"
                )
            
            # Validate all members first
            for member in members:
                # Skip directories
                if member.endswith('/'):
                    continue
                
                # Validate filename
                cls.validate_filename(member)
                
                # Get file info
                info = zf.getinfo(member)
                
                # Check individual file size
                if info.file_size > cls.MAX_FILE_SIZE:
                    raise SecurityError(
                        f"File too large: {member} ({info.file_size} bytes)"
                    )
                
                # Check total size
                total_size += info.file_size
                if total_size > cls.MAX_TOTAL_SIZE:
                    raise SecurityError(
                        f"Total archive size too large: {total_size} bytes"
                    )
            
            # Extract files safely
            for member in members:
                # Skip directories
                if member.endswith('/'):
                    continue
                
                # Validate extraction path
                target_path = cls.validate_extraction_path(member, extract_to)
                
                # Create parent directories
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                
                # Extract file
                with zf.open(member) as source:
                    with open(target_path, 'wb') as target:
                        target.write(source.read())
                
                extracted_files.append(target_path)
                logger.info(f"Extracted: {member} -> {target_path}")
        
        logger.info(f"Safely extracted {len(extracted_files)} files")
        return extracted_files
    
    @classmethod
    def validate_file_size(cls, file_path: str) -> None:
        """
        Validate file size.
        
        Args:
            file_path: Path to file
        
        Raises:
            SecurityError: If file too large
        """
        size = os.path.getsize(file_path)
        if size > cls.MAX_FILE_SIZE:
            raise SecurityError(f"File too large: {size} bytes > {cls.MAX_FILE_SIZE}")
    
    @classmethod
    def validate_file_extension(cls, filename: str) -> None:
        """
        Validate file extension.
        
        Args:
            filename: Filename to validate
        
        Raises:
            SecurityError: If extension not allowed
        """
        ext = os.path.splitext(filename)[1].lower()
        if ext and ext not in cls.ALLOWED_EXTENSIONS:
            raise SecurityError(f"File type not allowed: {ext}")
