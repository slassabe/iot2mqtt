# Makefile

# Project information
PROJECT_NAME = iot2mqtt

# Build directories
SHELL := /bin/bash

# Component information
COMPONENT_NAME := iot2mqtt
SRC_DIR := iot2mqtt

# Build directories
BUILD_DIR := build
DIST_DIR := dist

# Virtual environment (venv-first pattern)
VENV ?= .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

# Twine settings
TWINE := twine
#TWINE_REPOSITORY := testpypi
TWINE_REPOSITORY := pypi
VENV_TWINE := $(VENV)/bin/twine
ifeq (,$(wildcard $(VENV_TWINE)))
  TWINE_BIN := $(TWINE)
else
  TWINE_BIN := $(VENV_TWINE)
endif

# Load parent project variables if available (optional)
-include ../common.mk

.PHONY: help install dev test clean build format lint venv ensure-build ensure-twine upload all


# ANSI colors for pretty help output
BOLD := \033[1m
RESET := \033[0m
BLUE := \033[36m

help: ## Show lib commands
	@printf "$(BOLD)Lib Commands (component: $(COMPONENT_NAME)):$(RESET)\n"
	@printf "$(BOLD)=====================$(RESET)\n\n"
	@printf "$(BOLD)Development:$(RESET)\n"
	@printf "  $(BLUE)%-20s$(RESET) %s\n" "install" "Install $(COMPONENT_NAME) dependencies"
	@printf "  $(BLUE)%-20s$(RESET) %s\n" "dev" "Setup development environment"
	@printf "\n"
	@printf "$(BOLD)Quality:$(RESET)\n"
	@printf "  \033[36m%-20s\033[0m %s\n" "format" "Format code with black + isort"
	@printf "  \033[36m%-20s\033[0m %s\n" "lint" "Lint with flake8 + mypy"
	@printf "  \033[36m%-20s\033[0m %s\n" "test" "Run tests with pytest (if present)"
	@printf "\n"
	@printf "$(BOLD)Packaging:$(RESET)\n"
	@printf "  \033[36m%-20s\033[0m %s\n" "build" "Build sdist and wheel into dist/"
	@printf "  \033[36m%-20s\033[0m %s\n" "upload" "Upload distributions to $(TWINE_REPOSITORY)"
	@printf "\n"
	@printf "$(BOLD)Maintenance:$(RESET)\n"
	@printf "  \033[36m%-20s\033[0m %s\n" "clean" "Remove venv, build artifacts, and caches"

# Create a local virtual environment and prep basic tooling
venv: ## Create local virtual environment
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip setuptools wheel

install: venv ## Install component dependencies
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .
	@echo "✓ $(COMPONENT_NAME) installed"

dev: venv ## Setup development environment
	$(PIP) install -r requirements-dev.txt
	@echo "✓ Development environment ready"

test: ## Run tests (if tests/ exists)
	@if [ -d tests ]; then \
		$(PYTHON) -m pytest -v tests; \
	else \
		echo "No tests/ directory found; skipping."; \
	fi

clean: ## Clean build artifacts and caches
	rm -rf $(VENV) $(BUILD_DIR) $(DIST_DIR) *.egg-info
	find . -type d -name __pycache__ -delete
	find . -name "*.pyc" -delete

format: dev ## Format code
	$(PYTHON) -m black $(SRC_DIR)
	$(PYTHON) -m isort $(SRC_DIR)

lint: dev ## Lint code
	$(PYTHON) -m flake8 $(SRC_DIR)
	$(PYTHON) -m mypy $(SRC_DIR) || true

build: install ensure-build ## Build sdist and wheel
	$(PYTHON) -m build --outdir $(DIST_DIR)

ensure-build: ## Ensure the 'build' package is available
	@$(PYTHON) -c "import build" 2>/dev/null || \
	( echo "Installing missing 'build' into $(VENV)..." && $(PYTHON) -m pip install --upgrade build )

ensure-twine: ## Ensure 'twine' is available
	@command -v $(TWINE_BIN) >/dev/null 2>&1 || \
	( echo "Installing missing 'twine' into $(VENV)..." && $(PYTHON) -m pip install --upgrade twine )

upload: build ensure-twine ## Upload to repository
	$(TWINE_BIN) upload --repository $(TWINE_REPOSITORY) $(DIST_DIR)/*

all: lint format build ## Run quality checks and build

