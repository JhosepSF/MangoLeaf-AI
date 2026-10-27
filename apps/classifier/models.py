from django.db import models
from django.contrib.auth.models import User
import json

class AnalysisRecord(models.Model):
    """
    Registro histórico de cada análisis foliar realizado en el sistema.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='leaf_analyses',
        help_text="Usuario propietario del análisis (opcional si es sesión anónima)."
    )
    image = models.ImageField(
        upload_to='leaf_analyses/%Y/%m/',
        help_text="Fotografía de la hoja analizada."
    )
    original_filename = models.CharField(
        max_length=255,
        default="hoja.jpg",
        help_text="Nombre original del archivo subido."
    )
    predicted_class = models.CharField(
        max_length=100,
        help_text="Nombre de la categoría en inglés (identificador del modelo)."
    )
    predicted_class_es = models.CharField(
        max_length=100,
        help_text="Nombre de la categoría en español."
    )
    confidence = models.FloatField(
        help_text="Puntuación estimada por el clasificador SVM (0.0 a 1.0)."
    )
    confidence_pct = models.FloatField(
        default=0.0,
        help_text="Puntuación expresada en porcentaje (0.0 a 100.0%)."
    )
    is_healthy = models.BooleanField(
        default=False,
        help_text="Indica si la clasificación corresponde a 'Healthy' (Hoja sana)."
    )
    probabilities_json = models.JSONField(
        default=dict,
        help_text="Distribución completa de puntuaciones para las 8 categorías."
    )
    inference_time_ms = models.FloatField(
        default=0.0,
        help_text="Tiempo de cómputo en milisegundos."
    )
    model_version = models.CharField(
        max_length=100,
        default="EfficientNet-B0 + SVM",
        help_text="Arquitectura del modelo clasificador utilizado."
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Anotaciones u observaciones adicionales del usuario."
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="Fecha y hora del análisis."
    )

    class Meta:
        verbose_name = "Registro de Análisis"
        verbose_name_plural = "Registros de Análisis"
        ordering = ['-created_at']

    def __str__(self):
        return f"Análisis #{self.id} - {self.predicted_class_es} ({self.confidence_pct:.1f}%) [{self.created_at.strftime('%Y-%m-%d %H:%M')}]"

    @property
    def probabilities_dict(self):
        """Retorna el diccionario de probabilidades deserializado."""
        if isinstance(self.probabilities_json, dict):
            return self.probabilities_json
        try:
            return json.loads(self.probabilities_json)
        except Exception:
            return {}
