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
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Fondo principal limpio y texto oscuro de alto contraste */
    [data-testid="stAppViewContainer"] {
        background: #F8FAFC;
        color: #0F172A;
    }
    [data-testid="stHeader"] { 
        background: rgba(248, 250, 252, 0.95); 
    }

    /* Barra lateral corporativa Bahía Príncipe con texto blanco nítido */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0B1528 0%, #13223D 100%);
        color: #FFFFFF;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
    [data-testid="stSidebar"] label { 
        color: #F1F5F9 !important; 
        font-weight: 500;
    }
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 { 
        color: #FFFFFF !important; 
    }

    /* Títulos principales con contraste oscuro */
    h1, h2, h3, h4, h5, h6 { 
        color: #0F172A !important; 
        font-weight: 700;
        letter-spacing: -0.01em; 
    }
    p, span {
        color: #1E293B;
    }

    .block-container { 
        max-width: 1500px; 
        padding-top: 1.5rem; 
    }

    /* Tarjetas de Métricas Ejecutivas */
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 16px 18px;
        color: #0F172A;
        box-shadow: 0 4px 14px rgba(15, 23, 42, 0.05);
        min-height: 112px;
    }
    .metric-title {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #475569;
        margin-bottom: 6px;
        font-weight: 700;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 800;
        color: #0F172A;
        line-height: 1.1;
    }
    .metric-sub {
        font-size: 0.8rem;
        margin-top: 6px;
        color: #0284C7;
        font-weight: 600;
    }

    /* Banner corporativo */
    .brand-header {
        background: linear-gradient(90deg, #0B1528 0%, #172B4D 50%, #0B1528 100%);
        border: 1px solid rgba(197, 160, 89, 0.4);
        border-radius: 14px;
        padding: 22px 28px;
        margin-bottom: 24px;
        box-shadow: 0 8px 24px rgba(11, 21, 40, 0.25);
    }
    .brand-title {
        color: #FFFFFF !important;
        font-size: 1.7rem;
        font-weight: 800;
        margin: 0;
    }
    .brand-subtitle {
        color: #C5A059 !important;
        font-size: 0.92rem;
        font-weight: 600;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    .executive-hero {
        background: #0F766E;
        color: #FFFFFF;
        border-left: 6px solid #C2410C;
        border-radius: 8px;
        padding: 24px 28px;
        margin: 0 0 22px;
        box-shadow: none;
    }
    .executive-hero h1, .executive-hero p, .executive-hero span { 
        color: #FFFFFF !important; 
    }
    .executive-hero h1 { margin: 0; font-size: 1.8rem; }
    .executive-hero p { margin: 6px 0 0; opacity: 0.9; }

    .section-note {
        background: #EFF6FF;
        border-left: 4px solid #0284C7;
        border-radius: 6px;
        color: #1E3A8A;
        padding: 11px 16px;
        margin: 8px 0 16px;
        font-size: 0.88rem;
    }
    .section-note strong {
        color: #0F172A;
    }

    .decision-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 9px;
        padding: 16px;
        min-height: 120px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
    }
    .decision-card strong { 
        color: #0F172A; 
        font-size: 0.95rem;
    }
    .decision-card p { 
        color: #475569; 
        font-size: 0.85rem; 
        margin: 6px 0 0; 
    }

    /* Badges de semáforo de ocupación */
    .badge-ok {
        background-color: #DCFCE7;
        color: #166534;
        border: 1px solid #86EFAC;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-warning {
        background-color: #FEF3C7;
        color: #92400E;
        border: 1px solid #FCD34D;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-danger {
        background-color: #FEE2E2;
        color: #991B1B;
        border: 1px solid #FCA5A5;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* Estilo de pestañas visibles */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 2px solid #E2E8F0;
        padding-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background: #FFFFFF;
        border: 1px solid #CBD5E1;
        border-radius: 8px 8px 0 0;
        padding: 10px 18px;
        font-weight: 600;
        color: #334155;
    }
    .stTabs [aria-selected="true"] {
        background: #0B1528 !important;
        color: #FFFFFF !important;
        border-color: #0B1528 !important;
    }

    /* Métricas nativas de Streamlit */
    [data-testid="stMetricValue"] {
        color: #0F172A !important;
        font-weight: 800 !important;
    }
    [data-testid="stMetricLabel"] {
        color: #475569 !important;
        font-weight: 700 !important;
    }

    /* Alertas y avisos */
    .vip-alert-card {
        background: #FFFBEB;
        border-left: 4px solid #C5A059;
        padding: 14px 18px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 12px;
        color: #78350F;
    }
    .vip-alert-card strong {
        color: #92400E;
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
               0 AS prioridad_servicio, f.id_atencion AS id_tipo_atencion,
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
            mapped_attention = df_star["id_tipo_atencion"].map(attention_names)
            df_star["categoria_atencion"] = mapped_attention.fillna(df_star["categoria_atencion"])
            df_star["categoria_atencion"] = df_star["categoria_atencion"].replace(attention_names)
            df_star["id_tipo_atencion"] = mapped_attention.fillna(df_star["categoria_atencion"])
            df_star["categoria_atencion"] = (
                df_star["categoria_atencion"].fillna("Sin especificar").astype(str)
            )
            df_star["id_tipo_atencion"] = df_star["categoria_atencion"]
            df_star["id_fecha"] = pd.to_datetime(df_star["id_fecha"]).dt.date
            df_star["horario_texto"] = df_star["horario_texto"].fillna("Horario no registrado").astype(str)
            df_star["franja_horaria"] = df_star["franja_horaria"].fillna("Horario no registrado").astype(str)
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


# =====================================================================
# BARRA LATERAL (SIDEBAR): CARGA, FILTROS Y ESTADO
# =====================================================================

with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding: 10px 0 16px 0;">
            <div style="font-size: 2.2rem; margin-bottom: 4px;">🏖️ 🍽️</div>
            <div style="font-size: 1.15rem; font-weight: 800; color: #FFFFFF; letter-spacing: -0.01em;">BAHIA PRINCIPE</div>
            <div style="font-size: 0.75rem; font-weight: 600; color: #C5A059; letter-spacing: 0.12em; text-transform: uppercase;">Hotels & Resorts</div>
            <div style="font-size: 0.8rem; color: #94A3B8; margin-top: 4px;">Business Intelligence - A&B</div>
        </div>
    """, unsafe_allow_html=True)

    # 1. GESTIÓN DE FUENTE DE DATOS
    st.markdown("---")
    st.subheader("📂 Carga y actualización de datos")

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
        "📁 Cargar archivos de datos (uno o varios, sin límite de cantidad):",
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

        if st.button("⚡ Procesar y Cargar a BD", use_container_width=True, type="primary"):
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
    <div class="executive-hero">
        <span style="font-size: 0.78rem; font-weight: 700; letter-spacing: 0.12em;">BAHÍA PRÍNCIPE • RESTAURANTES</span>
        <h1>Demanda y experiencia de nuestros huéspedes</h1>
        <p>Un resumen sencillo de las reservas, los días con más actividad y lo que se espera para el futuro.</p>
        <div style="display: flex; gap: 22px; flex-wrap: wrap; margin-top: 16px; font-size: 0.82rem;">
            <span>📅 {f_inicio} → {f_fin}</span>
            <span>🏨 {hoteles_incluidos} hoteles disponibles</span>
            <span>🍽️ {restaurantes_incluidos} restaurantes disponibles</span>
            <span>📊 {len(df_filtrado):,} reservas en esta vista</span>
        </div>
    </div>
""", unsafe_allow_html=True)


# =====================================================================
# PESTAÑAS PRINCIPALES DEL SISTEMA BI
# =====================================================================

tabs = st.tabs([
    "Resumen",
    "Operación y pronóstico",
    "Preguntas y datos"
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

        # Fila 1: Tarjetas de Métricas Ejecutivas
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Total Reservas</div>
                    <div class="metric-value">{total_reservas:,}</div>
                    <div class="metric-sub">{dias_totales} días analizados</div>
                </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Total Comensales (Pax)</div>
                    <div class="metric-value">{total_pax:,}</div>
                    <div class="metric-sub">{round(total_pax/dias_totales, 1):,} pax/día prom.</div>
                </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Adultos vs Niños/Bebés</div>
                    <div class="metric-value">{total_adultos:,}</div>
                    <div class="metric-sub">{total_ninos + total_bebes:,} menores ({round((total_ninos+total_bebes)/total_pax*100, 1) if total_pax else 0}%)</div>
                </div>
            """, unsafe_allow_html=True)
        with c4:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Promedio Pax / Mesa</div>
                    <div class="metric-value">{prom_pax_reserva}</div>
                    <div class="metric-sub">comensales por reserva</div>
                </div>
            """, unsafe_allow_html=True)
        with c5:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Tasa Cross-Dining</div>
                    <div class="metric-value">{pct_cross}%</div>
                    <div class="metric-sub">{total_cross:,} huéspedes de otro hotel</div>
                </div>
            """, unsafe_allow_html=True)
        with c6:
            badge_color = "warning" if ocupacion_global_pct is None else ("ok" if ocupacion_global_pct < 75 else ("warning" if ocupacion_global_pct <= 90 else "danger"))
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Ocupación estimada</div>
                    <div class="metric-value">{f"{ocupacion_global_pct}%" if ocupacion_global_pct is not None else "Sin dato"}</div>
                    <div class="metric-sub"><span class="badge-{badge_color}">{"Aforo pendiente" if ocupacion_global_pct is None else "Estimación orientativa"}</span></div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("""
            <div class="section-note"><strong>Qué buscamos:</strong> detectar dónde se concentra la demanda, anticipar saturaciones y convertir los datos en acciones concretas para Dirección de A&B.</div>
        """, unsafe_allow_html=True)
        d1, d2, d3 = st.columns(3)
        with d1:
            st.markdown("<div class='decision-card'><strong>🔎 Diagnóstico</strong><p>Identifica hoteles, restaurantes y turnos con mayor presión operativa.</p></div>", unsafe_allow_html=True)
        with d2:
            st.markdown("<div class='decision-card'><strong>🧠 Predicción</strong><p>Entrena una red neuronal con la historia diaria para anticipar la demanda.</p></div>", unsafe_allow_html=True)
        with d3:
            st.markdown("<div class='decision-card'><strong>✅ Acción</strong><p>Recomienda ajustes de mesas, personal, turnos y capacidad antes del pico.</p></div>", unsafe_allow_html=True)

        # Fila 2: Semáforo Visual de Ocupación por Restaurante
        st.subheader("🚦 Semáforo de Ocupación por Restaurante de Especialidad")
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
                badge_html = f'<span class="badge-ok">🟢 {pct}% NORMAL</span>'
                b_color = "#10B981"
            elif pct <= 90:
                badge_html = f'<span class="badge-warning">🟡 {pct}% ALTA</span>'
                b_color = "#F59E0B"
            else:
                badge_html = f'<span class="badge-danger">🔴 {pct}% SATURADO</span>'
                b_color = "#EF4444"

            with rest_cols[col_idx]:
                st.markdown(f"""
                    <div style="background: #FFFFFF; border: 1px solid #E2E8F0; border-top: 4px solid {b_color}; border-radius: 8px; padding: 14px; margin-bottom: 14px; box-shadow: 0 4px 12px rgba(15, 23, 42, 0.05);">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 700; color: #0F172A; font-size: 0.95rem;">{row['nombre_restaurante']}</span>
                        </div>
                        <div style="font-size: 0.78rem; color: #0284C7; font-weight: 600; margin-top: 2px;">{row['especialidad']} • {row['hotel_restaurante']}</div>
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
            st.subheader("📈 Actividad por día")
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
                marker_color="rgba(197, 160, 89, 0.65)",
                yaxis="y"
            ))
            fig_trend.add_trace(go.Scatter(
                x=df_tiempo_trend["id_fecha"],
                y=df_tiempo_trend["total_reservas"],
                name="Nº Reservas",
                mode="lines+markers",
                line=dict(color="#38BDF8", width=3),
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
            st.markdown("<div class='section-note'><strong>Cómo leerla:</strong> las barras muestran comensales por día y la línea muestra reservas. Picos simultáneos indican necesidad de reforzar capacidad y personal.</div>", unsafe_allow_html=True)

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
                color_discrete_sequence=["#C5A059", "#38BDF8", "#10B981", "#818CF8", "#F472B6"]
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
            st.markdown("<div class='section-note'><strong>Resultado:</strong> permite localizar qué hoteles concentran el consumo y dónde conviene redistribuir promociones, mesas o recursos.</div>", unsafe_allow_html=True)

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
                    color_discrete_sequence=["#B45309"],
                )
            else:
                fig_restaurants = px.scatter(
                    top_restaurants,
                    x="valor",
                    y="nombre_restaurante",
                    labels={"nombre_restaurante": "Restaurante", "valor": metric_label},
                    color_discrete_sequence=["#B45309"],
                )
            fig_restaurants.update_layout(height=340, margin=dict(l=20, r=15, t=15, b=20), showlegend=False)
            st.plotly_chart(fig_restaurants, use_container_width=True, config=CONFIG_GRAFICAS)


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
        st.subheader("⏰ Mapa de Calor de Ocupación por Turno y Restaurante")
        st.caption("Permite a la Dirección de A&B balancear las cargas horarias y mitigar sobreventas en franjas pico.")
        st.markdown("<div class='section-note'><strong>Qué buscamos:</strong> encontrar la combinación restaurante-turno que concentra la demanda. Los colores intensos requieren redistribución de reservas, mesas o personal.</div>", unsafe_allow_html=True)

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

        st.markdown("---")
        c_cap1, c_cap2 = st.columns(2)

        with c_cap1:
            st.subheader("🔥 Identificación de Horas Pico vs Horas Valle")
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
                color_discrete_sequence=["#0F766E", "#B45309", "#2563EB", "#BE123C", "#4D7C0F", "#7C2D12"],
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
            st.subheader("🪑 Matriz Recomendada de Distribución de Mesas")
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
                color_discrete_sequence=["#C5A059", "#10B981", "#38BDF8", "#F59E0B"]
            )
            fig_mesas.update_layout(
                paper_bgcolor="rgba(255,255,255,0.7)",
                font=dict(color="#0F172A", family="Plus Jakarta Sans, sans-serif"),
                margin=dict(l=20, r=20, t=20, b=20),
                height=300,
                legend=dict(font=dict(color="#0F172A"))
            )
            st.plotly_chart(fig_mesas, use_container_width=True, config=CONFIG_GRAFICAS)

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
        st.subheader("👑 Segmentación de Clientes: VIPs, Fidelidad y Perfil Familiar")
        st.caption("Permite anticipar servicios especiales, atenciones protocolares y requerimientos de montaje infantil.")
        st.markdown("<div class='section-note'><strong>Cómo funciona:</strong> clasifica las reservas por atención, tamaño familiar y necesidades especiales para que el maître prepare el servicio antes de la llegada.</div>", unsafe_allow_html=True)

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
                    "VIP": "#EF4444",
                    "Fidelidad": "#C5A059",
                    "Especial": "#38BDF8",
                    "Standard": "#64748B"
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

        with col_seg2:
            st.markdown("#### 👶 Requerimientos Especiales: Mobiliario Infantil")
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

        st.markdown("---")
        st.subheader("🚨 Consola Operativa del Maître: Clientes VIP y Atenciones Prioritarias")
        st.caption("Listado en vivo de comensales que requieren atención protocolar de Gerencia o montajes con requerimientos especiales:")

        # Filtro de reservas VIP o con periquera o con observaciones
        cols_maitre_req = [
            "id_reserva", "id_fecha", "nombre_restaurante", "horario_texto",
            "categoria_atencion", "id_tipo_atencion", "hotel_hospedaje",
            "num_adultos", "num_ninos", "num_bebes", "total_pax",
            "requiere_periquera", "observaciones_limpias"
        ]
        for col_m in cols_maitre_req:
            if col_m not in df_filtrado.columns:
                df_filtrado[col_m] = "N/A"

        condicion_maitre = (
            (df_filtrado["categoria_atencion"].isin(["VIP", "Fidelidad", "Especial"])) |
            (df_filtrado["requiere_periquera"] == True) |
            (df_filtrado["observaciones_limpias"] != "")
        )
        filtro_maitre = df_filtrado[condicion_maitre][cols_maitre_req].copy()

        # Ordenar por fecha y horario
        sort_cols = [c for c in ["id_fecha", "horario_texto"] if c in filtro_maitre.columns]
        if sort_cols:
            filtro_maitre = filtro_maitre.sort_values(sort_cols)

        st.dataframe(
            filtro_maitre.rename(columns={
                "id_reserva": "ID Reserva",
                "id_fecha": "Fecha",
                "nombre_restaurante": "Restaurante",
                "horario_texto": "Horario",
                "categoria_atencion": "Categoría",
                "id_tipo_atencion": "Tipo de atención",
                "hotel_hospedaje": "Hotel Origen",
                "num_adultos": "Adultos",
                "num_ninos": "Niños",
                "num_bebes": "Bebés",
                "total_pax": "Total Pax",
                "requiere_periquera": "Periquera",
                "observaciones_limpias": "Observaciones / Alergias"
            }),
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
        st.subheader("🏨 Análisis de Flujo Inter-Hotel (Cross-Dining Experience)")
        st.caption("Rastrea el intercambio de comensales entre hoteles: desde el hotel donde se hospeda el huésped hasta el hotel donde cena.")
        st.markdown("<div class='section-note'><strong>Resultado esperado:</strong> medir el valor del cross-dining y localizar restaurantes imán para coordinar transporte, reservas y capacidad entre hoteles.</div>", unsafe_allow_html=True)

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
                line=dict(color="black", width=0.5),
                label=nodos,
                color=["#C5A059"] * len(hoteles_origen_unicos) + ["#38BDF8"] * len(hoteles_destino_unicos)
            ),
            link=dict(
                source=sources,
                target=targets,
                value=values,
                color="rgba(197, 160, 89, 0.3)"
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

        st.markdown("---")
        c_cd1, c_cd2 = st.columns(2)

        with c_cd1:
            st.subheader("🔄 Matriz de Movilidad Inter-Hotel (Comensales Pax)")
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
                color_continuous_scale="Blues",
            )
            fig_cross_heat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#F8FAFC"),
                margin=dict(l=50, r=20, t=20, b=50),
                height=340
            )
            st.plotly_chart(fig_cross_heat, use_container_width=True, config=CONFIG_GRAFICAS)

        with c_cd2:
            st.subheader("🧲 Restaurantes 'Imán' de Comensales Externos")
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
                color_continuous_scale="Viridis",
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


# =====================================================================
# TAB 5: MODELO PREDICTIVO Y SIMULADOR DE DEMANDA
# =====================================================================
with tabs[1]:
    st.divider()
    df_filtrado = filtrar_analisis(df_master, "pronostico", ["hotel", "restaurant", "shift"])
    st.caption(f"{len(df_filtrado):,} reservas incluidas en este análisis.")
    st.subheader("Pronóstico de comensales")
    st.caption("La red neuronal estima la demanda futura con el historial del periodo y los filtros seleccionados.")
    st.markdown("<div class='section-note'><strong>Cómo leerlo:</strong> la línea azul muestra datos registrados y la dorada es una estimación. El error de validación ayuda a entender cuánto puede desviarse; no es una garantía.</div>", unsafe_allow_html=True)

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
                line=dict(color="#38BDF8", width=3)
            ))
            if not df_proj_dia.empty:
                fig_proj.add_trace(go.Scatter(
                    x=df_proj_dia["id_fecha"],
                    y=df_proj_dia["pax_predichos"],
                    mode="lines",
                    name="Pronóstico neuronal",
                    line=dict(color="#C5A059", width=2)
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
            st.markdown("<div class='section-note'><strong>Para planificar:</strong> usa los días estimados como referencia para preparar compras, horarios, mesas y personal. Compara siempre la previsión con las reservas confirmadas.</div>", unsafe_allow_html=True)

            st.markdown("#### 📊 Resumen ejecutivo mensual")
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
            st.subheader("🧮 Simulador Interactivo de Capacidad y Dotación de Personal (A&B)")
            st.caption("Calcula en tiempo real las necesidades de meseros, cocineros y costos operativos en base a la ocupación proyectada:")

        s_col1, s_col2 = st.columns([1, 1.2])
        with s_col1:
            st.markdown("##### ⚙️ Parámetros de Simulación")
            sim_ocupacion = st.slider("Ocupación Hotelera Proyectada del Complejo (%):", min_value=50, max_value=100, value=85, step=5)
            sim_ratio_mesero = st.slider("Ratio Comensales por Mesero / Rango de Sala:", min_value=8, max_value=24, value=14, step=2)
            sim_ratio_cocina = st.slider("Ratio Comensales por Personal de Cocina:", min_value=15, max_value=40, value=25, step=5)
            sim_restaurante = st.selectbox("Seleccionar Restaurante para Simular:", options=["Todos los Restaurantes (Global)"] + sorted(df_master["nombre_restaurante"].unique().tolist()))

        with s_col2:
            st.markdown("##### 📋 Resultados Proyectados de Operación")
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

    st.subheader("Pregúntale a tus datos")
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
    st.subheader("📥 Exportación Multiformato de Reportes Operativos")
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

    if df_filtrado.empty:
        st.warning("No hay datos filtrados para exportar.")
    else:
        st.markdown("#### 🔍 Vista Previa de Datos Filtrados")
        cols_export = [
            "id_reserva", "id_fecha", "hotel_restaurante", "nombre_restaurante",
            "especialidad", "hotel_hospedaje", "franja_horaria", "categoria_atencion",
            "num_adultos", "num_ninos", "num_bebes", "total_pax", "es_cross_dining",
            "requiere_periquera", "observaciones_limpias"
        ]
        df_export = df_filtrado[cols_export].copy()
        st.dataframe(df_export.head(10), use_container_width=True, hide_index=True)

        exp_col1, exp_col2 = st.columns(2)

        # 1. Exportación CSV
        with exp_col1:
            csv_buffer = io.StringIO()
            df_export.to_csv(csv_buffer, index=False, encoding="utf-8")
            st.download_button(
                label="📄 Descargar Dataset Filtrado en CSV",
                data=csv_buffer.getvalue(),
                file_name=f"bahia_principe_reservas_{f_inicio}_{f_fin}.csv",
                mime="text/csv",
                use_container_width=True
            )

        # 2. Exportación Excel Multihija
        with exp_col2:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                # Hoja 1: Hechos Filtrados
                df_export.to_excel(writer, sheet_name="Reservas_Filtradas", index=False)
                # Hoja 2: Resumen por Restaurante
                df_resumen_rest = df_filtrado.groupby(["nombre_restaurante", "hotel_restaurante", "especialidad"]).agg(
                    total_pax=("total_pax", "sum"),
                    total_reservas=("id_reserva", "count"),
                    pax_cross_dining=("es_cross_dining", lambda x: df_filtrado.loc[x[x == True].index, "total_pax"].sum()),
                    periqueras=("requiere_periquera", "sum")
                ).reset_index()
                df_resumen_rest.to_excel(writer, sheet_name="Resumen_Restaurantes", index=False)
                # Hoja 3: Lista Maître (VIPs)
                df_vip = df_filtrado[df_filtrado["categoria_atencion"].isin(["VIP", "Fidelidad", "Especial"])][
                    ["id_reserva", "id_fecha", "horario_texto", "nombre_restaurante", "hotel_hospedaje", "categoria_atencion", "total_pax", "observaciones_limpias"]
                ]
                df_vip.to_excel(writer, sheet_name="Alertas_Maitre", index=False)

            excel_buffer.seek(0)
            st.download_button(
                label="📊 Descargar Reporte Ejecutivo en Excel (.xlsx)",
                data=excel_buffer.getvalue(),
                file_name=f"Reporte_Ejecutivo_Bahia_Principe_{f_inicio}_{f_fin}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                type="primary"
            )

        st.markdown("---")
        st.markdown("#### 📑 Resumen Ejecutivo en Texto para Dirección de A&B")
        texto_resumen = f"""
================================================================================
REPORTE EJECUTIVO DE OPERACIÓN DE RESTAURANTES DE ESPECIALIDAD
HOTELES BAHÍA PRÍNCIPE
Periodo Analizado: {f_inicio} al {f_fin}
================================================================================

1. INDICADORES CLAVE DE VOLUMEN:
   - Total de Reservas Procesadas: {total_reservas:,}
   - Total de Comensales (Pax): {total_pax:,}
   - Desglose: {total_adultos:,} Adultos | {total_ninos:,} Niños | {total_bebes:,} Bebés
   - Promedio de Comensales por Mesa: {prom_pax_reserva} pax/reserva

2. CROSS-DINING INTER-HOTEL:
   - Reservas Cross-Dining: {total_cross:,} ({pct_cross}%)
   - Los huéspedes que cenan en un hotel distinto al de hospedaje representan {round(pct_cross, 1)}% de la operación total.

3. REQUERIMIENTOS ESPECIALES Y SERVICIO VIP:
   - Mobiliario Infantil: Se requieren {reservas_con_periquera:,} periqueras montadas en sala.
   - Huéspedes VIP y Fidelidad registrados: {len(df_filtrado[df_filtrado['categoria_atencion'].isin(['VIP', 'Fidelidad'])]):,} reservas con protocolo especial.

Generado automáticamente por el Sistema de Business Intelligence Bahía Príncipe.
================================================================================
"""
        st.text_area("Copia rápida del resumen ejecutivo:", value=texto_resumen, height=220)


# =====================================================================
# PIE DE PÁGINA CORPORATIVO
# =====================================================================

st.markdown("""
    <div style="text-align: center; margin-top: 40px; padding: 20px 0; border-top: 1px solid rgba(255, 255, 255, 0.1); color: #64748B; font-size: 0.8rem;">
        Bahía Príncipe Hotels & Resorts © 2026 • Suite Analítica de Reservas de Restaurantes de Especialidad • Desarrollado con Streamlit & SQLAlchemy
    </div>
""", unsafe_allow_html=True)
