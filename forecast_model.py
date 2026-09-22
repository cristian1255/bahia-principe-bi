"""Forecasting neuronal de demanda diaria por restaurante y turno."""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler


FEATURES = [
    "day_sin",
    "day_cos",
    "month_sin",
    "month_cos",
    "trend",
    "turno",
    "capacity",
    "restaurant_code",
    "lag_7",
    "lag_14",
    "lag_28",
    "rolling_7",
    "rolling_28",
]


@dataclass
class ForecastResult:
    model: MLPRegressor
    scaler: StandardScaler
    history: pd.DataFrame
    metrics: Dict[str, float]
    groups: pd.DataFrame


def _normalise_history(df: pd.DataFrame) -> pd.DataFrame:
    required = {"id_fecha", "id_restaurante", "turno", "total_pax"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas para entrenar: {', '.join(sorted(missing))}")

    source = df.copy()
    source["id_fecha"] = pd.to_datetime(source["id_fecha"]).dt.normalize()
    source["id_restaurante"] = source["id_restaurante"].astype(str)
    source["turno"] = pd.to_numeric(source["turno"], errors="coerce").fillna(1).astype(int)
    source["total_pax"] = pd.to_numeric(source["total_pax"], errors="coerce").fillna(0).clip(lower=0)
    source["capacity"] = pd.to_numeric(
        source.get("capacidad_maxima_pax", pd.Series(120, index=source.index)),
        errors="coerce",
    ).fillna(120)

    grouped = (
        source.groupby(["id_fecha", "id_restaurante", "turno"], as_index=False)
        .agg(total_pax=("total_pax", "sum"), capacity=("capacity", "max"))
    )
    if grouped.empty:
        raise ValueError("No hay registros válidos para entrenar el pronóstico.")

    start = grouped["id_fecha"].min()
    end = grouped["id_fecha"].max()
    all_dates = pd.date_range(start, end, freq="D")
    groups = grouped[["id_restaurante", "turno", "capacity"]].drop_duplicates()
    calendar = groups.assign(_key=1).merge(
        pd.DataFrame({"id_fecha": all_dates, "_key": 1}), on="_key"
    ).drop(columns="_key")
    result = calendar.merge(
        grouped, on=["id_fecha", "id_restaurante", "turno", "capacity"], how="left"
    )
    result["total_pax"] = result["total_pax"].fillna(0.0)
    return result.sort_values(["id_restaurante", "turno", "id_fecha"]).reset_index(drop=True)


def _make_features(history: pd.DataFrame) -> pd.DataFrame:
    frame = history.copy()
    frame["restaurant_code"] = pd.factorize(frame["id_restaurante"])[0].astype(float)
    frame["day_of_year"] = frame["id_fecha"].dt.dayofyear
    frame["day_sin"] = np.sin(2 * np.pi * frame["day_of_year"] / 365.25)
    frame["day_cos"] = np.cos(2 * np.pi * frame["day_of_year"] / 365.25)
    frame["month_sin"] = np.sin(2 * np.pi * frame["id_fecha"].dt.month / 12)
    frame["month_cos"] = np.cos(2 * np.pi * frame["id_fecha"].dt.month / 12)
    frame["trend"] = (frame["id_fecha"] - frame["id_fecha"].min()).dt.days / 365.25

    grouped = frame.groupby(["id_restaurante", "turno"], group_keys=False)
    for days in (7, 14, 28):
        frame[f"lag_{days}"] = grouped["total_pax"].shift(days)
    frame["rolling_7"] = grouped["total_pax"].transform(
        lambda values: values.shift(1).rolling(7, min_periods=1).mean()
    )
    frame["rolling_28"] = grouped["total_pax"].transform(
        lambda values: values.shift(1).rolling(28, min_periods=1).mean()
    )
    frame["turno"] = frame["turno"].astype(float)
    frame = frame.dropna(subset=FEATURES).copy()
    return frame


def train_neural_forecast(df: pd.DataFrame, validation_days: int = 14) -> ForecastResult:
    """Entrena una red neuronal MLP con separación temporal de validación."""
    history = _normalise_history(df)
    feature_frame = _make_features(history)
    if len(feature_frame) < 30:
        raise ValueError("Se necesitan al menos 30 observaciones diarias con rezagos para entrenar.")

    cutoff = feature_frame["id_fecha"].max() - pd.Timedelta(days=max(1, validation_days))
    train = feature_frame[feature_frame["id_fecha"] <= cutoff]
    validation = feature_frame[feature_frame["id_fecha"] > cutoff]
    if len(train) < 20 or validation.empty:
        raise ValueError("No hay suficientes fechas para separar entrenamiento y validación temporal.")

    scaler = StandardScaler()
    x_train = scaler.fit_transform(train[FEATURES])
    x_validation = scaler.transform(validation[FEATURES])
    model = MLPRegressor(
        hidden_layer_sizes=(64, 32),
        activation="relu",
        solver="adam",
        learning_rate_init=0.002,
        max_iter=400,
        early_stopping=True,
        validation_fraction=0.15,
        random_state=42,
    )
    model.fit(x_train, train["total_pax"])
    predicted = np.clip(model.predict(x_validation), 0, None)
    actual = validation["total_pax"].to_numpy()
    metrics = {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "validation_rows": float(len(validation)),
        "training_rows": float(len(train)),
    }
    groups = history[["id_restaurante", "turno", "capacity"]].drop_duplicates()
    return ForecastResult(model, scaler, history, metrics, groups)


def forecast_future(result: ForecastResult, horizon_days: int) -> pd.DataFrame:
    """Genera predicción diaria recursiva para cualquier horizonte futuro."""
    if horizon_days < 1 or horizon_days > 1825:
        raise ValueError("El horizonte debe estar entre 1 y 1825 días (5 años).")

    history = result.history.copy()
    last_date = history["id_fecha"].max()
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=horizon_days, freq="D")
    working = history.copy()
    rows: List[Dict[str, Any]] = []

    for current_date in future_dates:
        feature_rows: List[Dict[str, Any]] = []
        metadata: List[Tuple[str, int, float]] = []
        for group in result.groups.itertuples(index=False):
            mask = (working["id_restaurante"] == group.id_restaurante) & (working["turno"] == group.turno)
            series = working.loc[mask].sort_values("id_fecha")["total_pax"].to_numpy()
            if len(series) < 28:
                padded = np.pad(series, (28 - len(series), 0), mode="constant")
            else:
                padded = series[-28:]
            restaurant_code = float(
                pd.factorize(history["id_restaurante"])[0][
                    list(history["id_restaurante"].unique()).index(group.id_restaurante)
                ]
            )
            day_of_year = current_date.dayofyear
            feature_rows.append({
                "day_sin": np.sin(2 * np.pi * day_of_year / 365.25),
                "day_cos": np.cos(2 * np.pi * day_of_year / 365.25),
                "month_sin": np.sin(2 * np.pi * current_date.month / 12),
                "month_cos": np.cos(2 * np.pi * current_date.month / 12),
                "trend": (current_date - history["id_fecha"].min()).days / 365.25,
                "turno": float(group.turno),
                "capacity": float(group.capacity),
                "restaurant_code": restaurant_code,
                "lag_7": padded[-7],
                "lag_14": padded[-14],
                "lag_28": padded[-28],
                "rolling_7": float(np.mean(padded[-7:])),
                "rolling_28": float(np.mean(padded)),
            })
            metadata.append((group.id_restaurante, int(group.turno), float(group.capacity)))

        predictions = np.clip(
            result.model.predict(result.scaler.transform(pd.DataFrame(feature_rows)[FEATURES])),
            0,
            None,
        )
        new_rows = []
        for (restaurant, turno, capacity), prediction in zip(metadata, predictions):
            prediction = round(float(prediction), 2)
            new_rows.append({
                "id_fecha": current_date,
                "id_restaurante": restaurant,
                "turno": turno,
                "capacity": capacity,
                "total_pax": prediction,
            })
            rows.append({
                "fecha": current_date.date(),
                "restaurante": restaurant,
                "turno": turno,
                "pax_predichos": round(prediction, 1),
            })
        working = pd.concat([working, pd.DataFrame(new_rows)], ignore_index=True)

    forecast = pd.DataFrame(rows)
    forecast["mes"] = pd.to_datetime(forecast["fecha"]).dt.to_period("M").astype(str)
    return forecast


def save_forecast_model(result: ForecastResult, path: str = "models/demand_mlp.pkl") -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as file:
        pickle.dump(result, file)


def load_forecast_model(path: str = "models/demand_mlp.pkl") -> ForecastResult:
    with Path(path).open("rb") as file:
        return pickle.load(file)
