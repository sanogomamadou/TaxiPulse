.PHONY: help install lint format test test-cov sample-data taxi-zones warehouse-zones warehouse-batch-ingest warehouse-staging warehouse-marts warehouse-quality warehouse-forecast emulator-up emulator-down emulator-setup replay tf-init tf-fmt tf-validate tf-plan tf-apply clean destroy

# No component under */src is pip-installed (see pyproject.toml's
# [tool.setuptools] comment) - pytest resolves them via its own
# `pythonpath` ini option, but a plain `python -m taxipulse_x.y` outside
# pytest needs this on the real PYTHONPATH, so every target gets it here.
export PYTHONPATH := common/src:replayer/src:pipeline/src:warehouse/src:api/src

help:
	@echo "TaxiPulse - available targets:"
	@echo "  install          Install project + dev dependencies in the current venv"
	@echo "  lint             Run ruff checks"
	@echo "  format           Auto-fix lint issues and format code with ruff"
	@echo "  test             Run the pytest suite"
	@echo "  test-cov         Run the pytest suite with coverage report"
	@echo "  sample-data      Download a small local sample of NYC TLC trip data"
	@echo "  taxi-zones       Download/build the zone lookup + centroid reference table"
	@echo "  warehouse-zones         Load the zone reference into stg_taxi_zones"
	@echo "  warehouse-batch-ingest  Ingest raw TLC sample Parquet into the raw Delta table"
	@echo "  warehouse-staging       Build stg_trips from the raw Delta table"
	@echo "  warehouse-marts         Build the zone_demand_hourly/daily marts"
	@echo "  warehouse-quality       Run data quality checks against staging/marts"
	@echo "  warehouse-forecast      Train+forecast per-zone demand (Prophet/MLflow)"
	@echo "  emulator-up      Start the local Event Hubs emulator + Azurite (Docker)"
	@echo "  emulator-down    Stop the local emulator"
	@echo "  emulator-setup   Verify the emulator is reachable and the hub exists"
	@echo "  replay           Run the replayer against the local emulator"
	@echo "  tf-init          terraform init (infra/envs/dev)"
	@echo "  tf-fmt           terraform fmt -recursive (infra/)"
	@echo "  tf-validate      terraform validate (infra/envs/dev)"
	@echo "  tf-plan          terraform plan (infra/envs/dev)"
	@echo "  tf-apply         terraform apply (infra/envs/dev, asks for confirmation)"
	@echo "  clean            Remove caches and build artifacts"
	@echo "  destroy          Destroy ALL Azure resources managed by Terraform (asks for confirmation)"

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

taxi-zones:
	python scripts/download_taxi_zones.py

warehouse-zones:
	python -m taxipulse_warehouse.zones $(ARGS)

warehouse-batch-ingest:
	python -m taxipulse_warehouse.batch_ingest $(ARGS)

warehouse-staging:
	python -m taxipulse_warehouse.staging $(ARGS)

warehouse-marts:
	python -m taxipulse_warehouse.marts $(ARGS)

warehouse-quality:
	python -m taxipulse_warehouse.quality $(ARGS)

warehouse-forecast:
	python -m taxipulse_warehouse.forecast $(ARGS)

EMULATOR_CONNECTION_STRING := Endpoint=sb://localhost;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=SAS_KEY_VALUE;UseDevelopmentEmulator=true;

emulator-up:
	docker compose up -d

emulator-down:
	docker compose down

emulator-setup:
	AZURE_EVENTHUB_CONNECTION_STRING="$(EMULATOR_CONNECTION_STRING)" python scripts/setup_eventhub_emulator.py

replay:
	AZURE_EVENTHUB_CONNECTION_STRING="$(EMULATOR_CONNECTION_STRING)" python -m taxipulse_replayer.main $(SAMPLE) $(ARGS)

tf-init:
	cd infra/envs/dev && terraform init

tf-fmt:
	terraform fmt -recursive infra/

tf-validate:
	cd infra/envs/dev && terraform validate

tf-plan:
	cd infra/envs/dev && terraform plan

# Applies Terraform changes. Asks for confirmation on top of Terraform's own
# interactive approval prompt - this creates/modifies real Azure resources.
tf-apply:
	@echo "This will CREATE/MODIFY Azure resources in the subscription defined by infra/envs/dev/terraform.tfvars."
	@read -p "Type 'apply' to confirm: " confirm && [ "$$confirm" = "apply" ] || (echo "Aborted."; exit 1)
	cd infra/envs/dev && terraform apply

clean:
	find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage

# Destroys every Azure resource created via Terraform. Run this at the end
# of EVERY cloud session to avoid burning through the $100 student credit.
destroy:
	@echo "This will DESTROY all Azure resources managed by Terraform in infra/envs/dev."
	@read -p "Type 'destroy' to confirm: " confirm && [ "$$confirm" = "destroy" ] || (echo "Aborted."; exit 1)
	cd infra/envs/dev && terraform destroy
