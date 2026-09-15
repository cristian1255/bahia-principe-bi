import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import google.generativeai as genai

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

app = FastAPI(title="Bahia Principe BI AI Backend", version="1.0.0")

SYSTEM_CONTEXT: Dict[str, Any] = {
    "hotel_info": {
        "chain": "Bahía Príncipe Hotels & Resorts",
        "property": "Bahia Principe Grand Bavaro",
        "region": "Punta Cana, República Dominicana",
        "date": "2026-09-11",
    },
    "kpis": {
        "occupancy_rate": 88.5,
        "adr_usd": 215.0,
        "revpar_usd": 190.27,
        "total_revenue_usd": 142700.0,
        "food_and_beverage_usd": 45200.0,
        "forecast_occupancy_next_7d": 92.1,
    },
    "competitor_compset": {
        "average_occupancy": 84.0,
        "average_adr_usd": 225.0,
    },
    "alerts_and_trends": [
        "Incremento del 12% en reservas de mercado estadounidense para Q4.",
        "Baja ligera en la venta de excursiones internas respecto al mes anterior.",
    ],
}


class AIConsultRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Pregunta o consulta del usuario")
    context: Dict[str, Any] | None = Field(default=None, description="Contexto opcional del negocio")


class AIConsultResponse(BaseModel):
    status: str
    summary: str
    analysis: str
    recommendations: List[str]
    risk_level: str


def _build_system_prompt(user_prompt: str, context: Dict[str, Any] | None) -> str:
    payload = context or SYSTEM_CONTEXT
    example_json = '{\n  "status": "success",\n  "summary": "Lorem ipsum",\n  "analysis": "Lorem ipsum",\n  "recommendations": ["recomendación 1", "recomendación 2"],\n  "risk_level": "LOW"\n}'
    return (
        "Eres un analista ejecutivo de hotelería para Bahía Príncipe Hotels & Resorts.\n"
        "Responde en español, en tono ejecutivo y directivo, orientado a KPIs hoteleros.\n\n"
        "Contexto del negocio:\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n\nReglas estrictas:\n"
        + "- No inventes datos que no estén en el contexto.\n"
        + "- Responde siempre en español.\n"
        + "- Devuelve solo un JSON válido y sin texto extra antes ni después.\n"
        + "- El JSON debe seguir exactamente esta estructura:\n"
        + example_json
        + "\n- Risk level debe ser uno de: LOW, MEDIUM, HIGH.\n"
        + "- Las recomendaciones deben estar orientadas a rendimiento, tarifa, ocupación, marginación y estrategia operativa.\n"
        + "- Si no hay suficientes datos, usa el contexto disponible y responde conservadoramente.\n\n"
        + "Pregunta del usuario:\n"
        + user_prompt
    ).strip()


def _extract_json_payload(text: str) -> Dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No se encontró JSON válido en la respuesta del modelo.")
    return json.loads(text[start : end + 1])


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "bahia-principe-bi-ai"}


@app.post("/api/v1/ai/consult", response_model=AIConsultResponse)
async def consult_ai(payload: AIConsultRequest) -> AIConsultResponse:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Falta GEMINI_API_KEY en el entorno del backend.")

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.5-flash")
        system_prompt = _build_system_prompt(payload.prompt, payload.context)
        response = model.generate_content(system_prompt)
        raw_text = (response.text or "").strip()
        parsed = _extract_json_payload(raw_text)

        recommendations = parsed.get("recommendations", ["Revisión de demanda y estrategia de precios."])
        if isinstance(recommendations, str):
            recommendations = [recommendations]
        if not isinstance(recommendations, list):
            recommendations = [str(recommendations)]

        normalized = {
            "status": parsed.get("status", "success"),
            "summary": str(parsed.get("summary", "Resumen no disponible.")),
            "analysis": str(parsed.get("analysis", "Análisis no disponible.")),
            "recommendations": recommendations,
            "risk_level": str(parsed.get("risk_level", "LOW")).upper(),
        }

        return AIConsultResponse(**normalized)
    except Exception as exc:  # pragma: no cover - safety fallback
        raise HTTPException(status_code=502, detail=f"Error al consultar a Gemini: {str(exc)}") from exc
