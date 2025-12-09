import pytest
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from backend.app.core.robust_downloader import download_file, calculate_sha256

# Test fixtures
@pytest.fixture
def tmp_path_fixture(tmp_path):
    return tmp_path

@pytest.fixture
def mock_response():
    resp = MagicMock()
    resp.status_code = 200
    resp.headers = {'content-length': '100'}
    resp.iter_content.return_value = [b'x' * 100]
    return resp

def test_calculate_sha256(tmp_path_fixture):
    p = tmp_path_fixture / "test.txt"
    p.write_bytes(b"hello world")
    # echo -n "hello world" | sha256sum
    # b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9
    assert calculate_sha256(p) == "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"

@patch('requests.Session.get')
def test_clean_download(mock_get, tmp_path_fixture, mock_response):
    target = tmp_path_fixture / "clean.json"
    mock_get.return_value.__enter__.return_value = mock_response
    
    assert download_file("http://example.com/clean.json", target)
    assert target.exists()
    assert not (target.with_suffix('.json.part')).exists()
    assert (target.with_suffix('.json.meta')).exists()

@patch('requests.Session.get')
def test_resume_download(mock_get, tmp_path_fixture):
    target = tmp_path_fixture / "resume.json"
    part = tmp_path_fixture / "resume.json.part"
    part.write_bytes(b'x' * 50)
    
    mock_response_partial = MagicMock()
    mock_response_partial.status_code = 206
    mock_response_partial.headers = {'content-length': '50'} # 50 more bytes
    mock_response_partial.iter_content.return_value = [b'x' * 50]
    
    mock_get.return_value.__enter__.return_value = mock_response_partial
    
    assert download_file("http://example.com/resume.json", target)
    
    # Check that Range header was sent
    call_args = mock_get.call_args
    assert 'Range' in call_args[1]['headers']
    assert call_args[1]['headers']['Range'] == 'bytes=50-'
    
    # Check final file size
    assert target.stat().st_size == 100

@patch('requests.Session.get')
def test_hash_mismatch(mock_get, tmp_path_fixture, mock_response):
    target = tmp_path_fixture / "mismatch.json"
    mock_get.return_value.__enter__.return_value = mock_response
    
    # Hash for 100 'x's
    # b'x'*100 sha256 = ...
    # We pass a fake expectations
    
    success = download_file("http://example.com/mismatch.json", target, expected_hash="badhash")
    assert not success
    assert not target.exists()
