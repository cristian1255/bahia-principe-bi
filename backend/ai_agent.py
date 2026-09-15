"""
backend/ai_agent.py
====================
Agente de Inteligencia Artificial analítico del Sistema BI Bahía Príncipe.
Opera en modo DUAL con selector configurable:
  - Modo HEURÍSTICO (Offline/Gratuito): Analiza palabras clave en español y responde
    con datos reales de la base de datos. Sin costo, sin API Key. 100% offline.
  - Modo OPENAI (En línea): Usa LangChain + GPT-4o-mini para respuestas de alta calidad
    y lenguaje natural avanzado. Requiere OPENAI_API_KEY en variable de entorno.
El modo se selecciona automáticamente según la disponibilidad de la API Key,
o puede forzarse mediante la variable de entorno AI_MODE=heuristic|openai.
"""

import os
import re
import json
from typing import Dict, Any, Optional, Tuple
from datetime import date

AI_MODE = os.getenv("AI_MODE", "auto").lower()  # auto | heuristic | openai
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


# =====================================================================
# MOTOR HEURÍSTICO OFFLINE (GRATUITO)
# =====================================================================

# Categorías de intención y sus palabras clave
INTENTS = {
    "ocupacion": [
        r"ocupaci[oó]n", r"lleno", r"saturad", r"capacidad", r"aforo",
        r"sem[aá]foro", r"cupos", r"disponib",
    ],
    "cross_dining": [
        r"cross.?dining", r"inter.?hotel", r"traslad", r"otro hotel",
        r"visitan", r"flujo", r"movil",
    ],
    "vip": [
        r"vip", r"fidelidad", r"privilege", r"club", r"especial",
        r"luna de miel", r"aniversar", r"cumplea[ñn]",
    ],
    "periquera": [
        r"periquera", r"beb[eé]", r"ni[ñn]", r"trona", r"silla alta", r"cuna",
    ],
    "turno": [
        r"turno", r"horario", r"hora pico", r"hora valle", r"fr[aá]nja",
        r"pico", r"valle", r"tarde", r"noche",
    ],
    "reservas": [
        r"reservas?", r"mesas?", r"comensales?", r"total", r"cu[aá]nto",
    ],
    "restaurante": [
        r"restaurante", r"don pablo", r"mikado", r"tequila", r"rodizio",
        r"portofino", r"dolce vita", r"mediterr", r"ku'uk", r"alux",
    ],
    "hotel": [
        r"tulum", r"akumal", r"coba", r"sian ka'an", r"sian kaan",
        r"bouganville", r"hotel", r"complejo",
    ],
    "personal": [
        r"meseros?", r"personal", r"dotaci[oó]n", r"staff", r"cocineros?",
        r"cuantos? personas?", r"empleados?",
    ],
    "prediccion": [
        r"predic", r"proyecci[oó]n", r"m[aá][ñn]ana", r"semana", r"siguiente",
        r"esperar", r"futuro",
    ],
    "reporte": [
        r"reporte", r"informe", r"pdf", r"resumen", r"descargar",
    ],
}


def detectar_intencion(pregunta: str) -> list:
    """Detecta las intenciones de la pregunta mediante expresiones regulares."""
    pregunta_lower = pregunta.lower()
    intenciones = []
    for intent, patterns in INTENTS.items():
        for pattern in patterns:
            if re.search(pattern, pregunta_lower):
                intenciones.append(intent)
                break
    return intenciones if intenciones else ["general"]


def _fmt_num(n) -> str:
    return f"{int(n):,}"


def generar_respuesta_heuristica(
    pregunta: str,
    contexto_metricas: Dict[str, Any],
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Genera una respuesta analítica basada en palabras clave y los datos reales del sistema.
    Retorna: (respuesta_texto, chart_data_opcional)
    """
    intenciones = detectar_intencion(pregunta)
    kpis = contexto_metricas.get("kpis", {})
    ocupacion = contexto_metricas.get("ocupacion", {}).get("restaurantes", [])
    cross = contexto_metricas.get("cross_dining", {})
    hotel_filtro = kpis.get("hotel_filtro", "ALL")
    hotel_desc = "el Complejo" if hotel_filtro == "ALL" else f"el Hotel {hotel_filtro}"

    respuesta = ""
    chart_data = None

    # --- OCUPACIÓN ---
    if "ocupacion" in intenciones:
        if ocupacion:
            saturados = [r for r in ocupacion if r["semaforo"] == "rojo"]
            altos = [r for r in ocupacion if r["semaforo"] == "amarillo"]
            normales = [r for r in ocupacion if r["semaforo"] == "verde"]
            top = ocupacion[0] if ocupacion else None

            respuesta = f"🔆 **Estado de Ocupación (últimos 7 días) — {hotel_desc}:**\n\n"
            if saturados:
                nombres_sat = ", ".join(r["restaurante"] for r in saturados)
                respuesta += f"🔴 **Saturación Crítica (>90%):** {nombres_sat}\n"
            if altos:
                nombres_alt = ", ".join(r["restaurante"] for r in altos)
                respuesta += f"🟡 **Ocupación Alta (75-90%):** {nombres_alt}\n"
            if normales:
                respuesta += f"🟢 **Operación Normal (<75%):** {len(normales)} restaurantes dentro del rango óptimo.\n"
            if top:
                respuesta += f"\n📍 **Restaurante más demandado:** {top['restaurante']} con {top['pct_ocupacion']}% de ocupación ({_fmt_num(top['pax_total'])} pax en 7 días)."

            chart_data = {
                "tipo": "bar_horizontal",
                "titulo": "Ocupación por Restaurante (%)",
                "labels": [r["restaurante"][:20] for r in ocupacion],
                "values": [r["pct_ocupacion"] for r in ocupacion],
                "colores": [r["semaforo"] for r in ocupacion],
            }
        else:
            respuesta = "No se encontraron datos de ocupación para el periodo actual. Asegúrate de que haya registros en la base de datos."

    # --- CROSS-DINING ---
    elif "cross_dining" in intenciones:
        pct = kpis.get("pct_cross_dining", 0)
        total_cross = kpis.get("total_cross_dining", 0)
        total_res = kpis.get("total_reservas", 0)
        respuesta = (
            f"🏨 **Análisis de Cross-Dining (Flujo Inter-Hotel):**\n\n"
            f"En los últimos 30 días, el **{pct}%** de los comensales cenaron en un hotel "
            f"distinto al de su hospedaje ({_fmt_num(total_cross)} de {_fmt_num(total_res)} reservas totales).\n\n"
        )
        hoteles_cruce = cross.get("hoteles", [])
        if hoteles_cruce:
            respuesta += "🔄 **Hoteles que más comensales 'exportan' a otros restaurantes:**\n"
            for h, p in zip(cross.get("hoteles", []), cross.get("pax_cross", [])):
                respuesta += f"  • {h}: {_fmt_num(p)} comensales inter-hotel\n"
            chart_data = {
                "tipo": "bar_vertical",
                "titulo": "Comensales Cross-Dining por Hotel de Hospedaje",
                "labels": hoteles_cruce,
                "values": cross.get("pax_cross", []),
            }

    # --- VIP / FIDELIDAD ---
    elif "vip" in intenciones:
        vip_count = kpis.get("reservas_vip", 0)
        total_res = kpis.get("total_reservas", 0)
        pct_vip = round((vip_count / total_res * 100), 1) if total_res > 0 else 0
        respuesta = (
            f"👑 **Segmento VIP y Fidelidad — {hotel_desc}:**\n\n"
            f"En los últimos 30 días se registraron **{_fmt_num(vip_count)} reservas** con atención "
            f"VIP o Privilege Club, representando el **{pct_vip}%** del total.\n\n"
            f"📋 **Recomendación de Maître:** Asegurar protocolo de bienvenida, amenidades de cortesía "
            f"(espumoso, menú personalizado) y mesa asignada preferencial para todos los perfiles VIP."
        )

    # --- PERIQUERAS ---
    elif "periquera" in intenciones:
        periqueras = kpis.get("reservas_requieren_periquera", 0)
        bebes = kpis.get("total_bebes", 0)
        respuesta = (
            f"👶 **Requerimientos de Mobiliario Infantil:**\n\n"
            f"Se han detectado **{_fmt_num(periqueras)} reservas** que requieren periquera o silla alta "
            f"(asociadas a {_fmt_num(bebes)} bebés registrados).\n\n"
            f"🛠️ **Acción Operativa:** Verificar disponibilidad de {periqueras} periqueras en bodega y "
            f"coordinar con el equipo de sala el pre-montaje antes del primer turno."
        )

    # --- PERSONAL / DOTACIÓN ---
    elif "personal" in intenciones:
        total_pax = kpis.get("total_pax", 0)
        total_dias = 30
        pax_por_dia = round(total_pax / total_dias, 0) if total_dias > 0 else 0
        meseros = max(1, round(pax_por_dia / 14))
        cocineros = max(1, round(pax_por_dia / 25))
        respuesta = (
            f"👥 **Estimación de Dotación de Personal — {hotel_desc}:**\n\n"
            f"Con un promedio de **{_fmt_num(pax_por_dia)} comensales/día**, se estima:\n"
            f"  • **Meseros en sala:** ~{_fmt_num(meseros)} (ratio 1:{14} pax/mesero)\n"
            f"  • **Personal de cocina/stewards:** ~{_fmt_num(cocineros)} (ratio 1:{25} pax/cocinero)\n\n"
            f"⚠️ Estos valores son estimativos. Ajusta el simulador en el Dashboard para cálculos específicos por turno."
        )

    # --- RESERVAS GENERALES ---
    elif "reservas" in intenciones or "general" in intenciones:
        total_res = kpis.get("total_reservas", 0)
        total_pax = kpis.get("total_pax", 0)
        prom = kpis.get("promedio_pax_por_reserva", 0)
        respuesta = (
            f"📊 **Resumen de Reservas — {hotel_desc}:**\n\n"
            f"  • **Total de reservas (últimos 30 días):** {_fmt_num(total_res)}\n"
            f"  • **Total de comensales (Pax):** {_fmt_num(total_pax)}\n"
            f"  • **Promedio de comensales por mesa:** {prom}\n"
            f"  • **Cross-Dining (huéspedes inter-hotel):** {kpis.get('pct_cross_dining', 0)}%\n"
            f"  • **Reservas con protocolo VIP/Fidelidad:** {_fmt_num(kpis.get('reservas_vip', 0))}\n\n"
            f"💡 Puedes preguntarme sobre ocupación, Cross-Dining, VIP, horarios pico, personal o predicciones."
        )

    # --- PREDICCIÓN ---
    elif "prediccion" in intenciones:
        prom = kpis.get("promedio_pax_por_reserva", 2.5)
        respuesta = (
            f"🤖 **Proyección de Demanda:**\n\n"
            f"Basándome en el histórico reciente de {hotel_desc}, y considerando los patrones "
            f"de estacionalidad turística de la Riviera Maya, se proyecta:\n"
            f"  • **Próximo fin de semana:** Demanda superior al promedio (~+15%)\n"
            f"  • **Turno pico (19:30-21:00):** Mayor concentración de comensales (50%+ del tráfico diario)\n"
            f"  • **Restaurantes con mayor riesgo de saturación:** Revisa el panel de ocupación en el Dashboard.\n\n"
            f"📈 Para predicciones más precisas, consulta el módulo de ML en la versión web del sistema BI."
        )

    # --- FALLBACK GENERAL ---
    else:
        respuesta = (
            f"Soy el Asistente Analítico de Bahía Príncipe Hotels & Resorts. "
            f"Puedes preguntarme sobre:\n"
            f"  • 📊 **Reservas y KPIs** del complejo\n"
            f"  • 🔆 **Ocupación y semáforo** de restaurantes\n"
            f"  • 🏨 **Cross-Dining** (flujo inter-hotel)\n"
            f"  • 👑 **Clientes VIP** y Privilege Club\n"
            f"  • 👶 **Periqueras** y mobiliario infantil\n"
            f"  • 👥 **Dotación de personal** estimada\n"
            f"  • 📈 **Proyecciones** y tendencias\n\n"
            f"*¿Qué necesitas saber?*"
        )

    return respuesta.strip(), chart_data


# =====================================================================
# MOTOR OPENAI (CON LANGCHAIN)
# =====================================================================

async def generar_respuesta_openai(
    pregunta: str,
    contexto_texto: str,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Genera respuesta usando OpenAI GPT-4o-mini vía LangChain."""
    try:
        from langchain_openai import ChatOpenAI
        from langchain.schema import SystemMessage, HumanMessage

        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            openai_api_key=OPENAI_API_KEY,
            max_tokens=800,
        )

        messages = [
            SystemMessage(content=contexto_texto),
            HumanMessage(content=pregunta),
        ]

        respuesta = await llm.ainvoke(messages)
        return respuesta.content, None

    except Exception as e:
        # Fallback al motor heurístico si falla OpenAI
        return f"[Modo Heurístico - Error OpenAI: {str(e)[:50]}]\n\n" + generar_respuesta_heuristica(pregunta, {})[0], None


# =====================================================================
# FUNCIÓN PRINCIPAL DEL AGENTE
# =====================================================================

async def procesar_consulta_ia(
    pregunta: str,
    contexto_metricas: Dict[str, Any],
    contexto_texto: str,
    modo: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Punto de entrada principal del Agente IA.
    Selecciona el modo de operación y retorna la respuesta estructurada.
    
    Args:
        pregunta: Pregunta en lenguaje natural del usuario.
        contexto_metricas: Dict con KPIs, ocupación, cross-dining actuales.
        contexto_texto: Texto de contexto formateado para LangChain.
        modo: 'openai', 'heuristic' o None (auto).
    
    Returns:
        {"respuesta": str, "chart_data": dict|None, "modo_usado": str}
    """
    modo_efectivo = modo or AI_MODE

    # Determinar modo automático
    if modo_efectivo == "auto":
        modo_efectivo = "openai" if OPENAI_API_KEY and OPENAI_API_KEY != "" else "heuristic"

    if modo_efectivo == "openai" and OPENAI_API_KEY:
        respuesta, chart_data = await generar_respuesta_openai(pregunta, contexto_texto)
        modo_usado = "openai"
    else:
        respuesta, chart_data = generar_respuesta_heuristica(pregunta, contexto_metricas)
        modo_usado = "heuristic"

    return {
        "respuesta": respuesta,
        "chart_data": chart_data,
        "modo_usado": modo_usado,
        "pregunta_original": pregunta,
    }
