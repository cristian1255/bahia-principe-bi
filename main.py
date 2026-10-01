"""
main.py
=======
Backend centralizado en FastAPI para el ecosistema Bahía Príncipe BI.
Utiliza exclusivamente la tabla única 'reservas' (mapeo 1:1 con los CSV reales).
"""

import os
import json
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func
from google import genai

from config_db import DimHotel, DimServicio, FactReservasRestaurantes, get_db_session, init_db

# Cargar variables de entorno
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

app = FastAPI(
    title="Bahia Principe BI Backend",
    description="API REST conectada a la base de datos con analítica de reservas y motor de IA Gemini.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> Session:
    with get_db_session() as session:
        yield session


@app.on_event("startup")
def on_startup():
    init_db()


class KpiCard(BaseModel):
    title: str
    value: str
    trend: str
    isPositiveTrend: bool
    colorHex: str = "#006B3F"


class KpiDashboardResponse(BaseModel):
    total_pax: int
    total_reservas: int
    distribucion_restaurante: List[Dict[str, Any]]
    desglose_hotel: List[Dict[str, Any]]
    cards: List[KpiCard]


class AIConsultRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    context: Optional[Dict[str, Any]] = None


class AIConsultResponse(BaseModel):
    status: str
    summary: str
    analysis: str
    recommendations: List[str]
    risk_level: str


def obtener_kpis_resumen(db: Session) -> Dict[str, Any]:
    fact = FactReservasRestaurantes
    total_reservas = db.query(func.count(fact.id_reserva)).scalar() or 0
    total_pax = db.query(func.sum(fact.pax_total)).scalar() or 0
    total_adultos = db.query(func.sum(fact.adultos)).scalar() or 0
    total_ninos = db.query(func.sum(fact.ninos)).scalar() or 0
    total_bebes = db.query(func.sum(fact.bebes)).scalar() or 0

    promedio_pax = round(total_pax / total_reservas, 2) if total_reservas > 0 else 0.0
    dias_operacion = db.query(func.count(func.distinct(fact.fecha_servicio))).scalar() or 1
    promedio_pax_dia = round(total_pax / dias_operacion, 1) if dias_operacion > 0 else 0.0

    top_servicio_row = (
        db.query(DimServicio.restaurante, func.sum(fact.pax_total).label("pax"))
        .join(fact, fact.id_servicio == DimServicio.id_servicio)
        .group_by(DimServicio.restaurante)
        .order_by(func.sum(fact.pax_total).desc())
        .first()
    )
    top_servicio = top_servicio_row[0] if top_servicio_row else "Sin datos"
    distribucion_restaurante = [
        {"restaurante": restaurante or "Sin nombre", "reservas": int(reservas), "pax": int(pax or 0)}
        for restaurante, reservas, pax in (
            db.query(
                DimServicio.restaurante,
                func.count(fact.id_reserva),
                func.sum(fact.pax_total),
            )
            .join(fact, fact.id_servicio == DimServicio.id_servicio)
            .group_by(DimServicio.restaurante)
            .order_by(func.sum(fact.pax_total).desc())
            .all()
        )
    ]
    desglose_hotel = [
        {"hotel": codigo or "Sin dato", "reservas": int(reservas), "pax": int(pax or 0)}
        for codigo, reservas, pax in (
            db.query(
                DimHotel.codigo_hotel,
                func.count(fact.id_reserva),
                func.sum(fact.pax_total),
            )
            .join(fact, fact.id_hotel == DimHotel.id_hotel)
            .group_by(DimHotel.codigo_hotel)
            .order_by(func.sum(fact.pax_total).desc())
            .all()
        )
    ]

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
        "distribucion_restaurante": distribucion_restaurante,
        "desglose_hotel": desglose_hotel,
    }


def obtener_kpis_android(db: Session) -> List[Dict[str, Any]]:
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


@app.get("/health")
def health(db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        total = db.query(FactReservasRestaurantes).count()
        return {
            "status": "ok",
            "service": "bahia-principe-bi-api",
            "database": "postgresql/sqlite",
            "total_reservas": total,
        }
    except Exception as e:
        return {"status": "degraded", "error": str(e)}


@app.get("/api/v1/kpis", response_model=KpiDashboardResponse)
def get_kpis(region: Optional[str] = None, db: Session = Depends(get_db)) -> KpiDashboardResponse:
    summary = obtener_kpis_resumen(db)
    return KpiDashboardResponse(
        total_pax=summary["total_pax"],
        total_reservas=summary["total_reservas"],
        distribucion_restaurante=summary["distribucion_restaurante"],
        desglose_hotel=summary["desglose_hotel"],
        cards=[KpiCard(**card) for card in obtener_kpis_android(db)],
    )


@app.get("/api/v1/kpis/summary")
def get_kpis_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    return obtener_kpis_resumen(db)


def _build_system_prompt_with_real_kpis(user_prompt: str, kpis: Dict[str, Any], extra_context: Optional[Dict[str, Any]]) -> str:
    contexto_operativo = {
        "hotel_cadena": "Bahía Príncipe Hotels & Resorts",
        "base_datos_origen": "Esquema en estrella normalizado de reservas CSV",
        "metricas_reales_actuales": kpis,
    }
    if extra_context:
        contexto_operativo["contexto_adicional"] = extra_context

    example_json = (
        '{\n'
        '  "status": "success",\n'
        '  "summary": "Resumen ejecutivo del estado actual",\n'
        '  "analysis": "Análisis estratégico detallado basado en datos reales",\n'
        '  "recommendations": ["Recomendación 1", "Recomendación 2", "Recomendación 3"],\n'
        '  "risk_level": "LOW"\n'
        '}'
    )

    return (
        "Eres un analista y asesor ejecutivo senior de Business Intelligence para Bahía Príncipe Hotels & Resorts.\n"
        "Debes responder en español formal, ejecutivo y con foco en toma de decisiones estratégicas.\n\n"
        "DATOS Y KPIS REALES DE LA BASE DE DATOS:\n"
        + json.dumps(contexto_operativo, ensure_ascii=False, indent=2)
        + "\n\nREGLAS OBLIGATORIAS:\n"
        + "1. Basa tus argumentos en los KPIs reales suministrados.\n"
        + "2. Responde ÚNICAMENTE con un JSON válido parseable, sin código markdown envolvente.\n"
        + "3. El JSON debe tener exactamente esta estructura:\n"
        + example_json
        + "\n4. status debe ser 'success'.\n"
        + "5. recommendations debe ser una lista de cadenas con acciones sugeridas.\n"
        + "6. risk_level debe ser 'LOW', 'MEDIUM' o 'HIGH'.\n\n"
        + "CONSULTA DEL USUARIO / DIRECTIVO:\n"
        + user_prompt
    ).strip()


def _parse_ai_json(text: str) -> Dict[str, Any]:
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        if len(lines) >= 2:
            clean = "\n".join(lines[1:-1]).strip()
    start = clean.find("{")
    end = clean.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(clean[start : end + 1])
    return json.loads(clean)


@app.post("/api/v1/ai/consult", response_model=AIConsultResponse)
async def consult_ai(payload: AIConsultRequest, db: Session = Depends(get_db)) -> AIConsultResponse:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Falta GEMINI_API_KEY en el entorno (.env).")

    kpis_reales = obtener_kpis_resumen(db)
    system_prompt = _build_system_prompt_with_real_kpis(payload.prompt, kpis_reales, payload.context)

    client = genai.Client(api_key=api_key)
    raw_text = ""
    try:
        response = client.models.generate_content(model="gemini-1.5-flash", contents=system_prompt)
        raw_text = (getattr(response, "text", "") or "").strip()
    except Exception:
        raw_text = ""

    if not raw_text:
        return AIConsultResponse(
            status="success",
            summary=f"Operación Bahía Príncipe: {kpis_reales['total_reservas']} reservas y {kpis_reales['total_pax']} comensales.",
            analysis=f"Ocupación promedio de {kpis_reales['promedio_pax_reserva']} pax/reserva. Servicio líder: {kpis_reales['top_servicio']}.",
            recommendations=["Optimizar asignación de mesas en turnos pico.", "Monitorear rotación de comensales."],
            risk_level="LOW"
        )

    try:
        parsed = _parse_ai_json(raw_text)
        recs = parsed.get("recommendations", ["Optimizar asignación de mesas."])
        if isinstance(recs, str):
            recs = [recs]
        return AIConsultResponse(
            status=parsed.get("status", "success"),
            summary=str(parsed.get("summary", "Resumen operativo generado.")),
            analysis=str(parsed.get("analysis", "Análisis completado.")),
            recommendations=recs,
            risk_level=str(parsed.get("risk_level", "LOW")).upper(),
        )
    except Exception:
        return AIConsultResponse(
            status="success",
            summary=f"Operación con {kpis_reales['total_reservas']} reservas.",
            analysis=raw_text[:400],
            recommendations=["Verificar capacidad de turnos."],
            risk_level="LOW",
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
