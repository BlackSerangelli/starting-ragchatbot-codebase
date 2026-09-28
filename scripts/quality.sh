#!/bin/bash
# Run all code quality checks without modifying files. Exits non-zero on the first failure.
set -e
cd "$(dirname "$0")/.."

echo "Checking import order (isort)..."
uv run isort --check-only --diff backend main.py

echo "Checking formatting (black)..."
uv run black --check --diff backend main.py

echo "Linting (flake8)..."
uv run flake8 backend main.py

echo "All quality checks passed."
