"""
app.py
======
Sistema Analítico Operativo y Predictivo de Reservas para Restaurantes de Especialidad
Cadena Hotelera Bahía Príncipe Hotels & Resorts.

Desarrollado con Streamlit, SQLAlchemy, Pandas, Plotly y Scikit-Learn.
Diseñado para despliegue 24/7 gratuito en Streamlit Community Cloud y Render / HF Spaces.
"""

import os
import io
from datetime import datetime, date, timedelta
from typing import Dict, Any, Tuple, Optional, List

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text

from config_db import (
    get_engine,
    get_db_session,
    init_db,
    get_database_url,
    FactReservasRestaurantes,
    DimServicio,
    DimAtencion,
    DimHotel,
    DimTiempo,
)
from etl_pipeline import (
    ejecutar_etl_desde_archivo,
    inicializar_demo_y_cargar_bd,
    HOTELES_CATALOGO,
    RESTAURANTES_CATALOGO,
    HORARIOS_CATALOGO,
    TIPOS_ATENCION_CATALOGO,
)

px.defaults.template = "plotly_white"
px.defaults.color_discrete_sequence = ["#0B4F39", "#B49A62", "#667A70", "#9A5C4A", "#627A8A"]

# =====================================================================
# CONFIGURACIÓN DE SERVIDOR PARA ACCESO LOCAL/ANDROID
# =====================================================================
# El servidor de Streamlit debe exponerse en 0.0.0.0 para permitir la
# conexión desde el teléfono Android por Wi‑Fi o cuando se envuelve la app
# web en una WebView local. La ejecución habitual sigue siendo:
#   streamlit run app.py --server.address 0.0.0.0 --server.port 8501
STREAMLIT_HOST = "0.0.0.0"
STREAMLIT_PORT = 8501


def get_streamlit_run_command() -> List[str]:
    """Devuelve la línea de comando recomendada para arrancar Streamlit."""
    return [
        "streamlit",
        "run",
        os.path.abspath(__file__),
        "--server.address",
        STREAMLIT_HOST,
        "--server.port",
        str(STREAMLIT_PORT),
        "--server.headless",
        "true",
    ]


@st.cache_data(ttl=600, show_spinner=False)
def entrenar_pronostico_cacheado(data: pd.DataFrame):
    from forecast_model import save_forecast_model, train_neural_forecast

    result = train_neural_forecast(data)
    save_forecast_model(result)
    return result


@st.cache_data(ttl=600, show_spinner=False)
def generar_pronostico_cacheado(data: pd.DataFrame, horizon_days: int) -> pd.DataFrame:
    from forecast_model import forecast_future

    result = entrenar_pronostico_cacheado(data)
    return forecast_future(result, horizon_days)


# =====================================================================
# CONFIGURACIÓN DE PÁGINA Y ESTILOS CSS CORPORATIVOS
# =====================================================================

st.set_page_config(
    page_title="Bahía Príncipe | BI Restaurantes de Especialidad",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inyección de estilos CSS elegantes con temática Bahía Príncipe
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;500;600;700&display=swap');

    :root {
        --bp-forest: #0B4F39;
        --bp-forest-deep: #083D2D;
        --bp-gold: #B49A62;
        --bp-ink: #1C2923;
        --bp-muted: #68766F;
        --bp-line: #DCE4DE;
        --bp-paper: #F4F7F4;
        --bp-white: #FFFFFF;
    }

    html, body, [class*="css"] {
        font-family: 'Source Sans 3', 'Segoe UI', sans-serif;
        color: var(--bp-ink);
        letter-spacing: 0;
    }
    [data-testid="stAppViewContainer"] { background: var(--bp-paper); }
    [data-testid="stHeader"] { background: rgba(244, 247, 244, 0.96); }
    .block-container { max-width: 1540px; padding: 1.7rem 2.2rem 3rem; }

    [data-testid="stSidebar"] { background: var(--bp-forest-deep); }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
    [data-testid="stSidebar"] label { color: #E8F0EB !important; font-weight: 400; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 { color: #FFFFFF !important; font-weight: 600; }
    [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.16); }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: #B9C9C0; }
    .sidebar-brand { text-align: center; padding: 8px 0 15px; }
    .brand-mark {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 42px;
        height: 42px;
        border: 1px solid rgba(180,154,98,.75);
        border-radius: 50%;
        color: #E8D9B6 !important;
        font-size: .9rem;
        font-weight: 700;
        margin-bottom: 8px;
    }
    .brand-name { color: #FFFFFF !important; font-size: 1rem; font-weight: 700; }
    .brand-subtitle { color: #D7C79F !important; font-size: .73rem; margin-top: 3px; }
    .brand-description { color: #B9C9C0 !important; font-size: .8rem; margin-top: 6px; }

    h1, h2, h3, h4, h5, h6 { color: var(--bp-ink) !important; font-weight: 600; letter-spacing: 0; }
    h2 { font-size: 1.45rem; }
    h3 { font-size: 1.2rem; }
    p { color: var(--bp-ink); }
    [data-testid="stCaptionContainer"] { color: var(--bp-muted); }

    .page-masthead {
        padding: 0 0 1.35rem;
        margin: 0 0 1.2rem;
        border-bottom: 1px solid var(--bp-line);
    }
    .masthead-kicker {
        color: var(--bp-forest) !important;
        font-size: .76rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: .08em;
        margin: 0 0 .35rem;
    }
    .page-masthead h1 { font-size: 1.9rem; line-height: 1.15; margin: 0; }
    .masthead-subtitle { color: var(--bp-muted) !important; font-size: 1rem; margin: .35rem 0 0; }
    .masthead-meta { display: flex; gap: 1.8rem; flex-wrap: wrap; margin-top: 1rem; }
    .meta-item { color: var(--bp-muted) !important; font-size: .88rem; }
    .meta-item strong { color: var(--bp-ink) !important; font-weight: 600; }

    .metric-card {
        min-height: 122px;
        padding: 15px 17px;
        background: var(--bp-white);
        border: 1px solid var(--bp-line);
        border-top: 2px solid var(--bp-forest);
        border-radius: 5px;
        box-shadow: 0 2px 8px rgba(21, 48, 36, .035);
    }
    .metric-card-head { display: flex; align-items: center; gap: 9px; margin-bottom: 10px; }
    .metric-icon {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 27px;
        height: 27px;
        flex: 0 0 27px;
        border-radius: 50%;
        background: #EAF1EC;
        color: var(--bp-forest);
        font-size: .95rem;
        font-weight: 600;
    }
    .metric-title { color: var(--bp-muted); font-size: .85rem; font-weight: 600; line-height: 1.15; }
    .metric-value { color: var(--bp-ink); font-size: 1.8rem; font-weight: 700; line-height: 1.05; }
    .metric-sub { color: var(--bp-muted); font-size: .82rem; margin-top: 6px; }

    .section-note {
        background: #EDF3EF;
        border-left: 3px solid var(--bp-forest);
        border-radius: 2px;
        color: #34483D;
        padding: 10px 14px;
        margin: 8px 0 16px;
        font-size: .9rem;
    }
    .section-note strong { color: var(--bp-forest-deep); }
    .chart-analysis {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 16px;
        background: #FFFFFF;
        border: 1px solid var(--bp-line);
        border-top: 2px solid var(--bp-gold);
        border-radius: 4px;
        padding: 14px 16px;
        margin: 4px 0 22px;
    }
    .chart-analysis-item { min-width: 0; }
    .chart-analysis-item + .chart-analysis-item {
        border-left: 1px solid var(--bp-line);
        padding-left: 16px;
    }
    .chart-analysis-label {
        color: var(--bp-forest) !important;
        font-size: .79rem;
        font-weight: 700;
        text-transform: uppercase;
        line-height: 1.3;
        margin-bottom: 8px;
    }
    .chart-analysis-text {
        color: #43534A !important;
        font-size: .9rem;
        line-height: 1.5;
        overflow-wrap: anywhere;
    }
    .project-section { padding: 18px 0; border-top: 1px solid var(--bp-line); }
    .project-section h3 { margin-top: 0; }
    .impact-item { padding: 12px 0; border-bottom: 1px solid var(--bp-line); }
    .impact-item strong { color: var(--bp-forest); }
    .status-line { display: flex; justify-content: space-between; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--bp-line); }
    .status-value { color: var(--bp-forest); font-weight: 600; text-align: right; }
    .decision-card {
        background: transparent;
        border: 0;
        border-top: 1px solid var(--bp-line);
        border-radius: 0;
        padding: 12px 4px;
        min-height: 86px;
        box-shadow: none;
    }
    .decision-card strong { color: var(--bp-forest); font-size: .95rem; }
    .decision-card p { color: var(--bp-muted); font-size: .87rem; margin: 5px 0 0; }

    .badge-ok, .badge-warning, .badge-danger {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 3px;
        font-size: .72rem;
        font-weight: 700;
    }
    .badge-ok { background: #E7F1EA; color: #245D3D; border: 1px solid #C9DDCE; }
    .badge-warning { background: #F5F0E3; color: #796333; border: 1px solid #E6D9B7; }
    .badge-danger { background: #F7EAE7; color: #8A3D31; border: 1px solid #E8C9C2; }

    .stTabs [data-baseweb="tab-list"] {
        gap: 1.4rem;
        border-bottom: 1px solid var(--bp-line);
        background: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border: 0;
        border-radius: 0;
        padding: 10px 2px;
        color: var(--bp-muted);
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        color: var(--bp-forest) !important;
        border-bottom: 2px solid var(--bp-forest) !important;
        background: transparent !important;
    }

    [data-testid="stMetricValue"] { color: var(--bp-ink) !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { color: var(--bp-muted) !important; font-weight: 600 !important; }
    [data-testid="stDataFrame"], [data-testid="stTable"] { border: 1px solid var(--bp-line); border-radius: 4px; }
    [data-testid="stExpander"] { border: 1px solid var(--bp-line); border-radius: 4px; background: var(--bp-white); }
    [data-testid="stBaseButton-primary"] { background: var(--bp-forest); border-color: var(--bp-forest); }
    [data-testid="stBaseButton-primary"]:hover { background: var(--bp-forest-deep); border-color: var(--bp-forest-deep); }
    [data-testid="stBaseButton-secondary"] { border-color: #BFCBC2; color: var(--bp-forest); }
    [data-testid="stBaseButton-secondary"]:hover { border-color: var(--bp-forest); color: var(--bp-forest-deep); }
    [data-testid="stWidgetLabel"] p { color: var(--bp-ink); font-weight: 500; }
    .vip-alert-card { background: #F5F0E3; border-left: 3px solid var(--bp-gold); padding: 14px 18px; border-radius: 2px; margin-bottom: 12px; color: #554A33; }
    .vip-alert-card strong { color: #69582D; }

    @media (max-width: 760px) {
        .block-container { padding: 1rem 1rem 2rem; }
        .page-masthead h1 { font-size: 1.55rem; }
        .masthead-meta { gap: .55rem 1rem; }
        .metric-card { min-height: 112px; padding: 12px; }
        .metric-value { font-size: 1.55rem; }
        .stTabs [data-baseweb="tab-list"] { gap: .8rem; }
        .chart-analysis { grid-template-columns: 1fr; gap: 10px; }
        .chart-analysis-item + .chart-analysis-item { border-left: 0; border-top: 1px solid var(--bp-line); padding: 10px 0 0; }
        .status-line { flex-direction: column; gap: 2px; }
        .status-value { text-align: left; }
    }
</style>
""", unsafe_allow_html=True)


# =====================================================================
# CARGA DE DATOS Y CACHÉ DE CONSULTAS
# =====================================================================

@st.cache_data(ttl=60)
def cargar_dataset_completo() -> pd.DataFrame:
    """
    Carga el dataset completo de reservas desde el Esquema en Estrella (BI)
    unido con las dimensiones reales de hoteles, restaurantes, horarios y atenciones.
    Se actualiza cada 60 segundos para reflejar nuevas filas en la base de datos.
    """
    columnas_obligatorias = [
        "id_reserva", "id_fecha", "anio", "mes", "dia", "dia_semana", "es_fin_de_semana", "temporada",
        "id_restaurante", "nombre_restaurante", "especialidad", "capacidad_maxima_pax",
        "cod_hotel_restaurante", "hotel_restaurante", "cod_hotel_hospedaje", "hotel_hospedaje",
        "turno", "horario_texto", "franja_horaria", "id_horario",
        "categoria_atencion", "prioridad_servicio", "id_tipo_atencion",
        "num_adultos", "num_ninos", "num_bebes", "total_pax", "habs_invitadas",
        "es_cross_dining", "requiere_periquera", "observaciones_limpias"
    ]

    try:
        engine_star = get_engine()
        init_db(engine_star)  # Asegurar creación automática de tablas y catálogos seed

        query_star = """
        SELECT f.id_reserva, f.fecha_servicio AS id_fecha,
               t.anio, t.mes, t.dia, t.dia_semana,
               f.id_servicio AS id_restaurante,
               COALESCE(s.restaurante, s.codigo_servicio) AS nombre_restaurante,
               s.codigo_servicio AS especialidad, 0 AS capacidad_maxima_pax,
               h.codigo_hotel AS cod_hotel_restaurante, h.codigo_hotel AS hotel_restaurante,
               COALESCE(h.hotel_res, h.codigo_hotel) AS cod_hotel_hospedaje,
               COALESCE(h.hotel_res, h.codigo_hotel) AS hotel_hospedaje,
               f.turno, f.horario AS horario_texto, f.horario AS franja_horaria,
               f.turno AS id_horario, COALESCE(a.atencion, 'Sin especificar') AS categoria_atencion,
               0 AS prioridad_servicio, a.atencion AS id_tipo_atencion,
               f.adultos AS num_adultos, f.ninos AS num_ninos, f.bebes AS num_bebes,
               f.pax_total AS total_pax, f.num_habs_invitadas AS habs_invitadas,
               CASE WHEN UPPER(COALESCE(f.cross_flag, '')) IN ('Y', 'YES', 'TRUE', '1', 'SI', 'S')
                    THEN 1 ELSE 0 END AS es_cross_dining,
               f.remarks AS observaciones_limpias, a.usuario
        FROM fact_reservas_restaurantes f
        INNER JOIN dim_tiempo t ON f.fecha_servicio = t.fecha
        INNER JOIN dim_servicio s ON f.id_servicio = s.id_servicio
        INNER JOIN dim_hotel h ON f.id_hotel = h.id_hotel
        INNER JOIN dim_atencion a ON f.id_atencion = a.id_atencion
        """
        df_star = pd.read_sql(text(query_star), con=engine_star)
        if not df_star.empty:
            hotel_names = {}
            for item in HOTELES_CATALOGO:
                for alias in (item["id_hotel"], item["codigo_origen"], item["nombre_hotel"]):
                    hotel_names[str(alias).strip().lower()] = item["nombre_hotel"]
            attention_names = {
                item["id_tipo_atencion"]: item["categoria_atencion"]
                for item in TIPOS_ATENCION_CATALOGO
            }
            for hotel_column in ("hotel_restaurante", "hotel_hospedaje"):
                df_star[hotel_column] = df_star[hotel_column].map(
                    lambda value: hotel_names.get(str(value).strip().lower(), value)
                )
            raw_attention = df_star["categoria_atencion"].astype("string").str.strip()
            attention_keys = raw_attention.str.upper()
            category_labels = {
                "STANDARD": "Standard",
                "VIP": "VIP",
                "FIDELIDAD": "Fidelidad",
                "ESPECIAL": "Especial",
                "SIN ESPECIFICAR": "Sin especificar",
                "OTRO TIPO DE ATENCIÓN": "Otro tipo de atención",
            }
            mapped_attention = attention_keys.map(attention_names).fillna(attention_keys.map(category_labels))
            missing_attention = attention_keys.isna() | attention_keys.isin({"", "NAN", "NONE", "NULL", "<NA>", "N/A"})
            df_star["categoria_atencion"] = mapped_attention.fillna("Otro tipo de atención")
            df_star.loc[missing_attention, "categoria_atencion"] = "Sin especificar"
            df_star["id_fecha"] = pd.to_datetime(df_star["id_fecha"]).dt.date
            horario_limpio = df_star["horario_texto"].astype("string").str.strip()
            horario_missing = horario_limpio.isna() | horario_limpio.str.casefold().isin({"", "nan", "none", "null", "<na>", "n/a"})
            df_star["horario_texto"] = horario_limpio.mask(horario_missing, "Horario no registrado").astype(str)
            df_star["franja_horaria"] = df_star["horario_texto"]
            df_star["es_fin_de_semana"] = pd.to_datetime(df_star["id_fecha"]).dt.weekday.isin([4, 5, 6])
            df_star["temporada"] = df_star["mes"].map(
                lambda month: "Alta" if month in (12, 1, 2, 3, 4, 7, 8) else ("Media" if month in (5, 6) else "Baja")
            )
            df_star["requiere_periquera"] = (df_star["num_bebes"] > 0) | df_star["observaciones_limpias"].astype(str).str.lower().str.contains("periquera|trona|bebe|bebé|cuna|baby", na=False)
            for c in columnas_obligatorias:
                if c not in df_star.columns:
                    df_star[c] = "N/A" if ("nombre" in c or "hotel" in c or "categoria" in c) else 0
            return df_star
    except Exception as e:
        st.error(f"Error al cargar datos desde el Esquema en Estrella: {e}")

    return pd.DataFrame(columns=columnas_obligatorias)


@st.cache_data(ttl=120)
def cargar_demo_habitaciones() -> pd.DataFrame:
    """Resume reservas y pax por habitación con los datos presentes en la tabla de hechos."""
    try:
        engine = get_engine()
        query = """
        SELECT habitacion, COUNT(*) AS reservas, SUM(pax_total) AS pax
        FROM fact_reservas_restaurantes
        WHERE habitacion IS NOT NULL AND habitacion != ''
        GROUP BY habitacion
        ORDER BY pax DESC
        LIMIT 20
        """
        return pd.read_sql(text(query), con=engine)
    except Exception:
        return pd.DataFrame()


def asegurar_base_datos_inicializada():
    """Verifica si hay datos en el esquema en estrella."""
    df = cargar_dataset_completo()
    if df.empty:
        st.info("Base de datos del Esquema en Estrella vacía. Sube el archivo histórico anual desde la barra lateral para comenzar.")


# Asegurar que la BD esté lista
asegurar_base_datos_inicializada()
df_master = cargar_dataset_completo()

filtros_pendientes = st.session_state.pop("_filtros_asistente_pendientes", {})
for widget_key, widget_value in filtros_pendientes.items():
    st.session_state[widget_key] = widget_value


def obtener_rango_db() -> Tuple[date, date]:
    """Devuelve el rango real de fechas que hay en la base de datos actual."""
    try:
        df_actual = cargar_dataset_completo().copy()
    except Exception:
        df_actual = df_master.copy()

    if df_actual.empty:
        hoy = date.today()
        return hoy, hoy

    min_date = df_actual["id_fecha"].min()
    max_date = df_actual["id_fecha"].max()
    return min_date, max_date


def normalizar_estado_multiselect(widget_key: str, options: List[Any]) -> None:
    """Drop stale selections and represent an all-values selection as empty."""
    if widget_key not in st.session_state:
        return
    current_values = st.session_state[widget_key]
    valid_values = [value for value in current_values if value in options]
    if options and len(valid_values) == len(options):
        valid_values = []
    st.session_state[widget_key] = valid_values


def filtrar_analisis(data: pd.DataFrame, section: str, fields: List[str]) -> pd.DataFrame:
    """Render independent, applicable filters for one analysis section."""
    if data.empty:
        return data.copy()

    date_min = pd.to_datetime(data["id_fecha"]).dt.date.min()
    date_max = pd.to_datetime(data["id_fecha"]).dt.date.max()
    applied_key = f"filtros_aplicados_{section}"
    saved = st.session_state.get(applied_key, {"dates": (date_min, date_max)})
    options_by_field = {
        "hotel": ("Hotel", "hotel_restaurante"),
        "restaurant": ("Restaurante", "nombre_restaurante"),
        "shift": ("Horario", "turno"),
        "attention": ("Tipo de atención", "categoria_atencion"),
        "origin": ("Hotel donde se hospeda", "hotel_hospedaje"),
        "destination": ("Hotel del restaurante", "hotel_restaurante"),
        "cross": ("Origen del huésped", "es_cross_dining"),
    }

    with st.expander("Filtros de este análisis", expanded=False):
        with st.form(f"form_filtros_{section}"):
            date_range = st.date_input(
                "Periodo",
                value=saved.get("dates", (date_min, date_max)),
                min_value=date_min,
                max_value=date_max,
                key=f"widget_fechas_{section}",
            )
            selections = {}
            filter_columns = st.columns(2)
            for index, field in enumerate(fields):
                label, column = options_by_field[field]
                options = [False, True] if field == "cross" else sorted(data[column].dropna().unique().tolist(), key=str)
                default = saved.get(field, [])
                default = [value for value in default if value in options]
                if field == "shift":
                    schedule_labels = {}
                    for value in options:
                        if value == 0:
                            schedule_labels[value] = "Horario no registrado"
                            continue
                        mode = data.loc[data[column] == value, "horario_texto"].dropna().mode()
                        schedule_labels[value] = f"Turno {value} · {mode.iloc[0]}" if not mode.empty else f"Turno {value}"
                    formatter = lambda value, labels=schedule_labels: labels.get(value, str(value))
                elif field == "cross":
                    formatter = lambda value: "De otro hotel" if value else "Del mismo hotel"
                else:
                    formatter = str
                with filter_columns[index % 2]:
                    selections[field] = st.multiselect(
                        label,
                        options=options,
                        default=default,
                        format_func=formatter,
                        key=f"widget_{field}_{section}",
                    )
            submitted = st.form_submit_button("Aplicar filtros", type="primary")

    if submitted:
        if not isinstance(date_range, (tuple, list)) or len(date_range) != 2:
            date_range = (date_min, date_max)
        st.session_state[applied_key] = {"dates": tuple(date_range), **selections}
        saved = st.session_state[applied_key]

    start, end = saved.get("dates", (date_min, date_max))
    dates = pd.to_datetime(data["id_fecha"]).dt.date
    result = data[(dates >= start) & (dates <= end)].copy()
    for field in fields:
        selection = saved.get(field, [])
        if selection:
            result = result[result[options_by_field[field][1]].isin(selection)]
    return result


CONFIG_GRAFICAS = {
    "displayModeBar": True,
    "displaylogo": False,
    "scrollZoom": True,
    "toImageButtonOptions": {"format": "png", "filename": "grafica_bahia_principe", "scale": 2},
}


def mostrar_analisis_grafica(muestra: str, objetivo: str, accion: str) -> None:
    """Renderiza una lectura gerencial breve vinculada a una gráfica."""
    st.markdown(f"""
        <div class="chart-analysis">
            <div class="chart-analysis-item">
                <div class="chart-analysis-label">¿Qué muestra esta gráfica?</div>
                <div class="chart-analysis-text">{muestra}</div>
            </div>
            <div class="chart-analysis-item">
                <div class="chart-analysis-label">¿Cuál es el objetivo analítico?</div>
                <div class="chart-analysis-text">{objetivo}</div>
            </div>
            <div class="chart-analysis-item">
                <div class="chart-analysis-label">Acción ejecutiva sugerida</div>
                <div class="chart-analysis-text">{accion}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# =====================================================================
# BARRA LATERAL (SIDEBAR): CARGA, FILTROS Y ESTADO
# =====================================================================

with st.sidebar:
    st.markdown("""
        <div class="sidebar-brand">
            <div class="brand-mark">BP</div>
            <div class="brand-name">BAHÍA PRÍNCIPE</div>
            <div class="brand-subtitle">Hotels & Resorts</div>
            <div class="brand-description">Business Intelligence · A&B</div>
        </div>
    """, unsafe_allow_html=True)

    # 1. GESTIÓN DE FUENTE DE DATOS
    st.markdown("---")
    st.subheader("Carga y actualización de datos")

    # Formatos aceptados (sin límite de archivos ni tamaño por archivo)
    FORMATOS_ACEPTADOS = [
        "csv", "xlsx", "xls", "ods",          # tabulares
        "tsv", "txt",                           # texto delimitado
        "sql",                                  # dump SQL (INSERT INTO)
        "db", "sqlite", "sqlite3",              # bases de datos SQLite
        "json", "jsonl",                        # JSON / JSON Lines
        "parquet", "feather", "orc",            # columnar/binario
    ]

    archivos_subidos = st.file_uploader(
        "Cargar archivos de datos",
        type=FORMATOS_ACEPTADOS,
        accept_multiple_files=True,
        help=(
            "Formatos soportados: CSV, Excel (.xlsx/.xls/.ods), TSV, TXT, SQL (INSERT INTO), "
            "SQLite (.db/.sqlite), JSON, JSONL, Parquet, Feather, ORC.\n\n"
            "Puedes seleccionar todos los archivos que necesites a la vez. "
            "El sistema los procesará en secuencia y consolidará los resultados."
        ),
    )

    if archivos_subidos:
        n = len(archivos_subidos)
        nombres = [f.name for f in archivos_subidos]
        st.info(
            f"**{n} archivo{'s' if n > 1 else ''} seleccionado{'s' if n > 1 else ''}:** "
            + ", ".join(f"`{nm}`" for nm in nombres[:8])
            + (f" … y {n - 8} más" if n > 8 else "")
        )

        reemplazar_datos = st.checkbox(
            "Reemplazar todos los datos actuales antes de cargar",
            value=False,
            help=(
                "Activa esta opción solo si deseas borrar toda la BD antes de cargar. "
                "Para carga acumulativa (agregar datos) déjala desactivada."
            ),
        )

        if st.button("Procesar y cargar datos", use_container_width=True, type="primary"):
            with st.spinner(f"Ejecutando carga masiva de {n} archivo{'s' if n > 1 else ''}..."):
                try:
                    from etl_pipeline import ejecutar_etl_carga_masiva
                    resumen = ejecutar_etl_carga_masiva(
                        archivos_subidos,
                        reemplazar_primero=reemplazar_datos,
                    )

                    exitosos = resumen["archivos_exitosos"]
                    con_error = resumen["archivos_con_error"]

                    if exitosos:
                        st.success(
                            f"✅ Carga masiva completada: **{resumen['total_registros']:,}** reservas únicas cargadas "
                            f"desde **{len(exitosos)}** archivo{'s' if len(exitosos) > 1 else ''}. "
                            + (f"Se consolidaron **{resumen['ids_duplicados']:,}** Id repetidos. " if resumen.get("ids_duplicados") else "")
                            + (
                                f"Rango de fechas: {resumen['fecha_min']} → {resumen['fecha_max']} "
                                f"({resumen['fechas_unicas']} días)."
                                if resumen["fecha_min"]
                                else ""
                            )
                        )
                    if con_error:
                        for nombre_err, msg_err in con_error:
                            st.warning(f"⚠️ **{nombre_err}** no se pudo procesar: {msg_err}")

                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error en la carga masiva: {e}")

        with st.expander("Herramientas internas", expanded=False):
            st.caption("Acciones de mantenimiento de la base de datos.")
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button("🔄 Recargar Demo", use_container_width=True, help="Regenera 1,250 reservas sintéticas en la base de datos"):
                    with st.spinner("Regenerando datos sintéticos..."):
                        inicializar_demo_y_cargar_bd(1250)
                        st.cache_data.clear()
                        st.rerun()
            with col_btn2:
                if st.button("🧹 Limpiar Caché", use_container_width=True):
                    st.cache_data.clear()
                    st.rerun()
            with col_btn3:
                if st.button("🗑️ Vaciar BD", use_container_width=True):
                    from etl_pipeline import limpiar_base_datos
                    limpiar_base_datos()
                    st.cache_data.clear()
                    st.success("Base vaciada. Ya puedes subir el histórico anual.")
                    st.rerun()
    
            db_url_str = get_database_url()
            tipo_bd = "PostgreSQL Local" if "localhost" in db_url_str or "127.0.0.1" in db_url_str else ("PostgreSQL Cloud" if "postgresql" in db_url_str else "SQLite Local")
            st.caption(f"Origen: {tipo_bd} · {len(df_master):,} reservas cargadas")


    
    st.markdown("---")
    st.caption("Ajusta cada análisis por separado desde los filtros dentro de cada apartado.")


min_date, max_date = obtener_rango_db()
f_inicio, f_fin = min_date, max_date
df_filtrado = df_master.copy()
hoteles_incluidos = df_filtrado["hotel_restaurante"].nunique() if not df_filtrado.empty else 0
restaurantes_incluidos = df_filtrado["nombre_restaurante"].nunique() if not df_filtrado.empty else 0

st.markdown(f"""
    <header class="page-masthead">
        <p class="masthead-kicker">Bahía Príncipe · Inteligencia de A&B</p>
        <h1>Restaurantes de especialidad</h1>
        <p class="masthead-subtitle">Demanda, capacidad y experiencia de servicio</p>
        <div class="masthead-meta">
            <span class="meta-item"><strong>Periodo</strong> &nbsp;{f_inicio} – {f_fin}</span>
            <span class="meta-item"><strong>{hoteles_incluidos}</strong> hoteles</span>
            <span class="meta-item"><strong>{restaurantes_incluidos}</strong> restaurantes</span>
            <span class="meta-item"><strong>{len(df_filtrado):,}</strong> reservas</span>
        </div>
    </header>
""", unsafe_allow_html=True)


# =====================================================================
# PESTAÑAS PRINCIPALES DEL SISTEMA BI
# =====================================================================

tabs = st.tabs([
    "Resumen",
    "Operación y pronóstico",
    "Preguntas y datos",
    "Resultados e impacto"
])


# =====================================================================
# TAB 1: RESUMEN EJECUTIVO Y KPIS EN TIEMPO REAL
# =====================================================================
with tabs[0]:
    df_filtrado = filtrar_analisis(df_master, "resumen", ["hotel", "restaurant"])
    st.caption(f"{len(df_filtrado):,} reservas en el periodo y selección de este resumen.")
    if df_filtrado.empty:
        st.warning("⚠️ No se encontraron reservas que coincidan con los filtros seleccionados.")
    else:
        # Métricas agregadas
        total_reservas = len(df_filtrado)
        total_pax = int(df_filtrado["total_pax"].sum())
        total_adultos = int(df_filtrado["num_adultos"].sum())
        total_ninos = int(df_filtrado["num_ninos"].sum())
        total_bebes = int(df_filtrado["num_bebes"].sum())
        prom_pax_reserva = round(total_pax / total_reservas, 2) if total_reservas > 0 else 0
        total_cross = int(df_filtrado["es_cross_dining"].sum())
        pct_cross = round((total_cross / total_reservas) * 100, 1) if total_reservas > 0 else 0

        fechas_resumen = pd.to_datetime(df_filtrado["id_fecha"]).dt.date
        dias_totales = max(1, (fechas_resumen.max() - fechas_resumen.min()).days + 1)
        turnos_resumen = max(1, df_filtrado["turno"].nunique())
        metrica_resumen = st.radio(
            "Mostrar las comparaciones por",
            options=["Comensales", "Reservas"],
            horizontal=True,
            key="metrica_resumen",
        )
        metric_column = "total_pax" if metrica_resumen == "Comensales" else "reservas"
        metric_label = metrica_resumen
        cap_instalada_diaria = df_filtrado.groupby(["id_restaurante", "capacidad_maxima_pax"]).size().reset_index()["capacidad_maxima_pax"].sum()
        # Capacidad estimada considerando turnos
        cap_total_periodo = cap_instalada_diaria * turnos_resumen * dias_totales
        ocupacion_global_pct = round((total_pax / cap_total_periodo * 100), 1) if cap_total_periodo > 0 else None
        if ocupacion_global_pct is not None:
            ocupacion_global_pct = min(100.0, ocupacion_global_pct)

        metric_cards = [
            ("▤", "Reservas", f"{total_reservas:,}", f"{dias_totales} días analizados"),
            ("◉", "Comensales", f"{total_pax:,}", f"{round(total_pax / dias_totales, 1):,} por día en promedio"),
            ("♙", "Adultos", f"{total_adultos:,}", f"{total_ninos + total_bebes:,} niños y bebés · {round((total_ninos + total_bebes) / total_pax * 100, 1) if total_pax else 0}%"),
            ("⌂", "Tamaño medio de mesa", f"{prom_pax_reserva}", "comensales por reserva"),
            ("↔", "Cross-dining", f"{pct_cross}%", f"{total_cross:,} reservas entre hoteles"),
        ]
        badge_color = "warning" if ocupacion_global_pct is None else ("ok" if ocupacion_global_pct < 75 else ("warning" if ocupacion_global_pct <= 90 else "danger"))
        occupancy_subtitle = "Capacidad pendiente" if ocupacion_global_pct is None else "Estimación orientativa"
        metric_cards.append(("◷", "Ocupación estimada", f"{ocupacion_global_pct}%" if ocupacion_global_pct is not None else "Sin dato", f"<span class='badge-{badge_color}'>{occupancy_subtitle}</span>"))

        for row_start in range(0, len(metric_cards), 3):
            metric_columns = st.columns(3)
            for column, (icon, label, value, subtitle) in zip(metric_columns, metric_cards[row_start:row_start + 3]):
                with column:
                    st.markdown(f"""
                        <div class="metric-card">
                            <div class="metric-card-head">
                                <span class="metric-icon" aria-hidden="true">{icon}</span>
                                <span class="metric-title">{label}</span>
                            </div>
                            <div class="metric-value">{value}</div>
                            <div class="metric-sub">{subtitle}</div>
                        </div>
                    """, unsafe_allow_html=True)

        st.markdown("<div style='height: 1.1rem'></div>", unsafe_allow_html=True)

        # Fila 2: Semáforo Visual de Ocupación por Restaurante
        st.subheader("Ocupación por restaurante")
        st.caption("Mide el porcentaje de comensales promedio por noche frente a la capacidad instalada del restaurante.")

        # Agrupar por restaurante y calcular ocupación media por noche
        df_rest_agg = df_filtrado.groupby(["id_restaurante", "nombre_restaurante", "especialidad", "hotel_restaurante", "capacidad_maxima_pax"]).agg(
            total_pax_rest=("total_pax", "sum"),
            total_reservas_rest=("id_reserva", "count"),
            dias_con_reserva=("id_fecha", "nunique")
        ).reset_index()

        df_rest_agg["dias_efectivos"] = df_rest_agg["dias_con_reserva"].apply(lambda x: max(1, x))
        # Pax por noche
        df_rest_agg["pax_por_noche"] = df_rest_agg["total_pax_rest"] / df_rest_agg["dias_efectivos"]
        # Porcentaje de ocupación sobre capacidad por noche (asumiendo turnos activos)
        cap_noche = df_rest_agg["capacidad_maxima_pax"] * turnos_resumen
        df_rest_agg["pct_ocupacion"] = np.where(
            cap_noche > 0,
            ((df_rest_agg["pax_por_noche"] / cap_noche) * 100).round(1),
            np.nan,
        )

        # Mostrar tarjetas semafóricas en columnas
        rest_cols = st.columns(4)
        for idx, row in df_rest_agg.sort_values(by="pct_ocupacion", ascending=False).iterrows():
            col_idx = idx % 4
            pct = row["pct_ocupacion"]
            if pd.isna(pct):
                badge_html = '<span class="badge-warning">Capacidad no registrada</span>'
                b_color = "#94A3B8"
            elif pct < 75:
                badge_html = f'<span class="badge-ok">{pct}% NORMAL</span>'
                b_color = "#5D806B"
            elif pct <= 90:
                badge_html = f'<span class="badge-warning">{pct}% ALTA</span>'
                b_color = "#B49A62"
            else:
                badge_html = f'<span class="badge-danger">{pct}% SATURADO</span>'
                b_color = "#A9695E"

            with rest_cols[col_idx]:
                st.markdown(f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid {b_color}; border-radius: 8px; padding: 14px; margin-bottom: 14px; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 700; color: #0F172A; font-size: 0.95rem;">{row['nombre_restaurante']}</span>
                        </div>
                        <div style="font-size: 0.78rem; color: #527366; font-weight: 600; margin-top: 2px;">{row['especialidad']} • {row['hotel_restaurante']}</div>
                        <div style="margin-top: 10px; display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 0.8rem; color: #64748B;">Capacidad: {'No registrada' if not row['capacidad_maxima_pax'] else f"{row['capacidad_maxima_pax']} pax"}</span>
                            {badge_html}
                        </div>
                        <div style="margin-top: 6px; font-size: 0.8rem; color: #334155;">
                            Total: <strong style="color: #0F172A;">{row['total_pax_rest']:,} pax</strong> ({int(row['pax_por_noche'])} pax/noche)
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Fila 3: Gráficos de Tendencias Temporales y Distribución
        g1, g2 = st.columns([1.3, 1])
        with g1:
            st.subheader("Actividad por día")
            st.caption("Cada barra representa cuántos comensales hubo ese día; la línea cuenta las reservas.")
            df_tiempo_trend = df_filtrado.groupby("id_fecha").agg(
                total_pax=("total_pax", "sum"),
                total_reservas=("id_reserva", "count"),
                adultos=("num_adultos", "sum"),
                menores=("num_ninos", lambda x: (x + df_filtrado.loc[x.index, "num_bebes"]).sum())
            ).reset_index().sort_values("id_fecha")

            fig_trend = go.Figure()
            fig_trend.add_trace(go.Bar(
                x=df_tiempo_trend["id_fecha"],
                y=df_tiempo_trend["total_pax"],
                name="Comensales (Pax)",
                marker_color="rgba(180, 154, 98, 0.65)",
                yaxis="y"
            ))
            fig_trend.add_trace(go.Scatter(
                x=df_tiempo_trend["id_fecha"],
                y=df_tiempo_trend["total_reservas"],
                name="Nº Reservas",
                mode="lines+markers",
                line=dict(color="#0B4F39", width=3),
                yaxis="y2"
            ))
            fig_trend.update_layout(
                paper_bgcolor="rgba(255,255,255,0.7)",
                plot_bgcolor="rgba(255,255,255,0.7)",
                font=dict(color="#0F172A", family="Plus Jakarta Sans, sans-serif"),
                xaxis=dict(gridcolor="#E2E8F0", tickfont=dict(color="#334155"), title_font=dict(color="#0F172A")),
                yaxis=dict(title="Total Comensales (Pax)", title_font=dict(color="#0F172A"), tickfont=dict(color="#334155"), gridcolor="#E2E8F0"),
                yaxis2=dict(title="Número de Reservas", title_font=dict(color="#0F172A"), tickfont=dict(color="#334155"), overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color="#0F172A")),
                margin=dict(l=40, r=40, t=30, b=30),
                height=380
            )
            st.plotly_chart(fig_trend, use_container_width=True, config=CONFIG_GRAFICAS)
            mostrar_analisis_grafica(
                "Cruza la fecha de la dimensión Tiempo con comensales y reservas de la tabla de hechos.",
                "Detectar tendencias, estacionalidad y jornadas de mayor presión de servicio.",
                "Ajustar turnos, compras y dotación en las fechas que concentran ambos indicadores.",
            )

        with g2:
            st.subheader(f"{metric_label} por hotel")
            pie_metric_column = "total_pax" if metric_column == "total_pax" else "reservas"
            pie_source_column = "total_pax" if pie_metric_column == "total_pax" else "id_reserva"
            pie_aggregation = "sum" if pie_metric_column == "total_pax" else "count"
            df_hotel_pie = df_filtrado.groupby("hotel_restaurante").agg(
                **{pie_metric_column: (pie_source_column, pie_aggregation)}
            ).reset_index()
            fig_pie = px.pie(
                df_hotel_pie,
                names="hotel_restaurante",
                values=pie_metric_column,
                hole=0.45,
                labels={pie_metric_column: metric_label, "hotel_restaurante": "Hotel"},
                color_discrete_sequence=["#0B4F39", "#B49A62", "#667A70", "#9A5C4A", "#627A8A"]
            )
            fig_pie.update_traces(textinfo="label+percent", hovertemplate="%{label}<br>%{value:,.0f} " + metric_label.lower() + "<extra></extra>")
            fig_pie.update_layout(
                paper_bgcolor="rgba(255,255,255,0.7)",
                font=dict(color="#0F172A", family="Plus Jakarta Sans, sans-serif"),
                margin=dict(l=20, r=20, t=20, b=20),
                height=380,
                legend=dict(orientation="v", yanchor="middle", y=0.5, font=dict(color="#0F172A"))
            )
            st.plotly_chart(fig_pie, use_container_width=True, config=CONFIG_GRAFICAS)
            mostrar_analisis_grafica(
                f"Distribuye {metric_label.lower()} por hotel del restaurante, agregados desde las reservas.",
                "Comparar la participación de cada hotel en la demanda del periodo filtrado.",
                "Revisar capacidad y promoción en los hoteles de mayor peso, sin descuidar los de menor participación.",
            )

        st.markdown("### Más formas de leer la actividad")
        tipo_comparacion = st.radio(
            "Tipo de gráfica",
            options=["Barras", "Línea"],
            horizontal=True,
            key="tipo_grafica_resumen",
        )
        chart_month, chart_restaurant = st.columns(2)
        monthly_data = df_filtrado.assign(
            mes=pd.to_datetime(df_filtrado["id_fecha"]).dt.to_period("M").astype(str)
        ).groupby("mes", as_index=False).agg(
            total_pax=("total_pax", "sum"),
            reservas=("id_reserva", "count"),
        )
        top_restaurants = (
            df_filtrado.groupby("nombre_restaurante", as_index=False).agg(
                total_pax=("total_pax", "sum"),
                reservas=("id_reserva", "count"),
            )
            .assign(valor=lambda frame: frame["total_pax"] if metric_column == "total_pax" else frame["reservas"])
            .sort_values("valor", ascending=True)
            .tail(10)
        )
        with chart_month:
            st.subheader(f"{metric_label} por mes")
            st.caption("Permite comparar cómo cambia la actividad durante el año.")
            monthly_metric_column = "total_pax" if metric_column == "total_pax" else "reservas"
            month_chart_builder = px.bar if tipo_comparacion == "Barras" else px.line
            fig_month = month_chart_builder(
                monthly_data,
                x="mes",
                y=monthly_metric_column,
                labels={"mes": "Mes", monthly_metric_column: metric_label},
                color_discrete_sequence=["#0F766E"],
            )
            if tipo_comparacion == "Línea":
                fig_month.update_traces(mode="lines+markers")
            fig_month.update_layout(height=340, margin=dict(l=20, r=15, t=15, b=20), showlegend=False)
            st.plotly_chart(fig_month, use_container_width=True, config=CONFIG_GRAFICAS)
            mostrar_analisis_grafica(
                f"Agrupa por mes de la dimensión Tiempo y suma {metric_label.lower()} de las reservas.",
                "Reconocer meses pico y valles para distinguir patrones de temporada.",
                "Planificar compras, calendario de personal y capacidad con antelación a los meses de mayor demanda.",
            )
        with chart_restaurant:
            st.subheader(f"Los 10 restaurantes con más {metric_label.lower()}")
            st.caption("Las barras más largas indican mayor actividad en el periodo elegido.")
            if tipo_comparacion == "Barras":
                fig_restaurants = px.bar(
                    top_restaurants,
                    x="valor",
                    y="nombre_restaurante",
                    orientation="h",
                    labels={"nombre_restaurante": "Restaurante", "valor": metric_label},
                    color_discrete_sequence=["#B49A62"],
                )
            else:
                fig_restaurants = px.scatter(
                    top_restaurants,
                    x="valor",
                    y="nombre_restaurante",
                    labels={"nombre_restaurante": "Restaurante", "valor": metric_label},
                    color_discrete_sequence=["#B49A62"],
                )
            fig_restaurants.update_layout(height=340, margin=dict(l=20, r=15, t=15, b=20), showlegend=False)
            st.plotly_chart(fig_restaurants, use_container_width=True, config=CONFIG_GRAFICAS)
            mostrar_analisis_grafica(
                f"Ordena los diez restaurantes con mayor volumen de {metric_label.lower()} en el periodo.",
                "Identificar restaurantes líderes y comparar su peso operativo.",
                "Contrastar la carga de los restaurantes líderes con su capacidad y reforzar los turnos que lo requieran.",
            )


# =====================================================================
# TAB 2: ANÁLISIS DE CAPACIDAD Y HORARIOS CRÍTICOS (YIELD MANAGEMENT)
# =====================================================================
with tabs[1]:
    df_filtrado = filtrar_analisis(df_master, "horarios", ["hotel", "restaurant", "shift"])
    st.caption(f"{len(df_filtrado):,} reservas incluidas en este análisis.")
    if not df_filtrado.empty:
        report_dates = pd.to_datetime(df_filtrado["id_fecha"]).dt.date
        f_inicio, f_fin = report_dates.min(), report_dates.max()
    if df_filtrado.empty:
        st.warning("⚠️ No hay datos disponibles para el análisis de capacidad.")
    else:
        metrica_operacion = st.radio(
            "Medir la actividad por",
            options=["Comensales", "Reservas"],
            horizontal=True,
            key="metrica_operacion",
        )
        operacion_columna = "total_pax" if metrica_operacion == "Comensales" else "id_reserva"
        operacion_agregacion = "sum" if operacion_columna == "total_pax" else "count"
        st.subheader("Ocupación por turno y restaurante")
        st.caption("Permite a la Dirección de A&B balancear las cargas horarias y mitigar sobreventas en franjas pico.")

        # Pivot table: Restaurante vs Turno
        pivot_ocup = df_filtrado.pivot_table(
            index="nombre_restaurante",
            columns="franja_horaria",
            values=operacion_columna,
            aggfunc=operacion_agregacion,
            fill_value=0
        )

        fig_heat = px.imshow(
            pivot_ocup,
            labels=dict(x="Horario", y="Restaurante", color=metrica_operacion),
            x=pivot_ocup.columns,
            y=pivot_ocup.index,
            color_continuous_scale="YlOrRd",
            aspect="auto"
        )
        fig_heat.update_layout(
            paper_bgcolor="rgba(255,255,255,0.7)",
            plot_bgcolor="rgba(255,255,255,0.7)",
            font=dict(color="#0F172A", family="Plus Jakarta Sans, sans-serif"),
            margin=dict(l=150, r=30, t=30, b=80),
            height=480
        )
        fig_heat.update_xaxes(tickfont=dict(color="#334155", size=11), title_font=dict(color="#0F172A"))
        fig_heat.update_yaxes(tickfont=dict(color="#334155", size=11), title_font=dict(color="#0F172A"))
        st.plotly_chart(fig_heat, use_container_width=True, config=CONFIG_GRAFICAS)
        mostrar_analisis_grafica(
            f"Cruza restaurante y franja horaria con el total de {metrica_operacion.lower()} de la tabla de hechos.",
            "Localizar combinaciones restaurante-turno que concentran o reciben poca demanda.",
            "Redistribuir reservas cuando sea viable y ajustar personal en las celdas de mayor volumen.",
        )

        st.markdown("### Demanda por restaurante y horario")
        st.caption("Compara la cantidad de comensales registrada. Estos volúmenes muestran carga relativa, no porcentaje de aforo.")
        fecha_registro = pd.to_datetime(df_filtrado["id_fecha"]).dt.date
        fechas_con_reservas = sorted(fecha_registro.unique())[-7:]
        datos_recientes = df_filtrado.loc[fecha_registro.isin(fechas_con_reservas)].copy()
        periodo_dias = max(len(fechas_con_reservas), 1)

        demanda_restaurante = (
            datos_recientes.groupby("nombre_restaurante", as_index=False)
            .agg(pax_periodo=("total_pax", "sum"), reservas=("id_reserva", "count"))
        )
        demanda_restaurante["pax_dia_promedio"] = demanda_restaurante["pax_periodo"] / periodo_dias
        demanda_restaurante = demanda_restaurante.sort_values("pax_dia_promedio", ascending=False)

        datos_recientes["hora_visible"] = datos_recientes["horario_texto"].astype(str).map(
            lambda value: value.split(" - ")[0]
            if len(value.split(" - ")) == 2 and value.split(" - ")[0] == value.split(" - ")[1]
            else value
        )
        demanda_horario = (
            datos_recientes.groupby("hora_visible", as_index=False)
            .agg(pax_periodo=("total_pax", "sum"), reservas=("id_reserva", "count"))
        )
        demanda_horario["pax_dia_promedio"] = demanda_horario["pax_periodo"] / periodo_dias
        demanda_horario = demanda_horario.sort_values("pax_dia_promedio", ascending=False).head(10)

        demanda_col1, demanda_col2 = st.columns(2)
        with demanda_col1:
            st.markdown("#### Comensales promedio por restaurante")
            fig_carga_restaurantes = px.bar(
                demanda_restaurante.head(10).sort_values("pax_dia_promedio"),
                x="pax_dia_promedio",
                y="nombre_restaurante",
                orientation="h",
                labels={"pax_dia_promedio": "Comensales por día", "nombre_restaurante": "Restaurante"},
                color_discrete_sequence=["#0B4F39"],
            )
            fig_carga_restaurantes.update_layout(height=390, margin=dict(l=10, r=20, t=10, b=20), showlegend=False)
            st.plotly_chart(fig_carga_restaurantes, use_container_width=True, config=CONFIG_GRAFICAS)
            mostrar_analisis_grafica(
                f"Compara los comensales registrados por restaurante durante {periodo_dias} días.",
                "Detectar qué restaurantes concentran la mayor carga reciente.",
                "Revisar disponibilidad y coordinar apoyo operativo en los restaurantes con más demanda.",
            )
        with demanda_col2:
            st.markdown("#### Comensales promedio por horario")
            fig_carga_horarios = px.bar(
                demanda_horario.sort_values("pax_dia_promedio"),
                x="pax_dia_promedio",
                y="hora_visible",
                orientation="h",
                labels={"pax_dia_promedio": "Comensales por día", "hora_visible": "Hora registrada"},
                color_discrete_sequence=["#B49A62"],
            )
            fig_carga_horarios.update_layout(height=390, margin=dict(l=10, r=20, t=10, b=20), showlegend=False)
            st.plotly_chart(fig_carga_horarios, use_container_width=True, config=CONFIG_GRAFICAS)
            mostrar_analisis_grafica(
                "Agrupa comensales por hora registrada para mostrar cuándo se concentra el servicio.",
                "Identificar las horas con mayor carga y los periodos relativamente más tranquilos.",
                "Escalonar preparación y turnos de personal alrededor de las horas de mayor demanda.",
            )

        restaurante_mayor = demanda_restaurante.iloc[0] if not demanda_restaurante.empty else None
        if restaurante_mayor is not None:
            st.info(
                f"Mayor carga registrada: **{restaurante_mayor['nombre_restaurante']}**, "
                f"con {restaurante_mayor['pax_dia_promedio']:.1f} comensales por día en las fechas seleccionadas. "
                "Revisa disponibilidad antes de reasignar reservas o personal."
            )

        st.markdown("### Simulación: ¿qué pasa si cambia la demanda?")
        st.caption(
            f"Base: últimos {periodo_dias} días con reservas cargadas ({fechas_con_reservas[0]} a {fechas_con_reservas[-1]}). "
            "La comparación estima carga semanal por restaurante, aunque algunas fechas sean futuras."
        )
        escenario_col1, escenario_col2, escenario_col3 = st.columns(3)
        with escenario_col1:
            cambio_demanda_pct = st.slider(
                "Cambio de demanda (%)",
                min_value=-30,
                max_value=100,
                value=15,
                step=5,
                key="variacion_what_if",
            )
        with escenario_col2:
            ratio_mesero_what_if = st.number_input(
                "Comensales por mesero",
                min_value=1,
                max_value=40,
                value=14,
                step=1,
                key="ratio_mesero_what_if",
            )
        with escenario_col3:
            ratio_cocina_what_if = st.number_input(
                "Comensales por personal de cocina",
                min_value=1,
                max_value=60,
                value=25,
                step=1,
                key="ratio_cocina_what_if",
            )

        escenario_restaurantes = demanda_restaurante.copy()
        escenario_restaurantes["Pax semana actual"] = escenario_restaurantes["pax_periodo"]
        escenario_restaurantes["Pax semana simulada"] = np.ceil(
            escenario_restaurantes["Pax semana actual"] * (1 + cambio_demanda_pct / 100)
        ).astype(int)
        escenario_restaurantes["Meseros estimados / servicio"] = np.ceil(
            escenario_restaurantes["Pax semana simulada"] / periodo_dias / ratio_mesero_what_if
        ).astype(int)
        escenario_restaurantes["Cocina estimada / servicio"] = np.ceil(
            escenario_restaurantes["Pax semana simulada"] / periodo_dias / ratio_cocina_what_if
        ).astype(int)
        escenario_restaurantes["Raciones de referencia"] = escenario_restaurantes["Pax semana simulada"]

        fig_escenario = go.Figure()
        fig_escenario.add_trace(go.Bar(
            x=escenario_restaurantes["nombre_restaurante"],
            y=escenario_restaurantes["Pax semana actual"],
            name="Semana registrada",
            marker_color="#AAB7AF",
        ))
        fig_escenario.add_trace(go.Bar(
            x=escenario_restaurantes["nombre_restaurante"],
            y=escenario_restaurantes["Pax semana simulada"],
            name=f"Escenario {cambio_demanda_pct:+}%",
            marker_color="#0B4F39",
        ))
        fig_escenario.update_layout(
            barmode="group",
            height=390,
            margin=dict(l=20, r=20, t=20, b=90),
            yaxis_title="Comensales por semana",
            xaxis_title="Restaurante",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_escenario, use_container_width=True, config=CONFIG_GRAFICAS)
        mostrar_analisis_grafica(
            "Compara los comensales registrados con la proyección ajustada por el porcentaje seleccionado.",
            "Estimar cómo cambiaría la carga semanal de cada restaurante ante una variación de demanda.",
            "Preparar compras y capacidad según el escenario; sustituirlo por reservas confirmadas cuando estén disponibles.",
        )

        st.markdown("#### Personal estimado por restaurante y servicio")
        fig_personal = go.Figure()
        fig_personal.add_trace(go.Bar(
            x=escenario_restaurantes["nombre_restaurante"],
            y=escenario_restaurantes["Meseros estimados / servicio"],
            name="Meseros",
            marker_color="#0B4F39",
        ))
        fig_personal.add_trace(go.Bar(
            x=escenario_restaurantes["nombre_restaurante"],
            y=escenario_restaurantes["Cocina estimada / servicio"],
            name="Cocina",
            marker_color="#B49A62",
        ))
        fig_personal.update_layout(
            barmode="group",
            height=350,
            margin=dict(l=20, r=20, t=15, b=90),
            yaxis_title="Personas estimadas por servicio",
            xaxis_title="Restaurante",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_personal, use_container_width=True, config=CONFIG_GRAFICAS)
        mostrar_analisis_grafica(
            "Traduce la demanda simulada a personas estimadas de sala y cocina por restaurante.",
            "Comparar cómo se distribuye la dotación teórica bajo el escenario elegido.",
            "Usar las ratios configuradas como punto de partida y validar la asignación con la operación real.",
        )

        total_actual = int(escenario_restaurantes["Pax semana actual"].sum())
        total_simulado = int(escenario_restaurantes["Pax semana simulada"].sum())
        total_meseros = int(escenario_restaurantes["Meseros estimados / servicio"].sum())
        total_cocina = int(escenario_restaurantes["Cocina estimada / servicio"].sum())
        resumen_escenario = st.columns(5)
        resumen_escenario[0].metric("Comensales observados", f"{total_actual:,}")
        resumen_escenario[1].metric("Comensales simulados", f"{total_simulado:,}", f"{cambio_demanda_pct:+}%")
        resumen_escenario[2].metric("Meseros estimados / servicio", f"{total_meseros:,}")
        resumen_escenario[3].metric("Personal cocina / servicio", f"{total_cocina:,}")
        resumen_escenario[4].metric("Raciones de referencia", f"{total_simulado:,}")
        st.caption(
            "La dotación usa las ratios que indicaste y representa personal por servicio, no puestos actualmente asignados. "
            "Las raciones son una equivalencia de un comensal por ración; el consumo real requiere recetas e inventario."
        )

        st.markdown("---")
        c_cap1, c_cap2 = st.columns(2)

        with c_cap1:
            st.subheader("Franjas de máxima y menor actividad")
            df_turno_agg = df_filtrado.groupby(["turno", "franja_horaria"]).agg(
                pax_total=(operacion_columna, operacion_agregacion),
                reservas=("id_reserva", "count"),
                promedio_pax_mesa=("total_pax", "mean")
            ).reset_index().sort_values("pax_total", ascending=False)

            fig_turnos = px.bar(
                df_turno_agg,
                x="franja_horaria",
                y="pax_total",
                color="franja_horaria",
                color_discrete_sequence=["#0B4F39", "#B49A62", "#667A70", "#9A5C4A", "#627A8A", "#AAB7AF"],
                labels={"pax_total": metrica_operacion, "franja_horaria": "Horario"}
            )
            fig_turnos.update_traces(hovertemplate=f"%{{x}}<br>{metrica_operacion}: %{{y:,.0f}}<extra></extra>")
            fig_turnos.update_layout(
                paper_bgcolor="rgba(255,255,255,0.7)",
                plot_bgcolor="rgba(255,255,255,0.7)",
                font=dict(color="#0F172A", family="Plus Jakarta Sans, sans-serif"),
                yaxis=dict(gridcolor="#E2E8F0", tickfont=dict(color="#334155"), title_font=dict(color="#0F172A")),
                xaxis=dict(tickfont=dict(color="#334155"), title_font=dict(color="#0F172A")),
                margin=dict(l=30, r=30, t=30, b=30),
                height=350
            )
            st.plotly_chart(fig_turnos, use_container_width=True, config=CONFIG_GRAFICAS)
            mostrar_analisis_grafica(
                f"Compara {metrica_operacion.lower()} por franja horaria y turno de servicio.",
                "Cuantificar la diferencia entre el horario de mayor actividad y el de menor actividad.",
                "Escalonar entradas y descansos hacia las franjas pico; aprovechar las franjas valle para preparación.",
            )

            # Alerta ejecutiva de Yield Management
            if not df_turno_agg.empty:
                hora_pico = df_turno_agg.iloc[0]["franja_horaria"]
                hora_valle = df_turno_agg.iloc[-1]["franja_horaria"]
                st.markdown(f"""
                    <div class="vip-alert-card">
                        <strong>📌 Horarios destacados:</strong><br>
                        • <strong>Mayor actividad:</strong> <span style="color: #DC2626; font-weight: 700;">{hora_pico}</span> ({round(df_turno_agg.iloc[0]['pax_total']/max(1, df_turno_agg['pax_total'].sum())*100, 1)}% de {metrica_operacion.lower()}).<br>
                        • <strong>Menor actividad:</strong> <span style="color: #059669; font-weight: 700;">{hora_valle}</span> ({round(df_turno_agg.iloc[-1]['pax_total']/max(1, df_turno_agg['pax_total'].sum())*100, 1)}% de {metrica_operacion.lower()}).
                    </div>
                """, unsafe_allow_html=True)

        with c_cap2:
            st.subheader("Distribución recomendada de mesas")
            st.caption("Estructura de configuración de sala sugerida para maximizar la rotación y evitar mesas ociosas:")

            # Clasificación de reservas por tamaño de mesa
            def clasificar_mesa(pax):
                if pax <= 2:
                    return "Mesa Pareja (2 pax)"
                elif pax <= 4:
                    return "Mesa Familiar Pequeña (3-4 pax)"
                elif pax <= 6:
                    return "Mesa Familiar Grande (5-6 pax)"
                else:
                    return "Mesa Grupal Imperial (>6 pax)"

            df_filtrado["tipo_mesa"] = df_filtrado["total_pax"].apply(clasificar_mesa)
            df_mesas_agg = df_filtrado["tipo_mesa"].value_counts().reset_index()
            df_mesas_agg.columns = ["Configuración de Mesa", "Nº Reservas"]
            df_mesas_agg["Porcentaje"] = ((df_mesas_agg["Nº Reservas"] / df_mesas_agg["Nº Reservas"].sum()) * 100).round(1)

            fig_mesas = px.pie(
                df_mesas_agg,
                names="Configuración de Mesa",
                values="Nº Reservas",
                color_discrete_sequence=["#B49A62", "#5D806B", "#627A8A", "#A9695E"]
            )
            fig_mesas.update_layout(
                paper_bgcolor="rgba(255,255,255,0.7)",
                font=dict(color="#0F172A", family="Plus Jakarta Sans, sans-serif"),
                margin=dict(l=20, r=20, t=20, b=20),
                height=300,
                legend=dict(font=dict(color="#0F172A"))
            )
            st.plotly_chart(fig_mesas, use_container_width=True, config=CONFIG_GRAFICAS)
            mostrar_analisis_grafica(
                "Clasifica las reservas de la tabla de hechos por tamaño de grupo y muestra su proporción.",
                "Conocer qué configuraciones de mesa se solicitan con más frecuencia.",
                "Ajustar el montaje previsto a la mezcla de grupos observada y validar el resultado con el equipo de sala.",
            )

            st.dataframe(
                df_mesas_agg.style.format({"Nº Reservas": "{:,}", "Porcentaje": "{:.1f}%"}),
                use_container_width=True,
                hide_index=True
            )


# =====================================================================
# TAB 3: SEGMENTACIÓN DE CLIENTES Y NIVELES DE ATENCIÓN (VIP & FAMILIAS)
# =====================================================================
with tabs[1]:
    st.divider()
    df_filtrado = filtrar_analisis(df_master, "huespedes", ["hotel", "restaurant", "attention"])
    st.caption(f"{len(df_filtrado):,} reservas incluidas en este análisis.")
    if df_filtrado.empty:
        st.warning("⚠️ No hay registros para segmentación de clientes.")
    else:
        st.subheader("Perfil de huéspedes y necesidades de servicio")
        st.caption("Permite anticipar servicios especiales, atenciones protocolares y requerimientos de montaje infantil.")

        col_seg1, col_seg2 = st.columns([1, 1.4])

        with col_seg1:
            df_atencion_agg = df_filtrado.groupby("categoria_atencion").agg(
                reservas=("id_reserva", "count"),
                pax=("total_pax", "sum")
            ).reset_index()

            fig_atencion = px.pie(
                df_atencion_agg,
                names="categoria_atencion",
                values="reservas",
                hole=0.45,
                color="categoria_atencion",
                color_discrete_map={
                    "VIP": "#9A5C4A",
                    "Fidelidad": "#B49A62",
                    "Especial": "#627A8A",
                    "Standard": "#8A9990"
                }
            )
            fig_atencion.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#F8FAFC"),
                margin=dict(l=20, r=20, t=20, b=20),
                height=320,
                legend=dict(orientation="h", y=-0.1)
            )
            st.plotly_chart(fig_atencion, use_container_width=True, config=CONFIG_GRAFICAS)
            mostrar_analisis_grafica(
                "Relaciona la categoría de atención de la dimensión correspondiente con el número de reservas.",
                "Entender la composición de reservas por protocolo, fidelidad y atención estándar.",
                "Anticipar protocolos y recursos de servicio para las categorías que representen mayor volumen.",
            )

        with col_seg2:
            st.markdown("#### Mobiliario infantil")
            total_bebes_res = int(df_filtrado["num_bebes"].sum())
            total_ninos_res = int(df_filtrado["num_ninos"].sum())
            reservas_con_periquera = int(df_filtrado["requiere_periquera"].sum())

            k1, k2, k3 = st.columns(3)
            with k1:
                st.metric("Total Bebés", f"{total_bebes_res:,}")
            with k2:
                st.metric("Total Niños", f"{total_ninos_res:,}")
            with k3:
                st.metric("Periqueras Requeridas", f"{reservas_con_periquera:,}")

            # Desglose de periqueras por restaurante
            df_periqueras_rest = df_filtrado[df_filtrado["requiere_periquera"] == True].groupby("nombre_restaurante")["id_reserva"].count().reset_index()
            df_periqueras_rest.columns = ["Restaurante", "Periqueras Solicitadas"]
            df_periqueras_rest = df_periqueras_rest.sort_values("Periqueras Solicitadas", ascending=False).head(5)

            st.dataframe(
                df_periqueras_rest.style.format({"Periqueras Solicitadas": "{:,}"}),
                use_container_width=True,
                hide_index=True
            )

# =====================================================================
# TAB 4: ANÁLISIS DE FLUJO INTER-HOTEL (CROSS-DINING)
# =====================================================================
with tabs[1]:
    st.divider()
    df_filtrado = filtrar_analisis(df_master, "movilidad", ["origin", "destination", "cross"])
    st.caption(f"{len(df_filtrado):,} reservas incluidas en este análisis.")
    if df_filtrado.empty:
        st.warning("⚠️ No hay datos para el análisis de Cross-Dining.")
    else:
        st.subheader("Flujo de comensales entre hoteles")
        st.caption("Rastrea el intercambio de comensales entre hoteles: desde el hotel donde se hospeda el huésped hasta el hotel donde cena.")

        # Matriz de flujo: Hotel Hospedaje -> Hotel Restaurante
        df_flujo = df_filtrado.groupby(["cod_hotel_hospedaje", "cod_hotel_restaurante", "hotel_hospedaje", "hotel_restaurante"]).agg(
            total_pax=("total_pax", "sum"),
            reservas=("id_reserva", "count")
        ).reset_index()

        # Diagrama de Sankey interactivo
        hoteles_origen_unicos = df_flujo["hotel_hospedaje"].unique().tolist()
        hoteles_destino_unicos = df_flujo["hotel_restaurante"].unique().tolist()
        
        # Nombres de nodos diferenciados
        nodos = [f"[Origen] {h}" for h in hoteles_origen_unicos] + [f"[Cena] {h}" for h in hoteles_destino_unicos]
        nodo_dict = {nombre: i for i, nombre in enumerate(nodos)}

        sources = [nodo_dict[f"[Origen] {row['hotel_hospedaje']}"] for _, row in df_flujo.iterrows()]
        targets = [nodo_dict[f"[Cena] {row['hotel_restaurante']}"] for _, row in df_flujo.iterrows()]
        values = df_flujo["total_pax"].tolist()

        fig_sankey = go.Figure(data=[go.Sankey(
            node=dict(
                pad=18,
                thickness=20,
                line=dict(color="#F4F7F4", width=0.8),
                label=nodos,
                color=["#B49A62"] * len(hoteles_origen_unicos) + ["#0B4F39"] * len(hoteles_destino_unicos)
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color="rgba(180, 154, 98, 0.3)"
            )
        )])
        fig_sankey.update_layout(
            title_text="Diagrama de Flujo: Hotel Hospedaje (Izquierda) ➔ Hotel Restaurante (Derecha)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#F8FAFC", size=11),
            height=450,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_sankey, use_container_width=True, config=CONFIG_GRAFICAS)
        mostrar_analisis_grafica(
            "Conecta el hotel de hospedaje con el hotel restaurante y pondera cada flujo por comensales.",
            "Medir los movimientos de cross-dining entre origen y destino dentro de la selección.",
            "Coordinar transporte y disponibilidad de mesa en los destinos que reciben más huéspedes externos.",
        )

        st.markdown("---")
        c_cd1, c_cd2 = st.columns(2)

        with c_cd1:
            st.subheader("Movilidad entre hoteles")
            pivot_cross = df_filtrado.pivot_table(
                index="hotel_hospedaje",
                columns="hotel_restaurante",
                values="total_pax",
                aggfunc="sum",
                fill_value=0
            )
            fig_cross_heat = px.imshow(
                pivot_cross,
                labels=dict(x="Hotel Restaurante (Destino)", y="Hotel Hospedaje (Origen)", color="Pax"),
                color_continuous_scale=["#F2F5F2", "#0B4F39"],
            )
            fig_cross_heat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#F8FAFC"),
                margin=dict(l=50, r=20, t=20, b=50),
                height=340
            )
            st.plotly_chart(fig_cross_heat, use_container_width=True, config=CONFIG_GRAFICAS)
            mostrar_analisis_grafica(
                "Cruza hoteles de hospedaje y de restaurante; la intensidad representa comensales del flujo.",
                "Comparar rápidamente las rutas interhotel más y menos utilizadas.",
                "Priorizar coordinación entre hoteles en las rutas de mayor volumen y revisar las de baja utilización.",
            )

        with c_cd2:
            st.subheader("Restaurantes con mayor recepción externa")
            st.caption("Restaurantes que más huéspedes atraen provenientes de otros hoteles del complejo:")

            df_iman = df_filtrado[df_filtrado["es_cross_dining"] == True].groupby(["nombre_restaurante", "especialidad", "hotel_restaurante"]).agg(
                pax_externos=("total_pax", "sum"),
                reservas_externas=("id_reserva", "count")
            ).reset_index().sort_values("pax_externos", ascending=False).head(7)

            fig_iman = px.bar(
                df_iman,
                x="pax_externos",
                y="nombre_restaurante",
                orientation="h",
                color="pax_externos",
                color_continuous_scale=["#E7EEE9", "#0B4F39"],
                labels={"pax_externos": "Pax Externos", "nombre_restaurante": "Restaurante"}
            )
            fig_iman.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#F8FAFC"),
                margin=dict(l=10, r=20, t=10, b=20),
                height=340,
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig_iman, use_container_width=True, config=CONFIG_GRAFICAS)
            mostrar_analisis_grafica(
                "Filtra reservas marcadas como cross-dining y suma comensales externos por restaurante.",
                "Identificar restaurantes que atraen más huéspedes de otros hoteles.",
                "Asegurar capacidad y coordinación de llegadas en los restaurantes con mayor recepción externa.",
            )


# =====================================================================
# TAB 5: MODELO PREDICTIVO Y SIMULADOR DE DEMANDA
# =====================================================================
with tabs[1]:
    st.divider()
    df_filtrado = filtrar_analisis(df_master, "pronostico", ["hotel", "restaurant", "shift"])
    st.caption(f"{len(df_filtrado):,} reservas incluidas en este análisis.")
    st.subheader("Pronóstico de comensales")
    st.caption("La red neuronal estima la demanda futura con el historial del periodo y los filtros seleccionados.")
    st.caption("La línea verde muestra el histórico y la dorada, la estimación. El error de validación es orientativo.")

    if len(df_filtrado) < 50:
        st.warning("Esta selección tiene menos de 50 reservas. Amplía el periodo o quita filtros para preparar el pronóstico.")
    else:
        horizon_label = st.selectbox(
            "Horizonte de planificación",
            options=["7 días", "30 días", "90 días", "6 meses", "1 año", "2 años", "5 años"],
            index=1,
        )
        horizon_days = {"7 días": 7, "30 días": 30, "90 días": 90, "6 meses": 182, "1 año": 365, "2 años": 730, "5 años": 1825}[horizon_label]

        if st.button("Calcular pronóstico", type="primary"):
            st.session_state["mostrar_pronostico"] = True

        df_futuro = pd.DataFrame()
        if st.session_state.get("mostrar_pronostico", False):
            with st.spinner("Preparando la previsión con la red neuronal..."):
                try:
                    resultado_red = entrenar_pronostico_cacheado(df_filtrado)
                    df_futuro = generar_pronostico_cacheado(df_filtrado, horizon_days)
                except ValueError as error:
                    st.error(str(error))

        if not st.session_state.get("mostrar_pronostico", False):
            st.info("Elige el periodo de planificación y pulsa «Calcular pronóstico» para generar la estimación.")

        if not df_futuro.empty:
            metric_1, metric_2, metric_3, metric_4 = st.columns(4)
            metric_1.metric("Modelo", "MLP neuronal")
            metric_2.metric("Error MAE validación", f"{resultado_red.metrics['mae']:.1f} pax")
            metric_3.metric("Error RMSE validación", f"{resultado_red.metrics['rmse']:.1f} pax")
            metric_4.metric("Horizonte", horizon_label)

            st.markdown("#### Demanda registrada y estimada, día por día")
            df_hist_real = df_filtrado.groupby("id_fecha", as_index=False)["total_pax"].sum().sort_values("id_fecha").reset_index(drop=True)
            df_proj_dia = df_futuro.groupby("fecha", as_index=False)["pax_predichos"].sum().rename(columns={"fecha": "id_fecha"})

            # Mostrar todo el historial disponible en la BD y luego el pronóstico futuro.
            df_hist_real["id_fecha"] = pd.to_datetime(df_hist_real["id_fecha"])
            df_proj_dia["id_fecha"] = pd.to_datetime(df_proj_dia["id_fecha"])

            fig_proj = go.Figure()
            fig_proj.add_trace(go.Scatter(
                x=df_hist_real["id_fecha"],
                y=df_hist_real["total_pax"],
                mode="lines+markers",
                name="Histórico real",
                    line=dict(color="#0B4F39", width=3)
            ))
            if not df_proj_dia.empty:
                fig_proj.add_trace(go.Scatter(
                    x=df_proj_dia["id_fecha"],
                    y=df_proj_dia["pax_predichos"],
                    mode="lines",
                    name="Pronóstico neuronal",
                    line=dict(color="#B49A62", width=2)
                ))

            fig_proj.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#1F2937"),
                yaxis_title="Comensales por día",
                height=360,
                xaxis_title="Fecha",
                margin=dict(l=45, r=20, t=20, b=45),
            )
            fig_proj.update_xaxes(showgrid=True, gridcolor="#E5E7EB", title_font=dict(color="#1F2937"), tickfont=dict(color="#374151"))
            fig_proj.update_yaxes(showgrid=True, gridcolor="#E5E7EB", title_font=dict(color="#1F2937"), tickfont=dict(color="#374151"))
            st.plotly_chart(fig_proj, use_container_width=True, config=CONFIG_GRAFICAS)
            mostrar_analisis_grafica(
                "Compara pax históricos agrupados por fecha con la estimación diaria del modelo neuronal.",
                "Observar la dirección y magnitud esperada de la demanda para el horizonte elegido.",
                "Usar la proyección como escenario de planificación y contrastarla con las reservas confirmadas.",
            )

            st.markdown("#### Resumen mensual")
            resumen_mensual = df_futuro.groupby("mes", as_index=False).agg(
                pax_previstos=("pax_predichos", "sum"),
                promedio_diario=("pax_predichos", "mean"),
                pico_diario=("pax_predichos", "max"),
            )
            resumen_mensual[["pax_previstos", "promedio_diario", "pico_diario"]] = resumen_mensual[["pax_previstos", "promedio_diario", "pico_diario"]].round(1)
            st.dataframe(resumen_mensual, use_container_width=True, hide_index=True)
            st.download_button(
                "⬇️ Descargar pronóstico completo (CSV)",
                data=df_futuro.to_csv(index=False).encode("utf-8"),
                file_name=f"pronostico_demanda_{horizon_days}_dias.csv",
                mime="text/csv",
                use_container_width=True,
            )

            st.markdown("---")
            # SIMULADOR DE CAPACIDAD Y PERSONAL (STAFFING & OPERATIONAL SIMULATOR)
            st.subheader("Simulador de capacidad y dotación de personal")
            st.caption("Calcula en tiempo real las necesidades de meseros, cocineros y costos operativos en base a la ocupación proyectada:")

        s_col1, s_col2 = st.columns([1, 1.2])
        with s_col1:
            st.markdown("##### Parámetros de simulación")
            sim_ocupacion = st.slider("Ocupación Hotelera Proyectada del Complejo (%):", min_value=50, max_value=100, value=85, step=5)
            sim_ratio_mesero = st.slider("Ratio Comensales por Mesero / Rango de Sala:", min_value=8, max_value=24, value=14, step=2)
            sim_ratio_cocina = st.slider("Ratio Comensales por Personal de Cocina:", min_value=15, max_value=40, value=25, step=5)
            sim_restaurante = st.selectbox("Seleccionar Restaurante para Simular:", options=["Todos los Restaurantes (Global)"] + sorted(df_master["nombre_restaurante"].unique().tolist()))

        with s_col2:
            st.markdown("##### Resultados de operación")
            if sim_restaurante == "Todos los Restaurantes (Global)":
                cap_base = sum([r["capacidad_maxima_pax"] for r in RESTAURANTES_CATALOGO]) * 3
            else:
                cap_base = df_master[df_master["nombre_restaurante"] == sim_restaurante]["capacidad_maxima_pax"].iloc[0] * 3

            pax_esperados = int(cap_base * (sim_ocupacion / 100.0))
            meseros_necesarios = max(1, int(np.ceil(pax_esperados / sim_ratio_mesero)))
            cocineros_necesarios = max(1, int(np.ceil(pax_esperados / sim_ratio_cocina)))
            mesas_estimadas = max(1, int(np.ceil(pax_esperados / 2.8)))

            res1, res2 = st.columns(2)
            with res1:
                st.metric("Comensales Estimados", f"{pax_esperados:,} pax")
                st.metric("Meseros Necesarios", f"{meseros_necesarios} meseros")
            with res2:
                st.metric("Mesas a Montar", f"{mesas_estimadas} mesas")
                st.metric("Personal Cocina / Stewards", f"{cocineros_necesarios} personas")

            # Diagnóstico operativo
            if sim_ocupacion > 90:
                st.error("🚨 **Alerta de Sobrecarga:** Ocupación crítica superior al 90%. Se recomienda habilitar un tercer turno y reforzar la línea caliente de cocina.")
            elif sim_ocupacion >= 75:
                st.warning("⚠️ **Alerta Moderada:** Ocupación alta. Mantener dotación completa de personal en sala y verificar periqueras.")
            else:
                st.success("✅ **Operación Fluida:** Ocupación dentro de los límites estándar de servicio.")



# =====================================================================
# TAB 7: ASISTENTE DE PREGUNTAS Y FILTROS
# =====================================================================
with tabs[2]:
    df_filtrado = filtrar_analisis(df_master, "datos", ["hotel", "restaurant", "shift", "attention", "cross"])
    from dashboard_assistant import responder_consulta

    st.subheader("Consulta de datos")
    st.caption("Escribe una pregunta sencilla sobre las reservas. Las respuestas se calculan aquí mismo con los datos seleccionados.")
    st.info("Puedes preguntar, por ejemplo: «¿Qué restaurante tuvo más comensales?», «¿Cuántas reservas hubo en agosto?» o «Filtra por turno 2». También puedes pedir «restablece filtros».")

    if "conversacion_dashboard" not in st.session_state:
        st.session_state["conversacion_dashboard"] = []

    for message in st.session_state["conversacion_dashboard"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    pregunta = st.chat_input("Pregunta por comensales, reservas, hoteles, restaurantes o meses")
    if pregunta:
        respuesta, filtros = responder_consulta(pregunta, df_filtrado, df_master)
        st.session_state["conversacion_dashboard"].append({"role": "user", "content": pregunta})
        st.session_state["conversacion_dashboard"].append({"role": "assistant", "content": respuesta})

        if filtros:
            applied = dict(st.session_state.get("filtros_aplicados_datos", {}))
            widget_updates = {}
            if filtros.get("reset"):
                applied = {"dates": filtros["date_range"]}
                widget_updates["widget_fechas_datos"] = filtros["date_range"]
                for field in ("hotel", "restaurant", "shift", "attention", "cross"):
                    widget_updates[f"widget_{field}_datos"] = []
            else:
                if "date_range" in filtros:
                    applied["dates"] = filtros["date_range"]
                    widget_updates["widget_fechas_datos"] = filtros["date_range"]
                for field in ("hotel", "restaurant", "shift", "attention"):
                    if field in filtros:
                        applied[field] = [filtros[field]]
                        widget_updates[f"widget_{field}_datos"] = [filtros[field]]
                if "cross_dining" in filtros:
                    applied["cross"] = [filtros["cross_dining"]]
                    widget_updates["widget_cross_datos"] = [filtros["cross_dining"]]
            widget_updates["filtros_aplicados_datos"] = applied
            st.session_state["_filtros_asistente_pendientes"] = widget_updates
            st.rerun()

        with st.chat_message("user"):
            st.markdown(pregunta)
        with st.chat_message("assistant"):
            st.markdown(respuesta)

    if st.session_state["conversacion_dashboard"] and st.button("Borrar conversación"):
        st.session_state["conversacion_dashboard"] = []
        st.rerun()


# =====================================================================
# TAB 8: EXPORTACIÓN Y REPORTES
# =====================================================================
with tabs[2]:
    st.divider()
    st.subheader("Exportación de reportes operativos")
    st.caption("Descarga la información procesada y limpia para análisis externo en Excel, CSV o reportes ejecutivos.")

    report_total = len(df_filtrado)
    report_pax = int(df_filtrado["total_pax"].sum()) if not df_filtrado.empty else 0
    report_avg = round(report_pax / report_total, 2) if report_total else 0
    report_cross = round(float(df_filtrado["es_cross_dining"].mean() * 100), 1) if not df_filtrado.empty else 0
    report_top = "Pendiente de datos"
    report_peak = "Pendiente de datos"
    if not df_filtrado.empty:
        report_top = str(df_filtrado.groupby("nombre_restaurante")["total_pax"].sum().idxmax())
        daily_report = df_filtrado.groupby("id_fecha")["total_pax"].sum()
        report_peak = f"{daily_report.idxmax()} ({int(daily_report.max()):,} pax)"

    st.markdown("""
        <div class="report-band">
            <h3>📘 Informe de Dirección: propósito y decisiones</h3>
            <p><strong>Qué buscamos hacer:</strong> construir una fuente única de inteligencia operativa para entender la demanda de restaurantes, anticipar la presión de servicio y mejorar la experiencia del huésped.</p>
            <p><strong>Cómo funciona:</strong> el ETL limpia y anonimiza los archivos históricos, los organiza por fecha, hotel, restaurante, turno y tipo de atención; después las gráficas diagnostican el comportamiento y la red neuronal proyecta la demanda futura.</p>
            <p><strong>Qué decisiones soporta:</strong> asignación de mesas, personal de sala y cocina, horarios de operación, coordinación cross-dining, preparación VIP/familiar y planificación de compras.</p>
        </div>
    """, unsafe_allow_html=True)

    report_cards = st.columns(4)
    report_cards[0].metric("Reservas analizadas", f"{report_total:,}")
    report_cards[1].metric("Comensales analizados", f"{report_pax:,}")
    report_cards[2].metric("Pax promedio / reserva", f"{report_avg}")
    report_cards[3].metric("Cross-dining", f"{report_cross}%")

    st.markdown(f"""
        <div class="report-band">
            <h4>📌 Resultado actual</h4>
            <p><strong>Restaurante con mayor demanda:</strong> {report_top}</p>
            <p><strong>Pico diario detectado:</strong> {report_peak}</p>
            <p><strong>Lectura ejecutiva:</strong> estos indicadores muestran el tamaño de la operación, el nivel de movilidad entre hoteles y el punto que debe priorizarse en la planificación.</p>
        </div>
        <div class="report-band">
            <h4>🛠️ Problemas que resolvemos</h4>
            <p>• Datos dispersos en archivos y formatos distintos: se normalizan en una base central.</p>
            <p>• Decisiones reactivas ante picos: se identifican patrones diarios y se proyectan escenarios.</p>
            <p>• Capacidad mal distribuida: se compara demanda contra restaurante, turno y hotel.</p>
            <p>• Atención especial no anticipada: se detectan perfiles VIP, familias, bebés y cross-dining.</p>
        </div>
        <div class="report-band">
            <h4>🚀 Optimizaciones y soluciones recomendadas</h4>
            <p>1. Cargar al menos un año completo y reentrenar mensualmente para mejorar estacionalidad.</p>
            <p>2. Reforzar personal y mise en place en los turnos con semáforo amarillo/rojo.</p>
            <p>3. Redistribuir reservas entre restaurantes imán y restaurantes con capacidad ociosa.</p>
            <p>4. Integrar ocupación hotelera, cancelaciones, no-shows, clima y eventos para aumentar precisión.</p>
            <p>5. Usar el CSV pronosticado como agenda operativa y comparar predicción contra resultado real.</p>
        </div>
    """, unsafe_allow_html=True)

    reporte_direccion = f"""REPORTE EJECUTIVO BAHIA PRINCIPE
Periodo: {f_inicio} a {f_fin}

OBJETIVO
Convertir reservas históricas en decisiones de capacidad, servicio y previsión de demanda.

RESULTADOS
Reservas analizadas: {report_total:,}
Comensales analizados: {report_pax:,}
Promedio pax/reserva: {report_avg}
Cross-dining: {report_cross}%
Restaurante líder: {report_top}
Pico diario: {report_peak}

SOLUCIONES
- Centralizar y normalizar la información mediante ETL.
- Detectar saturación por hotel, restaurante y turno.
- Predecir demanda diaria con red neuronal temporal.
- Optimizar mesas, personal, compras y coordinación cross-dining.

SIGUIENTE PASO
Cargar un año completo, entrenar el modelo y comparar cada predicción con el resultado real para mejorar continuamente.
"""
    st.download_button("📄 Descargar informe ejecutivo TXT", reporte_direccion, "informe_direccion_bahia_principe.txt", "text/plain", use_container_width=True)


# =====================================================================
# TAB 9: RESULTADOS DEL PROYECTO E IMPACTO OPERATIVO
# =====================================================================
with tabs[3]:
    st.subheader("Resultados del Proyecto & Impacto Operativo")
    st.caption("Alcance, valor operativo y capacidades disponibles en la plataforma.")

    proyecto_df = df_master.copy()
    if proyecto_df.empty:
        st.info("Carga reservas para ver resultados cuantitativos del proyecto.")
        proyecto_reservas = 0
        proyecto_pax = 0
        proyecto_hoteles = 0
        proyecto_restaurantes = 0
        proyecto_promedio = 0
    else:
        proyecto_reservas = len(proyecto_df)
        proyecto_pax = int(proyecto_df["total_pax"].sum())
        proyecto_hoteles = proyecto_df["hotel_restaurante"].nunique()
        proyecto_restaurantes = proyecto_df["nombre_restaurante"].nunique()
        proyecto_promedio = round(proyecto_pax / proyecto_reservas, 2) if proyecto_reservas else 0

    proyecto_kpis = st.columns(4)
    proyecto_kpis[0].metric("Reservas centralizadas", f"{proyecto_reservas:,}")
    proyecto_kpis[1].metric("Comensales procesados", f"{proyecto_pax:,}")
    proyecto_kpis[2].metric("Hoteles / restaurantes", f"{proyecto_hoteles} / {proyecto_restaurantes}")
    proyecto_kpis[3].metric("Pax por reserva", f"{proyecto_promedio}")

    st.markdown("---")
    st.markdown("### Problema original vs. solución actual")
    alcance_col, solucion_col = st.columns(2)
    with alcance_col:
        st.markdown("""
            **Alcance inicial planteado**

            Una plataforma para cubrir múltiples áreas corporativas y la operación completa del complejo. Ese alcance reunía fuentes, procesos y necesidades heterogéneas difíciles de consolidar con fiabilidad en una sola entrega.
        """)
    with solucion_col:
        st.markdown("""
            **Foco implementado**

            Un sistema BI centrado en la operación crítica de los restaurantes de especialidad: reservas, hotel, restaurante, fecha, turno, tipo de atención, comensales y movilidad interhotel. El foco permite validar datos y decisiones en un dominio operativo concreto.
        """)
    st.markdown("---")
    st.markdown("### Resultados y valor operativo")
    impacto_col, evidencia_col = st.columns([1.1, 1])
    with impacto_col:
        st.markdown("""
            <div class="impact-item"><strong>Centralización de datos</strong><br>El ETL limpia y consolida archivos de reservas en un modelo dimensional con hechos y dimensiones de tiempo, hotel, servicio y atención.</div>
            <div class="impact-item"><strong>Optimización de A&B</strong><br>Las vistas comparan demanda por restaurante, turno y hotel, muestran mezclas de grupos y ayudan a planificar dotación. La medición real de ocupación depende de contar con aforos confiables.</div>
            <div class="impact-item"><strong>Decisión asistida por IA</strong><br>El backend FastAPI incorpora el endpoint <code>/api/v1/ai/consult</code> con Gemini para generar análisis y recomendaciones basados en KPIs. Requiere <code>GEMINI_API_KEY</code>.</div>
        """, unsafe_allow_html=True)
        st.caption("El chat de esta pestaña de Streamlit responde con reglas locales; no invoca Gemini directamente.")

    with evidencia_col:
        st.markdown("#### Evidencia del periodo cargado")
        if not proyecto_df.empty:
            restaurantes_pax = proyecto_df.groupby("nombre_restaurante")["total_pax"].sum().sort_values(ascending=False)
            top_restaurant = str(restaurantes_pax.index[0])
            top_restaurant_pax = int(restaurantes_pax.iloc[0])
            st.markdown(f"**Mayor volumen:** {top_restaurant} · {top_restaurant_pax:,} pax")

            dolce_vita = restaurantes_pax[restaurantes_pax.index.str.casefold() == "dolce vita"]
            alux = restaurantes_pax[restaurantes_pax.index.str.casefold() == "alux"]
            if not dolce_vita.empty or not alux.empty:
                alux_value = int(alux.iloc[0]) if not alux.empty else 0
                dolce_value = int(dolce_vita.iloc[0]) if not dolce_vita.empty else 0
                st.markdown(f"**Comparativo Alux / Dolce Vita:** {alux_value:,} / {dolce_value:,} pax")

            demanda_turno = proyecto_df.groupby("franja_horaria")["total_pax"].sum().sort_values(ascending=False)
            if not demanda_turno.empty:
                st.markdown(f"**Franja con más pax:** {demanda_turno.index[0]} · {int(demanda_turno.iloc[0]):,} pax")
        else:
            st.caption("Los comparativos aparecerán después de cargar datos.")
        st.caption("Estos volúmenes describen el periodo cargado; por sí solos no demuestran ahorro ni ROI.")

    st.markdown("---")
    st.markdown("### Innovación y Valor Aportado del Proyecto")
    innovacion_cols = st.columns(3)
    with innovacion_cols[0]:
        st.markdown("""
            **De la operación a ciegas al dato oportuno**

            Frente a reportes en papel o registros aislados, el ETL consolida archivos de reservas y los organiza en un modelo dimensional común. Streamlit actualiza su lectura en intervalos de caché de hasta 60 segundos. La conexión cloud usa PostgreSQL y admite Supabase mediante `DATABASE_URL`; el proveedor depende de la configuración de cada despliegue.
        """)
    with innovacion_cols[1]:
        st.markdown("""
            **De la complejidad a la especialización estratégica en A&B**

            Focalizar el proyecto en restaurantes de especialidad permite observar afluencia por restaurante, fecha y turno, y preparar capacidad y dotación con datos comparables. Los tiempos de espera y la satisfacción del huésped no se miden directamente todavía: requieren capturar esas variables en las fuentes.
        """)
    with innovacion_cols[2]:
        st.markdown("""
            **IA como consultor gerencial**

            El backend FastAPI ofrece Gemini para convertir KPIs y una consulta ejecutiva en resumen, análisis, recomendaciones y nivel de riesgo. Requiere `GEMINI_API_KEY`. El chat de Streamlit opera con reglas locales y las tarjetas explicativas de gráficas son textos guiados; no son respuestas generadas por Gemini.
        """)

    st.markdown("---")
    st.markdown("### Plataforma y estado de integración")
    database_url_configured = get_database_url().lower()
    if "supabase" in database_url_configured:
        database_status = "PostgreSQL en Supabase configurado"
    elif database_url_configured.startswith("postgresql"):
        database_status = "PostgreSQL externo configurado"
    else:
        database_status = "SQLite local activo; Supabase requiere configurar DATABASE_URL"

    integration_col, next_steps_col = st.columns(2)
    with integration_col:
        st.markdown(f"<div class='status-line'><span>Base de datos</span><span class='status-value'>{database_status}</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='status-line'><span>Modelo analítico</span><span class='status-value'>Esquema dimensional de reservas</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='status-line'><span>Pronóstico</span><span class='status-value'>Modelo neuronal de demanda diaria</span></div>", unsafe_allow_html=True)
        st.markdown("<div class='status-line'><span>Gemini</span><span class='status-value'>Implementado en la API; requiere clave en backend</span></div>", unsafe_allow_html=True)
    with next_steps_col:
        st.markdown("#### Siguientes pasos para ampliar el impacto")
        st.markdown("""
            - Completar y validar aforos por restaurante y turno antes de interpretar porcentajes de ocupación.
            - Comparar previsiones con reservas reales para medir error operativo en el tiempo.
            - Registrar cambios de dotación y resultados para evaluar productividad y servicio.
            - Mantener `DATABASE_URL` y `GEMINI_API_KEY` en los secretos del despliegue; no se muestran credenciales en el dashboard.
        """)

# =====================================================================
# PIE DE PÁGINA CORPORATIVO
# =====================================================================

st.markdown("""
    <div style="text-align: center; margin-top: 40px; padding: 20px 0; border-top: 1px solid rgba(255, 255, 255, 0.1); color: #64748B; font-size: 0.8rem;">
        Bahía Príncipe Hotels & Resorts © 2026 • Suite Analítica de Reservas de Restaurantes de Especialidad • Desarrollado con Streamlit & SQLAlchemy
    </div>
""", unsafe_allow_html=True)
