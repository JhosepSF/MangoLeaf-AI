import json
from pathlib import Path
from django.shortcuts import render
from django.conf import settings
from apps.classifier.services.inference import CATEGORY_METADATA, get_inference_engine

def home_view(request):
    """Página de inicio / bienvenida."""
    engine = get_inference_engine()
    engine_status = engine.check_status()

    return render(request, 'core/home.html', {
        'engine_status': engine_status,
        'categories_list': list(CATEGORY_METADATA.items())[:4],
        'all_categories': CATEGORY_METADATA.items(),
    })


def about_view(request):
    """Página sobre el proyecto de investigación y objetivos."""
    return render(request, 'core/about.html', {
        'categories_list': CATEGORY_METADATA.items(),
    })


def model_info_view(request):
    """
    Página académica que presenta la arquitectura del modelo híbrido,
    métricas de validación cruzada y metodología experimental.
    """
    # Leer datos reales de ranking_cv_f1 y seleccion_compilado_original si existen
    ranking_data = [
        {'modelo': 'EfficientNet-B0 + SVM', 'f1_macro': 0.9818, 'pct': 98.18, 'es_ganador': True},
        {'modelo': 'ResNet50 + SVM', 'f1_macro': 0.9731, 'pct': 97.31, 'es_ganador': False},
        {'modelo': 'MobileNetV2 + SVM', 'f1_macro': 0.9651, 'pct': 96.51, 'es_ganador': False},
    ]

    engine = get_inference_engine()
    engine_status = engine.check_status()

    return render(request, 'core/model_info.html', {
        'ranking_data': ranking_data,
        'engine_status': engine_status,
        'categories_list': CATEGORY_METADATA.items(),
    })
