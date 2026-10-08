# Deliberately NOT built from the monorepo's root pyproject.toml - that
# would pull in pyspark/prophet/geopandas/mlflow (the processing/ML side's
# deps), which this serving layer never imports. It only reads already-
# materialized Delta tables via delta-rs (see services/warehouse.py), so
# its own requirements.txt lists just what it actually needs - a much
# smaller, faster-to-build, faster-to-start image.
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/taxipulse_api ./taxipulse_api
ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["uvicorn", "taxipulse_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
