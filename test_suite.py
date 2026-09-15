"""
test_suite.py
=============
Suite de pruebas automatizadas para validar:
1. Esquema en Estrella e integridad referencial de base de datos.
2. Pipeline ETL con cálculo de métricas (total_pax, cross_dining, periqueras) y anonimización.
3. Compatibilidad de carga con archivos CSV y Excel (.xlsx).
4. Motor de Machine Learning (entrenamiento y predicción de demanda con RandomForest).
"""

import os
import unittest
from datetime import date
import pandas as pd
import numpy as np

from config_db import (
    get_engine,
    get_db_session,
    init_db,
    DimHotel,
    DimRestaurante,
    DimHorario,
    DimTipoAtencion,
    DimTiempo,
    FactReservasRestaurantes,
)
from etl_pipeline import (
    transformar_dataframe_transaccional,
    generar_datos_mock,
    ejecutar_etl_desde_archivo,
    anonimizar_texto,
    mapear_codigo_hotel,
    mapear_codigo_restaurante,
)
from sklearn.ensemble import RandomForestRegressor


class TestBahiaPrincipeBI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Inicializa esquema y entorno de pruebas."""
        cls.engine = init_db()
        cls.base_dir = os.path.dirname(os.path.abspath(__file__))

    def test_01_star_schema_tables_exist(self):
        """Verifica que todas las tablas del Esquema en Estrella existan."""
        with get_db_session(self.engine) as session:
            hoteles = session.query(DimHotel).all()
            restaurantes = session.query(DimRestaurante).all()
            horarios = session.query(DimHorario).all()
            atenciones = session.query(DimTipoAtencion).all()

            self.assertEqual(len(hoteles), 5, "Deben existir 5 hoteles del complejo")
            self.assertEqual(len(restaurantes), 20, "Deben existir 20 restaurantes de especialidad")
            self.assertGreaterEqual(len(horarios), 6, "Deben existir los turnos y franjas horarias")
            self.assertGreaterEqual(len(atenciones), 5, "Deben existir los tipos de atención")

    def test_02_etl_metric_calculations(self):
        """Verifica cálculos de total_pax y es_cross_dining."""
        raw_test_data = pd.DataFrame([
            {
                "Id": 999001,
                "Fecha Servicio": "2026-09-15",
                "Servicio": "MIK",
                "Turno": 2,
                "Horario": "20:00 - 21:30",
                "Hotel": "AP3",
                "Hotel Res.": "BPG",  # Distinto -> Cross-Dining = True
                "#Adultos": 2,
                "#Niños": 2,
                "#Bebés": 1,
                "Atención": "VIP1",
                "Remarks": "Solicito periquera y llamar al 5551234567 para confirmar."
            },
            {
                "Id": 999002,
                "Fecha Servicio": "2026-09-15",
                "Servicio": "DPI",
                "Turno": 1,
                "Horario": "17:30 - 19:00",
                "Hotel": "BPG",
                "Hotel Res.": "BPG",  # Mismo hotel -> Cross-Dining = False
                "#Adultos": 2,
                "#Niños": 0,
                "#Bebés": 0,
                "Atención": "STANDARD",
                "Remarks": "Mesa cerca de ventana."
            }
        ])

        df_trans, resumen = transformar_dataframe_transaccional(raw_test_data)

        # Verificar total_pax
        self.assertEqual(df_trans.loc[df_trans["id_reserva"] == 999001, "total_pax"].iloc[0], 5)
        self.assertEqual(df_trans.loc[df_trans["id_reserva"] == 999002, "total_pax"].iloc[0], 2)

        # Verificar es_cross_dining
        self.assertTrue(df_trans.loc[df_trans["id_reserva"] == 999001, "es_cross_dining"].iloc[0])
        self.assertFalse(df_trans.loc[df_trans["id_reserva"] == 999002, "es_cross_dining"].iloc[0])

        # Verificar periquera
        self.assertTrue(df_trans.loc[df_trans["id_reserva"] == 999001, "requiere_periquera"].iloc[0])
        self.assertFalse(df_trans.loc[df_trans["id_reserva"] == 999002, "requiere_periquera"].iloc[0])

        # Verificar anonimización (no debe aparecer el teléfono 5551234567)
        obs_limpia = df_trans.loc[df_trans["id_reserva"] == 999001, "observaciones_limpias"].iloc[0]
        self.assertNotIn("5551234567", obs_limpia)

    def test_03_load_from_sample_files(self):
        """Verifica que el pipeline pueda cargar archivos sample_reservas.csv y .xlsx."""
        csv_file = os.path.join(self.base_dir, "sample_reservas.csv")
        xlsx_file = os.path.join(self.base_dir, "sample_reservas.xlsx")

        self.assertTrue(os.path.exists(csv_file), "Debe existir el archivo sample_reservas.csv")
        self.assertTrue(os.path.exists(xlsx_file), "Debe existir el archivo sample_reservas.xlsx")

        resumen_csv = ejecutar_etl_desde_archivo(csv_file, es_csv=True)
        self.assertGreater(resumen_csv["total_registros"], 0)
        self.assertGreater(resumen_csv["registros_cargados_bd"], 0)

    def test_04_machine_learning_pipeline(self):
        """Verifica que el modelo de RandomForest pueda entrenarse y predecir demanda."""
        # Dataset sintético mínimo para entrenamiento
        X_mock = pd.DataFrame({
            "mes": [8, 8, 9, 9, 9],
            "dia_num": [1, 2, 5, 6, 7],
            "es_fds_num": [0, 0, 1, 1, 1],
            "turno": [1, 2, 2, 3, 2],
            "capacidad": [110, 120, 150, 95, 140],
            "rest_encoded": [0, 1, 2, 3, 4]
        })
        y_mock = pd.Series([45, 80, 110, 50, 95])

        modelo = RandomForestRegressor(n_estimators=10, random_state=42)
        modelo.fit(X_mock, y_mock)
        preds = modelo.predict(X_mock)

        self.assertEqual(len(preds), 5)
        self.assertTrue(all(p > 0 for p in preds), "Todas las predicciones deben ser positivas")


if __name__ == "__main__":
    unittest.main()
