"""
etl/etl_pipeline.py
===================
Pipeline de Extracción, Transformación y Carga (ETL) para las reservas reales
de Bahía Príncipe Hotels & Resorts desde el archivo Excel a PostgreSQL Local.

Este ETL cumple con la normalización del esquema relacional: primero crea cada
dimensión (hoteles, servicios, turnos_horarios, tipos_atencion, usuarios),
resuelve todas las FK y luego carga la tabla transaccional reservas_servicios.
"""

import os
import sys
from datetime import datetime

import pandas as pd

# Agregar la raíz del proyecto al path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database import (
    HOTEL_ID_MAP,
    HOTEL_NAME_BY_ID,
    Hotel,
    Servicio,
    TurnoHorario,
    TipoAtencion,
    Usuario,
    SessionLocal,
    init_db,
    ReservaServicio,
    normalizar_texto,
)


HOTEL_CODIGOS = {
    1: "BPG",
    4: "AP3",
    10: "COB",
    16: "TOI",
    21: "SIA",
}


def encontrar_archivo_excel() -> str:
    """Busca el archivo Excel de reservas en el proyecto o descargas."""
    rutas_candidatas = [
        os.path.join(PROJECT_ROOT, "datos reservas (1).xlsx"),
        os.path.join(PROJECT_ROOT, "datos reservas.xlsx"),
        r"C:\Users\Informatica\Downloads\datos reservas (1).xlsx",
        r"C:\Users\Informatica\Downloads\datos reservas.xlsx",
    ]
    for ruta in rutas_candidatas:
        if os.path.exists(ruta):
            return ruta
    raise FileNotFoundError(f"No se encontró el archivo Excel en ninguna de las rutas: {rutas_candidatas}")


def limpiar_texto(valor) -> str:
    """Limpia cadenas de texto removiendo espacios extra o manejando nulos."""
    if pd.isna(valor) or valor is None:
        return ""
    return str(valor).strip()


def buscar_hotel_id(valor) -> int | None:
    """Resuelve el ID correcto de un hotel desde texto, nombre o número del Excel."""
    if valor is None or pd.isna(valor):
        return None
    texto = normalizar_texto(valor)

    if isinstance(valor, (int, float)):
        valor_int = int(valor)
        if valor_int in HOTEL_ID_MAP.values():
            return valor_int
        return None

    if texto == "":
        return None

    if texto.isdigit():
        valor_int = int(texto)
        if valor_int in HOTEL_ID_MAP.values():
            return valor_int
        return None

    for clave, hotel_id in HOTEL_ID_MAP.items():
        if clave == texto or clave in texto or texto in clave:
            return hotel_id

    for hotel_id, nombre in HOTEL_NAME_BY_ID.items():
        if normalizar_texto(nombre) in texto or texto in normalizar_texto(nombre):
            return hotel_id

    return None


def transformar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza columnas y limpia tipos sin perder su semántica original."""
    print(f"[ETL] Transformando {len(df)} registros...")

    col_map = {
        "Id": "id",
        "Fecha Servicio": "fecha_servicio",
        "Servicio": "servicio",
        "Turno": "turno",
        "Horario": "horario",
        "#Adultos": "adultos",
        "#Niños": "ninos",
        "#Bebés": "bebes",
        "Origen": "origen",
        "Hotel": "hotel",
        "Atención": "atencion",
        "Usuario": "usuario",
    }

    rename_dict = {}
    for col in df.columns:
        col_clean = str(col).strip()
        if col_clean in col_map:
            rename_dict[col] = col_map[col_clean]

    df = df.rename(columns=rename_dict)
    for col in ["id", "fecha_servicio", "servicio", "turno", "horario", "adultos", "ninos", "bebes", "origen", "hotel", "atencion", "usuario"]:
        if col not in df.columns:
            df[col] = None

    for col in ["adultos", "ninos", "bebes"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["pax_total"] = df["adultos"] + df["ninos"] + df["bebes"]

    df["id"] = pd.to_numeric(df["id"], errors="coerce").dropna().astype(int)
    df = df.dropna(subset=["id"])
    df = df.drop_duplicates(subset=["id"], keep="last")

    df["fecha_servicio"] = pd.to_datetime(df["fecha_servicio"], errors="coerce").dt.date
    df = df.dropna(subset=["fecha_servicio"])

    df["turno"] = pd.to_numeric(df["turno"], errors="coerce").fillna(1).astype(int)
    for col in ["servicio", "horario", "origen", "hotel", "atencion", "usuario"]:
        df[col] = df[col].apply(limpiar_texto)

    columnas_finales = [
        "id", "fecha_servicio", "servicio", "turno", "horario",
        "adultos", "ninos", "bebes", "pax_total",
        "origen", "hotel", "atencion", "usuario"
    ]
    return df[columnas_finales]


def _get_or_create_servicio(session, codigo: str, nombre: str = None):
    """Crea/reutiliza un servicio en la dimensión servicios."""
    codigo_norm = (codigo or "DPI").strip().upper()
    nombre_norm = nombre or codigo_norm
    servicio = session.query(Servicio).filter(Servicio.codigo == codigo_norm).first()
    if servicio is None:
        servicio = Servicio(codigo=codigo_norm, nombre=nombre_norm)
        session.add(servicio)
        session.flush()
    return servicio.id


def _get_or_create_turno_horario(session, turno: int, horario: str):
    """Crea/reutiliza el horario normalizado."""
    turno = int(turno) if turno is not None else 1
    horario_str = (horario or f"{turno}:00").strip()
    registro = session.query(TurnoHorario).filter(TurnoHorario.turno == turno, TurnoHorario.horario == horario_str).first()
    if registro is None:
        registro = TurnoHorario(turno=turno, horario=horario_str)
        session.add(registro)
        session.flush()
    return registro.id


def _get_or_create_hotel(session, valor):
    """Crea/reutiliza un hotel según el catálogo de IDs del negocio."""
    hotel_id = buscar_hotel_id(valor)
    if hotel_id is None:
        hotel_id = 1
    hotel = session.query(Hotel).filter(Hotel.id == hotel_id).first()
    if hotel is None:
        nombre = HOTEL_NAME_BY_ID.get(hotel_id, "Hotel Desconocido")
        codigo = {
            1: "BPG",
            4: "AP3",
            10: "COB",
            16: "TOI",
            21: "SIA",
        }.get(hotel_id, f"H{hotel_id}")
        hotel = Hotel(id=hotel_id, codigo=codigo, nombre=nombre)
        session.add(hotel)
        session.flush()
    return hotel.id


def _get_or_create_atencion(session, codigo: str):
    """Normaliza el tipo de atención y lo guarda en su dimensión."""
    normalizado = (codigo or "STANDARD").strip().upper()
    if normalizado in {"STD", "STANDARD", "ESTANDAR"}:
        codigo_final = "STANDARD"
        categoria_final = "Standard"
    elif normalizado in {"VIP", "VIP2", "VIP 2"}:
        codigo_final = "VIP2"
        categoria_final = "VIP"
    else:
        codigo_final = normalizado
        categoria_final = "Especial" if normalizado not in {"STANDARD", "VIP2"} else "Standard"

    registro = session.query(TipoAtencion).filter(TipoAtencion.codigo == codigo_final).first()
    if registro is None:
        registro = TipoAtencion(codigo=codigo_final, categoria=categoria_final)
        session.add(registro)
        session.flush()
    return registro.id


def _get_or_create_usuario(session, codigo: str):
    """Crea o reutiliza codigos de usuario cuando el Excel lo aporta."""
    valor = (codigo or "SYSTEM").strip()
    if not valor:
        valor = "SYSTEM"
    registro = session.query(Usuario).filter(Usuario.codigo == valor).first()
    if registro is None:
        registro = Usuario(codigo=valor)
        session.add(registro)
        session.flush()
    return registro.id


def cargar_a_postgresql(df: pd.DataFrame):
    """Carga las dimensiones y luego la tabla central con llaves foráneas resueltas."""
    init_db()
    total_registros = len(df)
    print(f"[ETL] Iniciando carga normalizada de {total_registros} reservas...")

    with SessionLocal() as session:
        for _, row in df.iterrows():
            servicio_id = _get_or_create_servicio(session, row.get("servicio", "DPI"), row.get("servicio", "DPI"))
            turno_id = _get_or_create_turno_horario(session, row.get("turno", 1), row.get("horario", ""))
            hotel_id = _get_or_create_hotel(session, row.get("hotel"))
            origen_id = _get_or_create_hotel(session, row.get("origen") or row.get("hotel"))
            atencion_id = _get_or_create_atencion(session, row.get("atencion", "STANDARD"))
            usuario_id = _get_or_create_usuario(session, row.get("usuario", "SYSTEM"))

            reserva = session.query(ReservaServicio).filter(ReservaServicio.id == int(row["id"])).first()
            if reserva is None:
                reserva = ReservaServicio(
                    id=int(row["id"]),
                    fecha_servicio=row["fecha_servicio"],
                    id_servicio=servicio_id,
                    id_turno_horario=turno_id,
                    id_hotel=hotel_id,
                    id_origen=origen_id,
                    id_atencion=atencion_id,
                    id_usuario=usuario_id,
                    adultos=int(row.get("adultos", 0) or 0),
                    ninos=int(row.get("ninos", 0) or 0),
                    bebes=int(row.get("bebes", 0) or 0),
                    pax_total=int(row.get("pax_total", 0) or 0),
                )
                session.add(reserva)
            else:
                reserva.fecha_servicio = row["fecha_servicio"]
                reserva.id_servicio = servicio_id
                reserva.id_turno_horario = turno_id
                reserva.id_hotel = hotel_id
                reserva.id_origen = origen_id
                reserva.id_atencion = atencion_id
                reserva.id_usuario = usuario_id
                reserva.adultos = int(row.get("adultos", 0) or 0)
                reserva.ninos = int(row.get("ninos", 0) or 0)
                reserva.bebes = int(row.get("bebes", 0) or 0)
                reserva.pax_total = int(row.get("pax_total", 0) or 0)

        session.commit()

    print("[ETL] Carga normalizada finalizada exitosamente.")


def mostrar_agregaciones_kpis(df: pd.DataFrame):
    """Genera y muestra en consola las agregaciones clave para KPIs."""
    total_filas = len(df)
    total_pax = df["pax_total"].sum()
    total_adultos = df["adultos"].sum()
    total_ninos = df["ninos"].sum()
    total_bebes = df["bebes"].sum()

    print("\n" + "=" * 65)
    print("           RESUMEN EJECUTIVO DE CARGA ETL - BAHÍA PRÍNCIPE")
    print("=" * 65)
    print(f" Total de reservas procesadas: {total_filas:,}")
    print(f" Total comensales (Pax):      {total_pax:,} (Adultos: {total_adultos:,}, Niños: {total_ninos:,}, Bebés: {total_bebes:,})")
    print(f" Promedio Pax por Reserva:    {round(total_pax / total_filas, 2) if total_filas else 0}")
    print("=" * 65)

    print("\n--- 1. TOTAL DE PAX POR SERVICIO Y TURNO (Top 10) ---")
    pax_servicio_turno = (
        df.groupby(["servicio", "turno"])["pax_total"]
        .agg(["count", "sum"])
        .rename(columns={"count": "Reservas", "sum": "Total Pax"})
        .sort_values(by="Total Pax", ascending=False)
        .head(10)
    )
    print(pax_servicio_turno.to_string())

    print("\n--- 2. DISTRIBUCIÓN DE RESERVAS POR ORIGEN ---")
    origen_dist = df["origen"].value_counts(normalize=True) * 100
    origen_count = df["origen"].value_counts()
    origen_df = pd.DataFrame({"Reservas": origen_count, "Porcentaje %": origen_dist.round(2)})
    print(origen_df.to_string())

    print("\n--- 3. OCUPACIÓN DIARIA (Últimos 10 días disponibles) ---")
    diario = (
        df.groupby("fecha_servicio")
        .agg(Total_Reservas=("id", "count"), Total_Pax=("pax_total", "sum"))
        .sort_index(ascending=False)
        .head(10)
    )
    print(diario.to_string())
    print("=" * 65 + "\n")


def run_etl():
    """Ejecuta el flujo completo de ETL."""
    archivo_excel = encontrar_archivo_excel()
    print(f"[ETL] Leyendo archivo: {archivo_excel}")

    df_raw = pd.read_excel(archivo_excel, engine="openpyxl")
    print(f"[ETL] Archivo leído correctamente: {len(df_raw)} filas encontradas.")

    df_clean = transformar_datos(df_raw)
    cargar_a_postgresql(df_clean)
    mostrar_agregaciones_kpis(df_clean)


if __name__ == "__main__":
    run_etl()
