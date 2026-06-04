# Makefile for Nexus Reins Development

# 基本设置
PYTHON ?= python
PIP ?= pip
UVICORN ?= uvicorn

# 项目配置
PROJECT_NAME = reins
VERSION = 0.1.0

# 路径配置
SRC_DIR = src
DATA_DIR = data
MIGRATIONS_DIR = migrations

# 依赖管理
.PHONY: install
install:
	@echo "Installing project dependencies..."
	$(PIP) install -r requirements.txt
	@echo "Dependencies installed successfully"

.PHONY: install-dev
install-dev: install
	@echo "Installing development dependencies..."
	$(PIP) install -r requirements-dev.txt
	@echo "Development dependencies installed successfully"

.PHONY: clean
clean:
	@echo "Cleaning up build files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.log" -delete
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".coverage" -exec rm -rf {} +
	@echo "Cleanup completed"

.PHONY: clean-pycache
clean-pycache:
	@echo "Cleaning up pycache files..."
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "pycache files cleaned"

.PHONY: lint
lint:
	@echo "Running code linting..."
	flake8 src/ tests/
	@echo "Linting completed"

.PHONY: format
format:
	@echo "Formatting code..."
	black src/ tests/
	isort src/ tests/
	@echo "Code formatting completed"

.PHONY: test
test:
	@echo "Running tests..."
	pytest tests/ -v
	@echo "Tests completed"

.PHONY: test-coverage
test-coverage:
	@echo "Running tests with coverage..."
	pytest tests/ -v --cov=src --cov-report=html
	@echo "Test coverage completed. Report available in htmlcov/"

.PHONY: migrate
migrate:
	@echo "Generating migration script..."
	python scripts/generate_migration.py
	@echo "Migration script generated in migrations/reins_migration.sql"

.PHONY: run
run:
	@echo "Starting Reins server..."
	$(UVICORN) reins.main:app --host $(HOST) --port $(PORT) --reload

.PHONY: run-prod
run-prod:
	@echo "Starting Reins server in production mode..."
	$(UVICORN) reins.main:app --host $(HOST) --port $(PORT) --workers $(WORKERS)

.PHONY: build-docker
build-docker:
	@echo "Building Docker image..."
	docker build -t nexus-reins:$(VERSION) .
	@echo "Docker image built successfully"

.PHONY: run-docker
run-docker:
	@echo "Running Reins in Docker container..."
	docker run -p 3000:3000 --name nexus-reins nexus-reins:$(VERSION)

.PHONY: run-docker-dev
run-docker-dev:
	@echo "Running Reins in Docker container with development mode..."
	docker run -p 3000:3000 -v $(CURDIR):/app -w /app --name nexus-reins-dev nexus-reins:$(VERSION) uvicorn reins.main:app --host 0.0.0.0 --port 3000 --reload

.PHONY: stop-docker
stop-docker:
	@echo "Stopping and removing Docker container..."
	docker stop nexus-reins > /dev/null 2>&1 || true
	docker rm nexus-reins > /dev/null 2>&1 || true
	@echo "Container stopped and removed"

.PHONY: docker-clean
docker-clean:
	@echo "Cleaning up Docker resources..."
	docker stop nexus-reins > /dev/null 2>&1 || true
	docker rm nexus-reins > /dev/null 2>&1 || true
	docker rmi nexus-reins:$(VERSION) > /dev/null 2>&1 || true
	@echo "Docker resources cleaned up"

.PHONY: help
help:
	@echo "Available make targets:"
	@echo "  install           - Install project dependencies"
	@echo "  install-dev       - Install development dependencies"
	@echo "  clean             - Clean up build files"
	@echo "  clean-pycache     - Clean up pycache files"
	@echo "  lint              - Run code linting"
	@echo "  format            - Format code"
	@echo "  test              - Run tests"
	@echo "  test-coverage     - Run tests with coverage"
	@echo "  migrate           - Generate migration script"
	@echo "  run               - Start Reins server (development mode)"
	@echo "  run-prod          - Start Reins server (production mode)"
	@echo "  build-docker      - Build Docker image"
	@echo "  run-docker        - Run Reins in Docker container"
	@echo "  run-docker-dev    - Run Reins in Docker container with development mode"
	@echo "  stop-docker       - Stop and remove Docker container"
	@echo "  docker-clean      - Clean up Docker resources"
	@echo "  help              - Show this help message"