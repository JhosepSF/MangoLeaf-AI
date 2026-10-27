def global_settings(request):
    """
    Context processor para variables globales de MangoLeaf-AI.
    """
    from apps.classifier.services.inference import get_inference_engine
    try:
        engine = get_inference_engine()
        is_model_ready = engine.is_ready
    except Exception:
        is_model_ready = False

    return {
        'APP_NAME': 'MangoLeaf-AI',
        'APP_SLOGAN': 'Inteligencia artificial al servicio de la salud foliar del mango',
        'THESIS_TITLE': 'Modelo híbrido de visión computacional para la clasificación automática de enfermedades en hojas de mango usando aprendizaje profundo',
        'THESIS_AUTHOR': 'Camila Vargas',
        'IS_MODEL_READY': is_model_ready,
    }
