.PHONY: help install lint format test test-cov sample-data emulator-up emulator-down emulator-setup replay pipeline-local tf-init tf-fmt tf-validate tf-plan tf-apply clean destroy

help:
	@echo "TaxiPulse - available targets:"
	@echo "  install          Install project + dev dependencies in the current venv"
	@echo "  lint             Run ruff checks"
	@echo "  format           Auto-fix lint issues and format code with ruff"
	@echo "  test             Run the pytest suite"
	@echo "  test-cov         Run the pytest suite with coverage report"
	@echo "  sample-data      Download a small local sample of NYC TLC trip data"
	@echo "  emulator-up      Start the local Pub/Sub emulator (Docker)"
	@echo "  emulator-down    Stop the local Pub/Sub emulator"
	@echo "  emulator-setup   Create the topics/subscription on the running emulator"
	@echo "  replay           Run the replayer against the local emulator"
	@echo "  pipeline-local   Run the Beam pipeline (DirectRunner) against the local emulator"
	@echo "  tf-init          terraform init (infra/envs/dev)"
	@echo "  tf-fmt           terraform fmt -recursive (infra/)"
	@echo "  tf-validate      terraform validate (infra/envs/dev)"
	@echo "  tf-plan          terraform plan (infra/envs/dev)"
	@echo "  tf-apply         terraform apply (infra/envs/dev, asks for confirmation)"
	@echo "  clean            Remove caches and build artifacts"
	@echo "  destroy          Destroy ALL GCP resources managed by Terraform (asks for confirmation)"

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

emulator-up:
	docker compose up -d

emulator-down:
	docker compose down

emulator-setup:
	PUBSUB_EMULATOR_HOST=localhost:8085 python scripts/setup_pubsub_emulator.py

replay:
	PUBSUB_EMULATOR_HOST=localhost:8085 python -m taxipulse_replayer.main $(SAMPLE) $(ARGS)

pipeline-local:
	PUBSUB_EMULATOR_HOST=localhost:8085 python -m taxipulse_pipeline.main \
		--input_subscription projects/$${GCP_PROJECT_ID:-taxipulse-mds}/subscriptions/taxi-trips-sub \
		--output_sink text --output_path output/zone_aggregates \
		--dead_letter_output output/dead_letters \
		--runner DirectRunner --streaming

tf-init:
	cd infra/envs/dev && terraform init

tf-fmt:
	terraform fmt -recursive infra/

tf-validate:
	cd infra/envs/dev && terraform validate

tf-plan:
	cd infra/envs/dev && terraform plan

# Applies Terraform changes. Asks for confirmation on top of Terraform's own
# interactive approval prompt - this creates/modifies real GCP resources.
tf-apply:
	@echo "This will CREATE/MODIFY GCP resources in project defined by infra/envs/dev/terraform.tfvars."
	@read -p "Type 'apply' to confirm: " confirm && [ "$$confirm" = "apply" ] || (echo "Aborted."; exit 1)
	cd infra/envs/dev && terraform apply

clean:
	find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage

# Destroys every GCP resource created via Terraform. Run this at the end of
# EVERY cloud session to avoid burning through the $300 trial credit.
destroy:
	@echo "This will DESTROY all GCP resources managed by Terraform in infra/envs/dev."
	@read -p "Type 'destroy' to confirm: " confirm && [ "$$confirm" = "destroy" ] || (echo "Aborted."; exit 1)
	cd infra/envs/dev && terraform destroy
