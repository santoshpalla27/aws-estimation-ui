#!/bin/bash

# Test Runner Script for AWS Cost Estimation Platform
# Runs all integration tests and generates reports

set -e

echo "🚀 Starting AWS Cost Estimation Platform Tests"
echo "=============================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Wait for backend to be ready
echo -e "${YELLOW}⏳ Waiting for backend to be ready...${NC}"
MAX_RETRIES=60
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://backend:8000/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is ready!${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}❌ Backend failed to start after ${MAX_RETRIES} attempts${NC}"
        exit 1
    fi
    echo "   Attempt $RETRY_COUNT/$MAX_RETRIES..."
    sleep 2
done

# Run tests
echo ""
echo "📋 Running Test Suites"
echo "=============================================="

# Test 1: API Endpoints
echo -e "${YELLOW}🧪 Test Suite 1: API Endpoints${NC}"
pytest /app/tests/integration/test_api_endpoints.py -v --tb=short --color=yes || TEST_FAILED=1

# Test 2: Service Calculations
echo ""
echo -e "${YELLOW}🧪 Test Suite 2: Service Cost Calculations${NC}"
pytest /app/tests/integration/test_service_calculations.py -v --tb=short --color=yes || TEST_FAILED=1

# Test 3: End-to-End Workflows
echo ""
echo -e "${YELLOW}🧪 Test Suite 3: End-to-End Workflows${NC}"
pytest /app/tests/integration/test_workflows.py -v --tb=short --color=yes || TEST_FAILED=1

# Summary
echo ""
echo "=============================================="
if [ -z "$TEST_FAILED" ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED!${NC}"
    echo -e "${GREEN}🎉 AWS Cost Estimation Platform is working correctly${NC}"
    exit 0
else
    echo -e "${RED}❌ SOME TESTS FAILED${NC}"
    echo -e "${RED}Please check the output above for details${NC}"
    exit 1
fi
