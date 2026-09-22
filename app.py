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
    DimRestaurante,
    DimHotel,
    DimHorario,
    DimTipoAtencion,
    DimTiempo,
    DimHabitacion,
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
    :root {
        --ink: #12233f;
        --muted: #627089;
        --blue: #1464d2;
        --blue-soft: #eaf2ff;
        --green: #13a678;
        --gold: #e5a52b;
        --line: #dce5f2;
        --surface: #ffffff;
    }

    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #f5f8fd 0%, #eef3fa 100%);
        color: var(--ink);
    }
    [data-testid="stHeader"] { background: rgba(245, 248, 253, 0.92); }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #10254b 0%, #172f5d 100%);
        color: #ffffff;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] label { color: #dfe9f8; }
    h1, h2, h3, h4 { color: var(--ink); letter-spacing: 0; }
    .block-container { max-width: 1500px; padding-top: 1.5rem; }

    .metric-card {
        background: var(--surface);
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 16px 18px;
        color: var(--ink);
        box-shadow: 0 8px 24px rgba(33, 63, 107, 0.08);
        min-height: 112px;
    }
    .metric-title {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--muted);
        margin-bottom: 6px;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 800;
        color: var(--ink);
        line-height: 1.1;
    }
    .metric-sub {
        font-size: 0.78rem;
        margin-top: 6px;
        color: var(--blue);
        font-weight: 500;
    }

    .executive-hero {
        background: linear-gradient(115deg, #102b5b 0%, #176bd1 68%, #16a678 130%);
        color: #ffffff;
        border-radius: 12px;
        padding: 24px 28px;
        margin: 0 0 22px;
        box-shadow: 0 12px 30px rgba(24, 65, 125, 0.2);
    }
    .executive-hero h1, .executive-hero p, .executive-hero span { color: #ffffff; }
    .executive-hero h1 { margin: 0; font-size: 1.8rem; }
    .executive-hero p { margin: 6px 0 0; opacity: 0.86; }
    .section-note {
        background: var(--blue-soft);
        border-left: 4px solid var(--blue);
        border-radius: 6px;
        color: #294568;
        padding: 10px 14px;
        margin: 8px 0 16px;
        font-size: 0.86rem;
    }
    .decision-card {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 9px;
        padding: 14px 16px;
        min-height: 120px;
        box-shadow: 0 6px 18px rgba(33, 63, 107, 0.06);
    }
    .decision-card strong { color: var(--ink); }
    .decision-card p { color: var(--muted); font-size: 0.84rem; margin: 6px 0 0; }
    .report-band {
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 18px 20px;
        margin: 12px 0;
    }
    
    /* Badges de semáforo de ocupación */
    .badge-ok {
        background-color: #e8f8f2;
        color: #087c5c;
        border: 1px solid #43c59e;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-warning {
        background-color: #fff5df;
        color: #986400;
        border: 1px solid #e5a52b;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-danger {
        background-color: #ffebed;
        color: #a82f3d;
        border: 1px solid #e5747e;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* Banner corporativo */
    .brand-header {
        background: linear-gradient(90deg, #0B1528 0%, #172B4D 50%, #0B1528 100%);
        border: 1px solid rgba(197, 160, 89, 0.35);
        border-radius: 14px;
        padding: 22px 28px;
        margin-bottom: 24px;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
    }
    .brand-title {
        color: #FFFFFF;
        font-size: 1.7rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.02em;
    }
    .brand-subtitle {
        color: #C5A059;
        font-size: 0.92rem;
        font-weight: 600;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 10px 18px;
        font-weight: 600;
    }
    
    /* Alertas y avisos */
    .vip-alert-card {
        background: rgba(197, 160, 89, 0.12);
        border-left: 4px solid #C5A059;
        padding: 12px 16px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)


# =====================================================================
# CARGA DE DATOS Y CACHÉ DE CONSULTAS
# =====================================================================

@st.cache_data(ttl=60)
def cargar_dataset_completo() -> pd.DataFrame:
    """
    Carga el dataset directamente desde PostgreSQL Local (tabla reservas_servicios).
    Normaliza y enriquece los datos para alimentar los gráficos interactivos de Plotly.
    """
    from database import engine, init_db as init_pg_db

    # El esquema estrella es la fuente histórica del ETL y conserva la granularidad diaria.
    try:
        engine_star = get_engine()
        query_star = """
        SELECT f.id_reserva, f.id_fecha, t.anio, t.mes, t.dia, t.dia_semana, t.es_fin_de_semana, t.temporada,
               f.id_restaurante, r.nombre_restaurante, r.especialidad, r.capacidad_maxima_pax,
               h_ub.codigo_origen AS cod_hotel_restaurante, h_ub.nombre_hotel AS hotel_restaurante,
               h_hosp.codigo_origen AS cod_hotel_hospedaje, h_hosp.nombre_hotel AS hotel_hospedaje,
               hor.turno, hor.horario_texto, hor.franja_horaria, ta.categoria_atencion, ta.prioridad_servicio,
               f.num_adultos, f.num_ninos, f.num_bebes, f.total_pax, f.habs_invitadas,
               f.es_cross_dining, f.requiere_periquera, f.observaciones_limpias
        FROM "Fact_Reservas_Restaurantes" f
        INNER JOIN "Dim_Tiempo" t ON f.id_fecha = t.id_fecha
        INNER JOIN "Dim_Restaurante" r ON f.id_restaurante = r.id_restaurante
        INNER JOIN "Dim_Hotel" h_ub ON r.id_hotel_ubicacion = h_ub.id_hotel
        INNER JOIN "Dim_Hotel" h_hosp ON f.id_hotel_hospedaje = h_hosp.id_hotel
        INNER JOIN "Dim_Horario" hor ON f.id_horario = hor.id_horario
        INNER JOIN "Dim_Tipo_Atencion" ta ON f.id_tipo_atencion = ta.id_tipo_atencion
        """
        df_star = pd.read_sql(text(query_star), con=engine_star)
        if not df_star.empty:
            df_star["id_fecha"] = pd.to_datetime(df_star["id_fecha"]).dt.date
            return df_star
    except Exception as e:
        st.warning(f"Aviso al consultar el histórico del esquema estrella: {e}")

    init_pg_db()

    try:
        query_pg = "SELECT * FROM v_reservas_completas ORDER BY fecha_servicio DESC, turno ASC"
        df = pd.read_sql(text(query_pg), con=engine)
        if not df.empty:
            df["id_servicio"] = df.get("id_servicio", 1)
            df["id_turno_horario"] = df.get("id_turno_horario", 1)
            df["id_hotel"] = df.get("id_hotel", df.get("id_hotel_ubicacion", 1))
            df["id_origen"] = df.get("id_origen", df.get("id_hotel", 1))
            df["id_atencion"] = df.get("id_atencion", 1)
            df["id_usuario"] = df.get("id_usuario", 1)

            df["id_restaurante"] = df["id_servicio"].fillna(1).astype(int)
            df["id_hotel_hospedaje"] = df["id_origen"].fillna(df["id_hotel"]).fillna(1).astype(int)
            df["id_hotel_ubicacion"] = df["id_hotel"].fillna(1).astype(int)
            df["id_horario"] = df["id_turno_horario"].fillna(1).astype(int)
            df["id_tipo_atencion"] = df["id_atencion"].fillna(1).astype(int)

            df["id_fecha"] = pd.to_datetime(df["fecha_servicio"]).dt.date
            df["id_reserva"] = df["id"]
            df["nombre_restaurante"] = df["servicio_nombre"].fillna(df["servicio"]).fillna("DPI - Gourmet")
            df["especialidad"] = "Gourmet / Fusión Internacional"
            df["capacidad_maxima_pax"] = 120
            df["cod_hotel_restaurante"] = df["hotel"].fillna("BPG")

            hotel_map = {
                "1": "Bahia Principe Grand Tulum",
                "4": "Bahia Principe Luxury Akumal",
                "10": "Bahia Principe Grand Coba",
                "16": "Bahia Principe Luxury Sian Ka'an",
                "21": "Bahia Principe Grand Bouganville",
                "BPG": "Bahia Principe Grand Tulum",
                "AP3": "Bahia Principe Luxury Akumal",
                "TOI": "Bahia Principe Grand Coba",
                "BPS": "Bahia Principe Luxury Sian Ka'an",
                "BPB": "Bahia Principe Grand Bouganville",
            }
            df["hotel_restaurante"] = df["hotel"].fillna("BPG").map(lambda x: hotel_map.get(str(x), f"Hotel {x}"))
            df["hotel_hospedaje"] = df["origen"].fillna("BPG").map(lambda x: hotel_map.get(str(x), f"Origen {x}"))
            df["cod_hotel_hospedaje"] = df["origen"].fillna("BPG")
            df["horario_texto"] = df["horario"].fillna("Horario Estándar")
            df["franja_horaria"] = "Turno " + df["turno"].astype(str) + " (" + df["horario_texto"] + ")"
            df["categoria_atencion"] = df["atencion"].fillna("Standard")
            df["prioridad_servicio"] = df["categoria_atencion"].apply(lambda x: 1 if "VIP" in str(x).upper() else 4)
            df["num_adultos"] = df["adultos"].fillna(0).astype(int)
            df["num_ninos"] = df["ninos"].fillna(0).astype(int)
            df["num_bebes"] = df["bebes"].fillna(0).astype(int)
            df["total_pax"] = df["pax_total"].fillna(0).astype(int)
            df["habs_invitadas"] = 0
            df["es_cross_dining"] = df["origen"].fillna("BPG") != df["hotel"].fillna("BPG")
            df["requiere_periquera"] = df["num_bebes"] > 0
            df["observaciones_limpias"] = df["usuario"].fillna("")

            dt_series = pd.to_datetime(df["id_fecha"])
            df["anio"] = dt_series.dt.year
            df["mes"] = dt_series.dt.month
            df["dia"] = dt_series.dt.day
            dias_map = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
            df["dia_semana"] = dt_series.dt.dayofweek.map(dias_map)
            df["es_fin_de_semana"] = dt_series.dt.dayofweek.isin([5, 6])
            df["temporada"] = "Temporada Alta"
            return df
    except Exception as e:
        st.warning(f"Aviso al consultar PostgreSQL Local: {e}")

    # Fallback al esquema en estrella si existiera
    try:
        engine_star = get_engine()
        query_star = """
        SELECT f.id_reserva, f.id_fecha, t.anio, t.mes, t.dia, t.dia_semana, t.es_fin_de_semana, t.temporada,
               f.id_restaurante, r.nombre_restaurante, r.especialidad, r.capacidad_maxima_pax,
               h_ub.codigo_origen AS cod_hotel_restaurante, h_ub.nombre_hotel AS hotel_restaurante,
               h_hosp.codigo_origen AS cod_hotel_hospedaje, h_hosp.nombre_hotel AS hotel_hospedaje,
               hor.turno, hor.horario_texto, hor.franja_horaria, ta.categoria_atencion, ta.prioridad_servicio,
               f.num_adultos, f.num_ninos, f.num_bebes, f.total_pax, f.habs_invitadas,
               f.es_cross_dining, f.requiere_periquera, f.observaciones_limpias
        FROM "Fact_Reservas_Restaurantes" f
        INNER JOIN "Dim_Tiempo" t ON f.id_fecha = t.id_fecha
        INNER JOIN "Dim_Restaurante" r ON f.id_restaurante = r.id_restaurante
        INNER JOIN "Dim_Hotel" h_ub ON r.id_hotel_ubicacion = h_ub.id_hotel
        INNER JOIN "Dim_Hotel" h_hosp ON f.id_hotel_hospedaje = h_hosp.id_hotel
        INNER JOIN "Dim_Horario" hor ON f.id_horario = hor.id_horario
        INNER JOIN "Dim_Tipo_Atencion" ta ON f.id_tipo_atencion = ta.id_tipo_atencion
        """
        df_star = pd.read_sql(text(query_star), con=engine_star)
        if not df_star.empty:
            df_star["id_fecha"] = pd.to_datetime(df_star["id_fecha"]).dt.date
        return df_star
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=120)
def cargar_demo_habitaciones() -> pd.DataFrame:
    """Carga datos de habitaciones para métricas de ocupación."""
    try:
        from database import engine
        return pd.read_sql(text("SELECT id, hotel, origen, usuario FROM reservas_servicios LIMIT 50"), con=engine)
    except Exception:
        return pd.DataFrame()


def asegurar_base_datos_inicializada():
    """Verifica si hay datos y deja la carga anual bajo control del usuario."""
    df = cargar_dataset_completo()
    if df.empty:
        st.info("Base de datos vacía. Sube el archivo histórico anual desde la barra lateral para comenzar.")


# Asegurar que la BD esté lista
asegurar_base_datos_inicializada()
df_master = cargar_dataset_completo()


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
    st.subheader("📂 Ingesta de Datos (ETL)")
    archivo_subido = st.file_uploader(
        "Cargar archivo transaccional (.xlsx o .csv):",
        type=["xlsx", "csv"],
        help="El archivo debe contener las columnas transaccionales: Id, Fecha Servicio, Servicio, Turno, Horario, Hotel, Hotel Res., #Adultos, #Niños, etc."
    )

    if archivo_subido is not None:
        reemplazar_datos = st.checkbox(
            "Reemplazar todos los datos actuales con este archivo",
            value=True,
            help="Úsalo cuando el archivo contiene el histórico completo de un año.",
        )
        if st.button("⚡ Procesar y Cargar a BD", use_container_width=True, type="primary"):
            with st.spinner("Ejecutando pipeline ETL hacia PostgreSQL Local..."):
                try:
                    from etl_pipeline import ejecutar_etl_desde_archivo
                    resumen = ejecutar_etl_desde_archivo(
                        archivo_subido,
                        es_csv=archivo_subido.name.lower().endswith(".csv"),
                        reemplazar=reemplazar_datos,
                    )
                    st.success(
                        f"✅ Histórico cargado: {resumen['registros_cargados_bd']} reservas, "
                        f"{resumen['fechas_unicas']} días entre {resumen['fecha_min']} y {resumen['fecha_max']}."
                    )
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error en el ETL: {e}")

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

    # Estado de la Base de Datos
    st.markdown("---")
    db_url_str = get_database_url()
    tipo_bd = "PostgreSQL Local" if "localhost" in db_url_str or "127.0.0.1" in db_url_str else ("PostgreSQL Cloud" if "postgresql" in db_url_str else "SQLite Local")
    total_reg = len(df_master)
    st.markdown(f"""
        <div style="background: rgba(15, 27, 48, 0.8); border: 1px solid rgba(197, 160, 89, 0.3); border-radius: 8px; padding: 10px 14px; font-size: 0.8rem;">
            <div style="color: #94A3B8;">Motor de Datos: <span style="color: #38BDF8; font-weight: 600;">{tipo_bd}</span></div>
            <div style="color: #94A3B8;">Reservas en PostgreSQL: <span style="color: #34D399; font-weight: 700;">{total_reg:,}</span></div>
            <div style="color: #94A3B8;">Estado: <span style="color: #34D399; font-weight: 700;">● Online 24/7</span></div>
        </div>
    """, unsafe_allow_html=True)

    # 2. FILTROS GLOBALES INTERACTIVOS
    st.markdown("---")
    st.subheader("🎯 Filtros Globales")

    if not df_master.empty:
        # Filtro de Fechas
        min_date = df_master["id_fecha"].min()
        max_date = df_master["id_fecha"].max()

        fecha_rango = st.date_input(
            "Rango de Fechas:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
            help="Filtra las reservas por fecha de servicio"
        )
        if isinstance(fecha_rango, (tuple, list)) and len(fecha_rango) == 2:
            f_inicio, f_fin = fecha_rango
        else:
            f_inicio, f_fin = min_date, max_date

        # Filtro de Hoteles (Hospedaje o Ubicación del Restaurante)
        todos_hoteles = sorted(df_master["hotel_restaurante"].unique().tolist())
        hoteles_sel = st.multiselect(
            "Hotel (Ubicación Restaurante):",
            options=todos_hoteles,
            default=todos_hoteles,
            help="Filtra por el hotel donde se encuentra físicamente el restaurante"
        )

        # Filtro de Restaurantes
        restaurantes_disponibles = sorted(
            df_master[df_master["hotel_restaurante"].isin(hoteles_sel)]["nombre_restaurante"].unique().tolist()
        )
        restaurantes_sel = st.multiselect(
            "Restaurante de Especialidad:",
            options=restaurantes_disponibles,
            default=restaurantes_disponibles,
            help="Selecciona uno o más de los 20 restaurantes de especialidad"
        )

        # Filtro de Turno
        turnos_disponibles = sorted(df_master["turno"].unique().tolist())
        turnos_sel = st.multiselect(
            "Turno de Servicio:",
            options=turnos_disponibles,
            default=turnos_disponibles,
            format_func=lambda x: f"Turno {x}"
        )

        # Filtro de Tipo de Atención
        atenciones_disponibles = sorted(df_master["categoria_atencion"].unique().tolist())
        atenciones_sel = st.multiselect(
            "Categoría de Atención:",
            options=atenciones_disponibles,
            default=atenciones_disponibles
        )

        # Toggle Cross-Dining
        filtro_cross = st.radio(
            "Modalidad de Comensal:",
            options=["Todos", "Solo Cross-Dining (Inter-Hotel)", "Solo Huéspedes Locales"],
            index=0
        )
    else:
        f_inicio, f_fin = date.today(), date.today()
        hoteles_sel, restaurantes_sel, turnos_sel, atenciones_sel = [], [], [], []
        filtro_cross = "Todos"


# =====================================================================
# APLICACIÓN DE FILTROS AL DATAFRAME
# =====================================================================

df_filtrado = df_master.copy()
if not df_filtrado.empty:
    # 1. Rango de Fechas
    df_filtrado = df_filtrado[
        (df_filtrado["id_fecha"] >= f_inicio) & (df_filtrado["id_fecha"] <= f_fin)
    ]
    # 2. Hoteles y Restaurantes
    if hoteles_sel:
        df_filtrado = df_filtrado[df_filtrado["hotel_restaurante"].isin(hoteles_sel)]
    if restaurantes_sel:
        df_filtrado = df_filtrado[df_filtrado["nombre_restaurante"].isin(restaurantes_sel)]
    # 3. Turnos
    if turnos_sel:
        df_filtrado = df_filtrado[df_filtrado["turno"].isin(turnos_sel)]
    # 4. Atención
    if atenciones_sel:
        df_filtrado = df_filtrado[df_filtrado["categoria_atencion"].isin(atenciones_sel)]
    # 5. Cross-Dining
    if filtro_cross == "Solo Cross-Dining (Inter-Hotel)":
        df_filtrado = df_filtrado[df_filtrado["es_cross_dining"] == True]
    elif filtro_cross == "Solo Huéspedes Locales":
        df_filtrado = df_filtrado[df_filtrado["es_cross_dining"] == False]


# =====================================================================
# ENCABEZADO PRINCIPAL DE LA APLICACIÓN
# =====================================================================

st.markdown(f"""
    <div class="executive-hero">
        <span style="font-size: 0.78rem; font-weight: 700; letter-spacing: 0.12em;">BAHÍA PRÍNCIPE • BUSINESS INTELLIGENCE A&B</span>
        <h1>Centro Ejecutivo de Demanda y Operación</h1>
        <p>Convertimos reservas históricas en decisiones: capacidad, personal, servicio y previsión de demanda.</p>
        <div style="display: flex; gap: 22px; flex-wrap: wrap; margin-top: 16px; font-size: 0.82rem;">
            <span>📅 {f_inicio} → {f_fin}</span>
            <span>🏨 {len(hoteles_sel)}/5 hoteles activos</span>
            <span>🍽️ {len(restaurantes_sel)}/20 restaurantes activos</span>
            <span>📊 {len(df_filtrado):,} reservas analizadas</span>
        </div>
    </div>
""", unsafe_allow_html=True)


# =====================================================================
# PESTAÑAS PRINCIPALES DEL SISTEMA BI
# =====================================================================

tabs = st.tabs([
    "📊 1. Resumen Ejecutivo & KPIs",
    "⏰ 2. Yield Management & Horarios",
    "👑 3. Segmentación VIP & Familias",
    "🏨 4. Flujo Inter-Hotel (Cross-Dining)",
    "🤖 5. Modelo Predictivo & Simulador",
    "🔮 6. Escalabilidad Futura (Habitaciones)",
    "📥 7. Exportación & Reportes"
])


# =====================================================================
# TAB 1: RESUMEN EJECUTIVO Y KPIS EN TIEMPO REAL
# =====================================================================
with tabs[0]:
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

        # Cálculo de ocupación global estimada
        # Capacidad total = suma de capacidades de restaurantes activos * turnos seleccionados * días filtrados
        dias_totales = max(1, (f_fin - f_inicio).days + 1)
        cap_instalada_diaria = df_filtrado.groupby(["id_restaurante", "capacidad_maxima_pax"]).size().reset_index()["capacidad_maxima_pax"].sum()
        # Capacidad estimada considerando turnos
        cap_total_periodo = cap_instalada_diaria * len(turnos_sel) * dias_totales
        ocupacion_global_pct = round((total_pax / cap_total_periodo * 100), 1) if cap_total_periodo > 0 else 0
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
                    <div class="metric-sub">{total_ninos + total_bebes:,} menores ({round((total_ninos+total_bebes)/total_pax*100, 1)}%)</div>
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
            badge_color = "ok" if ocupacion_global_pct < 75 else ("warning" if ocupacion_global_pct <= 90 else "danger")
            st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">Ocupación A&B Est.</div>
                    <div class="metric-value">{ocupacion_global_pct}%</div>
                    <div class="metric-sub"><span class="badge-{badge_color}">Semáforo Global</span></div>
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
        cap_noche = df_rest_agg["capacidad_maxima_pax"] * max(1, len(turnos_sel))
        df_rest_agg["pct_ocupacion"] = ((df_rest_agg["pax_por_noche"] / cap_noche) * 100).round(1)

        # Mostrar tarjetas semafóricas en columnas
        rest_cols = st.columns(4)
        for idx, row in df_rest_agg.sort_values(by="pct_ocupacion", ascending=False).iterrows():
            col_idx = idx % 4
            pct = row["pct_ocupacion"]
            if pct < 75:
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
                    <div style="background: #13223D; border-top: 4px solid {b_color}; border-radius: 8px; padding: 14px; margin-bottom: 14px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 700; color: #FFFFFF; font-size: 0.95rem;">{row['nombre_restaurante']}</span>
                        </div>
                        <div style="font-size: 0.75rem; color: #C5A059; margin-top: 2px;">{row['especialidad']} • {row['hotel_restaurante']}</div>
                        <div style="margin-top: 10px; display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 0.8rem; color: #94A3B8;">Capacidad: {row['capacidad_maxima_pax']} pax</span>
                            {badge_html}
                        </div>
                        <div style="margin-top: 6px; font-size: 0.75rem; color: #CBD5E1;">
                            Total: <strong>{row['total_pax_rest']:,} pax</strong> ({int(row['pax_por_noche'])} pax/noche)
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Fila 3: Gráficos de Tendencias Temporales y Distribución
        g1, g2 = st.columns([1.3, 1])
        with g1:
            st.subheader("📈 Tendencia Diaria de Comensales y Reservas")
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
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#F8FAFC"),
                yaxis=dict(title="Total Comensales (Pax)", gridcolor="rgba(255,255,255,0.08)"),
                yaxis2=dict(title="Número de Reservas", overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                margin=dict(l=40, r=40, t=30, b=30),
                height=380
            )
            st.plotly_chart(fig_trend, use_container_width=True)
            st.markdown("<div class='section-note'><strong>Cómo leerla:</strong> las barras muestran comensales por día y la línea muestra reservas. Picos simultáneos indican necesidad de reforzar capacidad y personal.</div>", unsafe_allow_html=True)

        with g2:
            st.subheader("🥧 Distribución de Demanda por Hotel")
            df_hotel_pie = df_filtrado.groupby("hotel_restaurante")["total_pax"].sum().reset_index()
            fig_pie = px.pie(
                df_hotel_pie,
                names="hotel_restaurante",
                values="total_pax",
                hole=0.45,
                color_discrete_sequence=["#C5A059", "#38BDF8", "#10B981", "#818CF8", "#F472B6"]
            )
            fig_pie.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#F8FAFC"),
                margin=dict(l=20, r=20, t=20, b=20),
                height=380,
                legend=dict(orientation="v", yanchor="middle", y=0.5)
            )
            st.plotly_chart(fig_pie, use_container_width=True)
            st.markdown("<div class='section-note'><strong>Resultado:</strong> permite localizar qué hoteles concentran el consumo y dónde conviene redistribuir promociones, mesas o recursos.</div>", unsafe_allow_html=True)


# =====================================================================
# TAB 2: ANÁLISIS DE CAPACIDAD Y HORARIOS CRÍTICOS (YIELD MANAGEMENT)
# =====================================================================
with tabs[1]:
    if df_filtrado.empty:
        st.warning("⚠️ No hay datos disponibles para el análisis de capacidad.")
    else:
        st.subheader("⏰ Mapa de Calor de Ocupación por Turno y Restaurante")
        st.caption("Permite a la Dirección de A&B balancear las cargas horarias y mitigar sobreventas en franjas pico.")
        st.markdown("<div class='section-note'><strong>Qué buscamos:</strong> encontrar la combinación restaurante-turno que concentra la demanda. Los colores intensos requieren redistribución de reservas, mesas o personal.</div>", unsafe_allow_html=True)

        # Pivot table: Restaurante vs Turno
        pivot_ocup = df_filtrado.pivot_table(
            index="nombre_restaurante",
            columns="franja_horaria",
            values="total_pax",
            aggfunc="sum",
            fill_value=0
        )

        fig_heat = px.imshow(
            pivot_ocup,
            labels=dict(x="Franja Horaria / Turno", y="Restaurante", color="Pax Totales"),
            x=pivot_ocup.columns,
            y=pivot_ocup.index,
            color_continuous_scale="YlOrRd",
            aspect="auto"
        )
        fig_heat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#F8FAFC"),
            margin=dict(l=150, r=30, t=30, b=80),
            height=480
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        st.markdown("---")
        c_cap1, c_cap2 = st.columns(2)

        with c_cap1:
            st.subheader("🔥 Identificación de Horas Pico vs Horas Valle")
            df_turno_agg = df_filtrado.groupby(["turno", "franja_horaria"]).agg(
                pax_total=("total_pax", "sum"),
                reservas=("id_reserva", "count"),
                promedio_pax_mesa=("total_pax", "mean")
            ).reset_index().sort_values("pax_total", ascending=False)

            fig_turnos = px.bar(
                df_turno_agg,
                x="franja_horaria",
                y="pax_total",
                color="turno",
                text="pax_total",
                color_continuous_scale=["#38BDF8", "#C5A059", "#EF4444"],
                labels={"pax_total": "Comensales (Pax)", "franja_horaria": "Franja Horaria"}
            )
            fig_turnos.update_traces(textposition="outside")
            fig_turnos.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#F8FAFC"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                margin=dict(l=30, r=30, t=30, b=30),
                height=350
            )
            st.plotly_chart(fig_turnos, use_container_width=True)

            # Alerta ejecutiva de Yield Management
            if not df_turno_agg.empty:
                hora_pico = df_turno_agg.iloc[0]["franja_horaria"]
                hora_valle = df_turno_agg.iloc[-1]["franja_horaria"]
                st.markdown(f"""
                    <div class="vip-alert-card">
                        <strong>📌 Hallazgo de Yield Management:</strong><br>
                        • <strong>Horario Pico Crítico:</strong> <span style="color: #F87171;">{hora_pico}</span> concentra el {round(df_turno_agg.iloc[0]['pax_total']/total_pax*100, 1)}% de la demanda.<br>
                        • <strong>Horario Valle Disponible:</strong> <span style="color: #34D399;">{hora_valle}</span> presenta {round(df_turno_agg.iloc[-1]['pax_total']/total_pax*100, 1)}% de demanda (oportunidad de redistribución e incentivos a huéspedes).
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
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#F8FAFC"),
                margin=dict(l=20, r=20, t=20, b=20),
                height=300
            )
            st.plotly_chart(fig_mesas, use_container_width=True)

            st.dataframe(
                df_mesas_agg.style.format({"Nº Reservas": "{:,}", "Porcentaje": "{:.1f}%"}),
                use_container_width=True,
                hide_index=True
            )


# =====================================================================
# TAB 3: SEGMENTACIÓN DE CLIENTES Y NIVELES DE ATENCIÓN (VIP & FAMILIAS)
# =====================================================================
with tabs[2]:
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
            st.plotly_chart(fig_atencion, use_container_width=True)

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
        filtro_maitre = df_filtrado[
            (df_filtrado["categoria_atencion"].isin(["VIP", "Fidelidad", "Especial"])) |
            (df_filtrado["requiere_periquera"] == True) |
            (df_filtrado["observaciones_limpias"] != "")
        ][["id_reserva", "id_fecha", "nombre_restaurante", "horario_texto", "categoria_atencion", "id_tipo_atencion", "hotel_hospedaje", "num_adultos", "num_ninos", "num_bebes", "total_pax", "requiere_periquera", "observaciones_limpias"]].copy()

        # Ordenar por fecha y horario
        filtro_maitre = filtro_maitre.sort_values(["id_fecha", "horario_texto"])

        st.dataframe(
            filtro_maitre.rename(columns={
                "id_reserva": "ID Reserva",
                "id_fecha": "Fecha",
                "nombre_restaurante": "Restaurante",
                "horario_texto": "Horario",
                "categoria_atencion": "Categoría",
                "id_tipo_atencion": "Tipo Atenc.",
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
with tabs[3]:
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
        st.plotly_chart(fig_sankey, use_container_width=True)

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
                text_auto=True
            )
            fig_cross_heat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#F8FAFC"),
                margin=dict(l=50, r=20, t=20, b=50),
                height=340
            )
            st.plotly_chart(fig_cross_heat, use_container_width=True)

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
            st.plotly_chart(fig_iman, use_container_width=True)


# =====================================================================
# TAB 5: MODELO PREDICTIVO Y SIMULADOR DE DEMANDA
# =====================================================================
with tabs[4]:
    st.subheader("🧠 Pronóstico Ejecutivo con Red Neuronal")
    st.caption("Entrenamiento temporal por restaurante y turno, con predicción diaria para días, meses y años.")
    st.markdown("<div class='section-note'><strong>Cómo funciona:</strong> la red aprende estacionalidad, tendencia y comportamiento de los últimos 7, 14 y 28 días. Se valida con fechas posteriores al entrenamiento para medir su capacidad real.</div>", unsafe_allow_html=True)

    if len(df_master) < 50:
        st.warning("Se requieren al menos 50 reservas históricas para entrenar el modelo predictivo.")
    else:
        from forecast_model import forecast_future, save_forecast_model, train_neural_forecast

        horizon_label = st.selectbox(
            "Horizonte de planificación",
            options=["7 días", "30 días", "90 días", "6 meses", "1 año", "2 años", "5 años"],
            index=2,
        )
        horizon_days = {"7 días": 7, "30 días": 30, "90 días": 90, "6 meses": 182, "1 año": 365, "2 años": 730, "5 años": 1825}[horizon_label]

        with st.spinner("Entrenando red neuronal y calculando validación temporal..."):
            try:
                resultado_red = train_neural_forecast(df_master)
                save_forecast_model(resultado_red)
                df_futuro = forecast_future(resultado_red, horizon_days)
            except ValueError as error:
                st.error(str(error))
                df_futuro = pd.DataFrame()

        if not df_futuro.empty:
            metric_1, metric_2, metric_3, metric_4 = st.columns(4)
            metric_1.metric("Modelo", "MLP neuronal")
            metric_2.metric("Error MAE validación", f"{resultado_red.metrics['mae']:.1f} pax")
            metric_3.metric("Error RMSE validación", f"{resultado_red.metrics['rmse']:.1f} pax")
            metric_4.metric("Horizonte", horizon_label)

            st.markdown("#### 📈 Demanda diaria prevista")
            df_proj_dia = df_futuro.groupby("fecha", as_index=False)["pax_predichos"].sum()
            df_hist_14 = df_master.groupby("id_fecha", as_index=False)["total_pax"].sum().tail(14)
            fig_proj = go.Figure()
            fig_proj.add_trace(go.Scatter(x=df_hist_14["id_fecha"], y=df_hist_14["total_pax"], mode="lines+markers", name="Histórico real", line=dict(color="#38BDF8", width=3)))
            fig_proj.add_trace(go.Scatter(x=df_proj_dia["fecha"], y=df_proj_dia["pax_predichos"], mode="lines", name="Pronóstico neuronal", line=dict(color="#C5A059", width=2)))
            fig_proj.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#F8FAFC"), yaxis_title="Comensales por día", height=360)
            st.plotly_chart(fig_proj, use_container_width=True)
            st.markdown("<div class='section-note'><strong>Cómo usar el resultado:</strong> selecciona el horizonte de planificación y usa los picos diarios para anticipar compras, horarios, mesas y dotación de sala/cocina.</div>", unsafe_allow_html=True)

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
# TAB 6: ESCALABILIDAD FUTURA (DEMO HABITACIONES Y ORIGEN)
# =====================================================================
with tabs[5]:
    st.subheader("🔮 Demostración de Escalabilidad Futura: Dim_Habitacion & Datos de Origen")
    st.markdown("""
        Esta sección demuestra cómo el **Esquema en Estrella** está preparado arquitectónicamente para integrarse
        con el sistema **PMS hotelero (Opera / Protel)** y el **CRM** de Bahía Príncipe mediante la tabla de dimensión `Dim_Habitacion`.
    """)

    df_hab = cargar_demo_habitaciones()
    if df_hab.empty:
        st.info("Cargando estructura demostrativa de habitaciones...")
    else:
        h1, h2 = st.columns(2)
        with h1:
            st.markdown("#### 🌍 Comensales por País de Procedencia Geográfica")
            df_pais = df_hab["pais_origen_agrupado"].value_counts().reset_index()
            df_pais.columns = ["País de Origen", "Huéspedes Activos"]

            fig_pais = px.bar(
                df_pais,
                x="Huéspedes Activos",
                y="País de Origen",
                orientation="h",
                color="Huéspedes Activos",
                color_continuous_scale="Peach",
            )
            fig_pais.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#F8FAFC"),
                margin=dict(l=30, r=30, t=20, b=30),
                height=320,
                yaxis=dict(autorange="reversed")
            )
            st.plotly_chart(fig_pais, use_container_width=True)

        with h2:
            st.markdown("#### 🛌 Distribución por Categoría de Habitación")
            df_cat = df_hab["tipo_categoria_cuarto"].value_counts().reset_index()
            df_cat.columns = ["Categoría de Habitación", "Total"]

            fig_cat = px.pie(
                df_cat,
                names="Categoría de Habitación",
                values="Total",
                hole=0.4,
                color_discrete_sequence=["#C5A059", "#38BDF8", "#10B981", "#818CF8", "#F472B6"]
            )
            fig_cat.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#F8FAFC"),
                margin=dict(l=20, r=20, t=20, b=20),
                height=320
            )
            st.plotly_chart(fig_cat, use_container_width=True)

        st.markdown("""
            <div class="vip-alert-card">
                <strong>💡 Arquitectura Lista para Producción:</strong><br>
                Cuando el departamento de IT habilite la sincronización de la base de datos de reservas de habitaciones con el PMS,
                el campo <code>id_habitacion</code> en <code>Fact_Reservas_Restaurantes</code> se vinculará directamente a <code>Dim_Habitacion.id_habitacion</code>,
                permitiendo correlacionar el <strong>gasto promedio por huésped</strong>, <strong>preferencias gastronómicas por nacionalidad</strong>
                y <strong>retención de membresías Privilege Club</strong> sin necesidad de reestructurar la base de datos.
            </div>
        """, unsafe_allow_html=True)


# =====================================================================
# TAB 7: EXPORTACIÓN Y REPORTES
# =====================================================================
with tabs[6]:
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
