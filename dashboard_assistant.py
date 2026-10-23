"""Local, data-grounded answers for common Spanish dashboard questions."""

from __future__ import annotations

import calendar
import re
import unicodedata
from datetime import date
from typing import Any

import pandas as pd


MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "setiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def _normalizar(value: Any) -> str:
    value = unicodedata.normalize("NFKD", str(value).lower())
    return "".join(char for char in value if not unicodedata.combining(char))


def _buscar_opcion(question: str, options: list[Any]) -> Any | None:
    normalized_question = _normalizar(question)
    matches = [option for option in options if _normalizar(option) in normalized_question]
    return max(matches, key=lambda option: len(_normalizar(option))) if matches else None


def _aplicar_filtros(data: pd.DataFrame, filters: dict[str, Any]) -> pd.DataFrame:
    result = data.copy()
    if result.empty:
        return result

    if "date_range" in filters:
        start, end = filters["date_range"]
        dates = pd.to_datetime(result["id_fecha"]).dt.date
        result = result[(dates >= start) & (dates <= end)]
    if "hotel" in filters:
        result = result[result["hotel_restaurante"] == filters["hotel"]]
    if "restaurant" in filters:
        result = result[result["nombre_restaurante"] == filters["restaurant"]]
    if "shift" in filters:
        result = result[pd.to_numeric(result["turno"], errors="coerce") == filters["shift"]]
    if "attention" in filters:
        result = result[result["categoria_atencion"] == filters["attention"]]
    if "cross_dining" in filters:
        result = result[result["es_cross_dining"].astype(bool) == filters["cross_dining"]]
    return result


def responder_consulta(
    question: str,
    data: pd.DataFrame,
    all_data: pd.DataFrame,
) -> tuple[str, dict[str, Any]]:
    """Answer a simple question from the current selection and detect filter requests."""
    normalized_question = _normalizar(question)
    filters: dict[str, Any] = {}

    if all_data.empty or data.empty:
        return "Todavía no hay datos disponibles para responder. Carga un archivo histórico y vuelve a consultar.", filters

    if any(term in normalized_question for term in ("restablece filtros", "limpia filtros", "quita filtros", "reinicia filtros")):
        minimum = pd.to_datetime(all_data["id_fecha"]).dt.date.min()
        maximum = pd.to_datetime(all_data["id_fecha"]).dt.date.max()
        filters = {
            "reset": True,
            "date_range": (minimum, maximum),
            "hotels": [],
            "restaurants": [],
            "shifts": [],
            "attentions": [],
            "cross": "Todos",
        }
        return "Restablecí los filtros para volver a ver todos los datos disponibles.", filters

    available_dates = pd.to_datetime(all_data["id_fecha"]).dt.date
    minimum_date = available_dates.min()
    maximum_date = available_dates.max()
    selected_month = next(
        ((name, month) for name, month in MONTHS.items() if re.search(rf"\b{ name }\b", normalized_question)),
        None,
    )
    if selected_month:
        _, month_number = selected_month
        year_match = re.search(r"\b(20\d{2})\b", normalized_question)
        year = int(year_match.group(1)) if year_match else maximum_date.year
        month_start = date(year, month_number, 1)
        month_end = date(year, month_number, calendar.monthrange(year, month_number)[1])
        start = max(month_start, minimum_date)
        end = min(month_end, maximum_date)
        if start <= end:
            filters["date_range"] = (start, end)
        else:
            month_name = next(name for name, number in MONTHS.items() if number == month_number)
            return f"No hay fechas cargadas para {month_name} de {year}. Elige un periodo disponible en los filtros.", filters

    hotels = all_data["hotel_restaurante"].dropna().unique().tolist()
    hotel = _buscar_opcion(question, hotels)
    if hotel is not None:
        filters["hotel"] = hotel

    restaurants = all_data["nombre_restaurante"].dropna().unique().tolist()
    restaurant = _buscar_opcion(question, restaurants)
    if restaurant is not None:
        filters["restaurant"] = restaurant

    shift_match = re.search(r"\bturno\s*(?:numero\s*)?(\d+)\b", normalized_question)
    if shift_match:
        requested_shift = int(shift_match.group(1))
        if requested_shift in pd.to_numeric(all_data["turno"], errors="coerce").dropna().astype(int).unique():
            filters["shift"] = requested_shift

    attentions = all_data["categoria_atencion"].dropna().unique().tolist()
    attention = _buscar_opcion(question, attentions)
    if attention is not None:
        filters["attention"] = attention

    if any(term in normalized_question for term in ("cross dining", "cross-dining", "otro hotel", "inter hotel")):
        filters["cross_dining"] = not any(term in normalized_question for term in ("local", "propio", "mismo hotel"))

    scoped_data = _aplicar_filtros(data, filters)
    if scoped_data.empty and filters:
        scoped_data = _aplicar_filtros(all_data, filters)
    if scoped_data.empty:
        return "No encontré reservas con esa selección. Prueba con otro mes, hotel o restaurante.", filters

    total_pax = int(pd.to_numeric(scoped_data["total_pax"], errors="coerce").fillna(0).sum())
    total_reservations = len(scoped_data)
    prefix = ""
    if filters:
        criteria = []
        if "date_range" in filters:
            start, end = filters["date_range"]
            criteria.append(f"fechas {start:%d/%m/%Y} a {end:%d/%m/%Y}")
        if hotel is not None:
            criteria.append(f"hotel {hotel}")
        if restaurant is not None:
            criteria.append(f"restaurante {restaurant}")
        if "shift" in filters:
            criteria.append(f"turno {filters['shift']}")
        if attention is not None:
            criteria.append(f"atención {attention}")
        if "cross_dining" in filters:
            criteria.append("huéspedes de otros hoteles" if filters["cross_dining"] else "huéspedes locales")
        if criteria:
            reservation_label = "reserva" if total_reservations == 1 else "reservas"
            prefix = f"Apliqué el filtro de {', '.join(criteria)}. En esa selección hay {total_reservations:,} {reservation_label} y {total_pax:,} comensales. "

    if any(term in normalized_question for term in ("pronostico", "prediccion", "red neuronal", "como se calcula")):
        response = (
            "La previsión usa una red neuronal entrenada con la demanda diaria por restaurante y turno. "
            "Considera estacionalidad y rezagos recientes; se contrasta con días que no participaron en el entrenamiento. "
            "Es una estimación, no una garantía. El error de validación aparece junto al gráfico."
        )
    elif any(term in normalized_question for term in ("de donde", "fuente", "actualiza", "base de datos")):
        response = "Los resultados se calculan con las reservas cargadas en la base de datos del dashboard. La consulta se actualiza automáticamente, normalmente en un máximo de 60 segundos; las cargas manuales actualizan la vista de inmediato."
    elif "capacidad" in normalized_question:
        response = "La capacidad registrada puede estar incompleta. Cuando no existe un aforo confiable en la base, el tablero no debería presentar el porcentaje como una medición real; revisa el dato del restaurante antes de tomar decisiones."
    elif any(term in normalized_question for term in ("mayor demanda", "mas comensales", "mas demanda", "mas popular", "top restaurante", "restaurante lider")):
        ranking = scoped_data.groupby("nombre_restaurante")["total_pax"].sum().sort_values(ascending=False)
        response = f"El restaurante con más comensales en esta selección es {ranking.index[0]}, con {int(ranking.iloc[0]):,} comensales."
    elif any(term in normalized_question for term in ("hotel", "entre hoteles")) and any(term in normalized_question for term in ("mas", "mayor", "lider", "compar")):
        ranking = scoped_data.groupby("hotel_restaurante")["total_pax"].sum().sort_values(ascending=False)
        response = f"El hotel con más comensales en esta selección es {ranking.index[0]}, con {int(ranking.iloc[0]):,} comensales."
    elif any(term in normalized_question for term in ("pico", "dia mas ocupado", "dia con mas", "maximo")):
        daily = scoped_data.groupby("id_fecha")["total_pax"].sum().sort_values(ascending=False)
        response = f"El día con más demanda es {pd.to_datetime(daily.index[0]).strftime('%d/%m/%Y')}, con {int(daily.iloc[0]):,} comensales."
    elif any(term in normalized_question for term in ("promedio", "media")):
        average = total_pax / total_reservations if total_reservations else 0
        response = f"El promedio es de {average:.1f} comensales por reserva, calculado con {total_reservations:,} reservas."
    elif any(term in normalized_question for term in ("nino", "menor", "familia", "bebe")):
        children = int(scoped_data["num_ninos"].sum() + scoped_data["num_bebes"].sum())
        response = f"En esta selección hay {children:,} niños y bebés, dentro de {total_pax:,} comensales."
    elif any(term in normalized_question for term in ("mes a mes", "por mes", "mensual")):
        monthly = scoped_data.assign(mes=pd.to_datetime(scoped_data["id_fecha"]).dt.to_period("M").astype(str))
        totals = monthly.groupby("mes")["total_pax"].sum().sort_values(ascending=False)
        response = "Comensales por mes: " + "; ".join(f"{month}: {int(value):,}" for month, value in totals.items()) + "."
    elif any(term in normalized_question for term in ("reserva", "cuantas", "cuantos registros")):
        response = f"Hay {total_reservations:,} reservas en la selección actual, con {total_pax:,} comensales en total."
    else:
        response = (
            f"En la selección actual hay {total_reservations:,} reservas y {total_pax:,} comensales. "
            "También puedo comparar hoteles, encontrar el restaurante o día con más demanda, resumir por mes, "
            "contar familias o filtrar por mes, hotel, restaurante y turno."
        )

    return prefix + response, filters