import os
import json
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.core.files.base import ContentFile
from django.conf import settings
from PIL import Image

from .models import AnalysisRecord
from .services.inference import (
    get_inference_engine,
    predict_mango_leaf,
    ModelNotConfiguredError,
    CATEGORY_METADATA
)
from .services.pdf_report import generate_analysis_pdf


def _validate_image_file(uploaded_file):
    """
    Valida tamaño, extensión y formato interno real mediante Pillow.
    Retorna (es_valido, mensaje_error).
    """
    # 1. Validación de tamaño
    if uploaded_file.size > settings.MAX_UPLOAD_SIZE_BYTES:
        max_mb = settings.MAX_UPLOAD_SIZE_MB
        return False, f"El archivo excede el tamaño máximo permitido de {max_mb} MB."

    # 2. Validación de extensión permitida
    name = uploaded_file.name.lower()
    allowed_exts = ('.jpg', '.jpeg', '.png')
    if not any(name.endswith(ext) for ext in allowed_exts):
        return False, "Formato no permitido. Solo se aceptan archivos JPEG, JPG y PNG."

    # 3. Validación real de cabeceras de imagen
    try:
        uploaded_file.seek(0)
        with Image.open(uploaded_file) as img:
            img.verify()
        uploaded_file.seek(0)
    except Exception:
        return False, "El archivo proporcionado no es una imagen válida o está dañado."

    return True, None


@require_http_methods(["GET", "POST"])
def analyze_view(request):
    """
    Vista principal para cargar y analizar imágenes foliares.
    Soporta peticiones normales de formulario y llamadas AJAX (JSON).
    """
    engine = get_inference_engine()
    engine_status = engine.check_status()

    # Obtener imágenes de demostración existentes en fotos_test
    demo_photos = []
    test_dir = getattr(settings, 'TEST_PHOTOS_DIR', settings.BASE_DIR / 'EfficientNetB0_SVM' / 'fotos_test')
    if test_dir and Path(test_dir).exists():
        manifest_file = Path(test_dir) / 'manifest_test.json'
        manifest = {}
        if manifest_file.exists():
            try:
                raw_manifest = json.loads(manifest_file.read_text(encoding='utf-8'))
                if isinstance(raw_manifest, list):
                    manifest = {item.get('archivo'): item for item in raw_manifest if isinstance(item, dict)}
                elif isinstance(raw_manifest, dict):
                    manifest = raw_manifest
            except Exception:
                pass

        for p in Path(test_dir).glob('*.jpg'):
            demo_photos.append({
                'filename': p.name,
                'path': str(p),
                'info': manifest.get(p.name, {})
            })

    if request.method == "POST":
        if not engine_status['is_ready']:
            error_msg = engine_status.get('error') or "El modelo híbrido no está configurado."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=503)
            messages.error(request, error_msg)
            return render(request, 'classifier/analyze.html', {
                'engine_status': engine_status,
                'demo_photos': demo_photos
            })

        uploaded_file = request.FILES.get('image')
        if not uploaded_file:
            error_msg = "Por favor, seleccione o arrastre una imagen de hoja de mango para analizar."
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': error_msg}, status=400)
            messages.warning(request, error_msg)
            return render(request, 'classifier/analyze.html', {
                'engine_status': engine_status,
                'demo_photos': demo_photos
            })

        # Validar archivo
        is_valid, validation_error = _validate_image_file(uploaded_file)
        if not is_valid:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': validation_error}, status=400)
            messages.error(request, validation_error)
            return render(request, 'classifier/analyze.html', {
                'engine_status': engine_status,
                'demo_photos': demo_photos
            })

        # Ejecutar inferencia
        try:
            prediction_result = predict_mango_leaf(uploaded_file)
        except Exception as exc:
            err_text = f"Error durante la inferencia: {str(exc)}"
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': err_text}, status=500)
            messages.error(request, err_text)
            return render(request, 'classifier/analyze.html', {
                'engine_status': engine_status,
                'demo_photos': demo_photos
            })

        # Guardar registro en base de datos
        uploaded_file.seek(0)
        record = AnalysisRecord.objects.create(
            user=request.user if request.user.is_authenticated else None,
            image=uploaded_file,
            original_filename=uploaded_file.name,
            predicted_class=prediction_result['predicted_class'],
            predicted_class_es=prediction_result['predicted_class_es'],
            confidence=prediction_result['confidence'],
            confidence_pct=prediction_result['confidence_pct'],
            is_healthy=prediction_result['is_healthy'],
            probabilities_json=prediction_result['probabilities'],
            inference_time_ms=prediction_result['inference_time_ms'],
            model_version=prediction_result['model_info']['name']
        )

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'record_id': record.id,
                'redirect_url': f"/clasificador/resultado/{record.id}/"
            })

        return redirect('classifier:result_detail', record_id=record.id)

    return render(request, 'classifier/analyze.html', {
        'engine_status': engine_status,
        'demo_photos': demo_photos
    })


def analyze_demo_view(request, demo_name):
    """
    Permite probar rápidamente la inferencia sobre las imágenes de demostración
    originales de la tesis (prueba_01.jpg y prueba_02.jpg).
    """
    engine = get_inference_engine()
    if not engine.is_ready:
        messages.error(request, "El modelo no se encuentra listo para inferencia.")
        return redirect('classifier:analyze')

    test_dir = getattr(settings, 'TEST_PHOTOS_DIR', settings.BASE_DIR / 'EfficientNetB0_SVM' / 'fotos_test')
    target_path = Path(test_dir) / demo_name

    if not target_path.exists() or not target_path.is_file():
        messages.error(request, f"La imagen de prueba {demo_name} no existe.")
        return redirect('classifier:analyze')

    try:
        # Ejecutar inferencia
        prediction_result = predict_mango_leaf(target_path)

        # Crear registro guardando copia de la imagen
        with open(target_path, 'rb') as f:
            content = f.read()

        record = AnalysisRecord(
            user=request.user if request.user.is_authenticated else None,
            original_filename=demo_name,
            predicted_class=prediction_result['predicted_class'],
            predicted_class_es=prediction_result['predicted_class_es'],
            confidence=prediction_result['confidence'],
            confidence_pct=prediction_result['confidence_pct'],
            is_healthy=prediction_result['is_healthy'],
            probabilities_json=prediction_result['probabilities'],
            inference_time_ms=prediction_result['inference_time_ms'],
            model_version=prediction_result['model_info']['name'],
            notes=f"Análisis ejecutado sobre muestra de prueba oficial ({demo_name})"
        )
        record.image.save(demo_name, ContentFile(content), save=True)

        messages.success(request, f"Muestra {demo_name} analizada con éxito.")
        return redirect('classifier:result_detail', record_id=record.id)

    except Exception as exc:
        messages.error(request, f"Fallo al analizar la muestra de prueba: {str(exc)}")
        return redirect('classifier:analyze')


def result_detail_view(request, record_id):
    """
    Muestra los resultados detallados del análisis foliar:
    - Fotografía
    - Diagnóstico y confianza
    - Gráfico interactivo con las 8 puntuaciones
    - Ficha técnica de la patología y recomendaciones de manejo
    - Acciones para descargar PDF o nuevo análisis
    """
    record = get_object_or_404(AnalysisRecord, id=record_id)

    # Si el registro pertenece a un usuario autenticado y otro usuario intenta verlo
    if record.user and request.user.is_authenticated and record.user != request.user and not request.user.is_staff:
        messages.warning(request, "Solo puedes acceder a tus propios registros de análisis.")
        return redirect('history:history_list')

    category_info = CATEGORY_METADATA.get(record.predicted_class, {})

    # Preparar distribución de probabilidades para Chart.js y tabla
    probs = record.probabilities_dict
    chart_labels = []
    chart_data = []
    detailed_probabilities = []

    for class_en, prob_val in probs.items():
        info = CATEGORY_METADATA.get(class_en, {})
        class_es = info.get('nombre_es', class_en)
        pct = round(prob_val * 100, 2)
        is_winner = (class_en == record.predicted_class)

        chart_labels.append(class_es)
        chart_data.append(pct)
        detailed_probabilities.append({
            'class_en': class_en,
            'class_es': class_es,
            'probability': prob_val,
            'percentage': pct,
            'is_winner': is_winner,
            'color_badge': info.get('color_badge', 'secondary')
        })

    # Ordenar ranking descendente
    ranked_probabilities = sorted(detailed_probabilities, key=lambda x: x['probability'], reverse=True)

    return render(request, 'classifier/result.html', {
        'record': record,
        'category_info': category_info,
        'chart_labels_json': json.dumps(chart_labels),
        'chart_data_json': json.dumps(chart_data),
        'detailed_probabilities': detailed_probabilities,
        'ranked_probabilities': ranked_probabilities,
    })


def download_pdf_report_view(request, record_id):
    """
    Genera y descarga el reporte PDF técnico del resultado.
    """
    record = get_object_or_404(AnalysisRecord, id=record_id)

    # Protección de privacidad básica
    if record.user and request.user.is_authenticated and record.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Acceso denegado a este reporte.")

    try:
        pdf_bytes = generate_analysis_pdf(record, request=request)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        filename = f"reporte_mangoleaf_analisis_{record.id}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as exc:
        messages.error(request, f"Error al generar el reporte PDF: {str(exc)}")
        return redirect('classifier:result_detail', record_id=record.id)
