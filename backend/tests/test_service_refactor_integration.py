import pytest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure backend can be imported
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import services
# Note: we import them inside tests or after patching to ensure they use mocked robust_downloader if we were patching modules from sys.modules,
# but since we are patching where they are used, we can import them now (if they don't do side effects at import time).
# They assign logger and constants at top level, which is fine.

from backend.services.s3 import downloader as s3_downloader
from backend.services.ec2 import downloader as ec2_downloader
from backend.services.efs import downloader as efs_downloader
from backend.services.rds import downloader as rds_downloader

@pytest.fixture
def mock_download_file():
    with patch('backend.app.core.robust_downloader.download_file') as mock:
        mock.return_value = True
        yield mock

@pytest.fixture
def mock_requests_get():
    with patch('requests.get') as mock:
        # Mock the region index response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'regions': {
                'us-east-1': {
                    'currentVersionUrl': '/offers/v1.0/aws/Service/20231201/us-east-1/index.json'
                }
            }
        }
        mock.return_value = mock_resp
        yield mock

def test_s3_downloader_uses_robust(mock_download_file, mock_requests_get):
    s3_downloader.download()
    
    assert mock_requests_get.called
    assert mock_download_file.called
    args, _ = mock_download_file.call_args
    assert "https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/Service/20231201/us-east-1/index.json" in args[0]
    assert "s3.json" in str(args[1])

def test_ec2_downloader_uses_robust(mock_download_file, mock_requests_get):
    ec2_downloader.download()
    assert mock_download_file.called
    args, _ = mock_download_file.call_args
    assert "ec2.json" in str(args[1])

def test_efs_downloader_uses_robust(mock_download_file, mock_requests_get):
    efs_downloader.download()
    assert mock_download_file.called
    args, _ = mock_download_file.call_args
    assert "efs.json" in str(args[1])

def test_rds_downloader_uses_robust(mock_download_file, mock_requests_get):
    rds_downloader.download()
    assert mock_download_file.called
    args, _ = mock_download_file.call_args
    assert "rds.json" in str(args[1])
