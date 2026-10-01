"""Regression tests for the normalized restaurant-reservation star schema."""

import os
import tempfile
import unittest

import pandas as pd
from sqlalchemy import inspect
from sklearn.ensemble import RandomForestRegressor

from config_db import DimServicio, FactReservasRestaurantes, get_db_session, get_engine, init_db
from etl.etl_pipeline import cargar_dataframe, transformar_datos
from main import get_kpis, obtener_kpis_resumen


class TestBahiaPrincipeBI(unittest.TestCase):
    def setUp(self):
        file_descriptor, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(file_descriptor)
        self.engine = get_engine(f"sqlite:///{self.db_path}")
        init_db(self.engine)

    def tearDown(self):
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_star_schema_has_expected_tables_and_columns(self):
        expected = {
            "dim_hotel": {"id_hotel", "codigo_hotel", "hotel_res"},
            "dim_servicio": {"id_servicio", "codigo_servicio", "restaurante"},
            "dim_atencion": {"id_atencion", "atencion", "usuario", "origen"},
            "dim_tiempo": {"fecha", "anio", "mes", "dia", "trimestre", "dia_semana"},
            "fact_reservas_restaurantes": {
                "id_reserva", "id_hotel", "id_servicio", "id_atencion", "fecha_servicio",
                "habitacion", "titular", "mesa", "turno", "horario", "cargado", "obs",
                "cross_flag", "remarks", "adultos", "ninos", "bebes", "pax_total",
                "num_habs_invitadas",
            },
        }
        inspector = inspect(self.engine)
        self.assertEqual(set(inspector.get_table_names()), set(expected))
        for table, columns in expected.items():
            actual = {column["name"] for column in inspector.get_columns(table)}
            self.assertEqual(actual, columns)

    def test_transform_deduplicates_and_calculates_pax(self):
        raw = pd.DataFrame([
            {"Id": "8001", "Fecha Servicio": "2026-09-15", "Servicio": "ALI", "Hotel": "1", "Hotel Res.": "1", "#Adultos": "2", "#Niños": None, "#Bebés": "1"},
            {"Id": "8001", "Fecha Servicio": "2026-09-15", "Servicio": "ALI", "Hotel": "1", "Hotel Res.": "1", "#Adultos": "3", "#Niños": "1", "#Bebés": "0", "Habitación": " 0102 ", "Titular": "  TEST   PERSON  ", "Nº Habs. Invitadas": "2"},
        ])

        clean = transformar_datos(raw, "ALUX")

        self.assertEqual(len(clean), 1)
        self.assertEqual(clean.iloc[0]["pax_total"], 4)
        self.assertEqual(clean.iloc[0]["num_habs_invitadas"], 2)
        self.assertEqual(clean.iloc[0]["habitacion"], "0102")
        self.assertEqual(clean.iloc[0]["titular"], "TEST PERSON")

    def test_load_and_api_kpis_are_idempotent(self):
        raw = pd.DataFrame([
            {"Id": 8101, "Fecha Servicio": "2026-09-15", "Servicio": "ALI", "Hotel": "1", "Hotel Res.": "1", "Atención": "VIP1", "Usuario": "U1", "Origen": "BPG", "#Adultos": 2, "#Niños": 1, "#Bebés": 0},
        ])

        self.assertEqual(cargar_dataframe(raw, "ALUX", self.engine), 1)
        init_db(self.engine)
        with get_db_session(self.engine) as session:
            summary = obtener_kpis_resumen(session)
            response = get_kpis(db=session)
            self.assertEqual(session.query(FactReservasRestaurantes).count(), 1)
            self.assertEqual(summary["total_pax"], 3)
            self.assertEqual(summary["distribucion_restaurante"][0]["restaurante"], "ALUX")
            self.assertEqual(summary["desglose_hotel"][0]["hotel"], "1")
            self.assertEqual(response.total_pax, 3)
            self.assertEqual(len(response.cards), 4)

    def test_shared_service_code_keeps_each_restaurant(self):
        first = pd.DataFrame([
            {"Id": 8201, "Fecha Servicio": "2026-09-15", "Servicio": "SHARED", "Hotel": "1", "#Adultos": 2},
        ])
        second = pd.DataFrame([
            {"Id": 8202, "Fecha Servicio": "2026-09-15", "Servicio": "SHARED", "Hotel": "1", "#Adultos": 3},
        ])

        cargar_dataframe(first, "RESTAURANTE UNO", self.engine)
        cargar_dataframe(second, "RESTAURANTE DOS", self.engine)

        with get_db_session(self.engine) as session:
            mappings = {
                (item.codigo_servicio, item.restaurante)
                for item in session.query(DimServicio).all()
            }
            self.assertIn(("SHARED", "RESTAURANTE UNO"), mappings)
            self.assertTrue(any(name == "RESTAURANTE DOS" and code != "SHARED" for code, name in mappings))

    def test_random_forest_prediction(self):
        features = pd.DataFrame({"mes": [8, 8, 9, 9, 9], "dia_num": [1, 2, 5, 6, 7], "turno": [1, 2, 2, 3, 2]})
        targets = pd.Series([45, 80, 110, 50, 95])
        model = RandomForestRegressor(n_estimators=10, random_state=42)
        model.fit(features, targets)
        predictions = model.predict(features)
        self.assertEqual(len(predictions), len(targets))
        self.assertTrue(all(value > 0 for value in predictions))


if __name__ == "__main__":
    unittest.main()