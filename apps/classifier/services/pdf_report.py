# -*- coding: utf-8 -*-
"""
Generador de Reportes PDF Académicos para MangoLeaf-AI
Utiliza ReportLab para construir un informe técnico profesional y limpio.
"""

import io
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, KeepTogether, HRFlowable
)
from reportlab.lib.units import inch

def generate_analysis_pdf(record, request=None) -> bytes:
    """
    Genera el archivo PDF binario para un registro de análisis.
    `record` es una instancia de AnalysisRecord o dict equivalente.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    story = []
    styles = getSampleStyleSheet()

    # Colores institucionales
    PRIMARY_COLOR = colors.HexColor("#065f46")  # Verde bosque oscuro
    ACCENT_COLOR = colors.HexColor("#059669")   # Verde esmeralda
    LIGHT_BG = colors.HexColor("#f0fdf4")       # Verde menta muy claro
    DARK_TEXT = colors.HexColor("#0f172a")      # Slate 900
    MUTED_TEXT = colors.HexColor("#475569")     # Slate 600
    BORDER_COLOR = colors.HexColor("#cbd5e1")

    # Estilos de párrafos personalizados
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=PRIMARY_COLOR
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=MUTED_TEXT
    )
    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=PRIMARY_COLOR,
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=DARK_TEXT
    )
    badge_style = ParagraphStyle(
        'BadgeText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.white,
        alignment=1  # Centrado
    )

    # 1. ENCABEZADO INSTITUCIONAL
    header_data = [
        [
            Paragraph("<b>MangoLeaf-AI</b> &bull; Sistema Inteligente Fitosanitario", title_style),
            Paragraph(f"<b>Fecha:</b> {record.created_at.strftime('%d/%m/%Y %H:%M')}<br/><b>ID:</b> #{record.id}", subtitle_style)
        ]
    ]
    header_table = Table(header_data, colWidths=[380, 160])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 4))

    # Tesis subtítulo
    story.append(Paragraph(
        "Tesis: <i>Modelo híbrido de visión computacional para la clasificación automática de enfermedades en hojas de mango usando aprendizaje profundo</i>",
        subtitle_style
    ))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT_COLOR, spaceAfter=12))

    # 2. RESULTADO DESTACADO
    is_healthy = record.is_healthy
    badge_bg = colors.HexColor("#059669") if is_healthy else colors.HexColor("#dc2626")
    badge_text = f"DIAGNÓSTICO: {record.predicted_class_es.upper()} ({record.confidence_pct}%)"

    result_box_data = [
        [Paragraph(badge_text, badge_style)],
        [Paragraph(f"<b>Categoría internacional:</b> {record.predicted_class} | <b>Modelo:</b> {record.model_version} | <b>Tiempo de inferencia:</b> {record.inference_time_ms} ms", ParagraphStyle('ResSub', parent=body_style, alignment=1, textColor=MUTED_TEXT, fontSize=8))]
    ]
    result_box = Table(result_box_data, colWidths=[540])
    result_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), badge_bg),
        ('BACKGROUND', (0, 1), (0, 1), LIGHT_BG),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOX', (0, 0), (-1, -1), 1, BORDER_COLOR),
    ]))
    story.append(result_box)
    story.append(Spacer(1, 14))

    # 3. DETALLE VISUAL Y METADATOS TÉCNICOS
    # Preparar imagen si existe
    img_element = None
    if record.image:
        try:
            img_path = Path(record.image.path)
            if img_path.exists():
                img_element = RLImage(str(img_path), width=2.4*inch, height=2.4*inch)
        except Exception:
            img_element = None

    from apps.classifier.services.inference import CATEGORY_METADATA
    cat_meta = CATEGORY_METADATA.get(record.predicted_class, {})

    desc_paragraphs = [
        Paragraph(f"<b>Patógeno / Agente causal:</b> {cat_meta.get('agente', 'N/A')}", body_style),
        Spacer(1, 3),
        Paragraph(f"<b>Nivel de severidad típica:</b> {cat_meta.get('gravedad', 'N/A')}", body_style),
        Spacer(1, 4),
        Paragraph(f"<b>Descripción fitopatológica:</b> {cat_meta.get('descripcion', '')}", body_style),
        Spacer(1, 4),
        Paragraph(f"<b>Sintomatología foliar:</b> {cat_meta.get('sintomas', '')}", body_style),
    ]

    if img_element:
        split_table_data = [
            [img_element, desc_paragraphs]
        ]
        split_table = Table(split_table_data, colWidths=[180, 360])
        split_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(split_table)
    else:
        for p in desc_paragraphs:
            story.append(p)

    story.append(Spacer(1, 12))

    # 4. TABLA DE DISTRIBUCIÓN DE PUNTUACIONES
    story.append(Paragraph("Distribución de Probabilidades por Categoría", h2_style))

    table_rows = [
        [
            Paragraph("<b>#</b>", body_style),
            Paragraph("<b>Categoría (Español)</b>", body_style),
            Paragraph("<b>Clase Original</b>", body_style),
            Paragraph("<b>Puntuación Estimada</b>", body_style),
            Paragraph("<b>Porcentaje</b>", body_style),
        ]
    ]

    probs_dict = record.probabilities_dict
    for idx, (c_en, p_val) in enumerate(probs_dict.items(), start=1):
        c_es = CATEGORY_METADATA.get(c_en, {}).get('nombre_es', c_en)
        pct = round(p_val * 100, 2)
        is_win = (c_en == record.predicted_class)
        row_style = ParagraphStyle('WinR', parent=body_style, fontName='Helvetica-Bold' if is_win else 'Helvetica', textColor=PRIMARY_COLOR if is_win else DARK_TEXT)

        marker = " &#9658; " if is_win else ""
        table_rows.append([
            Paragraph(f"{idx}", row_style),
            Paragraph(f"{marker}{c_es}", row_style),
            Paragraph(f"{c_en}", row_style),
            Paragraph(f"{p_val:.6f}", row_style),
            Paragraph(f"<b>{pct:.2f}%</b>", row_style),
        ])

    prob_table = Table(table_rows, colWidths=[24, 170, 150, 106, 90])
    prob_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 3.5),
        ('ALIGN', (3, 1), (-1, -1), 'RIGHT'),
    ]))
    story.append(prob_table)
    story.append(Spacer(1, 10))

    # 5. RECOMENDACIONES FITOSANITARIAS
    recs = cat_meta.get('recomendaciones', [])
    if recs:
        story.append(Paragraph("Pautas de Manejo Cultural y Preventivo", h2_style))
        for r in recs:
            story.append(Paragraph(f"&bull; {r}", body_style))
            story.append(Spacer(1, 2))

    story.append(Spacer(1, 10))

    # 6. ADVERTENCIA LEGAL Y ACADÉMICA
    disclaimer_text = (
        "<b>ADVERTENCIA ACADÉMICA:</b> Este reporte es generado de forma automatizada mediante un modelo de "
        "aprendizaje profundo (EfficientNet-B0 + SVM) con fines estrictamente académicos e investigativos. "
        "No sustituye la evaluación fitopatológica directa de un ingeniero agrónomo colegiado o especialista fitosanitario."
    )
    disc_table = Table([[Paragraph(disclaimer_text, ParagraphStyle('Disc', parent=body_style, fontSize=7.5, leading=10, textColor=MUTED_TEXT))]], colWidths=[540])
    disc_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(disc_table)

    doc.build(story)
    pdf_content = buffer.getvalue()
    buffer.close()
    return pdf_content
