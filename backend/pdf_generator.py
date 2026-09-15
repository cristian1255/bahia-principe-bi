"""
backend/pdf_generator.py
=========================
Generador de reportes ejecutivos en PDF para la App Móvil Bahía Príncipe.
Utiliza ReportLab para crear documentos PDF con calidad editorial profesional.

Estructura del reporte (4-6 páginas):
  1. Portada Corporativa (Logo + Periodo + Autorizante)
  2. Resumen Ejecutivo de KPIs (Tarjetas de métricas clave)
  3. Semáforo de Ocupación por Restaurante
  4. Análisis de Cross-Dining Inter-Hotel
  5. Segmentación VIP y Requerimientos Especiales
  6. Pie de Página Institucional y Firma Electrónica
"""

import io
from datetime import date, datetime, timezone
from typing import Dict, Any, Optional, List

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.colors import (
    Color, HexColor, white, black
)
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether,
)
from reportlab.platypus.flowables import Flowable


# =====================================================================
# PALETA DE COLORES BAHÍA PRÍNCIPE
# =====================================================================

NAVY_BLUE    = HexColor("#0B1E36")
GOLD         = HexColor("#C5A059")
LIGHT_GOLD   = HexColor("#E8C87A")
DARK_BG      = HexColor("#13223D")
LIGHT_GRAY   = HexColor("#F0F0F0")
MEDIUM_GRAY  = HexColor("#8A8A8A")
WHITE        = white
RED_ALERT    = HexColor("#EF4444")
YELLOW_ALERT = HexColor("#F59E0B")
GREEN_OK     = HexColor("#10B981")


# =====================================================================
# ESTILOS TIPOGRÁFICOS
# =====================================================================

def crear_estilos():
    """Crea el diccionario de estilos de párrafo para el reporte."""
    styles = getSampleStyleSheet()

    estilos = {
        "titulo_portada": ParagraphStyle(
            "titulo_portada",
            fontName="Helvetica-Bold",
            fontSize=26,
            textColor=GOLD,
            alignment=TA_CENTER,
            spaceAfter=8,
            leading=32,
        ),
        "subtitulo_portada": ParagraphStyle(
            "subtitulo_portada",
            fontName="Helvetica",
            fontSize=13,
            textColor=WHITE,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=GOLD,
            spaceBefore=16,
            spaceAfter=8,
            borderPad=4,
        ),
        "body": ParagraphStyle(
            "body",
            fontName="Helvetica",
            fontSize=10,
            textColor=HexColor("#1A1A2E"),
            spaceAfter=4,
            leading=14,
            alignment=TA_JUSTIFY,
        ),
        "kpi_value": ParagraphStyle(
            "kpi_value",
            fontName="Helvetica-Bold",
            fontSize=24,
            textColor=NAVY_BLUE,
            alignment=TA_CENTER,
        ),
        "kpi_label": ParagraphStyle(
            "kpi_label",
            fontName="Helvetica",
            fontSize=9,
            textColor=MEDIUM_GRAY,
            alignment=TA_CENTER,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=WHITE,
            alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            fontName="Helvetica",
            fontSize=9,
            textColor=HexColor("#1A1A2E"),
            alignment=TA_LEFT,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontName="Helvetica",
            fontSize=8,
            textColor=MEDIUM_GRAY,
            alignment=TA_CENTER,
        ),
    }
    return estilos


# =====================================================================
# ELEMENTOS VISUALES PERSONALIZADOS
# =====================================================================

class BannerHeader(Flowable):
    """Banner de encabezado azul marino con texto dorado."""
    def __init__(self, titulo: str, subtitulo: str = "", width: float = None):
        super().__init__()
        self.titulo = titulo
        self.subtitulo = subtitulo
        self.width = width or (A4[0] - 3 * cm)
        self.height = 2.5 * cm

    def draw(self):
        # Fondo degradado simulado
        self.canv.setFillColor(NAVY_BLUE)
        self.canv.rect(0, 0, self.width, self.height, fill=1, stroke=0)
        # Borde dorado inferior
        self.canv.setStrokeColor(GOLD)
        self.canv.setLineWidth(2.5)
        self.canv.line(0, 0, self.width, 0)
        # Título
        self.canv.setFillColor(GOLD)
        self.canv.setFont("Helvetica-Bold", 14)
        self.canv.drawString(12, self.height - 20, self.titulo)
        # Subtítulo
        if self.subtitulo:
            self.canv.setFillColor(WHITE)
            self.canv.setFont("Helvetica", 9)
            self.canv.drawString(12, self.height - 34, self.subtitulo)


class KPICard(Flowable):
    """Tarjeta de KPI con valor grande y etiqueta."""
    def __init__(self, valor: str, etiqueta: str, color_fondo=LIGHT_GRAY, color_valor=NAVY_BLUE):
        super().__init__()
        self.valor = valor
        self.etiqueta = etiqueta
        self.color_fondo = color_fondo
        self.color_valor = color_valor
        self.width = 3.8 * cm
        self.height = 2.2 * cm

    def draw(self):
        self.canv.setFillColor(self.color_fondo)
        self.canv.roundRect(0, 0, self.width, self.height, 6, fill=1, stroke=0)
        self.canv.setFillColor(self.color_valor)
        self.canv.setFont("Helvetica-Bold", 18)
        self.canv.drawCentredString(self.width / 2, self.height - 22, self.valor)
        self.canv.setFillColor(MEDIUM_GRAY)
        self.canv.setFont("Helvetica", 7.5)
        self.canv.drawCentredString(self.width / 2, 5, self.etiqueta)


# =====================================================================
# GENERACIÓN DE SECCIONES
# =====================================================================

def _seccion_portada(estilos: dict, kpis: Dict, hotel_filtro: str, fecha_gen: str) -> list:
    """Genera los elementos de la portada del reporte."""
    nombre_hotel = "Complejo Bahía Príncipe (5 Hoteles)" if hotel_filtro == "ALL" else f"Hotel {hotel_filtro}"

    elementos = []
    elementos.append(Spacer(1, 3 * cm))
    elementos.append(Paragraph("BAHÍA PRÍNCIPE", estilos["titulo_portada"]))
    elementos.append(Paragraph("Hotels & Resorts", estilos["subtitulo_portada"]))
    elementos.append(Spacer(1, 0.5 * cm))
    elementos.append(HRFlowable(width="100%", thickness=1.5, color=GOLD))
    elementos.append(Spacer(1, 0.4 * cm))
    elementos.append(Paragraph("REPORTE EJECUTIVO OPERATIVO", estilos["subtitulo_portada"]))
    elementos.append(Paragraph("Restaurantes de Especialidad — Alimentos & Bebidas", estilos["subtitulo_portada"]))
    elementos.append(Spacer(1, 0.6 * cm))
    elementos.append(Paragraph(f"📍 {nombre_hotel}", estilos["subtitulo_portada"]))
    elementos.append(Paragraph(f"📅 Generado: {fecha_gen}", estilos["subtitulo_portada"]))
    elementos.append(Paragraph(f"🗓️ Periodo: {kpis.get('fecha_inicio', '')} al {kpis.get('fecha_fin', '')}", estilos["subtitulo_portada"]))
    elementos.append(Spacer(1, 5 * cm))
    elementos.append(Paragraph("Documento Confidencial · Uso Exclusivo de Dirección General A&B", estilos["footer"]))
    elementos.append(PageBreak())
    return elementos


def _seccion_kpis(estilos: dict, kpis: Dict) -> list:
    """Genera la sección de tarjetas de KPIs."""
    elementos = []
    elementos.append(BannerHeader("1. INDICADORES CLAVE DE OPERACIÓN (KPIs)", "Últimos 30 días del complejo"))
    elementos.append(Spacer(1, 0.4 * cm))

    # Tabla de KPIs (2 filas de 4 tarjetas)
    def kpi_fila(items):
        row = []
        for val, lbl, color in items:
            data = [
                [Paragraph(f"<b>{val}</b>", estilos["kpi_value"])],
                [Paragraph(lbl, estilos["kpi_label"])],
            ]
            t = Table(data, colWidths=[3.8 * cm], rowHeights=[1.5 * cm, 0.6 * cm])
            t.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), color),
                ("ROUNDEDCORNERS", (0, 0), (-1, -1), 6),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.5, HexColor("#D0D0D0")),
            ]))
            row.append(t)
        return row

    fila1 = kpi_fila([
        (f"{kpis.get('total_reservas', 0):,}", "TOTAL RESERVAS", LIGHT_GRAY),
        (f"{kpis.get('total_pax', 0):,}", "COMENSALES (PAX)", LIGHT_GRAY),
        (f"{kpis.get('total_adultos', 0):,}", "ADULTOS", LIGHT_GRAY),
        (f"{kpis.get('total_ninos', 0) + kpis.get('total_bebes', 0):,}", "NIÑOS + BEBÉS", LIGHT_GRAY),
    ])
    fila2 = kpi_fila([
        (f"{kpis.get('promedio_pax_por_reserva', 0)}", "PROM. PAX/MESA", LIGHT_GRAY),
        (f"{kpis.get('pct_cross_dining', 0)}%", "TASA CROSS-DINING", LIGHT_GRAY),
        (f"{kpis.get('reservas_vip', 0):,}", "RESERVAS VIP/FIDEL.", HexColor("#FFF8EC")),
        (f"{kpis.get('reservas_requieren_periquera', 0):,}", "PERIQUERAS REQ.", HexColor("#FFF0F0")),
    ])

    outer_table = Table(
        [fila1, [Spacer(1, 0.3 * cm)] * 4, fila2],
        colWidths=[4.0 * cm] * 4,
        rowHeights=[2.2 * cm, 0.3 * cm, 2.2 * cm],
    )
    outer_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    elementos.append(outer_table)
    elementos.append(Spacer(1, 0.5 * cm))
    return elementos


def _seccion_ocupacion(estilos: dict, ocupacion_data: Dict) -> list:
    """Genera la sección de semáforo de ocupación por restaurante."""
    elementos = []
    elementos.append(BannerHeader("2. SEMÁFORO DE OCUPACIÓN — RESTAURANTES DE ESPECIALIDAD", "Últimos 7 días"))
    elementos.append(Spacer(1, 0.3 * cm))

    restaurantes = ocupacion_data.get("restaurantes", [])
    if not restaurantes:
        elementos.append(Paragraph("No se encontraron datos de ocupación.", estilos["body"]))
        return elementos

    headers = [
        Paragraph("Restaurante", estilos["table_header"]),
        Paragraph("Pax (7 días)", estilos["table_header"]),
        Paragraph("Capacidad", estilos["table_header"]),
        Paragraph("Ocupación %", estilos["table_header"]),
        Paragraph("Estado", estilos["table_header"]),
    ]
    data = [headers]

    for r in restaurantes:
        pct = r["pct_ocupacion"]
        semaforo = r["semaforo"]
        emoji = "🟢 NORMAL" if semaforo == "verde" else ("🟡 ALTA" if semaforo == "amarillo" else "🔴 SATURADO")
        color_fondo_fila = HexColor("#F0FFF4") if semaforo == "verde" else (HexColor("#FFFBEB") if semaforo == "amarillo" else HexColor("#FEF2F2"))
        data.append([
            Paragraph(r["restaurante"][:28], estilos["table_cell"]),
            Paragraph(f"{r['pax_total']:,}", estilos["table_cell"]),
            Paragraph(f"{r['capacidad']:,}", estilos["table_cell"]),
            Paragraph(f"<b>{pct}%</b>", estilos["table_cell"]),
            Paragraph(emoji, estilos["table_cell"]),
        ])

    table = Table(data, colWidths=[5.5 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm, 3.0 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#D0D0D0")),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWHEIGHT", (0, 0), (-1, -1), 22),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    elementos.append(table)
    elementos.append(Spacer(1, 0.5 * cm))
    return elementos


def _seccion_cross_dining(estilos: dict, cross_data: Dict, kpis: Dict) -> list:
    """Genera la sección de análisis de Cross-Dining."""
    elementos = []
    elementos.append(BannerHeader("3. ANÁLISIS CROSS-DINING — FLUJO INTER-HOTEL", "Huéspedes que cenan fuera de su hotel de hospedaje"))
    elementos.append(Spacer(1, 0.3 * cm))

    pct_cross = kpis.get("pct_cross_dining", 0)
    total_cross = kpis.get("total_cross_dining", 0)
    total_res = kpis.get("total_reservas", 0)

    elementos.append(Paragraph(
        f"En el periodo analizado, el <b>{pct_cross}%</b> de los comensales "
        f"({total_cross:,} de {total_res:,} reservas) cenaron en un restaurante ubicado "
        f"en un hotel diferente al de su hospedaje dentro del complejo.",
        estilos["body"]
    ))
    elementos.append(Spacer(1, 0.3 * cm))

    hoteles = cross_data.get("hoteles", [])
    pax_cross = cross_data.get("pax_cross", [])
    if hoteles:
        data = [[
            Paragraph("Hotel Hospedaje", estilos["table_header"]),
            Paragraph("Pax Cross-Dining", estilos["table_header"]),
            Paragraph("% del Total Cross", estilos["table_header"]),
        ]]
        total_pax_cross = sum(pax_cross) or 1
        for h, p in sorted(zip(hoteles, pax_cross), key=lambda x: x[1], reverse=True):
            pct = round((p / total_pax_cross) * 100, 1)
            data.append([
                Paragraph(h, estilos["table_cell"]),
                Paragraph(f"{p:,}", estilos["table_cell"]),
                Paragraph(f"{pct}%", estilos["table_cell"]),
            ])

        t = Table(data, colWidths=[6 * cm, 4 * cm, 4 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DARK_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#D0D0D0")),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWHEIGHT", (0, 0), (-1, -1), 20),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
        ]))
        elementos.append(t)

    elementos.append(Spacer(1, 0.5 * cm))
    return elementos


def _seccion_pie_firma(estilos: dict, usuario_nombre: str, fecha_gen: str) -> list:
    """Genera el pie de página con firma electrónica."""
    elementos = []
    elementos.append(Spacer(1, 1 * cm))
    elementos.append(HRFlowable(width="100%", thickness=1, color=GOLD))
    elementos.append(Spacer(1, 0.4 * cm))
    elementos.append(Paragraph(
        f"Reporte generado electrónicamente el <b>{fecha_gen}</b> por <b>{usuario_nombre}</b> · "
        f"Documento de uso interno y confidencial · Bahía Príncipe Hotels & Resorts ©",
        estilos["footer"]
    ))
    return elementos


# =====================================================================
# FUNCIÓN PRINCIPAL DE GENERACIÓN
# =====================================================================

def generar_reporte_pdf(
    kpis: Dict[str, Any],
    ocupacion_data: Dict[str, Any],
    cross_data: Dict[str, Any],
    hotel_filtro: str = "ALL",
    usuario_nombre: str = "Director General A&B",
) -> bytes:
    """
    Genera el reporte ejecutivo PDF completo y retorna el contenido como bytes.
    Listo para ser descargado por la app móvil mediante streaming HTTP.
    """
    buffer = io.BytesIO()
    fecha_gen = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title="Reporte Ejecutivo Bahía Príncipe A&B",
        author="Sistema BI Bahía Príncipe",
        subject="Restaurantes de Especialidad",
    )

    estilos = crear_estilos()
    elementos = []

    # 1. Portada
    elementos.extend(_seccion_portada(estilos, kpis, hotel_filtro, fecha_gen))

    # 2. KPIs
    elementos.extend(_seccion_kpis(estilos, kpis))

    # 3. Ocupación
    elementos.extend(_seccion_ocupacion(estilos, ocupacion_data))

    # 4. Cross-Dining
    elementos.extend(_seccion_cross_dining(estilos, cross_data, kpis))

    # 5. Firma y pie de página
    elementos.extend(_seccion_pie_firma(estilos, usuario_nombre, fecha_gen))

    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()
