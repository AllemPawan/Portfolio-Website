# Automated ML Pipeline

Upload a CSV and let the pipeline handle the rest — EDA, feature engineering, multi-model training, hyperparameter tuning, and model comparison.

## Quick Start

```bash
# Backend
cd backend
pip install -r ../requirements.txt
uvicorn api:app --reload --port 8000

# Open http://localhost:8000/frontend/
```

### Docker

```bash
docker compose up -d
# Open http://localhost:8000/frontend/
```

## Features

- **Auto EDA** — statistics, distributions, correlations, missing values
- **Auto Preprocessing** — imputation, encoding, scaling
- **13 Algorithms** — 6 classification + 7 regression
- **Hyperparameter Tuning** — GridSearchCV with sensible grids
- **Model Comparison** — side-by-side metrics, confusion matrices, charts
- **Export** — download trained models as .pkl files

## API

| Endpoint | Method | Description |
|---|---|---|
| `/api/upload` | POST | Upload CSV, get EDA |
| `/api/eda/{session_id}` | GET | Get EDA results |
| `/api/train/{session_id}` | POST | Train models |
| `/api/results/{session_id}` | GET | Get training results |
| `/api/download/{session_id}/{model}` | GET | Download .pkl |
| `/api/sessions` | GET | List sessions |
| `/api/sessions/{session_id}` | DELETE | Delete session |
