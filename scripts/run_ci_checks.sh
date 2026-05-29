#!/bin/bash
# Local CI checks script - run before pushing to GitHub

set -e

echo "=========================================="
echo "Running BharatDoc CI Checks Locally"
echo "=========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if in project root
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}Error: Must run from project root${NC}"
    exit 1
fi

# Install dependencies if needed
echo ""
echo "1. Checking dependencies..."
pip install -q ruff mypy pytest pytest-cov pytest-timeout bandit 2>/dev/null || true

# Run ruff
echo ""
echo "2. Running ruff linting..."
if ruff check gateway/ inference/ schemas/ router/ core/ data_pipeline/ evaluation/ feedback_loop/ training/ apps/; then
    echo -e "${GREEN}✓ Ruff passed${NC}"
else
    echo -e "${RED}✗ Ruff failed${NC}"
    echo "Run 'ruff check --fix' to auto-fix issues"
    exit 1
fi

# Run mypy
echo ""
echo "3. Running mypy type checking..."
if mypy gateway/ inference/ schemas/ --ignore-missing-imports --no-strict-optional; then
    echo -e "${GREEN}✓ Mypy passed${NC}"
else
    echo -e "${RED}✗ Mypy failed${NC}"
    exit 1
fi

# Run pytest
echo ""
echo "4. Running pytest..."
if pytest tests/ -v --tb=short --timeout=30; then
    echo -e "${GREEN}✓ Tests passed${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
    exit 1
fi

# Run bandit
echo ""
echo "5. Running security scan..."
if bandit -r gateway/ inference/ schemas/ router/ core/ -ll; then
    echo -e "${GREEN}✓ Security scan passed${NC}"
else
    echo -e "${RED}⚠ Security issues found (non-blocking)${NC}"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}All CI checks passed!${NC}"
echo "=========================================="
echo ""
echo "Ready to push to GitHub!"
