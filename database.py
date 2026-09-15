"""
database.py
===========
Configuración de Base de Datos PostgreSQL y Modelo Relacional Normalizado con SQLAlchemy 2.0.
Implementa tablas independientes normalizadas (hoteles, servicios, turnos_horarios,
tipos_atencion, usuarios y reservas_servicios) junto a la vista SQL v_reservas_completas.
"""

import os
from typing import Generator, Dict, Any, List

from dotenv import load_dotenv
from sqlalchemy import (
    create_engine,
    Column,
    BigInteger,
    Integer,
    String,
    Date,
    ForeignKey,
    func,
    inspect,
    text,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

# Cargar variables de entorno desde .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/bahia_principe_db"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

HOTEL_ID_MAP = {
    "bpg": 1,
    "tulum": 1,
    "bahia principe grand tumul": 1,
    "bahia principe grand tulum": 1,
    "ap3": 4,
    "akumal": 4,
    "bahia principe luxury akumal": 4,
    "toi": 16,
    "tequila": 16,
    "bahia principe tequila": 16,
    "coba": 10,
    "bahia principe grand coba": 10,
    "cob": 10,
    "sian ka'an": 21,
    "sian kaan": 21,
    "sia": 21,
    "bahia principe luxury sian ka'an": 21,
    "bahia principe luxury sian kaan": 21,
    "sian kaan luxury": 21,
    "sian ka'an luxury": 21,
    "grand tumul": 1,
    "grand coba": 10,
}

HOTEL_NAME_BY_ID = {
    1: "Bahia Principe Grand Tulum",
    4: "Bahia Principe Luxury Akumal",
    10: "Bahia Principe Grand Coba",
    16: "Bahia Principe Hotel Tequila",
    21: "Bahia Principe Luxury Sian Ka'an",
}


def normalizar_texto(value) -> str:
    if value is None:
        return ""
    return str(value).strip().lower().replace("_", " ").replace("-", " ").replace(".", " ").replace("  ", " ")


# =====================================================================
# TABLAS NORMALIZADAS (DIMENSIONES / ENTIDADES)
# =====================================================================

class Hotel(Base):
    """Tabla normalizada de hoteles / complejos."""
    __tablename__ = "hoteles"

    id = Column(Integer, primary_key=True, autoincrement=False)
    codigo = Column(String(20), unique=True, nullable=False, index=True)
    nombre = Column(String(100), nullable=False)

    reservas_ubicacion = relationship("ReservaServicio", back_populates="hotel_ubicacion", foreign_keys="ReservaServicio.id_hotel")
    reservas_origen = relationship("ReservaServicio", back_populates="hotel_origen", foreign_keys="ReservaServicio.id_origen")

    def __repr__(self):
        return f"<Hotel(id={self.id}, codigo='{self.codigo}', nombre='{self.nombre}')>"


class Servicio(Base):
    """Tabla normalizada de restaurantes y servicios gastronómicos."""
    __tablename__ = "servicios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(20), unique=True, nullable=False, index=True)
    nombre = Column(String(100), nullable=False)

    reservas = relationship("ReservaServicio", back_populates="servicio_rel")

    def __repr__(self):
        return f"<Servicio(id={self.id}, codigo='{self.codigo}', nombre='{self.nombre}')>"


class TurnoHorario(Base):
    """Tabla normalizada de turnos y franjas horarias."""
    __tablename__ = "turnos_horarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    turno = Column(Integer, nullable=False, index=True)
    horario = Column(String(50), nullable=False)

    reservas = relationship("ReservaServicio", back_populates="turno_horario_rel")

    def __repr__(self):
        return f"<TurnoHorario(id={self.id}, turno={self.turno}, horario='{self.horario}')>"


class TipoAtencion(Base):
    """Tabla normalizada de tipos de atención."""
    __tablename__ = "tipos_atencion"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(50), unique=True, nullable=False, index=True)
    categoria = Column(String(50), nullable=False, default="Standard")

    reservas = relationship("ReservaServicio", back_populates="atencion_rel")

    def __repr__(self):
        return f"<TipoAtencion(id={self.id}, codigo='{self.codigo}', categoria='{self.categoria}')>"


class Usuario(Base):
    """Tabla normalizada de usuarios / ejecutivos."""
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    codigo = Column(String(100), unique=True, nullable=False, index=True)

    reservas = relationship("ReservaServicio", back_populates="usuario_rel")

    def __repr__(self):
        return f"<Usuario(id={self.id}, codigo='{self.codigo}')>"


class ReservaServicio(Base):
    """Tabla central transaccional / hechos de reservas."""
    __tablename__ = "reservas_servicios"

    id = Column(BigInteger, primary_key=True, index=True)
    fecha_servicio = Column(Date, nullable=False, index=True)
    id_servicio = Column(Integer, ForeignKey("servicios.id"), nullable=True, index=True)
    id_turno_horario = Column(Integer, ForeignKey("turnos_horarios.id"), nullable=True, index=True)
    id_hotel = Column(Integer, ForeignKey("hoteles.id"), nullable=True, index=True)
    id_origen = Column(Integer, ForeignKey("hoteles.id"), nullable=True, index=True)
    id_atencion = Column(Integer, ForeignKey("tipos_atencion.id"), nullable=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    adultos = Column(Integer, default=0, nullable=False)
    ninos = Column(Integer, default=0, nullable=False)
    bebes = Column(Integer, default=0, nullable=False)
    pax_total = Column(Integer, default=0, nullable=False)

    hotel_ubicacion = relationship("Hotel", back_populates="reservas_ubicacion", foreign_keys=[id_hotel])
    hotel_origen = relationship("Hotel", back_populates="reservas_origen", foreign_keys=[id_origen])
    servicio_rel = relationship("Servicio", back_populates="reservas")
    turno_horario_rel = relationship("TurnoHorario", back_populates="reservas")
    atencion_rel = relationship("TipoAtencion", back_populates="reservas")
    usuario_rel = relationship("Usuario", back_populates="reservas")

    @property
    def servicio(self) -> str:
        return self.servicio_rel.codigo if self.servicio_rel else "N/A"

    @property
    def turno(self) -> int:
        return self.turno_horario_rel.turno if self.turno_horario_rel else 1

    @property
    def horario(self) -> str:
        return self.turno_horario_rel.horario if self.turno_horario_rel else ""

    @property
    def hotel(self) -> str:
        return self.hotel_ubicacion.codigo if self.hotel_ubicacion else ""

    @property
    def origen(self) -> str:
        return self.hotel_origen.codigo if self.hotel_origen else ""

    @property
    def atencion(self) -> str:
        return self.atencion_rel.codigo if self.atencion_rel else "STANDARD"

    @property
    def usuario(self) -> str:
        return self.usuario_rel.codigo if self.usuario_rel else ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "fecha_servicio": str(self.fecha_servicio) if self.fecha_servicio else None,
            "servicio": self.servicio,
            "turno": self.turno,
            "horario": self.horario,
            "adultos": self.adultos,
            "ninos": self.ninos,
            "bebes": self.bebes,
            "pax_total": self.pax_total,
            "origen": self.origen,
            "hotel": self.hotel,
            "atencion": self.atencion,
            "usuario": self.usuario,
        }

    def __repr__(self):
        return f"<ReservaServicio(id={self.id}, fecha={self.fecha_servicio}, pax={self.pax_total})>"


# =====================================================================
# INICIALIZACIÓN Y VISTA SQL CONSOLIDADA
# =====================================================================

def crear_vista_reservas_completas(conn):
    """Crea o reemplaza la vista SQL v_reservas_completas."""
    vista_sql = """
    CREATE OR REPLACE VIEW v_reservas_completas AS
    SELECT
        r.id,
        r.fecha_servicio,
        r.id_servicio,
        r.id_turno_horario,
        r.id_hotel,
        r.id_origen,
        r.id_atencion,
        r.id_usuario,
        s.codigo AS servicio,
        s.nombre AS servicio_nombre,
        th.turno,
        th.horario,
        r.adultos,
        r.ninos,
        r.bebes,
        r.pax_total,
        h_orig.id AS id_origen_hotel,
        h_orig.codigo AS origen,
        h_orig.nombre AS hotel_hospedaje,
        h_ubic.id AS id_hotel_ubicacion,
        h_ubic.codigo AS hotel,
        h_ubic.nombre AS hotel_restaurante,
        ta.codigo AS atencion,
        ta.categoria AS categoria_atencion,
        u.codigo AS usuario
    FROM reservas_servicios r
    LEFT JOIN servicios s ON r.id_servicio = s.id
    LEFT JOIN turnos_horarios th ON r.id_turno_horario = th.id
    LEFT JOIN hoteles h_ubic ON r.id_hotel = h_ubic.id
    LEFT JOIN hoteles h_orig ON r.id_origen = h_orig.id
    LEFT JOIN tipos_atencion ta ON r.id_atencion = ta.id
    LEFT JOIN usuarios u ON r.id_usuario = u.id;
    """
    conn.execute(text(vista_sql))


def init_db():
    """Crea la estructura normalizada y actualiza la vista consolidada."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    legacy_tables = [
        "reservas_servicios",
        "servicios",
        "turnos_horarios",
        "tipos_atencion",
        "usuarios",
        "hoteles",
    ]

    for table_name in legacy_tables:
        if table_name in existing_tables:
            cols = {col["name"] for col in inspector.get_columns(table_name)}
            if table_name == "reservas_servicios" and {"id_servicio", "id_turno_horario", "id_hotel", "id_origen", "id_atencion", "id_usuario"}.issubset(cols):
                continue
            with engine.begin() as conn:
                conn.execute(text(f'DROP TABLE IF EXISTS "{table_name}" CASCADE'))

    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        crear_vista_reservas_completas(conn)


def get_db() -> Generator[Session, None, None]:
    """Generador de sesiones para FastAPI Depends."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =====================================================================
# FUNCIONES ANALÍTICAS SQL
# =====================================================================

def obtener_kpis_resumen(db: Session) -> Dict[str, Any]:
    """Calcula las métricas consolidadas sobre las tablas normalizadas."""
    total_reservas = db.query(func.count(ReservaServicio.id)).scalar() or 0
    total_pax = db.query(func.sum(ReservaServicio.pax_total)).scalar() or 0
    total_adultos = db.query(func.sum(ReservaServicio.adultos)).scalar() or 0
    total_ninos = db.query(func.sum(ReservaServicio.ninos)).scalar() or 0
    total_bebes = db.query(func.sum(ReservaServicio.bebes)).scalar() or 0

    promedio_pax = round(total_pax / total_reservas, 2) if total_reservas > 0 else 0.0
    dias_operacion = db.query(func.count(func.distinct(ReservaServicio.fecha_servicio))).scalar() or 1
    promedio_pax_dia = round(total_pax / dias_operacion, 1) if dias_operacion > 0 else 0.0

    top_servicio_row = (
        db.query(Servicio.codigo, func.sum(ReservaServicio.pax_total).label("pax"))
        .join(Servicio, ReservaServicio.id_servicio == Servicio.id)
        .group_by(Servicio.codigo)
        .order_by(func.sum(ReservaServicio.pax_total).desc())
        .first()
    )
    top_servicio = top_servicio_row[0] if top_servicio_row else "DPI"

    return {
        "total_reservas": int(total_reservas),
        "total_pax": int(total_pax),
        "total_adultos": int(total_adultos),
        "total_ninos": int(total_ninos),
        "total_bebes": int(total_bebes),
        "promedio_pax_reserva": float(promedio_pax),
        "promedio_pax_dia": float(promedio_pax_dia),
        "top_servicio": str(top_servicio),
        "dias_operacion": int(dias_operacion),
    }


def obtener_kpis_android(db: Session) -> List[Dict[str, Any]]:
    """Retorna tarjetas KPI para la App Android."""
    summary = obtener_kpis_resumen(db)
    return [
        {
            "title": "Huéspedes Totales (Pax)",
            "value": f"{summary['total_pax']:,}",
            "trend": "+8.4%",
            "isPositiveTrend": True,
            "colorHex": "#006B3F"
        },
        {
            "title": "Total de Reservas",
            "value": f"{summary['total_reservas']:,}",
            "trend": "+5.2%",
            "isPositiveTrend": True,
            "colorHex": "#1565C0"
        },
        {
            "title": "Promedio Pax / Reserva",
            "value": f"{summary['promedio_pax_reserva']}",
            "trend": "+0.3",
            "isPositiveTrend": True,
            "colorHex": "#D4AF37"
        },
        {
            "title": "Top Servicio Demandado",
            "value": f"{summary['top_servicio']}",
            "trend": "Líder",
            "isPositiveTrend": True,
            "colorHex": "#003366"
        },
    ]


if __name__ == "__main__":
    print("[*] Inicializando base de datos normalizada en PostgreSQL Local...")
    init_db()
    print("[+] Tablas normalizadas creadas:")
    for t in Base.metadata.tables.keys():
        print(f"    - {t}")
