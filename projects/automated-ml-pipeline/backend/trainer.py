import pandas as pd
import numpy as np
import pickle
import os
import json
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, roc_curve, auc, classification_report,
    mean_absolute_error, mean_squared_error, r2_score,
)
from sklearn.linear_model import LogisticRegression, LinearRegression, Ridge, Lasso
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.svm import SVC, SVR
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from utils import fig_to_base64, logger

CLASSIFIERS = {
    "Logistic Regression": (LogisticRegression, {"max_iter": 1000, "random_state": 42, "n_jobs": -1}),
    "Random Forest": (RandomForestClassifier, {"random_state": 42, "n_jobs": -1}),
    "Gradient Boosting": (GradientBoostingClassifier, {"random_state": 42}),
    "SVM": (SVC, {"random_state": 42, "probability": True}),
    "KNN": (KNeighborsClassifier, {"n_jobs": -1}),
    "Decision Tree": (DecisionTreeClassifier, {"random_state": 42}),
}

REGRESSORS = {
    "Linear Regression": (LinearRegression, {"n_jobs": -1}),
    "Ridge": (Ridge, {"random_state": 42}),
    "Lasso": (Lasso, {"random_state": 42}),
    "Random Forest": (RandomForestRegressor, {"random_state": 42, "n_jobs": -1}),
    "Gradient Boosting": (GradientBoostingRegressor, {"random_state": 42}),
    "SVR": (SVR, {}),
    "KNN": (KNeighborsRegressor, {"n_jobs": -1}),
}

CLASSIFIER_PARAM_GRIDS = {
    "Logistic Regression": {
        "C": [0.01, 0.1, 1, 10],
        "solver": ["lbfgs", "liblinear"],
    },
    "Random Forest": {
        "n_estimators": [50, 100, 200],
        "max_depth": [None, 10, 20],
        "min_samples_split": [2, 5],
    },
    "Gradient Boosting": {
        "n_estimators": [50, 100],
        "learning_rate": [0.01, 0.1],
        "max_depth": [3, 5],
    },
    "SVM": {
        "C": [0.1, 1, 10],
        "kernel": ["rbf", "linear"],
    },
    "KNN": {
        "n_neighbors": [3, 5, 7, 9],
        "weights": ["uniform", "distance"],
    },
    "Decision Tree": {
        "max_depth": [None, 5, 10, 20],
        "min_samples_split": [2, 5, 10],
    },
}

REGRESSOR_PARAM_GRIDS = {
    "Linear Regression": {},
    "Ridge": {"alpha": [0.01, 0.1, 1, 10, 100]},
    "Lasso": {"alpha": [0.001, 0.01, 0.1, 1, 10]},
    "Random Forest": {
        "n_estimators": [50, 100, 200],
        "max_depth": [None, 10, 20],
        "min_samples_split": [2, 5],
    },
    "Gradient Boosting": {
        "n_estimators": [50, 100],
        "learning_rate": [0.01, 0.1],
        "max_depth": [3, 5],
    },
    "SVR": {"C": [0.1, 1, 10], "kernel": ["rbf", "linear"]},
    "KNN": {"n_neighbors": [3, 5, 7, 9], "weights": ["uniform", "distance"]},
}


class ModelTrainer:
    def __init__(self, session_dir):
        self.session_dir = session_dir
        self.models_dir = os.path.join(session_dir, "models")
        self.results_file = os.path.join(session_dir, "results.json")
        os.makedirs(self.models_dir, exist_ok=True)

    def split_data(self, df, target_col, test_size=0.2, random_state=42):
        X = df.drop(columns=[target_col])
        y = df[target_col]

        numeric_cols = X.select_dtypes(include=[np.number]).columns
        X = X[numeric_cols]
        X = X.fillna(X.median())

        y = y.fillna(y.mode()[0] if hasattr(y.mode(), "__iter__") else y)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        logger.info("Split: train=%d, test=%d", len(X_train), len(X_test))
        return X_train, X_test, y_train, y_test, X.columns.tolist()

    def train_model(self, X_train, y_train, problem_type, algorithm_name, params=None):
        if problem_type == "classification":
            algo_class, default_params = CLASSIFIERS[algorithm_name]
        else:
            algo_class, default_params = REGRESSORS[algorithm_name]

        merged_params = {**default_params}
        if params:
            merged_params.update(params)

        model = algo_class(**merged_params)
        model.fit(X_train, y_train)
        logger.info("Trained %s model: %s", problem_type, algorithm_name)
        return model

    def evaluate(self, model, X_test, y_test, problem_type):
        y_pred = model.predict(X_test)
        metrics = {}

        if problem_type == "classification":
            metrics["accuracy"] = round(accuracy_score(y_test, y_pred), 4)
            try:
                metrics["precision"] = round(precision_score(y_test, y_pred, average="weighted", zero_division=0), 4)
                metrics["recall"] = round(recall_score(y_test, y_pred, average="weighted", zero_division=0), 4)
                metrics["f1"] = round(f1_score(y_test, y_pred, average="weighted", zero_division=0), 4)
            except Exception:
                pass

            cm = confusion_matrix(y_test, y_pred)
            metrics["confusion_matrix"] = cm.tolist()

            try:
                if hasattr(model, "predict_proba"):
                    y_prob = model.predict_proba(X_test)
                    if y_prob.shape[1] == 2:
                        fpr, tpr, _ = roc_curve(y_test, y_prob[:, 1])
                        metrics["roc_auc"] = round(auc(fpr, tpr), 4)

                report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
                metrics["classification_report"] = report
            except Exception:
                pass

        else:
            metrics["mae"] = round(mean_absolute_error(y_test, y_pred), 4)
            metrics["mse"] = round(mean_squared_error(y_test, y_pred), 4)
            metrics["rmse"] = round(np.sqrt(mean_squared_error(y_test, y_pred)), 4)
            metrics["r2"] = round(r2_score(y_test, y_pred), 4)
            try:
                metrics["mape"] = round(
                    np.mean(np.abs((y_test - y_pred) / (y_test + 1e-10))) * 100, 2
                )
            except Exception:
                pass

        return metrics, y_pred

    def hyperparameter_tune(self, X_train, y_train, problem_type, algorithm_name):
        if problem_type == "classification":
            algo_class, default_params = CLASSIFIERS[algorithm_name]
            param_grid = CLASSIFIER_PARAM_GRIDS.get(algorithm_name, {})
        else:
            algo_class, default_params = REGRESSORS[algorithm_name]
            param_grid = REGRESSOR_PARAM_GRIDS.get(algorithm_name, {})

        if not param_grid:
            logger.info("No param grid for %s, skipping tuning", algorithm_name)
            model = self.train_model(X_train, y_train, problem_type, algorithm_name)
            return model, {}

        model = algo_class(**default_params)
        scoring = "accuracy" if problem_type == "classification" else "neg_mean_squared_error"
        try:
            gs = GridSearchCV(
                model, param_grid, scoring=scoring, cv=3, n_jobs=-1, verbose=0
            )
            gs.fit(X_train, y_train)
            logger.info("Tuning %s: best params %s", algorithm_name, gs.best_params_)
            return gs.best_estimator_, gs.best_params_
        except Exception as e:
            logger.warning("Tuning failed for %s: %s", algorithm_name, str(e))
            model = self.train_model(X_train, y_train, problem_type, algorithm_name)
            return model, {}

    def save_model(self, model, algorithm_name, metrics):
        filename = f"{algorithm_name.replace(' ', '_').lower()}.pkl"
        path = os.path.join(self.models_dir, filename)
        with open(path, "wb") as f:
            pickle.dump(model, f)
        return path

    def load_results(self):
        if os.path.exists(self.results_file):
            with open(self.results_file) as f:
                return json.load(f)
        return {"models": [], "best_model": None, "feature_columns": []}

    def save_results(self, results):
        with open(self.results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)


def generate_comparison_plots(results, problem_type, session_dir):
    plots = {}
    models_data = results.get("models", [])
    if not models_data:
        return plots

    df_metrics = pd.DataFrame(models_data)

    if problem_type == "classification":
        metrics_to_plot = [m for m in ["accuracy", "precision", "recall", "f1"] if m in df_metrics.columns]
    else:
        metrics_to_plot = [m for m in ["r2", "rmse", "mae"] if m in df_metrics.columns]

    if metrics_to_plot:
        fig, ax = plt.subplots(figsize=(10, 5))
        x = np.arange(len(models_data))
        width = 0.8 / len(metrics_to_plot)
        for i, metric in enumerate(metrics_to_plot):
            values = df_metrics[metric].values
            bars = ax.bar(x + i * width - len(metrics_to_plot) * width / 2, values, width, label=metric.upper())
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                        f"{val:.3f}", ha="center", va="bottom", fontsize=7, color="#cbd5e1")
        ax.set_xticks(x)
        ax.set_xticklabels([m.get("algorithm", f"Model {i}") for i, m in enumerate(models_data)], rotation=30, ha="right")
        ax.set_ylabel("Score")
        ax.set_title("Model Comparison", color="#e2e8f0", fontsize=14)
        ax.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1")
        ax.set_ylim(0, max(1, df_metrics[metrics_to_plot].values.max() * 1.2))
        plots["comparison"] = fig_to_base64(fig)

    if problem_type == "regression":
        fig, ax = plt.subplots(figsize=(8, 5))
        for model_data in models_data:
            algo = model_data.get("algorithm", "Model")
            actual_vs_pred = model_data.get("actual_vs_predicted")
        plots["regression_plot"] = None
        plt.close("all")

    return plots
