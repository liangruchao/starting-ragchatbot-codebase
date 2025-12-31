#!/bin/bash

# Code formatting script for the RAG chatbot project
# This script automatically fixes formatting and linting issues

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Formatting code...${NC}"
echo ""

# Check if dev dependencies are installed
if ! uv run black --version &>/dev/null; then
    echo -e "${YELLOW}Dev dependencies not found. Installing...${NC}"
    uv sync --all-extras
fi

# Run Black (format mode)
echo -e "${YELLOW}1. Running Black (applying code formatting)...${NC}"
uv run black backend/
echo -e "${GREEN}   Done${NC}"
echo ""

# Run Ruff with auto-fix
echo -e "${YELLOW}2. Running Ruff (auto-fixing linting issues)...${NC}"
uv run ruff check backend/ --fix
echo -e "${GREEN}   Done${NC}"
echo ""

echo -e "${GREEN}Code formatted successfully!${NC}"
