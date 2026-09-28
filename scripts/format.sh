#!/bin/bash
# Auto-format Python code: sort imports (isort), then format (black).
set -e
cd "$(dirname "$0")/.."

echo "Sorting imports with isort..."
uv run isort backend main.py

echo "Formatting with black..."
uv run black backend main.py
