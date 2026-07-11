import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler, LabelEncoder, OneHotEncoder
from sklearn.impute import SimpleImputer
from utils import logger


def detect_feature_types(df):
    types = {}
    for col in df.columns:
        dtype = df[col].dtype
        if pd.api.types.is_numeric_dtype(dtype):
            unique_ratio = df[col].nunique() / max(len(df), 1)
            if unique_ratio < 0.01 and df[col].nunique() <= 15:
                types[col] = "categorical_numeric"
            else:
                types[col] = "numeric"
        elif pd.api.types.is_object_dtype(dtype):
            if df[col].nunique() <= 25:
                types[col] = "categorical"
            elif df[col].str.len().mean() > 100:
                types[col] = "text"
            else:
                types[col] = "categorical"
        elif pd.api.types.is_datetime64_dtype(dtype):
            types[col] = "datetime"
        else:
            types[col] = "other"
    return types


def suggest_imputation(df):
    suggestions = {}
    for col in df.columns:
        missing_count = df[col].isnull().sum()
        if missing_count == 0:
            continue
        if pd.api.types.is_numeric_dtype(df[col].dtype):
            suggestions[col] = "median"
        else:
            suggestions[col] = "most_frequent"
    return suggestions


def handle_missing_values(df, strategy_dict=None):
    df = df.copy()
    if strategy_dict is None:
        strategy_dict = suggest_imputation(df)
    for col, strategy in strategy_dict.items():
        if col not in df.columns:
            continue
        if strategy == "drop":
            df = df.dropna(subset=[col])
        elif strategy in ("mean", "median", "most_frequent"):
            imputer = SimpleImputer(strategy=strategy)
            if pd.api.types.is_numeric_dtype(df[col].dtype):
                df[col] = imputer.fit_transform(df[[col]]).ravel()
            else:
                df[col] = imputer.fit_transform(df[[col]]).ravel()
        elif strategy == "constant":
            df[col] = df[col].fillna("Unknown")
    return df


def encode_categorical(df, method="auto"):
    df = df.copy()
    feature_types = detect_feature_types(df)
    categorical_cols = [c for c, t in feature_types.items() if t in ("categorical", "categorical_numeric")]
    label_encoders = {}
    for col in categorical_cols:
        if method == "auto":
            n_unique = df[col].nunique()
            if n_unique <= 2:
                le = LabelEncoder()
                df[col] = le.fit_transform(df[col].astype(str))
                label_encoders[col] = le
            elif n_unique <= 15:
                dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
                df = pd.concat([df.drop(columns=[col]), dummies], axis=1)
            else:
                le = LabelEncoder()
                df[col + "_encoded"] = le.fit_transform(df[col].astype(str))
                label_encoders[col] = le
        elif method == "label":
            le = LabelEncoder()
            df[col] = le.fit_transform(df[col].astype(str))
            label_encoders[col] = le
        elif method == "onehot":
            dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
            df = pd.concat([df.drop(columns=[col]), dummies], axis=1)
    return df, label_encoders


def scale_features(df, method="standard"):
    df = df.copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if not numeric_cols:
        return df, None
    scaler = StandardScaler() if method == "standard" else MinMaxScaler()
    df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
    return df, scaler


def auto_preprocess(df, target_col=None, scale=True, encode=True, handle_missing=True):
    logger.info("Auto-preprocessing data: %d rows, %d cols", len(df), len(df.columns))
    if handle_missing:
        df = handle_missing_values(df)
    if encode:
        df, _ = encode_categorical(df)
    feature_types = detect_feature_types(df)
    non_feature_cols = [target_col] if target_col else []
    feature_cols = [c for c in df.columns if c not in non_feature_cols and feature_types.get(c) != "text"]
    if scale and feature_cols:
        scaler = StandardScaler()
        numeric_feats = [c for c in feature_cols if pd.api.types.is_numeric_dtype(df[c].dtype)]
        if numeric_feats:
            df[numeric_feats] = scaler.fit_transform(df[numeric_feats])
    logger.info("Preprocessing done: %d features", len(feature_cols))
    return df, feature_cols
