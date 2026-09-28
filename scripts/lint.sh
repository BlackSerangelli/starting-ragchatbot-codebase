#!/bin/bash
# Lint Python code with flake8.
set -e
cd "$(dirname "$0")/.."

echo "Linting with flake8..."
uv run flake8 backend main.py
