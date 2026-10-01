"""
config_db.py
==============
Configuración de Base de Datos y Modelo ORM con SQLAlchemy 2.0.

Esquema en Estrella (Star Schema) optimizado para Inteligencia de Negocios (BI):
- dim_hotel: Catálogo oficial de hoteles del complejo (Tulum=1, Akumal=4, Coba=10, Tequila=16, Sian Ka'an=21)
- dim_restaurante: Catálogo de restaurantes de especialidad
- dim_horario: Turnos y franjas horarias
- dim_tipo_atencion: Tipos de atención / VIP / Standard
- dim_tiempo: Calendario para análisis temporal y estacionalidad
- fact_reservas_restaurantes: Tabla de hechos consolidada con las columnas reales del Excel/CSV

Sin datos sintéticos ni información inventada.
"""

import os
from datetime import datetime, timezone
from typing import Optional, Generator
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from sqlalchemy import create_engine, Column, Integer, String, Boolean, Date, Text, BigInteger, ForeignKey, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

Base = declarative_base()


# =====================================================================
# MODELOS DE ESQUEMA EN ESTRELLA (Dimensiones y Hechos)
# =====================================================================

class DimHotel(Base):
    __tablename__ = "dim_hotel"
    id_hotel = Column(Integer, primary_key=True, autoincrement=True)
    codigo_hotel = Column(String(50), nullable=False, unique=True)
    hotel_res = Column(String(50), nullable=True)


class DimServicio(Base):
    __tablename__ = "dim_servicio"
    id_servicio = Column(Integer, primary_key=True, autoincrement=True)
    codigo_servicio = Column(String(50), nullable=False, unique=True)
    restaurante = Column(String(100), nullable=True)


class DimAtencion(Base):
    __tablename__ = "dim_atencion"
    id_atencion = Column(Integer, primary_key=True, autoincrement=True)
    atencion = Column(String(100), nullable=True)
    usuario = Column(String(100), nullable=True)
    origen = Column(String(100), nullable=True)


class DimTiempo(Base):
    __tablename__ = "dim_tiempo"
    fecha = Column(Date, primary_key=True)
    anio = Column(Integer)
    mes = Column(Integer)
    dia = Column(Integer)
    trimestre = Column(Integer)
    dia_semana = Column(String(20))


class FactReservasRestaurantes(Base):
    __tablename__ = "fact_reservas_restaurantes"

    id_reserva = Column(BigInteger, primary_key=True, autoincrement=False)
    id_hotel = Column(Integer, ForeignKey("dim_hotel.id_hotel"))
    id_servicio = Column(Integer, ForeignKey("dim_servicio.id_servicio"))
    id_atencion = Column(Integer, ForeignKey("dim_atencion.id_atencion"))
    fecha_servicio = Column(Date, ForeignKey("dim_tiempo.fecha"))
    habitacion = Column(String(50), nullable=True)
    titular = Column(String(255), nullable=True)
    mesa = Column(String(50), nullable=True)
    turno = Column(Integer, default=1)
    horario = Column(String(50), nullable=True)
    cargado = Column(Boolean, default=False)
    obs = Column(String(50), nullable=True)
    cross_flag = Column(String(10), nullable=True)
    remarks = Column(Text, nullable=True)
    adultos = Column(Integer, default=0)
    ninos = Column(Integer, default=0)
    bebes = Column(Integer, default=0)
    pax_total = Column(Integer, default=0)
    num_habs_invitadas = Column(Integer, default=0)


# =====================================================================
# GESTOR DE CONEXIÓN
# =====================================================================

def get_database_url() -> str:
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sqlite_path = os.path.join(base_dir, "bahia_principe_bi.db")
    return f"sqlite:///{sqlite_path}"


def get_engine(db_url: Optional[str] = None):
    url = db_url or get_database_url()
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True,
        )
    return create_engine(
        url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
    )


def get_session_factory(engine=None):
    eng = engine or get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=eng)


@contextmanager
def get_db_session(engine=None) -> Generator[Session, None, None]:
    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(engine=None):
    """Crea el esquema BI y sustituye, una sola vez, el esquema estrella anterior."""
    eng = engine or get_engine()
    inspector = inspect(eng)
    tables = set(inspector.get_table_names())
    fact_columns = {column["name"] for column in inspector.get_columns("fact_reservas_restaurantes")} if "fact_reservas_restaurantes" in tables else set()
    hotel_columns = {column["name"] for column in inspector.get_columns("dim_hotel")} if "dim_hotel" in tables else set()
    schema_is_old = bool(tables & {"fact_reservas_restaurantes", "dim_hotel"}) and (
        not {"id_hotel", "fecha_servicio"}.issubset(fact_columns)
        or "codigo_hotel" not in hotel_columns
    )

    if schema_is_old:
        Base.metadata.drop_all(bind=eng)
        legacy_tables = {
            "dim_restaurante", "dim_horario", "dim_tipo_atencion", "dim_habitacion",
            "reservas", "reservas_servicios", "hoteles", "servicios", "turnos_horarios",
            "tipos_atencion", "usuarios", "Fact_Reservas_Restaurantes", "Dim_Hotel",
            "Dim_Restaurante", "Dim_Horario", "Dim_Tipo_Atencion", "Dim_Tiempo", "Dim_Habitacion",
        }
        dialect = eng.dialect.name
        with eng.begin() as connection:
            for table in legacy_tables & tables:
                suffix = " CASCADE" if dialect == "postgresql" else ""
                connection.execute(text(f'DROP TABLE IF EXISTS "{table}"{suffix}'))

    Base.metadata.create_all(bind=eng)
    return eng


if __name__ == "__main__":
    print(f"[*] Conectando a: {get_database_url()}")
    engine = init_db()
    print("[+] Base de datos inicializada (Esquema en Estrella BI con IDs exactos):")
    for t in Base.metadata.tables:
        print(f"    - {t}")
