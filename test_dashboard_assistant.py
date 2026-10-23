import unittest

import pandas as pd

from dashboard_assistant import responder_consulta


class TestDashboardAssistant(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame([
            {
                "id_fecha": "2026-08-01",
                "hotel_restaurante": "Hotel Norte",
                "nombre_restaurante": "Portofino",
                "turno": 1,
                "es_cross_dining": False,
                "total_pax": 4,
                "id_reserva": 1,
                "num_ninos": 1,
                "num_bebes": 0,
                "categoria_atencion": "Normal",
            },
            {
                "id_fecha": "2026-08-02",
                "hotel_restaurante": "Hotel Norte",
                "nombre_restaurante": "Portofino",
                "turno": 2,
                "es_cross_dining": True,
                "total_pax": 6,
                "id_reserva": 2,
                "num_ninos": 0,
                "num_bebes": 1,
                "categoria_atencion": "VIP",
            },
            {
                "id_fecha": "2026-07-03",
                "hotel_restaurante": "Hotel Sur",
                "nombre_restaurante": "Tequila",
                "turno": 1,
                "es_cross_dining": False,
                "total_pax": 3,
                "id_reserva": 3,
                "num_ninos": 0,
                "num_bebes": 0,
                "categoria_atencion": "Normal",
            },
        ])

    def test_month_question_returns_real_totals_and_date_filter(self):
        answer, filters = responder_consulta("¿Cuántas reservas hubo en agosto?", self.data, self.data)

        self.assertIn("2 reservas", answer)
        self.assertIn("10 comensales", answer)
        self.assertEqual(filters["date_range"], (pd.Timestamp("2026-08-01").date(), pd.Timestamp("2026-08-02").date()))

    def test_new_restaurant_filter_replaces_conflicting_selection(self):
        current_selection = self.data[self.data["nombre_restaurante"] == "Tequila"]

        answer, filters = responder_consulta("Filtra por restaurante Portofino", current_selection, self.data)

        self.assertEqual(filters["restaurant"], "Portofino")
        self.assertIn("10 comensales", answer)

    def test_shift_filter_is_detected(self):
        answer, filters = responder_consulta("Filtra por turno 2", self.data, self.data)

        self.assertEqual(filters["shift"], 2)
        self.assertIn("6 comensales", answer)

    def test_empty_dataset_has_clear_response(self):
        answer, filters = responder_consulta("¿Cuántas reservas hay?", self.data.iloc[0:0], self.data.iloc[0:0])

        self.assertIn("no hay datos", answer.lower())
        self.assertEqual(filters, {})


if __name__ == "__main__":
    unittest.main()
