"""Normalize dirty schedule and attention sentinels in the active BI database."""

from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import BigInteger, Column, Integer, MetaData, String, Table, insert, text
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config_db import get_engine
from etl.etl_pipeline import _limpiar_cadena, _normalizar_horario, _normalizar_turno


BACKUP_FACT_TABLE = "respaldo_limpieza_fact_reservas_20261104"
BACKUP_ATTENTION_TABLE = "respaldo_limpieza_atencion_20261104"
BATCH_SIZE = 1000


def _insert_without_duplicates(connection, table: Table, rows: list[dict], key: str) -> None:
    if not rows:
        return
    if connection.dialect.name == "postgresql":
        statement = postgresql_insert(table).on_conflict_do_nothing(index_elements=[key])
    elif connection.dialect.name == "sqlite":
        statement = sqlite_insert(table).on_conflict_do_nothing(index_elements=[key])
    else:
        connection.execute(insert(table), rows)
        return
    connection.execute(statement, rows)


def normalizar_base_operativa() -> tuple[int, int]:
    engine = get_engine()
    metadata = MetaData()
    backup_facts = Table(
        BACKUP_FACT_TABLE,
        metadata,
        Column("id_reserva", BigInteger, primary_key=True),
        Column("turno_original", Integer),
        Column("horario_original", String(50)),
    )
    backup_attention = Table(
        BACKUP_ATTENTION_TABLE,
        metadata,
        Column("id_atencion", Integer, primary_key=True),
        Column("atencion_original", String(100)),
    )
    normalized_fact_count = 0
    normalized_attention_count = 0

    with engine.begin() as connection:
        backup_facts.create(connection, checkfirst=True)
        backup_attention.create(connection, checkfirst=True)

        result = connection.execute(text(
            "SELECT id_reserva, turno, horario FROM fact_reservas_restaurantes ORDER BY id_reserva"
        )).mappings()
        while rows := result.fetchmany(BATCH_SIZE):
            updates = []
            backups = []
            for row in rows:
                original_hour = row["horario"]
                clean_hour = _normalizar_horario(original_hour)
                clean_turn = _normalizar_turno(row["turno"], clean_hour)
                if clean_hour != original_hour or clean_turn != row["turno"]:
                    backups.append({
                        "id_reserva": row["id_reserva"],
                        "turno_original": row["turno"],
                        "horario_original": original_hour,
                    })
                    updates.append({
                        "id_reserva": row["id_reserva"],
                        "turno": clean_turn,
                        "horario": clean_hour,
                    })
            _insert_without_duplicates(connection, backup_facts, backups, "id_reserva")
            if updates:
                connection.execute(text(
                    "UPDATE fact_reservas_restaurantes "
                    "SET turno = :turno, horario = :horario "
                    "WHERE id_reserva = :id_reserva"
                ), updates)
                normalized_fact_count += len(updates)

        attention_rows = connection.execute(text(
            "SELECT id_atencion, atencion FROM dim_atencion"
        )).mappings().all()
        attention_backups = []
        attention_updates = []
        for row in attention_rows:
            clean_value = _limpiar_cadena(row["atencion"])
            if clean_value is None:
                clean_value = "Sin especificar"
            if clean_value != row["atencion"]:
                attention_backups.append({
                    "id_atencion": row["id_atencion"],
                    "atencion_original": row["atencion"],
                })
                attention_updates.append({
                    "id_atencion": row["id_atencion"],
                    "atencion": clean_value,
                })
        _insert_without_duplicates(connection, backup_attention, attention_backups, "id_atencion")
        if attention_updates:
            connection.execute(text(
                "UPDATE dim_atencion SET atencion = :atencion WHERE id_atencion = :id_atencion"
            ), attention_updates)
            normalized_attention_count = len(attention_updates)

    engine.dispose()
    return normalized_fact_count, normalized_attention_count


if __name__ == "__main__":
    facts, attentions = normalizar_base_operativa()
    print(f"Reservas normalizadas: {facts:,}")
    print(f"Tipos de atención faltantes limpiados: {attentions:,}")
    print(f"Respaldo de horarios y turnos: {BACKUP_FACT_TABLE}")
    print(f"Respaldo de etiquetas de atención: {BACKUP_ATTENTION_TABLE}")