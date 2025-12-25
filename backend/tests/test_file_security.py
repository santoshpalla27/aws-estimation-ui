"""
Tests for file security validation.
"""
import pytest
import os
import zipfile
import tempfile
from pathlib import Path

from app.security.file_validation import FileValidator, SecurityError


class TestFilenameValidation:
    """Test filename validation."""
    
    def test_valid_terraform_file(self):
        """Test valid .tf file passes."""
        FileValidator.validate_filename("main.tf")
        FileValidator.validate_filename("modules/vpc/main.tf")
    
    def test_reject_absolute_path(self):
        """Test absolute paths are rejected."""
        with pytest.raises(SecurityError, match="Absolute paths not allowed"):
            FileValidator.validate_filename("/etc/passwd")
        
        with pytest.raises(SecurityError, match="Absolute paths not allowed"):
            FileValidator.validate_filename("C:\\Windows\\System32\\config")
    
    def test_reject_path_traversal(self):
        """Test path traversal is rejected."""
        with pytest.raises(SecurityError, match="Path traversal not allowed"):
            FileValidator.validate_filename("../../../etc/passwd")
        
        with pytest.raises(SecurityError, match="Path traversal not allowed"):
            FileValidator.validate_filename("modules/../../secrets.txt")
    
    def test_reject_hidden_files(self):
        """Test hidden files are rejected."""
        with pytest.raises(SecurityError, match="Hidden files not allowed"):
            FileValidator.validate_filename(".env")
        
        with pytest.raises(SecurityError, match="Hidden files not allowed"):
            FileValidator.validate_filename("modules/.git/config")
    
    def test_reject_invalid_extension(self):
        """Test invalid extensions are rejected."""
        with pytest.raises(SecurityError, match="File type not allowed"):
            FileValidator.validate_filename("malicious.exe")
        
        with pytest.raises(SecurityError, match="File type not allowed"):
            FileValidator.validate_filename("script.sh")
    
    def test_reject_long_path(self):
        """Test excessively long paths are rejected."""
        long_path = "a/" * 200 + "file.tf"
        with pytest.raises(SecurityError, match="Path too long"):
            FileValidator.validate_filename(long_path)


class TestExtractionPathValidation:
    """Test extraction path validation."""
    
    def test_valid_extraction_path(self):
        """Test valid extraction path."""
        root = "/tmp/extract"
        member = "main.tf"
        
        result = FileValidator.validate_extraction_path(member, root)
        assert result.startswith(root)
    
    def test_reject_escape_attempt(self):
        """Test path escaping extraction root is rejected."""
        root = "/tmp/extract"
        member = "../../../etc/passwd"
        
        with pytest.raises(SecurityError, match="Path traversal detected"):
            FileValidator.validate_extraction_path(member, root)
    
    def test_reject_absolute_in_zip(self):
        """Test absolute path in zip is rejected."""
        root = "/tmp/extract"
        member = "/etc/passwd"
        
        # This will be caught by validate_filename first
        with pytest.raises(SecurityError):
            FileValidator.validate_filename(member)


class TestZipExtraction:
    """Test safe zip extraction."""
    
    def test_safe_extraction(self):
        """Test safe extraction of valid zip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test zip
            zip_path = os.path.join(tmpdir, "test.zip")
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr("main.tf", "resource \"aws_instance\" \"web\" {}")
                zf.writestr("variables.tf", "variable \"region\" {}")
            
            # Extract safely
            extract_to = os.path.join(tmpdir, "extracted")
            files = FileValidator.safe_extract_zip(zip_path, extract_to)
            
            assert len(files) == 2
            assert all(os.path.exists(f) for f in files)
    
    def test_reject_zip_slip(self):
        """Test Zip Slip attack is prevented."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create malicious zip
            zip_path = os.path.join(tmpdir, "malicious.zip")
            with zipfile.ZipFile(zip_path, 'w') as zf:
                # Try to escape extraction directory
                zf.writestr("../../../etc/passwd", "malicious content")
            
            extract_to = os.path.join(tmpdir, "extracted")
            
            with pytest.raises(SecurityError, match="Path traversal"):
                FileValidator.safe_extract_zip(zip_path, extract_to)
    
    def test_reject_too_many_files(self):
        """Test excessive file count is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "large.zip")
            with zipfile.ZipFile(zip_path, 'w') as zf:
                # Create more than MAX_FILES
                for i in range(FileValidator.MAX_FILES + 1):
                    zf.writestr(f"file{i}.tf", "content")
            
            extract_to = os.path.join(tmpdir, "extracted")
            
            with pytest.raises(SecurityError, match="Too many files"):
                FileValidator.safe_extract_zip(zip_path, extract_to)
    
    def test_reject_large_file(self):
        """Test excessively large file is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "large.zip")
            with zipfile.ZipFile(zip_path, 'w') as zf:
                # Create file larger than MAX_FILE_SIZE
                large_content = "x" * (FileValidator.MAX_FILE_SIZE + 1)
                zf.writestr("large.tf", large_content)
            
            extract_to = os.path.join(tmpdir, "extracted")
            
            with pytest.raises(SecurityError, match="File too large"):
                FileValidator.safe_extract_zip(zip_path, extract_to)
    
    def test_reject_invalid_extension_in_zip(self):
        """Test invalid file extension in zip is rejected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "bad.zip")
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr("malicious.exe", "bad content")
            
            extract_to = os.path.join(tmpdir, "extracted")
            
            with pytest.raises(SecurityError, match="File type not allowed"):
                FileValidator.safe_extract_zip(zip_path, extract_to)
    
    def test_skip_directories(self):
        """Test directories in zip are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "test.zip")
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr("modules/", "")  # Directory
                zf.writestr("modules/main.tf", "content")
            
            extract_to = os.path.join(tmpdir, "extracted")
            files = FileValidator.safe_extract_zip(zip_path, extract_to)
            
            # Only file extracted, not directory
            assert len(files) == 1
