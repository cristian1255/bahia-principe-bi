"""
backend/database.py
====================
Adaptador de base de datos para el Backend FastAPI.
Reutiliza el Esquema en Estrella del sistema BI existente (config_db.py)
y expone funciones de consulta optimizadas para los endpoints REST de la API.
Soporte dual: SQLite local (desarrollo) y PostgreSQL Cloud (producción en Render).
"""

import os
import sys
from datetime import date, timedelta
from typing import Optional, Dict, Any, List

# Añadir el directorio raíz del proyecto al path para importar config_db.py
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

from sqlalchemy import create_engine, text, func, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

# Importar modelos del Star Schema ya definido en config_db.py
from config_db import (
    Base,
    DimHotel,
    DimRestaurante,
    DimHorario,
    DimTipoAtencion,
    DimTiempo,
    DimHabitacion,
    FactReservasRestaurantes,
    get_database_url,
    init_db,
)


# =====================================================================
# CONEXIÓN A LA BASE DE DATOS
# =====================================================================

def get_engine_backend():
    """Motor de base de datos para el backend FastAPI."""
    db_url = get_database_url()
    if db_url.startswith("sqlite"):
        return create_engine(db_url, connect_args={"check_same_thread": False}, pool_pre_ping=True)
    return create_engine(db_url, pool_size=20, max_overflow=10, pool_pre_ping=True)


_engine = get_engine_backend()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

# Asegurar que las tablas existan
init_db(_engine)


@contextmanager
def get_db():
    """Generador de sesiones para dependencias FastAPI."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session():
    """Para usar con Depends() en FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =====================================================================
# CATÁLOGOS BASE (5 HOTELES Y 20 RESTAURANTES)
# =====================================================================

HOTELES_INFO = {
    1:  {"codigo": "BPG", "nombre": "Grand Tulum",        "categoria": "Grand"},
    4:  {"codigo": "AP3", "nombre": "Luxury Akumal",      "categoria": "Luxury"},
    10: {"codigo": "TOI", "nombre": "Grand Coba",         "categoria": "Grand"},
    16: {"codigo": "BPS", "nombre": "Luxury Sian Ka'an", "categoria": "Luxury"},
    21: {"codigo": "BPB", "nombre": "Grand Bouganville",  "categoria": "Grand"},
}

CODIGO_A_ID = {v["codigo"]: k for k, v in HOTELES_INFO.items()}


# =====================================================================
# FUNCIONES ANALÍTICAS (KPIs Y GRÁFICAS)
# =====================================================================

def obtener_kpis_globales(
    db: Session,
    hotel_codigo: Optional[str] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Retorna las métricas clave de operación A&B del complejo o de un hotel específico.
    """
    if fecha_inicio is None:
        fecha_inicio = date.today() - timedelta(days=30)
    if fecha_fin is None:
        fecha_fin = date.today() + timedelta(days=14)

    query = db.query(FactReservasRestaurantes).filter(
        FactReservasRestaurantes.id_fecha >= fecha_inicio,
        FactReservasRestaurantes.id_fecha <= fecha_fin,
    )

    # Filtro por hotel si se especifica
    if hotel_codigo and hotel_codigo != "ALL":
        hotel_id = CODIGO_A_ID.get(hotel_codigo.upper())
        if hotel_id:
            # Filtrar por restaurantes ubicados en ese hotel
            restaurant_ids = [
                r.id_restaurante
                for r in db.query(DimRestaurante)
                .filter(DimRestaurante.id_hotel_ubicacion == hotel_id)
                .all()
            ]
            query = query.filter(FactReservasRestaurantes.id_restaurante.in_(restaurant_ids))

    resultados = query.all()

    if not resultados:
        return {
            "total_reservas": 0,
            "total_pax": 0,
            "total_adultos": 0,
            "total_ninos": 0,
            "total_bebes": 0,
            "promedio_pax_por_reserva": 0.0,
            "total_cross_dining": 0,
            "pct_cross_dining": 0.0,
            "reservas_vip": 0,
            "reservas_requieren_periquera": 0,
            "fecha_inicio": str(fecha_inicio),
            "fecha_fin": str(fecha_fin),
            "hotel_filtro": hotel_codigo or "ALL",
        }

    total_reservas = len(resultados)
    total_pax = sum(r.total_pax for r in resultados)
    total_adultos = sum(r.num_adultos for r in resultados)
    total_ninos = sum(r.num_ninos for r in resultados)
    total_bebes = sum(r.num_bebes for r in resultados)
    total_cross = sum(1 for r in resultados if r.es_cross_dining)
    periqueras = sum(1 for r in resultados if r.requiere_periquera)

    # KPIs de tipos de atención VIP
    ids_reservas = [r.id_reserva for r in resultados]
    reservas_vip = (
        db.query(func.count(FactReservasRestaurantes.id_reserva))
        .join(DimTipoAtencion)
        .filter(
            FactReservasRestaurantes.id_reserva.in_(ids_reservas),
            DimTipoAtencion.categoria_atencion.in_(["VIP", "Fidelidad"]),
        )
        .scalar()
        or 0
    )

    return {
        "total_reservas": total_reservas,
        "total_pax": total_pax,
        "total_adultos": total_adultos,
        "total_ninos": total_ninos,
        "total_bebes": total_bebes,
        "promedio_pax_por_reserva": round(total_pax / total_reservas, 2) if total_reservas > 0 else 0.0,
        "total_cross_dining": total_cross,
        "pct_cross_dining": round((total_cross / total_reservas) * 100, 1) if total_reservas > 0 else 0.0,
        "reservas_vip": int(reservas_vip),
        "reservas_requieren_periquera": periqueras,
        "fecha_inicio": str(fecha_inicio),
        "fecha_fin": str(fecha_fin),
        "hotel_filtro": hotel_codigo or "ALL",
    }


def obtener_chart_tendencia(
    db: Session,
    hotel_codigo: Optional[str] = None,
    dias_atras: int = 14,
) -> Dict[str, Any]:
    """Retorna datos de la tendencia diaria de comensales para la gráfica de línea/barra."""
    fecha_inicio = date.today() - timedelta(days=dias_atras)

    query = (
        db.query(
            FactReservasRestaurantes.id_fecha,
            func.sum(FactReservasRestaurantes.total_pax).label("pax"),
            func.count(FactReservasRestaurantes.id_reserva).label("reservas"),
        )
        .filter(FactReservasRestaurantes.id_fecha >= fecha_inicio)
        .group_by(FactReservasRestaurantes.id_fecha)
        .order_by(FactReservasRestaurantes.id_fecha)
    )

    if hotel_codigo and hotel_codigo != "ALL":
        hotel_id = CODIGO_A_ID.get(hotel_codigo.upper())
        if hotel_id:
            restaurant_ids = [
                r.id_restaurante
                for r in db.query(DimRestaurante)
                .filter(DimRestaurante.id_hotel_ubicacion == hotel_id)
                .all()
            ]
            query = query.filter(FactReservasRestaurantes.id_restaurante.in_(restaurant_ids))

    rows = query.all()
    return {
        "tipo": "tendencia",
        "labels": [str(r.id_fecha) for r in rows],
        "pax": [int(r.pax) for r in rows],
        "reservas": [int(r.reservas) for r in rows],
    }


def obtener_chart_cross_dining(db: Session) -> Dict[str, Any]:
    """Retorna la matriz de flujo inter-hotel para el diagrama de Cross-Dining."""
    fecha_inicio = date.today() - timedelta(days=30)

    rows = (
        db.query(
            DimHotel.codigo_origen.label("hotel_hospedaje_cod"),
            func.sum(FactReservasRestaurantes.total_pax).label("pax"),
        )
        .join(FactReservasRestaurantes, FactReservasRestaurantes.id_hotel_hospedaje == DimHotel.id_hotel)
        .join(DimRestaurante, DimRestaurante.id_restaurante == FactReservasRestaurantes.id_restaurante)
        .filter(
            FactReservasRestaurantes.id_fecha >= fecha_inicio,
            FactReservasRestaurantes.es_cross_dining == True,
        )
        .group_by(DimHotel.codigo_origen)
        .all()
    )

    return {
        "tipo": "cross_dining",
        "hoteles": [r.hotel_hospedaje_cod for r in rows],
        "pax_cross": [int(r.pax) for r in rows],
    }


def obtener_chart_ocupacion(db: Session, hotel_codigo: Optional[str] = None) -> Dict[str, Any]:
    """Retorna el nivel de ocupación estimado por restaurante (últimos 7 días)."""
    fecha_inicio = date.today() - timedelta(days=7)

    query = (
        db.query(
            DimRestaurante.nombre_restaurante,
            DimRestaurante.capacidad_maxima_pax,
            func.sum(FactReservasRestaurantes.total_pax).label("pax_total"),
        )
        .join(FactReservasRestaurantes)
        .filter(FactReservasRestaurantes.id_fecha >= fecha_inicio)
        .group_by(DimRestaurante.nombre_restaurante, DimRestaurante.capacidad_maxima_pax)
        .order_by(func.sum(FactReservasRestaurantes.total_pax).desc())
    )

    if hotel_codigo and hotel_codigo != "ALL":
        hotel_id = CODIGO_A_ID.get(hotel_codigo.upper())
        if hotel_id:
            query = query.filter(DimRestaurante.id_hotel_ubicacion == hotel_id)

    rows = query.limit(10).all()
    
    resultado = []
    for r in rows:
        dias = 7
        cap_periodo = r.capacidad_maxima_pax * 3 * dias  # 3 turnos por día
        pct = round((r.pax_total / cap_periodo * 100), 1) if cap_periodo > 0 else 0
        pct = min(100.0, pct)
        resultado.append({
            "restaurante": r.nombre_restaurante,
            "pax_total": int(r.pax_total),
            "capacidad": r.capacidad_maxima_pax,
            "pct_ocupacion": pct,
            "semaforo": "verde" if pct < 75 else ("amarillo" if pct <= 90 else "rojo"),
        })

    return {"tipo": "ocupacion", "restaurantes": resultado}


def obtener_chart_atencion(db: Session, hotel_codigo: Optional[str] = None) -> Dict[str, Any]:
    """Retorna distribución de tipos de atención para gráfico de dona."""
    fecha_inicio = date.today() - timedelta(days=30)

    query = (
        db.query(
            DimTipoAtencion.categoria_atencion,
            func.count(FactReservasRestaurantes.id_reserva).label("total"),
        )
        .join(FactReservasRestaurantes)
        .filter(FactReservasRestaurantes.id_fecha >= fecha_inicio)
        .group_by(DimTipoAtencion.categoria_atencion)
    )
    rows = query.all()

    return {
        "tipo": "atencion",
        "categorias": [r.categoria_atencion for r in rows],
        "totales": [int(r.total) for r in rows],
    }


def obtener_reservas_paginadas(
    db: Session,
    hotel_codigo: Optional[str] = None,
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    categoria_atencion: Optional[str] = None,
    pagina: int = 1,
    por_pagina: int = 20,
) -> Dict[str, Any]:
    """Retorna lista paginada de reservas para la pantalla de gestión."""
    if fecha_inicio is None:
        fecha_inicio = date.today()
    if fecha_fin is None:
        fecha_fin = date.today() + timedelta(days=7)

    query = (
        db.query(
            FactReservasRestaurantes,
            DimRestaurante.nombre_restaurante,
            DimHotel.nombre_hotel.label("hotel_hospedaje_nombre"),
            DimHorario.horario_texto,
            DimHorario.turno,
            DimTipoAtencion.categoria_atencion,
        )
        .join(DimRestaurante)
        .join(DimHotel, DimHotel.id_hotel == FactReservasRestaurantes.id_hotel_hospedaje)
        .join(DimHorario)
        .join(DimTipoAtencion)
        .filter(
            FactReservasRestaurantes.id_fecha >= fecha_inicio,
            FactReservasRestaurantes.id_fecha <= fecha_fin,
        )
        .order_by(FactReservasRestaurantes.id_fecha, DimHorario.turno)
    )

    if hotel_codigo and hotel_codigo != "ALL":
        hotel_id = CODIGO_A_ID.get(hotel_codigo.upper())
        if hotel_id:
            restaurant_ids = [
                r.id_restaurante
                for r in db.query(DimRestaurante)
                .filter(DimRestaurante.id_hotel_ubicacion == hotel_id)
                .all()
            ]
            query = query.filter(FactReservasRestaurantes.id_restaurante.in_(restaurant_ids))

    if categoria_atencion:
        query = query.filter(DimTipoAtencion.categoria_atencion == categoria_atencion)

    total = query.count()
    registros = query.offset((pagina - 1) * por_pagina).limit(por_pagina).all()

    return {
        "total": total,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total_paginas": (total + por_pagina - 1) // por_pagina,
        "reservas": [
            {
                "id_reserva": r.FactReservasRestaurantes.id_reserva,
                "fecha": str(r.FactReservasRestaurantes.id_fecha),
                "restaurante": r.nombre_restaurante,
                "hotel_hospedaje": r.hotel_hospedaje_nombre,
                "horario": r.horario_texto,
                "turno": r.turno,
                "categoria_atencion": r.categoria_atencion,
                "num_adultos": r.FactReservasRestaurantes.num_adultos,
                "num_ninos": r.FactReservasRestaurantes.num_ninos,
                "num_bebes": r.FactReservasRestaurantes.num_bebes,
                "total_pax": r.FactReservasRestaurantes.total_pax,
                "es_cross_dining": r.FactReservasRestaurantes.es_cross_dining,
                "requiere_periquera": r.FactReservasRestaurantes.requiere_periquera,
                "observaciones": r.FactReservasRestaurantes.observaciones_limpias or "",
            }
            for r in registros
        ],
    }


def actualizar_reserva(db: Session, id_reserva: int, datos: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Actualiza campos editables de una reserva desde la app móvil."""
    reserva = db.get(FactReservasRestaurantes, id_reserva)
    if not reserva:
        return None

    campos_editables = ["num_adultos", "num_ninos", "num_bebes", "id_horario", "id_tipo_atencion", "observaciones_limpias"]
    for campo in campos_editables:
        if campo in datos:
            setattr(reserva, campo, datos[campo])

    # Recalcular total_pax y periquera
    reserva.total_pax = reserva.num_adultos + reserva.num_ninos + reserva.num_bebes
    reserva.requiere_periquera = reserva.num_bebes > 0

    db.flush()
    return {"id_reserva": id_reserva, "actualizado": True, "total_pax": reserva.total_pax}


def obtener_contexto_ia(db: Session, hotel_codigo: Optional[str] = None) -> str:
    """
    Genera un resumen textual de las métricas actuales para inyectar como contexto
    al Agente de IA, permitiendo que responda con datos reales.
    """
    kpis = obtener_kpis_globales(db, hotel_codigo=hotel_codigo)
    ocup = obtener_chart_ocupacion(db, hotel_codigo=hotel_codigo)
    cross = obtener_chart_cross_dining(db)

    hotel_desc = hotel_codigo if hotel_codigo and hotel_codigo != "ALL" else "todo el Complejo Bahía Príncipe"

    contexto = f"""
Eres el Asistente Analítico de Bahía Príncipe Hotels & Resorts. 
Aquí están los datos actuales de la operación de A&B para {hotel_desc}:

📊 KPIs ACTUALES (últimos 30 días al {date.today()}):
- Total de Reservas: {kpis['total_reservas']:,}
- Total de Comensales (Pax): {kpis['total_pax']:,}
- Promedio Pax/Mesa: {kpis['promedio_pax_por_reserva']}
- Tasa Cross-Dining: {kpis['pct_cross_dining']}% ({kpis['total_cross_dining']:,} reservas inter-hotel)
- Reservas VIP/Fidelidad: {kpis['reservas_vip']:,}
- Periqueras/Sillas altas requeridas: {kpis['reservas_requieren_periquera']:,}

🔆 ESTADO DE OCUPACIÓN POR RESTAURANTE (últimos 7 días):
"""
    for r in ocup.get("restaurantes", [])[:5]:
        emoji = "🟢" if r["semaforo"] == "verde" else ("🟡" if r["semaforo"] == "amarillo" else "🔴")
        contexto += f"  {emoji} {r['restaurante']}: {r['pct_ocupacion']}% ocupación ({r['pax_total']:,} pax)\n"

    contexto += "\nResponde SIEMPRE en español. Sé conciso, ejecutivo y orientado a la toma de decisiones operativas de la gerencia de A&B.\n"
    return contexto.strip()
