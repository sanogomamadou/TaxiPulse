.PHONY: help install lint format test test-cov sample-data clean destroy

help:
	@echo "TaxiPulse - available targets:"
	@echo "  install       Install project + dev dependencies in the current venv"
	@echo "  lint          Run ruff checks"
	@echo "  format        Auto-fix lint issues and format code with ruff"
	@echo "  test          Run the pytest suite"
	@echo "  test-cov      Run the pytest suite with coverage report"
	@echo "  sample-data   Download a small local sample of NYC TLC trip data"
	@echo "  clean         Remove caches and build artifacts"
	@echo "  destroy       Destroy ALL GCP resources managed by Terraform (asks for confirmation)"

install:
	python -m pip install --upgrade pip
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check .

format:
	ruff check --fix .
	ruff format .

test:
	pytest

test-cov:
	pytest --cov=replayer/src --cov=pipeline/src --cov=api/src --cov-report=term-missing

sample-data:
	python scripts/download_tlc_sample.py --year-month 2024-01 --sample-size 5000

clean:
	find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage

# Destroys every GCP resource created via Terraform. Run this at the end of
# EVERY cloud session to avoid burning through the $300 trial credit.
destroy:
	@echo "This will DESTROY all GCP resources managed by Terraform in infra/envs/dev."
	@read -p "Type 'destroy' to confirm: " confirm && [ "$$confirm" = "destroy" ] || (echo "Aborted."; exit 1)
	cd infra/envs/dev && terraform destroy
