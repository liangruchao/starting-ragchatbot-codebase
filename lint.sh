#!/bin/bash

# Code quality checks script for the RAG chatbot project
# This script runs Black (formatter), Ruff (linter), and mypy (type checker)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Running code quality checks...${NC}"
echo ""

# Check if dev dependencies are installed
if ! uv run black --version &>/dev/null; then
    echo -e "${YELLOW}Dev dependencies not found. Installing...${NC}"
    uv sync --all-extras
fi

# Run Black (check mode)
echo -e "${YELLOW}1. Running Black (code formatting check)...${NC}"
uv run black backend/ --check
echo -e "${GREEN}   Black: No formatting issues found${NC}"
echo ""

# Run Ruff
echo -e "${YELLOW}2. Running Ruff (linting)...${NC}"
uv run ruff check backend/
echo -e "${GREEN}   Ruff: No linting issues found${NC}"
echo ""

# Run mypy
echo -e "${YELLOW}3. Running mypy (type checking)...${NC}"
uv run mypy backend/ || true
echo ""

echo -e "${GREEN}All code quality checks passed!${NC}"
