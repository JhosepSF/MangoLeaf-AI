from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Avg, Count, Q
from apps.classifier.models import AnalysisRecord
from apps.classifier.services.inference import CATEGORY_METADATA

@login_required
def history_list_view(request):
    """
    Vista de historial protegida: cada usuario visualiza exclusivamente sus registros.
    Incluye búsqueda, filtrado por patología, métricas resumen y paginación.
    """
    queryset = AnalysisRecord.objects.filter(user=request.user)

    # Filtro por búsqueda de texto
    search_query = request.GET.get('q', '').strip()
    if search_query:
        queryset = queryset.filter(
            Q(original_filename__icontains=search_query) |
            Q(predicted_class_es__icontains=search_query) |
            Q(predicted_class__icontains=search_query) |
            Q(notes__icontains=search_query)
        )

    # Filtro por categoría fitosanitaria
    category_filter = request.GET.get('category', '').strip()
    if category_filter:
        queryset = queryset.filter(predicted_class=category_filter)

    # Filtro por estado de salud
    health_filter = request.GET.get('health', '').strip()
    if health_filter == 'healthy':
        queryset = queryset.filter(is_healthy=True)
    elif health_filter == 'disease':
        queryset = queryset.filter(is_healthy=False)

    # Métricas agregadas del usuario
    user_records = AnalysisRecord.objects.filter(user=request.user)
    total_count = user_records.count()
    healthy_count = user_records.filter(is_healthy=True).count()
    disease_count = user_records.filter(is_healthy=False).count()
    avg_conf = user_records.aggregate(Avg('confidence_pct'))['confidence_pct__avg'] or 0.0

    # Paginación (8 por página)
    paginator = Paginator(queryset, 8)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'history/history_list.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'category_filter': category_filter,
        'health_filter': health_filter,
        'total_count': total_count,
        'healthy_count': healthy_count,
        'disease_count': disease_count,
        'avg_conf': round(avg_conf, 1),
        'categories_list': CATEGORY_METADATA.items(),
    })


@login_required
def history_delete_view(request, record_id):
    """
    Elimina un registro perteneciente al usuario autenticado.
    """
    record = get_object_or_404(AnalysisRecord, id=record_id, user=request.user)
    if request.method == "POST":
        # Eliminar archivo físico de la imagen si se desea
        try:
            if record.image:
                record.image.delete(save=False)
        except Exception:
            pass
        record.delete()
        messages.success(request, f"Registro #{record_id} eliminado exitosamente.")
    return redirect('history:history_list')
