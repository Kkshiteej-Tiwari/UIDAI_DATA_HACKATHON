# Gender Inclusion Tracker - ML Backend Makefile
# Common commands for development and deployment

.PHONY: install dev test run build docker-build docker-run clean sample-data

# Python executable
PYTHON := python

# Default target
help:
	@echo "Gender Inclusion Tracker - ML Backend"
	@echo ""
	@echo "Available commands:"
	@echo "  make install      - Install dependencies"
	@echo "  make dev          - Run development server with reload"
	@echo "  make run          - Run production server"
	@echo "  make test         - Run tests"
	@echo "  make sample-data  - Generate sample data"
	@echo "  make run-demo     - Run full demo pipeline"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run Docker container"
	@echo "  make clean        - Clean artifacts and cache"

# Install dependencies
install:
	pip install --upgrade pip
	pip install -r requirements.txt

# Run development server with hot reload
dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run production server
run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

# Run tests
test:
	pytest tests/ -v --tb=short

# Generate sample data
sample-data:
	$(PYTHON) scripts/generate_sample_data.py

# Run full demo pipeline
run-demo:
	@echo "=== Gender Inclusion Tracker Demo ==="
	@echo ""
	@echo "1. Generating sample data..."
	$(PYTHON) scripts/generate_sample_data.py
	@echo ""
	@echo "2. Starting server (press Ctrl+C to stop)..."
	@echo "   API Docs: http://localhost:8000/docs"
	@echo ""
	@echo "3. Demo commands (run in another terminal):"
	@echo "   curl http://localhost:8000/api/health"
	@echo "   curl http://localhost:8000/api/datasets/"
	@echo ""
	uvicorn app.main:app --host 0.0.0.0 --port 8000

# Docker commands
docker-build:
	docker build -t gender-tracker-backend:latest .

docker-run:
	docker run -p 8000:8000 --env-file .env gender-tracker-backend:latest

# Clean artifacts
clean:
	rm -rf artifacts/*
	rm -rf models/*
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Lint code
lint:
	flake8 app/ tests/ --max-line-length=100
	black app/ tests/ --check

# Format code
format:
	black app/ tests/

# Type check
typecheck:
	mypy app/ --ignore-missing-imports
