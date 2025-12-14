# Testing Container Documentation

## Overview

The testing container provides comprehensive automated testing for the AWS Cost Estimation Platform. It includes API endpoint tests, service cost calculation validation, and end-to-end workflow tests.

## Test Suites

### 1. API Endpoint Tests (`test_api_endpoints.py`)
- **Health Check**: Validates `/health` endpoint
- **Projects CRUD**: Create, read, update, delete projects
- **Services API**: List services and get service schemas
- **Estimates API**: Create estimates, list estimates, retrieve specific estimates

### 2. Service Calculation Tests (`test_service_calculations.py`)
- **S3 Calculations**: Tests all storage classes (STANDARD, Glacier, Intelligent-Tiering)
- **EC2 Calculations**: Tests instance types, multiple instances, data transfer
- **Multi-Service Estimates**: Combined S3 + EC2 estimates
- **Edge Cases**: Zero values, large values, boundary conditions

### 3. Workflow Tests (`test_workflows.py`)
- **Complete E2E Workflow**: Full user journey from project creation to estimate generation
- **Error Handling**: Invalid inputs, missing configurations
- **Performance Tests**: Large estimates, concurrent requests

## Running Tests

### Automatic (with docker-compose)
```bash
# Run tests automatically
docker compose --profile test up tests

# Or run with all services
docker compose --profile test up
```

### Manual
```bash
# Build test container
docker compose build tests

# Run tests
docker compose run --rm tests
```

### On Server
```bash
# Pull latest code
git pull

# Run tests
docker compose --profile test up tests --build
```

## Test Output

The test runner provides colored output:
- ✅ **Green**: Tests passed
- ❌ **Red**: Tests failed  
- ⏳ **Yellow**: Tests running

## Exit Codes

- `0`: All tests passed
- `1`: Some tests failed

## Test Coverage

The test suite covers:
- ✅ All REST API endpoints
- ✅ S3 cost calculations (all storage classes)
- ✅ EC2 cost calculations (multiple instance types)
- ✅ Multi-service estimates
- ✅ Error handling and validation
- ✅ Performance and scalability
- ✅ Complete user workflows

## Dependencies

- pytest
- pytest-asyncio
- requests
- pytest-timeout

## Configuration

Tests automatically wait for backend to be ready (up to 60 attempts with 2s delay).

## Production Ready

This test suite is production-ready and can be:
- Run in CI/CD pipelines
- Used for smoke testing after deployments
- Executed on schedule for continuous validation
- Integrated with monitoring systems

## Adding New Tests

1. Create test file in `backend/tests/integration/`
2. Follow pytest conventions
3. Use `BASE_URL = "http://backend:8000"`
4. Add to `run_tests.sh` if needed
