"""
etl_pipeline.py
===============
Pipeline de Extracción, Transformación y Carga (ETL) y Generador Mock para
el Sistema Analítico de Reservas - Hoteles Bahía Príncipe.

Funcionalidades clave:
1. Poblado y mantenimiento de tablas de dimensiones (5 hoteles, 20 restaurantes, horarios, atenciones, habitaciones).
2. Procesamiento de archivos .xlsx y .csv según columnas transaccionales del hotel.
3. Cálculo de métricas derivadas (total_pax, es_cross_dining, periqueras).
4. Anonimización y sanitización de datos personales y sensibles.
5. Inserción atómica y carga en Esquema en Estrella (SQLite / PostgreSQL).
6. Generador de datos sintéticos hiper-realistas para demostración y pruebas inmediatas.
"""

import os
import re
import random
import hashlib
from datetime import datetime, date, timedelta, timezone
from typing import Union, Tuple, Optional, Dict, Any, List
import io

import pandas as pd
import numpy as np
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from config_db import (
    get_engine,
    get_db_session,
    init_db,
    DimHotel,
    DimRestaurante,
    DimHorario,
    DimTipoAtencion,
    DimTiempo,
    DimHabitacion,
    FactReservasRestaurantes,
)


# =====================================================================
# CATÁLOGOS BASE MAESTROS (5 Hoteles y 20 Restaurantes de Especialidad)
# =====================================================================

HOTELES_CATALOGO = [
    {"id_hotel": 1, "nombre_hotel": "Bahia Principe Grand Tulum", "codigo_origen": "BPG", "categoria": "Grand"},
    {"id_hotel": 4, "nombre_hotel": "Bahia Principe Luxury Akumal", "codigo_origen": "AP3", "categoria": "Luxury"},
    {"id_hotel": 10, "nombre_hotel": "Bahia Principe Grand Coba", "codigo_origen": "TOI", "categoria": "Grand"},
    {"id_hotel": 16, "nombre_hotel": "Bahia Principe Luxury Sian Ka'an", "codigo_origen": "BPS", "categoria": "Luxury (Adults Only)"},
    {"id_hotel": 21, "nombre_hotel": "Bahia Principe Grand Bouganville", "codigo_origen": "BPB", "categoria": "Grand"},
]

# 20 Restaurantes de Especialidad distribuidos entre los 5 hoteles
RESTAURANTES_CATALOGO = [
    # Hotel 1 (BPG - Grand Tulum)
    {"id_restaurante": "DPI", "nombre_restaurante": "Don Pablo Gourmet Cuisine", "especialidad": "Gourmet / Francesa", "id_hotel_ubicacion": 1, "capacidad_maxima_pax": 110},
    {"id_restaurante": "TEQ", "nombre_restaurante": "Tequila Mexican Experience", "especialidad": "Mexicana Auténtica", "id_hotel_ubicacion": 1, "capacidad_maxima_pax": 140},
    {"id_restaurante": "HIN", "nombre_restaurante": "Thali Flavors of India", "especialidad": "India / Especias", "id_hotel_ubicacion": 1, "capacidad_maxima_pax": 95},
    {"id_restaurante": "POR", "nombre_restaurante": "Portofino Trattoria", "especialidad": "Italiana Tradicional", "id_hotel_ubicacion": 1, "capacidad_maxima_pax": 130},

    # Hotel 4 (AP3 - Luxury Akumal)
    {"id_restaurante": "MIK", "nombre_restaurante": "Mikado Teppanyaki & Sushi Bar", "especialidad": "Japonesa / Teppanyaki", "id_hotel_ubicacion": 4, "capacidad_maxima_pax": 120},
    {"id_restaurante": "FRU", "nombre_restaurante": "Frutos del Mar Seafood & Grill", "especialidad": "Mariscos & Pescados", "id_hotel_ubicacion": 4, "capacidad_maxima_pax": 105},
    {"id_restaurante": "DOL", "nombre_restaurante": "Dolce Vita Ristorante", "especialidad": "Italiana Gourmet", "id_hotel_ubicacion": 4, "capacidad_maxima_pax": 115},
    {"id_restaurante": "ARK", "nombre_restaurante": "Arlequín Haute Cuisine", "especialidad": "Cocina de Autor Internacional", "id_hotel_ubicacion": 4, "capacidad_maxima_pax": 90},

    # Hotel 10 (TOI - Grand Coba)
    {"id_restaurante": "ROD", "nombre_restaurante": "Le Gourmet Rodizio Grill", "especialidad": "Cortes & Brasileña", "id_hotel_ubicacion": 10, "capacidad_maxima_pax": 150},
    {"id_restaurante": "MED", "nombre_restaurante": "Mediterráneo Coastal Bistro", "especialidad": "Mediterránea Fusión", "id_hotel_ubicacion": 10, "capacidad_maxima_pax": 130},
    {"id_restaurante": "KUB", "nombre_restaurante": "Ku'uk Mayan Gastronomy", "especialidad": "Fusión Maya Peninsular", "id_hotel_ubicacion": 10, "capacidad_maxima_pax": 110},
    {"id_restaurante": "OAS", "nombre_restaurante": "Oasis Rodizio & Smokehouse", "especialidad": "Carnes & Ahumados", "id_hotel_ubicacion": 10, "capacidad_maxima_pax": 140},

    # Hotel 16 (BPS - Luxury Sian Ka'an)
    {"id_restaurante": "ALB", "nombre_restaurante": "Alux Cenote Experience", "especialidad": "Cocina Sensorial de Vanguardia", "id_hotel_ubicacion": 16, "capacidad_maxima_pax": 85},
    {"id_restaurante": "TAK", "nombre_restaurante": "Takara Pan-Asian Gourmet", "especialidad": "Asiática Pan-Pacífico", "id_hotel_ubicacion": 16, "capacidad_maxima_pax": 95},
    {"id_restaurante": "YUC", "nombre_restaurante": "Cenote Maya Yucateco", "especialidad": "Regional Yucateca Contemporánea", "id_hotel_ubicacion": 16, "capacidad_maxima_pax": 90},
    {"id_restaurante": "GRA", "nombre_restaurante": "Gran Tortuga Rodizio Prime", "especialidad": "Brasileña Prime Cuts", "id_hotel_ubicacion": 16, "capacidad_maxima_pax": 100},

    # Hotel 21 (BPB - Grand Bouganville)
    {"id_restaurante": "CAR", "nombre_restaurante": "El Pescador Caribeño", "especialidad": "Pescados Caribeños & Fusión", "id_hotel_ubicacion": 21, "capacidad_maxima_pax": 125},
    {"id_restaurante": "BEA", "nombre_restaurante": "Bella Italia Oven & Pasta", "especialidad": "Italiana Rustica & Pizzas", "id_hotel_ubicacion": 21, "capacidad_maxima_pax": 135},
    {"id_restaurante": "GOU", "nombre_restaurante": "Bouganville Gourmet Lounge", "especialidad": "Internacional de Autor", "id_hotel_ubicacion": 21, "capacidad_maxima_pax": 105},
    {"id_restaurante": "LOS", "nombre_restaurante": "Los Corales Prime Steakhouse", "especialidad": "Cortes Finos & Parrilla", "id_hotel_ubicacion": 21, "capacidad_maxima_pax": 145},
]

HORARIOS_CATALOGO = [
    {"id_horario": "T1_1730", "turno": 1, "horario_texto": "17:30 - 19:00", "franja_horaria": "Turno 1: Temprano (17:30 - 19:00)"},
    {"id_horario": "T1_1800", "turno": 1, "horario_texto": "18:00 - 19:30", "franja_horaria": "Turno 1: Temprano (18:00 - 19:30)"},
    {"id_horario": "T2_1930", "turno": 2, "horario_texto": "19:30 - 21:00", "franja_horaria": "Turno 2: Pico Central (19:30 - 21:00)"},
    {"id_horario": "T2_2000", "turno": 2, "horario_texto": "20:00 - 21:30", "franja_horaria": "Turno 2: Pico Central (20:00 - 21:30)"},
    {"id_horario": "T3_2130", "turno": 3, "horario_texto": "21:30 - 23:00", "franja_horaria": "Turno 3: Nocturno (21:30 - 23:00)"},
    {"id_horario": "T3_2200", "turno": 3, "horario_texto": "22:00 - 23:30", "franja_horaria": "Turno 3: Nocturno (22:00 - 23:30)"},
]

TIPOS_ATENCION_CATALOGO = [
    {"id_tipo_atencion": "STANDARD", "categoria_atencion": "Standard", "prioridad_servicio": 4},
    {"id_tipo_atencion": "VIP1", "categoria_atencion": "VIP", "prioridad_servicio": 1},
    {"id_tipo_atencion": "VIP2", "categoria_atencion": "VIP", "prioridad_servicio": 1},
    {"id_tipo_atencion": "GEB06", "categoria_atencion": "VIP", "prioridad_servicio": 1},
    {"id_tipo_atencion": "ATE01", "categoria_atencion": "Fidelidad", "prioridad_servicio": 2},
    {"id_tipo_atencion": "CLUB_GOLDEN", "categoria_atencion": "Fidelidad", "prioridad_servicio": 2},
    {"id_tipo_atencion": "HONEYMOON", "categoria_atencion": "Especial", "prioridad_servicio": 3},
    {"id_tipo_atencion": "ANIVERSARIO", "categoria_atencion": "Especial", "prioridad_servicio": 3},
    {"id_tipo_atencion": "CUMPLEANOS", "categoria_atencion": "Especial", "prioridad_servicio": 3},
]

PAISES_ORIGEN = [
    "Estados Unidos", "Canadá", "Reino Unido", "España",
    "México", "Argentina", "Alemania", "Francia", "Colombia", "Chile"
]

CATEGORIAS_CUARTO = [
    "Junior Suite Superior", "Junior Suite Premium",
    "Ocean Front Suite", "Presidential Suite", "Deluxe Family Room"
]

SEGMENTOS_MERCADO = [
    "Directo Web (bahia-principe.com)", "Privilege Club (Timeshare)",
    "OTA (Booking / Expedia)", "Tour Operador Mayorista (TUI)"
]


# =====================================================================
# POBLADO DE DIMENSIONES BASE (SEEDS)
# =====================================================================

def seed_dimensiones(session: Session) -> None:
    """
    Inserta o actualiza los catálogos fijos de dimensiones:
    - Dim_Hotel (5 hoteles)
    - Dim_Restaurante (20 restaurantes)
    - Dim_Horario (6 franjas / 3 turnos)
    - Dim_Tipo_Atencion (VIP, Fidelidad, etc.)
    - Dim_Habitacion (muestra para escalabilidad futura)
    """
    # 1. Hoteles
    for h in HOTELES_CATALOGO:
        existente = session.get(DimHotel, h["id_hotel"])
        if not existente:
            session.add(DimHotel(**h))
        else:
            existente.nombre_hotel = h["nombre_hotel"]
            existente.codigo_origen = h["codigo_origen"]
            existente.categoria = h["categoria"]

    session.flush()

    # 2. Restaurantes
    for r in RESTAURANTES_CATALOGO:
        existente = session.get(DimRestaurante, r["id_restaurante"])
        if not existente:
            session.add(DimRestaurante(**r))
        else:
            existente.nombre_restaurante = r["nombre_restaurante"]
            existente.especialidad = r["especialidad"]
            existente.id_hotel_ubicacion = r["id_hotel_ubicacion"]
            existente.capacidad_maxima_pax = r["capacidad_maxima_pax"]

    session.flush()

    # 3. Horarios
    for hor in HORARIOS_CATALOGO:
        existente = session.get(DimHorario, hor["id_horario"])
        if not existente:
            session.add(DimHorario(**hor))
        else:
            existente.turno = hor["turno"]
            existente.horario_texto = hor["horario_texto"]
            existente.franja_horaria = hor["franja_horaria"]

    session.flush()

    # 4. Tipos de Atención
    for ta in TIPOS_ATENCION_CATALOGO:
        existente = session.get(DimTipoAtencion, ta["id_tipo_atencion"])
        if not existente:
            session.add(DimTipoAtencion(**ta))
        else:
            existente.categoria_atencion = ta["categoria_atencion"]
            existente.prioridad_servicio = ta["prioridad_servicio"]

    session.flush()

    # 5. Habitaciones (Demo escalabilidad)
    habitaciones_count = session.query(DimHabitacion).count()
    if habitaciones_count < 100:
        for hotel in HOTELES_CATALOGO:
            h_id = hotel["id_hotel"]
            for num in range(101, 126):
                hab = DimHabitacion(
                    numero_habitacion=f"{h_id}{num}",
                    id_hotel=h_id,
                    tipo_categoria_cuarto=random.choice(CATEGORIAS_CUARTO),
                    pais_origen_agrupado=random.choice(PAISES_ORIGEN),
                    segmento_mercado=random.choice(SEGMENTOS_MERCADO)
                )
                session.add(hab)
        session.flush()


def seed_dim_tiempo(session: Session, start_date: date, end_date: date) -> None:
    """
    Puebla Dim_Tiempo para el rango de fechas requerido con variables de calendario.
    """
    cur = start_date
    dias_semana_es = {
        0: "Lunes", 1: "Martes", 2: "Miércoles",
        3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"
    }

    while cur <= end_date:
        existente = session.get(DimTiempo, cur)
        if not existente:
            # Temporada: Alta (Dic-Abril, Julio-Agosto), Media (Mayo-Junio), Baja (Sept-Nov)
            mes = cur.month
            if mes in [12, 1, 2, 3, 4, 7, 8]:
                temporada = "Alta"
            elif mes in [5, 6]:
                temporada = "Media"
            else:
                temporada = "Baja"

            es_fds = cur.weekday() in [4, 5, 6] # Viernes, Sábado, Domingo

            dim_t = DimTiempo(
                id_fecha=cur,
                anio=cur.year,
                mes=cur.month,
                dia=cur.day,
                dia_semana=dias_semana_es[cur.weekday()],
                es_fin_de_semana=es_fds,
                temporada=temporada
            )
            session.add(dim_t)
        cur += timedelta(days=1)
    session.flush()


# =====================================================================
# UTILIDADES DE MAPEO, LIMPIEZA Y ANONIMIZACIÓN
# =====================================================================

def mapear_codigo_hotel(valor: Any) -> int:
    """
    Convierte cualquier identificador o código de hotel ('BPG', 'AP3', '1', 1, etc.)
    al ID entero canónico en Dim_Hotel.
    """
    if pd.isna(valor) or valor == "" or valor is None:
        return 1

    v_str = str(valor).strip().upper()
    mapeo = {
        "BPG": 1, "TULUM": 1, "1": 1, 1: 1,
        "AP3": 4, "AKUMAL": 4, "4": 4, 4: 4,
        "TOI": 10, "COBA": 10, "10": 10, 10: 10,
        "BPS": 16, "SIAN KA'AN": 16, "SIAN KAAN": 16, "16": 16, 16: 16,
        "BPB": 21, "BOUGANVILLE": 21, "21": 21, 21: 21
    }
    return mapeo.get(v_str, 1)


def mapear_codigo_restaurante(valor: Any) -> str:
    """
    Normaliza el código de restaurante / servicio a un ID válido de Dim_Restaurante.
    """
    if pd.isna(valor) or valor == "" or valor is None:
        return "DPI"
    
    v_str = str(valor).strip().upper()
    valid_ids = {r["id_restaurante"] for r in RESTAURANTES_CATALOGO}
    if v_str in valid_ids:
        return v_str
    
    # Intentar búsqueda parcial
    for r in RESTAURANTES_CATALOGO:
        if r["id_restaurante"] in v_str or r["nombre_restaurante"].upper().startswith(v_str):
            return r["id_restaurante"]

    return "DPI"


def mapear_horario_y_turno(turno_val: Any, horario_val: Any) -> Tuple[int, str]:
    """
    Determina el turno y el ID de horario normalizado.
    """
    turno = 2
    try:
        t_int = int(turno_val)
        if t_int in [1, 2, 3]:
            turno = t_int
    except (ValueError, TypeError):
        pass

    h_str = str(horario_val).strip()
    
    if "17:" in h_str or "18:" in h_str or turno == 1:
        id_horario = "T1_1730" if "17:" in h_str else "T1_1800"
        turno = 1
    elif "21:" in h_str or "22:" in h_str or turno == 3:
        id_horario = "T3_2130" if "21:" in h_str else "T3_2200"
        turno = 3
    else:
        id_horario = "T2_1930" if "19:" in h_str else "T2_2000"
        turno = 2

    return turno, id_horario


def anonimizar_texto(texto: Any) -> str:
    """
    Sanitiza observaciones personales, nombres o teléfonos para cumplimiento de privacidad y GDPR.
    Conserva únicamente indicaciones operativas relevantes para el servicio de sala / cocina.
    """
    if pd.isna(texto) or not str(texto).strip():
        return ""
    
    s = str(texto).strip()
    # Eliminar números de teléfono o tarjetas (4 o más dígitos consecutivos)
    s = re.sub(r"\b\d{4,}\b", "[DATOS_NUMERICOS_PROTEGIDOS]", s)
    # Reemplazar posibles correos
    s = re.sub(r"[\w\.-]+@[\w\.-]+", "[EMAIL_PROTEGIDO]", s)
    # Limitar longitud para BD
    return s[:250]


def hash_usuario(usuario: Any) -> str:
    """Anonimiza el ID o nombre de usuario emisor de la reserva."""
    if pd.isna(usuario) or not str(usuario).strip():
        return "USR_ANONIMO"
    usr_str = str(usuario).strip()
    h = hashlib.sha256(usr_str.encode("utf-8")).hexdigest()[:8].upper()
    return f"USR_{h}"


# =====================================================================
# TRANSFORMACIÓN PRINCIPAL DEL DATAFRAME
# =====================================================================

def transformar_dataframe_transaccional(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Aplica las reglas de negocio, limpieza y cálculo de métricas al DataFrame crudo:
    1. Estandarización de nombres de columnas.
    2. Parsing de fechas 'Fecha Servicio' a objeto date.
    3. Conversión de campos numéricos (#Adultos, #Niños, #Bebés).
    4. Cálculo de 'total_pax = #Adultos + #Niños + #Bebés'.
    5. Mapeo de hoteles y cálculo de 'es_cross_dining = (Hotel != Hotel Res.)'.
    6. Identificación de requerimiento de periqueras.
    7. Anonimización.
    """
    df = df_raw.copy()

    # Normalizar columnas (limpiar espacios en encabezados)
    df.columns = [str(c).strip() for c in df.columns]

    # Mapeo de nombres alternativos en caso de ligeras variaciones
    rename_dict = {}
    for col in df.columns:
        c_low = col.lower()
        if "adult" in c_low and "#" in col:
            rename_dict[col] = "#Adultos"
        elif "niñ" in c_low and "#" in col:
            rename_dict[col] = "#Niños"
        elif "beb" in c_low and "#" in col:
            rename_dict[col] = "#Bebés"
        elif "fecha" in c_low and "serv" in c_low:
            rename_dict[col] = "Fecha Servicio"
        elif "hotel res" in c_low:
            rename_dict[col] = "Hotel Res."
        elif col in ["Hotel", "hotel"]:
            rename_dict[col] = "Hotel"
        elif "serv" in c_low and "fecha" not in c_low:
            rename_dict[col] = "Servicio"
        elif "aten" in c_low:
            rename_dict[col] = "Atención"
        elif "invitad" in c_low:
            rename_dict[col] = "Nº Habs. Invitadas"
    
    if rename_dict:
        df = df.rename(columns=rename_dict)

    # 1. Parsing de fechas
    if "Fecha Servicio" in df.columns:
        df["Fecha Servicio"] = pd.to_datetime(df["Fecha Servicio"], errors="coerce").dt.date
    else:
        df["Fecha Servicio"] = date.today()

    # Descartar filas sin fecha válida
    df = df.dropna(subset=["Fecha Servicio"])

    # 2. Métricas de Pax
    for col, default_val in [("#Adultos", 2), ("#Niños", 0), ("#Bebés", 0), ("Nº Habs. Invitadas", 0)]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(default_val).astype(int)
        else:
            df[col] = default_val

    # Regla: mínimo 1 adulto por reserva si total pax es 0
    df["#Adultos"] = df["#Adultos"].apply(lambda x: max(1, x) if x <= 0 else x)
    df["total_pax"] = df["#Adultos"] + df["#Niños"] + df["#Bebés"]

    # 3. ID de Reserva
    if "Id" in df.columns:
        df["id_reserva"] = pd.to_numeric(df["Id"], errors="coerce")
        # Rellenar IDs nulos con números autoincrementales
        mask_nan = df["id_reserva"].isna()
        if mask_nan.any():
            start_id = 900000
            df.loc[mask_nan, "id_reserva"] = range(start_id, start_id + mask_nan.sum())
        df["id_reserva"] = df["id_reserva"].astype(int)
    else:
        df["id_reserva"] = range(100001, 100001 + len(df))

    # 4. Mapeo de Restaurantes
    col_rest = "Servicio" if "Servicio" in df.columns else "Restaurante"
    if col_rest in df.columns:
        df["id_restaurante"] = df[col_rest].apply(mapear_codigo_restaurante)
    else:
        df["id_restaurante"] = "DPI"

    # 5. Mapeo de Hoteles y Cross-Dining
    col_hotel_rest = "Hotel" if "Hotel" in df.columns else "Hotel Ubicacion"
    col_hotel_res = "Hotel Res." if "Hotel Res." in df.columns else "Hotel Origen"

    hotel_ubicacion_series = df[col_hotel_rest].apply(mapear_codigo_hotel) if col_hotel_rest in df.columns else 1
    hotel_hospedaje_series = df[col_hotel_res].apply(mapear_codigo_hotel) if col_hotel_res in df.columns else hotel_ubicacion_series

    df["id_hotel_hospedaje"] = hotel_hospedaje_series
    df["id_hotel_restaurante"] = hotel_ubicacion_series

    # Regla de Cross-Dining: True si Hotel != Hotel Res.
    if "Cross" in df.columns:
        # Si la columna viene en el archivo, verificar o complementar
        df["es_cross_dining"] = (df["id_hotel_hospedaje"] != df["id_hotel_restaurante"]) | (df["Cross"].astype(str).str.upper().isin(["TRUE", "1", "SI", "YES"]))
    else:
        df["es_cross_dining"] = df["id_hotel_hospedaje"] != df["id_hotel_restaurante"]

    # 6. Horarios y Turnos
    col_turno = "Turno" if "Turno" in df.columns else None
    col_horario = "Horario" if "Horario" in df.columns else None

    turnos_list = []
    horarios_list = []
    for idx, row in df.iterrows():
        t_val = row.get(col_turno, 2)
        h_val = row.get(col_horario, "20:00")
        t_calc, h_id = mapear_horario_y_turno(t_val, h_val)
        turnos_list.append(t_calc)
        horarios_list.append(h_id)

    df["turno_calc"] = turnos_list
    df["id_horario"] = horarios_list

    # 7. Tipo de Atención
    valid_atenciones = {t["id_tipo_atencion"] for t in TIPOS_ATENCION_CATALOGO}
    if "Atención" in df.columns:
        df["id_tipo_atencion"] = df["Atención"].fillna("STANDARD").astype(str).str.strip().str.upper()
        # Normalizar si no existe
        df["id_tipo_atencion"] = df["id_tipo_atencion"].apply(lambda x: x if x in valid_atenciones else "STANDARD")
    else:
        df["id_tipo_atencion"] = "STANDARD"

    # 8. Requerimiento de Periqueras y Observaciones
    obs_col = "Remarks" if "Remarks" in df.columns else ("Obs." if "Obs." in df.columns else None)
    if obs_col:
        df["observaciones_limpias"] = df[obs_col].apply(anonimizar_texto)
        tiene_palabra_bebe = df[obs_col].astype(str).str.lower().str.contains("periquera|trona|bebe|bebé|cuna|baby", na=False)
        df["requiere_periquera"] = (df["#Bebés"] > 0) | tiene_palabra_bebe
    else:
        df["observaciones_limpias"] = ""
        df["requiere_periquera"] = df["#Bebés"] > 0

    # 9. Asignación opcional a Dim_Habitacion
    df["id_habitacion"] = None

    # Métricas de resumen del ETL
    resumen = {
        "total_registros": len(df),
        "total_pax": int(df["total_pax"].sum()),
        "total_adultos": int(df["#Adultos"].sum()),
        "total_ninos": int(df["#Niños"].sum()),
        "total_bebes": int(df["#Bebés"].sum()),
        "total_cross_dining": int(df["es_cross_dining"].sum()),
        "pct_cross_dining": round(float(df["es_cross_dining"].mean() * 100), 2),
        "fechas_unicas": df["Fecha Servicio"].nunique(),
        "fecha_min": df["Fecha Servicio"].min(),
        "fecha_max": df["Fecha Servicio"].max(),
    }

    return df, resumen


# =====================================================================
# CARGA ATÓMICA EN BASE DE DATOS (STAR SCHEMA)
# =====================================================================

def cargar_en_base_de_datos(df_transformado: pd.DataFrame, session: Session) -> int:
    """
    Inserta o actualiza en lote los registros procesados en Fact_Reservas_Restaurantes.
    Asegura previamente la existencia de fechas en Dim_Tiempo.
    """
    # 1. Asegurar fechas en Dim_Tiempo
    fechas_unicas = df_transformado["Fecha Servicio"].dropna().unique()
    if len(fechas_unicas) > 0:
        f_min = min(fechas_unicas)
        f_max = max(fechas_unicas)
        seed_dim_tiempo(session, f_min, f_max)

    # 2. Cargar en Fact_Reservas_Restaurantes (Carga en lote de alto rendimiento)
    now_utc = datetime.now(timezone.utc)
    
    # Preparar lista de diccionarios
    fact_records = []
    ids_a_cargar = []
    for _, row in df_transformado.iterrows():
        id_res = int(row["id_reserva"])
        ids_a_cargar.append(id_res)
        fact_records.append({
            "id_reserva": id_res,
            "id_fecha": row["Fecha Servicio"],
            "id_restaurante": row["id_restaurante"],
            "id_hotel_hospedaje": int(row["id_hotel_hospedaje"]),
            "id_tipo_atencion": row["id_tipo_atencion"],
            "id_horario": row["id_horario"],
            "id_habitacion": row["id_habitacion"],
            "num_adultos": int(row["#Adultos"]),
            "num_ninos": int(row["#Niños"]),
            "num_bebes": int(row["#Bebés"]),
            "total_pax": int(row["total_pax"]),
            "habs_invitadas": float(row.get("Nº Habs. Invitadas", 0)),
            "es_cross_dining": bool(row["es_cross_dining"]),
            "requiere_periquera": bool(row["requiere_periquera"]),
            "observaciones_limpias": row.get("observaciones_limpias", ""),
            "fecha_carga_etl": now_utc
        })

    # Eliminar duplicados previos en lotes para permitir re-ejecución idempotente
    if ids_a_cargar:
        for i in range(0, len(ids_a_cargar), 500):
            batch = ids_a_cargar[i:i+500]
            session.query(FactReservasRestaurantes).filter(
                FactReservasRestaurantes.id_reserva.in_(batch)
            ).delete(synchronize_session=False)

    # Inserción en lote ultra-rápida
    session.bulk_insert_mappings(FactReservasRestaurantes, fact_records)
    session.flush()
    return len(fact_records)


def ejecutar_etl_desde_archivo(
    archivo: Union[str, io.BytesIO],
    es_csv: Optional[bool] = None,
    reemplazar: bool = False,
) -> Dict[str, Any]:
    """
    Función principal de ejecución del pipeline ETL desde un archivo subido (.xlsx o .csv).
    """
    # 1. Extracción
    if isinstance(archivo, str):
        if archivo.endswith(".csv") or es_csv is True:
            df_raw = pd.read_csv(archivo)
        else:
            df_raw = pd.read_excel(archivo)
    else:
        # BytesIO proveniente de st.file_uploader
        try:
            df_raw = pd.read_excel(archivo)
        except Exception:
            archivo.seek(0)
            df_raw = pd.read_csv(archivo)

    # 2. Transformación
    df_transformado, resumen = transformar_dataframe_transaccional(df_raw)

    if reemplazar:
        limpiar_base_datos()

    # 3. Carga en BD
    with get_db_session() as session:
        seed_dimensiones(session)
        registros_cargados = cargar_en_base_de_datos(df_transformado, session)
        resumen["registros_cargados_bd"] = registros_cargados

    return resumen


def limpiar_base_datos() -> None:
    """Elimina todos los datos cargados y conserva las tablas para una nueva carga."""
    engine = get_engine()
    tables = inspect(engine).get_table_names()
    managed_tables = [
        "Fact_Reservas_Restaurantes", "Dim_Habitacion", "Dim_Tiempo", "Dim_Horario",
        "Dim_Tipo_Atencion", "Dim_Restaurante", "Dim_Hotel", "reservas_servicios",
        "usuarios", "turnos_horarios", "tipos_atencion", "servicios", "hoteles",
    ]
    existing = [table for table in managed_tables if table in tables]
    if existing:
        quoted = ", ".join(f'"{table}"' for table in existing)
        with engine.begin() as connection:
            connection.execute(text(f"TRUNCATE TABLE {quoted} RESTART IDENTITY CASCADE"))


# =====================================================================
# GENERADOR DE DATOS MOCK HIPER-REALISTAS (DEMO INICIAL Y PRUEBAS)
# =====================================================================

def generar_datos_mock(num_registros: int = 1200, dias_atras: int = 30, dias_adelante: int = 14) -> pd.DataFrame:
    """
    Genera un conjunto de datos sintéticos con las columnas exactas del sistema de Bahía Príncipe:
    ['Remarks', 'Actions', 'Cargado', 'Obs.', 'Cross', 'Atención', '#Adultos', '#Niños',
     '#Bebés', 'Nº Habs. Invitadas', 'Fecha Servicio', 'Servicio', 'Turno', 'Horario',
     'Id', 'Usuario', 'Origen', 'Hotel', 'Hotel Res.']
    """
    random.seed(42)
    np.random.seed(42)

    fecha_base = date.today()
    fecha_inicio = fecha_base - timedelta(days=dias_atras)
    fecha_fin = fecha_base + timedelta(days=dias_adelante)
    delta_dias = (fecha_fin - fecha_inicio).days

    rest_ids = [r["id_restaurante"] for r in RESTAURANTES_CATALOGO]
    rest_dict = {r["id_restaurante"]: r for r in RESTAURANTES_CATALOGO}

    hoteles_codigos = ["BPG", "AP3", "TOI", "BPS", "BPB"]
    hotel_id_to_cod = {1: "BPG", 4: "AP3", 10: "TOI", 16: "BPS", 21: "BPB"}

    atenciones_prob = [
        ("STANDARD", 0.62),
        ("VIP1", 0.05),
        ("VIP2", 0.06),
        ("GEB06", 0.04),
        ("ATE01", 0.12),
        ("CLUB_GOLDEN", 0.05),
        ("HONEYMOON", 0.04),
        ("CUMPLEANOS", 0.02)
    ]
    atenciones_nombres = [a[0] for a in atenciones_prob]
    atenciones_weights = [a[1] for a in atenciones_prob]

    remarks_pool = [
        "Mesa cerca de ventana con vista a jardín.",
        "Cliente celíaco - requiere menú sin gluten.",
        "Alergia severa a cacahuates y frutos secos.",
        "Celebración de Aniversario de Bodas #25.",
        "Solicitan periquera para bebé y espacio para carriola.",
        "Cliente VIP Grand Bahia - botella de espumoso de cortesía.",
        "Mesa tranquila alejada del show de teppanyaki.",
        "Familia con 2 niños, favor de atender con prontitud.",
        "Huésped repetidor Bahia Privilege Club.",
        ""
    ]

    records = []
    base_id = 745000

    for i in range(num_registros):
        res_id = base_id + i
        # Fecha aleatoria ponderada
        dia_offset = random.randint(0, delta_dias)
        f_serv = fecha_inicio + timedelta(days=dia_offset)

        # Seleccionar restaurante
        rest_id = random.choice(rest_ids)
        hotel_rest_id = rest_dict[rest_id]["id_hotel_ubicacion"]
        hotel_rest_cod = hotel_id_to_cod[hotel_rest_id]

        # Simular Cross-Dining (30% de probabilidad de que el cliente provenga de otro hotel)
        es_cross = random.random() < 0.30
        if es_cross:
            otros_hoteles = [h for h in hoteles_codigos if h != hotel_rest_cod]
            hotel_res_cod = random.choice(otros_hoteles)
        else:
            hotel_res_cod = hotel_rest_cod

        # Turno y Horario (Turno 2 tiene mayor demanda - Hora Pico)
        turno_rnd = random.choices([1, 2, 3], weights=[0.30, 0.50, 0.20])[0]
        if turno_rnd == 1:
            horario = random.choice(["17:30 - 19:00", "18:00 - 19:30"])
        elif turno_rnd == 2:
            horario = random.choice(["19:30 - 21:00", "20:00 - 21:30"])
        else:
            horario = random.choice(["21:30 - 23:00", "22:00 - 23:30"])

        # Tamaño de Grupo (55% parejas, 35% familias con niños, 10% grupos grandes)
        tipo_grupo = random.choices(["pareja", "familia", "grupo"], weights=[0.55, 0.35, 0.10])[0]
        if tipo_grupo == "pareja":
            adultos = 2
            ninos = 0
            bebes = 1 if random.random() < 0.08 else 0
        elif tipo_grupo == "familia":
            adultos = random.choice([2, 3, 4])
            ninos = random.choice([1, 2, 3])
            bebes = 1 if random.random() < 0.25 else 0
        else:
            adultos = random.randint(5, 8)
            ninos = random.randint(0, 2)
            bebes = 0

        # Atención
        atencion = random.choices(atenciones_nombres, weights=atenciones_weights)[0]

        # Remarks & Periquera
        obs = random.choice(remarks_pool)
        if bebes > 0 and "periquera" not in obs.lower():
            obs = "Requiere periquera para bebé. " + obs

        usuario = f"recep_{random.randint(10, 85)}"
        origen = random.choice(["APP_EXPERIENCE", "TOTEM_LOBBY", "CONCIERGE", "WEB_DIRECT"])

        record = {
            "Id": res_id,
            "Fecha Servicio": f_serv.strftime("%Y-%m-%d"),
            "Servicio": rest_id,
            "Turno": turno_rnd,
            "Horario": horario,
            "Hotel": hotel_rest_cod,
            "Hotel Res.": hotel_res_cod,
            "Cross": "TRUE" if es_cross else "FALSE",
            "Atención": atencion,
            "#Adultos": adultos,
            "#Niños": ninos,
            "#Bebés": bebes,
            "Nº Habs. Invitadas": 0 if random.random() > 0.15 else random.choice([1, 2]),
            "Remarks": obs,
            "Obs.": obs,
            "Actions": "CONFIRMED",
            "Cargado": "SI",
            "Usuario": usuario,
            "Origen": origen
        }
        records.append(record)

    df_mock = pd.DataFrame(records)
    return df_mock


def inicializar_demo_y_cargar_bd(num_registros: int = 1250) -> Dict[str, Any]:
    """
    Puebla la base de datos con un dataset demo completo y genera archivos de muestra
    ('sample_reservas.csv' y 'sample_reservas.xlsx') para facilitar pruebas inmediatas.
    """
    print(f"[*] Generando {num_registros} registros sintéticos para demostración...")
    df_mock = generar_datos_mock(num_registros=num_registros)

    # Guardar copias locales en CSV y Excel para pruebas de carga
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, "sample_reservas.csv")
    xlsx_path = os.path.join(base_dir, "sample_reservas.xlsx")

    df_mock.to_csv(csv_path, index=False, encoding="utf-8")
    df_mock.to_excel(xlsx_path, index=False, engine="openpyxl")
    print(f"[+] Archivos de prueba generados:\n    - {csv_path}\n    - {xlsx_path}")

    # Ejecutar ETL y cargar en BD
    print("[*] Ejecutando ETL y cargando en Esquema en Estrella...")
    df_transformado, resumen = transformar_dataframe_transaccional(df_mock)

    with get_db_session() as session:
        seed_dimensiones(session)
        registros = cargar_en_base_de_datos(df_transformado, session)
        resumen["registros_cargados_bd"] = registros

    print(f"[+] Carga completada exitosamente. Resumen: {resumen}")
    return resumen


if __name__ == "__main__":
    init_db()
    inicializar_demo_y_cargar_bd(1250)
