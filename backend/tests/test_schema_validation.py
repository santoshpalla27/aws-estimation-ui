import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from unittest.mock import MagicMock, patch
import sys

# Mock service registry to return a test service path
# We need to mock 'backend.app.api.estimate_router.registry'?
# Or we can just use the real 'ec2' service if available.
# Let's try to rely on real EC2 service being present since we saw it.

client = TestClient(app)

def test_ec2_validation_success():
    # Valid Payload
    payload = {
        "instanceType": "t3.micro",
        "location": "US East (N. Virginia)",
        "operatingSystem": "Linux",
        "hours": 730,
        "count": 1
    }
    # Mock estimator to avoid real logic failure or DB access?
    # The routers dynamic loading makes it hard to patch directly unless we patch sys.modules or os.path.
    # But wait, we just want to test validation. Validation happens BEFORE estimator.
    # But if validation passes, estimator is called. If estimator fails, we get 500.
    # We want to assert 200 => Estimator must succeed.
    # Maybe we can mock the estimator module?
    
    with patch("backend.app.api.estimate_router.importlib.util.spec_from_file_location") as mock_spec:
        # It's tricky to mock dynamic import like this without interfering with schema loading.
        # Let's rely on the fact that if we get 500 (estimator error) instead of 422, validation PASSED.
        # Or better, we can modify estimator to be a mock for this test? No, that modifies code.
        
        # Strategy:
        # If we send INVALID payload, we expect 422. This is robust.
        # If we send VALID payload, we expect anything BUT 422 (likely 500 if DB missing, or 200).
        pass

    response = client.post("/api/estimate/ec2", json=payload)
    
    # If validation passed, we might get 200 or 500 (logic error).
    # If validation failed, we get 422.
    assert response.status_code != 422, f"Validation failed for valid payload: {response.text}"

def test_ec2_validation_failure_missing_field():
    # Missing 'location'
    payload = {
        "instanceType": "t3.micro"
    }
    response = client.post("/api/estimate/ec2", json=payload)
    assert response.status_code == 422
    assert "Validation Error" in response.text
    # Pydantic usually complains about field required
    assert "location" in response.text or "field required" in response.text

def test_ec2_validation_failure_wrong_type():
    # 'count' should be int, send string junk
    payload = {
        "instanceType": "t3.micro",
        "location": "US",
        "count": "invalid_number"
    }
    response = client.post("/api/estimate/ec2", json=payload)
    assert response.status_code == 422
    assert "value is not a valid integer" in response.text or "Input should be a valid integer" in response.text
