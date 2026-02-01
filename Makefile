.PHONY: help install update clean run dry-run check format lint test hydrate-fixtures

# Python settings
PYTHON := python3
PIPENV := pipenv

help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install project dependencies (`pip` and `pipenv` need to be instaled separately)
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

stream:  ## Run the Zotero Substack analyzer in stream mode
	$(PIPENV) run python src/main.py --stream $(ARGS)

check:  ## Run all code quality checks
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test

format:  ## Format code using black
	$(PIPENV) run black src || true

lint:  ## Run linting using ruff
	$(PIPENV) run ruff check src || true

test:  ## Run offline tests with local fixtures
	$(MAKE) clean
	$(MAKE) install
	$(PIPENV) run python src/main.py --test-yaml

hydrate-fixtures:  ## Download and update test fixtures
	$(PIPENV) run python tests/hydrate_fixtures.py
