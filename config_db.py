"""
config_db.py
==============
Configuración de Base de Datos y Modelos ORM con SQLAlchemy 2.0.
Implementa el Esquema en Estrella (Star Schema) para el Sistema Analítico
de Reservas de Restaurantes de Especialidad - Hoteles Bahía Príncipe.
Soporte dual: SQLite local (zero-config) y PostgreSQL para despliegue Cloud (Render, Supabase, Neon).
"""

import os
from datetime import datetime, date, timezone
from typing import Optional, Generator
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Text,
    Index
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

# Base declarativa de SQLAlchemy
Base = declarative_base()


# =====================================================================
# TABLAS DE DIMENSIONES (Star Schema)
# =====================================================================

class DimHotel(Base):
    """
    Dimensión Hotel:
    Almacena los hoteles del complejo Bahía Príncipe (ej. Tulum, Akumal, Coba, etc.)
    """
    __tablename__ = "Dim_Hotel"

    id_hotel = Column(Integer, primary_key=True, autoincrement=False)
    nombre_hotel = Column(String(100), nullable=False)
    codigo_origen = Column(String(20), nullable=False, unique=True, index=True)
    categoria = Column(String(50), nullable=True, default="Grand")

    # Relaciones
    restaurantes_ubicados = relationship("DimRestaurante", back_populates="hotel_ubicacion")
    reservas_hospedaje = relationship("FactReservasRestaurantes", back_populates="hotel_hospedaje")
    habitaciones = relationship("DimHabitacion", back_populates="hotel")

    def __repr__(self):
        return f"<DimHotel(id={self.id_hotel}, codigo='{self.codigo_origen}', nombre='{self.nombre_hotel}')>"


class DimRestaurante(Base):
    """
    Dimensión Restaurante:
    Catálogo de los 20 restaurantes de especialidad distribuidos entre los 5 hoteles.
    """
    __tablename__ = "Dim_Restaurante"

    id_restaurante = Column(String(20), primary_key=True)  # Ej. 'DPI', 'MIK', 'TEQ'
    nombre_restaurante = Column(String(100), nullable=False)
    especialidad = Column(String(60), nullable=False)       # Ej. 'Italiana', 'Japonesa / Teppanyaki'
    id_hotel_ubicacion = Column(Integer, ForeignKey("Dim_Hotel.id_hotel"), nullable=False, index=True)
    capacidad_maxima_pax = Column(Integer, nullable=False, default=120)

    # Relaciones
    hotel_ubicacion = relationship("DimHotel", back_populates="restaurantes_ubicados")
    reservas = relationship("FactReservasRestaurantes", back_populates="restaurante")

    def __repr__(self):
        return f"<DimRestaurante(id='{self.id_restaurante}', nombre='{self.nombre_restaurante}', hotel_id={self.id_hotel_ubicacion})>"


class DimHorario(Base):
    """
    Dimensión Horario:
    Turnos de servicio (1, 2, 3) y franjas horarias operativas de las reservas.
    """
    __tablename__ = "Dim_Horario"

    id_horario = Column(String(30), primary_key=True)  # Ej. 'T1_1730', 'T2_1930'
    turno = Column(Integer, nullable=False, index=True)
    horario_texto = Column(String(50), nullable=False) # Ej. "17:30 - 19:00"
    franja_horaria = Column(String(60), nullable=False)# Ej. "Turno Temprano (17:30 - 19:00)"

    # Relaciones
    reservas = relationship("FactReservasRestaurantes", back_populates="horario")

    def __repr__(self):
        return f"<DimHorario(id='{self.id_horario}', turno={self.turno}, horario='{self.horario_texto}')>"


class DimTipoAtencion(Base):
    """
    Dimensión Tipo de Atención:
    Clasificación del perfil de comensal (VIP, Fidelidad, Especial, Standard).
    """
    __tablename__ = "Dim_Tipo_Atencion"

    id_tipo_atencion = Column(String(30), primary_key=True) # Ej. 'STANDARD', 'VIP2', 'ATE01', 'GEB06'
    categoria_atencion = Column(String(50), nullable=False) # 'Standard', 'VIP', 'Fidelidad', 'Especial'
    prioridad_servicio = Column(Integer, nullable=False, default=4) # 1: Máxima / VIP, 4: Normal

    # Relaciones
    reservas = relationship("FactReservasRestaurantes", back_populates="tipo_atencion")

    def __repr__(self):
        return f"<DimTipoAtencion(id='{self.id_tipo_atencion}', cat='{self.categoria_atencion}', prioridad={self.prioridad_servicio})>"


class DimTiempo(Base):
    """
    Dimensión Tiempo:
    Granularidad diaria con calendario extendido, días de semana y estacionalidad turística.
    """
    __tablename__ = "Dim_Tiempo"

    id_fecha = Column(Date, primary_key=True)
    anio = Column(Integer, nullable=False, index=True)
    mes = Column(Integer, nullable=False, index=True)
    dia = Column(Integer, nullable=False)
    dia_semana = Column(String(20), nullable=False) # 'Lunes', 'Martes', etc.
    es_fin_de_semana = Column(Boolean, nullable=False, default=False)
    temporada = Column(String(30), nullable=False, default="Media") # 'Alta', 'Media', 'Baja'

    # Relaciones
    reservas = relationship("FactReservasRestaurantes", back_populates="tiempo")

    def __repr__(self):
        return f"<DimTiempo(id_fecha='{self.id_fecha}', dia_semana='{self.dia_semana}', temp='{self.temporada}')>"


class DimHabitacion(Base):
    """
    Dimensión Habitación [Escalabilidad Futura]:
    Estructura para enriquecer con datos del PMS hotelero (categoría de cuarto,
    país de procedencia anonimizado y segmento de mercado).
    """
    __tablename__ = "Dim_Habitacion"

    id_habitacion = Column(Integer, primary_key=True, autoincrement=True)
    numero_habitacion = Column(String(20), nullable=False)
    id_hotel = Column(Integer, ForeignKey("Dim_Hotel.id_hotel"), nullable=False, index=True)
    tipo_categoria_cuarto = Column(String(60), nullable=False, default="Junior Suite")
    pais_origen_agrupado = Column(String(60), nullable=False, default="Internacional")
    segmento_mercado = Column(String(60), nullable=False, default="Directo")

    # Relaciones
    hotel = relationship("DimHotel", back_populates="habitaciones")
    reservas = relationship("FactReservasRestaurantes", back_populates="habitacion")

    def __repr__(self):
        return f"<DimHabitacion(id={self.id_habitacion}, num='{self.numero_habitacion}', pais='{self.pais_origen_agrupado}')>"


# =====================================================================
# TABLA DE HECHOS (Star Schema Central)
# =====================================================================

class FactReservasRestaurantes(Base):
    """
    Tabla de Hechos Central: Fact_Reservas_Restaurantes
    Almacena cada reserva efectuada con sus métricas transaccionales y llaves foráneas.
    """
    __tablename__ = "Fact_Reservas_Restaurantes"

    id_reserva = Column(Integer, primary_key=True, autoincrement=False) # Id original
    id_fecha = Column(Date, ForeignKey("Dim_Tiempo.id_fecha"), nullable=False, index=True)
    id_restaurante = Column(String(20), ForeignKey("Dim_Restaurante.id_restaurante"), nullable=False, index=True)
    id_hotel_hospedaje = Column(Integer, ForeignKey("Dim_Hotel.id_hotel"), nullable=False, index=True)
    id_tipo_atencion = Column(String(30), ForeignKey("Dim_Tipo_Atencion.id_tipo_atencion"), nullable=False, index=True)
    id_horario = Column(String(30), ForeignKey("Dim_Horario.id_horario"), nullable=False, index=True)
    id_habitacion = Column(Integer, ForeignKey("Dim_Habitacion.id_habitacion"), nullable=True, index=True)

    # Métricas cuantitativas
    num_adultos = Column(Integer, nullable=False, default=1)
    num_ninos = Column(Integer, nullable=False, default=0)
    num_bebes = Column(Integer, nullable=False, default=0)
    total_pax = Column(Integer, nullable=False, default=1)
    habs_invitadas = Column(Float, nullable=True, default=0.0)

    # Indicadores analíticos
    es_cross_dining = Column(Boolean, nullable=False, default=False, index=True)
    requiere_periquera = Column(Boolean, nullable=False, default=False)
    observaciones_limpias = Column(Text, nullable=True)
    fecha_carga_etl = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones ORM
    tiempo = relationship("DimTiempo", back_populates="reservas")
    restaurante = relationship("DimRestaurante", back_populates="reservas")
    hotel_hospedaje = relationship("DimHotel", back_populates="reservas_hospedaje")
    tipo_atencion = relationship("DimTipoAtencion", back_populates="reservas")
    horario = relationship("DimHorario", back_populates="reservas")
    habitacion = relationship("DimHabitacion", back_populates="reservas")

    # Índices compuestos para optimizar consultas agregadas en Streamlit
    __table_args__ = (
        Index("idx_reserva_fecha_restaurante", "id_fecha", "id_restaurante"),
        Index("idx_reserva_cross_dining", "id_hotel_hospedaje", "es_cross_dining"),
    )

    def __repr__(self):
        return f"<FactReserva(id={self.id_reserva}, fecha={self.id_fecha}, rest='{self.id_restaurante}', pax={self.total_pax}, cross={self.es_cross_dining})>"


# =====================================================================
# GESTOR DE CONEXIÓN Y UTILIDADES DE BASE DE DATOS
# =====================================================================

def get_database_url() -> str:
    """
    Obtiene la URL de conexión a base de datos.
    Prioriza la variable de entorno DATABASE_URL (para PostgreSQL en Render, Supabase, Neon).
    Si no está configurada, utiliza SQLite local 'bahia_principe_bi.db'.
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # Corregir prefijo heredado 'postgres://' a 'postgresql://' requerido por SQLAlchemy
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
        return db_url
    
    # Ruta local SQLite
    base_dir = os.path.dirname(os.path.abspath(__file__))
    sqlite_path = os.path.join(base_dir, "bahia_principe_bi.db")
    return f"sqlite:///{sqlite_path}"


def get_engine(db_url: Optional[str] = None):
    """
    Crea y retorna un motor de SQLAlchemy optimizado según el dialecto.
    """
    url = db_url or get_database_url()
    if url.startswith("sqlite"):
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            pool_pre_ping=True
        )
    else:
        return create_engine(
            url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True
        )


def get_session_factory(engine=None):
    """
    Retorna una fábrica de sesiones configurada con el motor proporcionado.
    """
    eng = engine or get_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=eng)


@contextmanager
def get_db_session(engine=None) -> Generator[Session, None, None]:
    """
    Generador contextual de sesiones con commit y rollback automático.
    Uso:
        with get_db_session() as session:
            session.query(...)
    """
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
    """
    Crea todas las tablas del Esquema en Estrella en la base de datos si no existen.
    """
    eng = engine or get_engine()
    Base.metadata.create_all(bind=eng)
    return eng


if __name__ == "__main__":
    print(f"[*] Conectando a Base de Datos: {get_database_url()}")
    engine = init_db()
    print("[+] Tablas del Esquema en Estrella creadas exitosamente:")
    for table_name in Base.metadata.tables.keys():
        print(f"    - {table_name}")
