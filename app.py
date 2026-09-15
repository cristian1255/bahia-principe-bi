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
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score

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
    /* Estilos generales y tipografía */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Encabezados y tarjetas */
    .metric-card {
        background: linear-gradient(135deg, #13223D 0%, #0F1B30 100%);
        border: 1px solid rgba(197, 160, 89, 0.25);
        border-radius: 12px;
        padding: 18px 20px;
        color: #F8FAFC;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(197, 160, 89, 0.6);
    }
    .metric-title {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #94A3B8;
        margin-bottom: 6px;
        font-weight: 600;
    }
    .metric-value {
        font-size: 1.85rem;
        font-weight: 800;
        color: #FFFFFF;
        line-height: 1.1;
    }
    .metric-sub {
        font-size: 0.78rem;
        margin-top: 6px;
        color: #C5A059;
        font-weight: 500;
    }
    
    /* Badges de semáforo de ocupación */
    .badge-ok {
        background-color: rgba(16, 185, 129, 0.18);
        color: #34D399;
        border: 1px solid #10B981;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-warning {
        background-color: rgba(245, 158, 11, 0.18);
        color: #FBBF24;
        border: 1px solid #F59E0B;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
    }
    .badge-danger {
        background-color: rgba(239, 68, 68, 0.18);
        color: #F87171;
        border: 1px solid #EF4444;
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
        FROM Fact_Reservas_Restaurantes f
        INNER JOIN Dim_Tiempo t ON f.id_fecha = t.id_fecha
        INNER JOIN Dim_Restaurante r ON f.id_restaurante = r.id_restaurante
        INNER JOIN Dim_Hotel h_ub ON r.id_hotel_ubicacion = h_ub.id_hotel
        INNER JOIN Dim_Hotel h_hosp ON f.id_hotel_hospedaje = h_hosp.id_hotel
        INNER JOIN Dim_Horario hor ON f.id_horario = hor.id_horario
        INNER JOIN Dim_Tipo_Atencion ta ON f.id_tipo_atencion = ta.id_tipo_atencion
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
    """Verifica si PostgreSQL Local tiene datos; si no, ejecuta el pipeline ETL automáticamente."""
    df = cargar_dataset_completo()
    if df.empty:
        with st.spinner("Cargando reservas reales en PostgreSQL Local vía ETL..."):
            try:
                from etl.etl_pipeline import run_etl
                run_etl()
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error ejecutando ETL inicial: {e}")


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
        if st.button("⚡ Procesar y Cargar a BD", use_container_width=True, type="primary"):
            with st.spinner("Ejecutando pipeline ETL hacia PostgreSQL Local..."):
                try:
                    from etl.etl_pipeline import transformar_datos, cargar_a_postgresql
                    if archivo_subido.name.endswith(".csv"):
                        df_raw = pd.read_csv(archivo_subido)
                    else:
                        df_raw = pd.read_excel(archivo_subido, engine="openpyxl")
                    df_clean = transformar_datos(df_raw)
                    cargar_a_postgresql(df_clean)
                    st.success(f"✅ ¡ETL Exitoso! {len(df_clean)} reservas cargadas en PostgreSQL Local.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error en el ETL: {e}")

    col_btn1, col_btn2 = st.columns(2)
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
    <div class="brand-header">
        <div class="brand-subtitle">Complejo Riviera Maya & Punta Cana • 5 Hoteles • 20 Restaurantes de Especialidad</div>
        <h1 class="brand-title">Sistema Analítico Operativo y Predictivo de Reservas A&B</h1>
        <div style="display: flex; gap: 18px; margin-top: 10px; font-size: 0.82rem; color: #CBD5E1;">
            <div>📅 Periodo: <strong style="color: #C5A059;">{f_inicio}</strong> al <strong style="color: #C5A059;">{f_fin}</strong></div>
            <div>🏨 Hoteles activos: <strong style="color: #38BDF8;">{len(hoteles_sel)}/5</strong></div>
            <div>🍽️ Restaurantes activos: <strong style="color: #38BDF8;">{len(restaurantes_sel)}/20</strong></div>
            <div>📊 Muestra analizada: <strong style="color: #34D399;">{len(df_filtrado):,} reservas</strong></div>
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


# =====================================================================
# TAB 2: ANÁLISIS DE CAPACIDAD Y HORARIOS CRÍTICOS (YIELD MANAGEMENT)
# =====================================================================
with tabs[1]:
    if df_filtrado.empty:
        st.warning("⚠️ No hay datos disponibles para el análisis de capacidad.")
    else:
        st.subheader("⏰ Mapa de Calor de Ocupación por Turno y Restaurante")
        st.caption("Permite a la Dirección de A&B balancear las cargas horarias y mitigar sobreventas en franjas pico.")

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
    st.subheader("🤖 Modelo Predictivo de Demanda de Comensales (Scikit-Learn)")
    st.caption("Entrena un algoritmo de Machine Learning sobre los datos históricos y proyecta la afluencia de comensales.")

    if len(df_master) < 50:
        st.warning("Se requieren al menos 50 reservas en la base de datos para entrenar el modelo predictivo.")
    else:
        # Preparación de datos para entrenamiento de Machine Learning
        # Agrupar por fecha, restaurante y turno
        df_ml_base = df_master.groupby(["id_fecha", "id_restaurante", "turno"]).agg(
            pax_dia_turno=("total_pax", "sum"),
            reservas_dia_turno=("id_reserva", "count"),
            adultos=("num_adultos", "sum"),
            menores=("num_ninos", "sum"),
            anio=("anio", "first"),
            mes=("mes", "first"),
            dia=("dia", "first"),
            dia_semana=("dia_semana", "first"),
            es_fin_de_semana=("es_fin_de_semana", "first"),
            capacidad=("capacidad_maxima_pax", "first")
        ).reset_index()

        if df_ml_base.empty:
            st.warning("No hay datos agregados suficientes para construir el modelo predictivo.")
        else:
            # Feature Engineering: Encoding categórico
            dias_map = {"Lunes": 1, "Martes": 2, "Miércoles": 3, "Jueves": 4, "Viernes": 5, "Sábado": 6, "Domingo": 7}
            df_ml_base["dia_num"] = df_ml_base["dia_semana"].map(dias_map).fillna(1)
            df_ml_base["es_fds_num"] = df_ml_base["es_fin_de_semana"].astype(int)

            # Mapeo numérico de restaurante
            rest_cat = {rid: i for i, rid in enumerate(df_ml_base["id_restaurante"].unique())}
            df_ml_base["rest_encoded"] = df_ml_base["id_restaurante"].map(rest_cat)

            features = ["mes", "dia_num", "es_fds_num", "turno", "capacidad", "rest_encoded"]
            target = "pax_dia_turno"

            X = df_ml_base[features]
            y = df_ml_base[target]

            if X.empty or y.empty or len(X) < 2:
                st.warning("La base histórica tiene demasiados pocos registros para entrenar un modelo fiable.")
            else:
                # Entrenar RandomForestRegressor
                modelo = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=8)
                modelo.fit(X, y)
                y_pred = modelo.predict(X)

                r2 = r2_score(y, y_pred)
                mae = mean_absolute_error(y, y_pred)

                m_col1, m_col2, m_col3 = st.columns(3)
                with m_col1:
                    st.metric("Algoritmo de ML", "Random Forest Regressor")
                with m_col2:
                    st.metric("Precisión del Modelo (R²)", f"{round(r2 * 100, 1)}%")
                with m_col3:
                    st.metric("Error Medio Absoluto (MAE)", f"{round(mae, 1)} pax / turno")

                # Proyección futura a 7 días
                st.markdown("#### 📅 Proyección de Demanda para los Próximos 7 Días")
                fecha_max_hist = df_master["id_fecha"].max()
                fechas_futuras = [fecha_max_hist + timedelta(days=i) for i in range(1, 8)]

                registros_futuros = []
                for f_fut in fechas_futuras:
                    d_num = dias_map.get(f_fut.strftime("%A"), f_fut.weekday() + 1)
                    es_fds = 1 if f_fut.weekday() in [4, 5, 6] else 0
                    for r_id, r_idx in rest_cat.items():
                        cap = df_ml_base[df_ml_base["id_restaurante"] == r_id]["capacidad"].iloc[0]
                        for t in [1, 2, 3]:
                            registros_futuros.append({
                                "id_fecha": f_fut,
                                "id_restaurante": r_id,
                                "mes": f_fut.month,
                                "dia_num": d_num,
                                "es_fds_num": es_fds,
                                "turno": t,
                                "capacidad": cap,
                                "rest_encoded": r_idx
                            })

                df_futuro = pd.DataFrame(registros_futuros)
                if not df_futuro.empty:
                    df_futuro["pax_predicho"] = modelo.predict(df_futuro[features]).round(0).astype(int)

                    # Agrupar proyección por fecha
                    df_proj_dia = df_futuro.groupby("id_fecha")["pax_predicho"].sum().reset_index()

                    fig_proj = go.Figure()
                    # Histórico últimos 14 días
                    df_hist_14 = df_master.groupby("id_fecha")["total_pax"].sum().reset_index().tail(14)
                    fig_proj.add_trace(go.Scatter(
                        x=df_hist_14["id_fecha"],
                        y=df_hist_14["total_pax"],
                        mode="lines+markers",
                        name="Histórico Real",
                        line=dict(color="#38BDF8", width=3)
                    ))
                    fig_proj.add_trace(go.Scatter(
                        x=df_proj_dia["id_fecha"],
                        y=df_proj_dia["pax_predicho"],
                        mode="lines+markers",
                        name="Proyección ML (7 días)",
                        line=dict(color="#C5A059", width=3, dash="dash")
                    ))
                    fig_proj.update_layout(
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        font=dict(color="#F8FAFC"),
                        yaxis=dict(title="Comensales Totales", gridcolor="rgba(255,255,255,0.08)"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                        margin=dict(l=30, r=30, t=30, b=30),
                        height=320
                    )
                    st.plotly_chart(fig_proj, use_container_width=True)

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
