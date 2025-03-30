.PHONY: help install update clean run dry-run check format lint test

# Python settings
PYTHON := python3
PIPENV := pipenv

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install project dependencies
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install pipenv
	$(PIPENV) install --dev

update:  ## Update dependencies to latest versions
	$(PIPENV) update

clean:  ## Remove build artifacts and cache files
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name "*.egg" -exec rm -rf {} +
	find . -type f -name "Changes_*.md" -delete

run:  ## Run the Zotero Substack analyzer
	$(PIPENV) run python src/main.py $(ARGS)

dry-run:  ## Run the analyzer in dry-run mode
	$(PIPENV) run python src/main.py --dry-run $(ARGS)

check:  ## Run all code quality checks
	$(MAKE) format
	$(MAKE) lint

format:  ## Format code using black
	$(PIPENV) run black src || true

lint:  ## Run linting using ruff
	$(PIPENV) run ruff check src || true
