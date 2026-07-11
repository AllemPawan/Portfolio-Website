import pandas as pd
import numpy as np
import base64
import io
import matplotlib.pyplot as plt
import seaborn as sns
from utils import fig_to_base64, logger


def load_data(filepath, nrows=None):
    df = pd.read_csv(filepath, nrows=nrows)
    logger.info("Loaded %d rows, %d columns", len(df), len(df.columns))
    return df


def generate_overview(df):
    buf = io.StringIO()
    df.info(buf=buf)
    info_str = buf.getvalue()

    desc = df.describe(include="all").to_dict()

    missing = df.isnull().sum().to_dict()
    missing_pct = (df.isnull().sum() / len(df) * 100).round(2).to_dict()

    dtypes = df.dtypes.astype(str).to_dict()

    unique_counts = {col: int(df[col].nunique()) for col in df.columns}

    sample_values = {}
    for col in df.columns:
        if df[col].dtype == "object":
            sample_values[col] = df[col].dropna().value_counts().head(5).to_dict()
        else:
            sample_values[col] = {
                "min": float(df[col].min()) if pd.notna(df[col].min()) else None,
                "max": float(df[col].max()) if pd.notna(df[col].max()) else None,
            }

    return {
        "shape": {"rows": len(df), "columns": len(df.columns)},
        "columns": list(df.columns),
        "dtypes": dtypes,
        "missing": missing,
        "missing_pct": missing_pct,
        "unique_counts": unique_counts,
        "describe": desc,
        "sample_values": sample_values,
        "info": info_str,
    }


def generate_correlation_heatmap(df):
    numeric_df = df.select_dtypes(include=[np.number])
    if numeric_df.shape[1] < 2:
        return None

    corr = numeric_df.corr()
    fig, ax = plt.subplots(figsize=(max(6, corr.shape[1] * 0.6), max(5, corr.shape[0] * 0.6)))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(
        corr, mask=mask, annot=True, fmt=".2f", cmap="coolwarm",
        cbar_kws={"shrink": 0.8}, linewidths=0.5, ax=ax,
        annot_kws={"color": "#e2e8f0", "fontsize": 8}
    )
    ax.set_title("Correlation Matrix", color="#e2e8f0", fontsize=14, pad=16)
    return fig_to_base64(fig)


def generate_distribution_plots(df):
    plots = {}
    numeric_cols = df.select_dtypes(include=[np.number]).columns

    for col in numeric_cols[:10]:
        fig, ax = plt.subplots(figsize=(7, 4))
        valid = df[col].dropna()
        if len(valid) == 0:
            plt.close(fig)
            continue
        ax.hist(valid, bins=30, color="#6366f1", alpha=0.7, edgecolor="#4338ca", linewidth=0.5)
        ax.axvline(valid.mean(), color="#f59e0b", linestyle="--", linewidth=1.5, label=f"Mean: {valid.mean():.2f}")
        ax.axvline(valid.median(), color="#10b981", linestyle="--", linewidth=1.5, label=f"Median: {valid.median():.2f}")
        ax.set_xlabel(col)
        ax.set_ylabel("Frequency")
        ax.set_title(f"Distribution of {col}", color="#e2e8f0", fontsize=13)
        ax.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#cbd5e1")
        plots[col] = fig_to_base64(fig)

    return plots


def generate_missing_heatmap(df):
    missing = df.isnull()
    if missing.sum().sum() == 0:
        return None

    fig, ax = plt.subplots(figsize=(max(8, len(df.columns) * 0.5), 6))
    sns.heatmap(
        missing, cbar=False, cmap=["#1e293b", "#6366f1"],
        yticklabels=False, ax=ax
    )
    ax.set_title("Missing Values Heatmap", color="#e2e8f0", fontsize=13, pad=16)
    ax.set_xlabel("Columns")
    return fig_to_base64(fig)


def detect_problem_type(y):
    unique = y.nunique()
    if y.dtype == "object" or unique <= 15:
        return "classification"
    return "regression"


def generate_class_balance(y):
    if detect_problem_type(y) != "classification":
        return None

    counts = y.value_counts()
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = sns.color_palette("viridis", len(counts))
    bars = ax.bar(range(len(counts)), counts.values, color=colors, edgecolor="#334155")
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels([str(c)[:20] for c in counts.index], rotation=45, ha="right")
    ax.set_ylabel("Count")
    ax.set_title("Target Class Distribution", color="#e2e8f0", fontsize=13)
    for bar, val in zip(bars, counts.values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(counts) * 0.01,
                str(val), ha="center", va="bottom", color="#cbd5e1", fontsize=9)
    return fig_to_base64(fig)


def full_eda(filepath):
    df = load_data(filepath)
    overview = generate_overview(df)
    corr_heatmap = generate_correlation_heatmap(df)
    distributions = generate_distribution_plots(df)
    missing_heatmap = generate_missing_heatmap(df)

    target_col = None
    problem_type = None
    class_balance = None
    return df, {
        "overview": overview,
        "correlation_heatmap": corr_heatmap,
        "distributions": distributions,
        "missing_heatmap": missing_heatmap,
        "target_col": target_col,
        "problem_type": problem_type,
        "class_balance": class_balance,
    }
