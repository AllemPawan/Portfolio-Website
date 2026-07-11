from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
import json
import shutil
import pandas as pd

from utils import generate_session_id, save_upload, cleanup_session, format_timestamp, logger, UPLOAD_DIR
from eda import full_eda, detect_problem_type, generate_class_balance, load_data
from feature_engineering import auto_preprocess, detect_feature_types
from trainer import ModelTrainer, CLASSIFIERS, REGRESSORS, generate_comparison_plots

app = FastAPI(title="Automated ML Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSIONS_FILE = os.path.join(UPLOAD_DIR, "..", "sessions.json")
os.makedirs(os.path.join(UPLOAD_DIR, ".."), exist_ok=True)


def load_sessions():
    if os.path.exists(SESSIONS_FILE):
        with open(SESSIONS_FILE) as f:
            return json.load(f)
    return {}


def save_sessions(sessions):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=2, default=str)


@app.get("/api/health")
def health():
    return {"status": "ok", "timestamp": format_timestamp()}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files are supported")

    session_id = generate_session_id()
    filepath = save_upload(file, session_id)
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    os.makedirs(session_dir, exist_ok=True)

    shutil.move(filepath, os.path.join(session_dir, "data.csv"))
    filepath = os.path.join(session_dir, "data.csv")

    df, eda_results = full_eda(filepath)

    sessions = load_sessions()
    sessions[session_id] = {
        "id": session_id,
        "filename": file.filename,
        "rows": len(df),
        "columns": len(df.columns),
        "columns_list": list(df.columns),
        "created": format_timestamp(),
        "target_col": None,
        "problem_type": None,
        "trained": False,
    }
    save_sessions(sessions)

    feature_types = detect_feature_types(df)

    return {
        "session_id": session_id,
        "filename": file.filename,
        "eda": eda_results,
        "feature_types": feature_types,
        "suggested_targets": [c for c, t in feature_types.items() if t in ("categorical", "categorical_numeric")][:10]
        + [c for c in df.select_dtypes(include=[int, float]).columns[:5]],
    }


@app.get("/api/sessions")
def list_sessions():
    sessions = load_sessions()
    return {"sessions": list(sessions.values())}


@app.get("/api/eda/{session_id}")
def get_eda(session_id: str):
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    data_path = os.path.join(session_dir, "data.csv")
    if not os.path.exists(data_path):
        raise HTTPException(404, "Session not found")

    df, eda = full_eda(data_path)
    target_col = None
    problem_type = None
    class_balance = None

    sessions = load_sessions()
    if session_id in sessions:
        target_col = sessions[session_id].get("target_col")
        problem_type = sessions[session_id].get("problem_type")

    if target_col and problem_type == "classification":
        class_balance = generate_class_balance(df[target_col])

    eda["target_col"] = target_col
    eda["problem_type"] = problem_type
    eda["class_balance"] = class_balance

    return {"session_id": session_id, "eda": eda}


@app.post("/api/train/{session_id}")
async def train(
    session_id: str,
    target_col: str = Form(...),
    algorithms: str = Form(...),
    test_size: float = Form(0.2),
    tune_hyperparams: bool = Form(False),
):
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    data_path = os.path.join(session_dir, "data.csv")
    if not os.path.exists(data_path):
        raise HTTPException(404, "Session not found")

    df = load_data(data_path)
    if target_col not in df.columns:
        raise HTTPException(400, f"Target column '{target_col}' not found")

    y = df[target_col]
    problem_type = detect_problem_type(y)

    algo_list = [a.strip() for a in algorithms.split(",")]
    available = list(CLASSIFIERS.keys()) if problem_type == "classification" else list(REGRESSORS.keys())
    algo_list = [a for a in algo_list if a in available]
    if not algo_list:
        algo_list = available[:3]

    df_processed, feature_cols = auto_preprocess(df, target_col=target_col)

    trainer = ModelTrainer(session_dir)
    X_train, X_test, y_train, y_test, used_features = trainer.split_data(
        df_processed, target_col, test_size=test_size
    )

    results = {"models": [], "best_model": None, "feature_columns": used_features, "target": target_col, "problem_type": problem_type}
    best_score = -float("inf")
    best_model_name = None

    for algo in algo_list:
        try:
            if tune_hyperparams:
                model, best_params = trainer.hyperparameter_tune(X_train, y_train, problem_type, algo)
            else:
                model = trainer.train_model(X_train, y_train, problem_type, algo)
                best_params = {}

            metrics, y_pred = trainer.evaluate(model, X_test, y_test, problem_type)

            if problem_type == "regression":
                score = metrics.get("r2", -inf)
            else:
                score = metrics.get("accuracy", 0)

            model_path = trainer.save_model(model, algo, metrics)

            model_entry = {
                "algorithm": algo,
                "best_params": best_params,
                "metrics": metrics,
                "model_path": model_path,
                "score": score,
            }
            results["models"].append(model_entry)

            if score > best_score:
                best_score = score
                best_model_name = algo
                results["best_model"] = algo
        except Exception as e:
            logger.error("Failed to train %s: %s", algo, str(e))
            results["models"].append({
                "algorithm": algo,
                "error": str(e),
                "metrics": {},
                "score": -1,
            })

    results["models"].sort(key=lambda m: m.get("score", -1), reverse=True)

    comparison_plots = generate_comparison_plots(results, problem_type, session_dir)

    trainer.save_results(results)

    sessions = load_sessions()
    if session_id in sessions:
        sessions[session_id]["target_col"] = target_col
        sessions[session_id]["problem_type"] = problem_type
        sessions[session_id]["trained"] = True
        sessions[session_id]["algorithms"] = algo_list
        sessions[session_id]["best_model"] = best_model_name
        save_sessions(sessions)

    return {
        "session_id": session_id,
        "results": results,
        "plots": comparison_plots,
    }


@app.get("/api/results/{session_id}")
def get_results(session_id: str):
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    trainer = ModelTrainer(session_dir)
    results = trainer.load_results()
    if not results.get("models"):
        raise HTTPException(404, "No results found for this session")
    return {"session_id": session_id, "results": results}


@app.get("/api/download/{session_id}/{model_name}")
def download_model(session_id: str, model_name: str):
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    models_dir = os.path.join(session_dir, "models")
    filename = f"{model_name.replace(' ', '_').lower()}.pkl"
    path = os.path.join(models_dir, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Model file not found")
    return FileResponse(path, filename=filename, media_type="application/octet-stream")


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str):
    session_dir = os.path.join(UPLOAD_DIR, session_id)
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)
    sessions = load_sessions()
    sessions.pop(session_id, None)
    save_sessions(sessions)
    return {"status": "deleted", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
