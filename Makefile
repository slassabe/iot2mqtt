# Makefile

# Project information
PROJECT_NAME = iot2mqtt

# Build directories
BUILD_DIR = build
DIST_DIR = dist

# Python environment
PYTHON = python3
PIP = pip3

# Twine command
TWINE = twine
#TWINE_REPOSITORY = testpypi
TWINE_REPOSITORY = pypi

# Clean target
.PHONY: clean
clean:
	rm -rf $(BUILD_DIR) $(DIST_DIR) *.egg-info

# Build target
.PHONY: build
build: clean
	$(PYTHON) -m build --outdir $(DIST_DIR)

# Upload target
.PHONY: upload
upload: build
	$(TWINE) upload --repository $(TWINE_REPOSITORY) $(DIST_DIR)/*

# Install target
.PHONY: install
install:
	$(PIP) install .

# Develop target
.PHONY: develop
develop:
	$(PIP) install -e .

# Lint target
.PHONY: lint
lint:
	$(PYTHON) -m pylint $(PROJECT_NAME)

# Format target
.PHONY: format
format:
	$(PYTHON) -m black $(PROJECT_NAME)
	$(PYTHON) -m isort $(PROJECT_NAME)

# All target
.PHONY: all
all: lint format build

