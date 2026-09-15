#!/bin/bash
set -e

echo "======================================================"
echo "   Campus360 — Analytics & Early Warning Platform     "
echo "======================================================"

# Ensure processed directory exists
mkdir -p /app/data/processed /app/models /app/logs

# Ensure warehouse database exists; if not, run master ETL pipeline
if [ ! -f "/app/data/processed/warehouse.db" ]; then
    echo "[ENTRYPOINT] warehouse.db not found. Running master ETL pipeline..."
    python /app/etl/pipeline.py
else
    echo "[ENTRYPOINT] SQLite warehouse detected at /app/data/processed/warehouse.db"
fi

# Ensure ML models exist; if not, train them
if [ ! -f "/app/models/next_semester_marks_model.pkl" ]; then
    echo "[ENTRYPOINT] Model 1 missing. Training performance regression model..."
    python /app/models/model_1_performance_regression.py
fi

if [ ! -f "/app/models/at_risk_classifier_model.pkl" ]; then
    echo "[ENTRYPOINT] Model 2 missing. Training at-risk classifier model..."
    python /app/models/model_2_at_risk_classifier.py
fi

echo "[ENTRYPOINT] Starting Campus360 Streamlit Dashboard on port 8501..."
exec streamlit run /app/dashboard/app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
