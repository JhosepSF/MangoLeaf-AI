import os
from pathlib import Path
from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.conf import settings
from PIL import Image
import io

from apps.classifier.models import AnalysisRecord
from apps.classifier.services.inference import (
    get_inference_engine,
    predict_mango_leaf,
    CATEGORY_METADATA
)
from apps.classifier.services.pdf_report import generate_analysis_pdf


class ModelInferenceTests(TestCase):
    """Pruebas técnicas del motor de inferencia híbrido EfficientNet-B0 + SVM."""

    def setUp(self):
        self.engine = get_inference_engine()
        self.test_dir = getattr(settings, 'TEST_PHOTOS_DIR', settings.BASE_DIR / 'EfficientNetB0_SVM' / 'fotos_test')

    def test_01_engine_is_configured_and_ready(self):
        """Verifica que el extractor Keras y el clasificador SVM se cargaron correctamente."""
        status = self.engine.check_status()
        self.assertTrue(status['is_ready'], f"El motor no está listo: {status.get('error')}")
        self.assertEqual(status['feature_dim'], 1280)
        self.assertEqual(len(status['classes']), 8)
        self.assertEqual(len(status['labels_es']), 8)

    def test_02_end_to_end_inference_prueba_01(self):
        """
        Prueba de inferencia de extremo a extremo con prueba_01.jpg
        Compara la salida con el benchmark de Colab (Anthracnose, certeza > 99%).
        """
        img_path = Path(self.test_dir) / 'prueba_01.jpg'
        self.assertTrue(img_path.exists(), f"Falta imagen de prueba {img_path}")

        result = self.engine.predict(img_path)
        self.assertEqual(result['predicted_class'], 'Anthracnose')
        self.assertEqual(result['predicted_class_es'], 'Antracnosis')
        self.assertGreater(result['confidence'], 0.99)
        self.assertFalse(result['is_healthy'])
        self.assertEqual(len(result['probabilities']), 8)

    def test_03_end_to_end_inference_prueba_02(self):
        """
        Prueba de inferencia de extremo a extremo con prueba_02.jpg
        Compara la salida con el benchmark de Colab (Powdery Mildew / Oídio, certeza > 98%).
        """
        img_path = Path(self.test_dir) / 'prueba_02.jpg'
        self.assertTrue(img_path.exists(), f"Falta imagen de prueba {img_path}")

        result = self.engine.predict(img_path)
        self.assertEqual(result['predicted_class'], 'Powdery Mildew')
        self.assertEqual(result['predicted_class_es'], 'Oídio')
        self.assertGreater(result['confidence'], 0.98)
        self.assertFalse(result['is_healthy'])

    def test_04_category_metadata_completeness(self):
        """Verifica que las 8 categorías cuenten con descripciones y recomendaciones fitosanitarias."""
        classes = self.engine.config['classes']
        self.assertEqual(len(classes), 8)
        for c in classes:
            self.assertIn(c, CATEGORY_METADATA)
            meta = CATEGORY_METADATA[c]
            self.assertTrue(len(meta['nombre_es']) > 0)
            self.assertTrue(len(meta['descripcion']) > 0)
            self.assertTrue(len(meta['recomendaciones']) > 0)


class ClassifierViewTests(TestCase):
    """Pruebas de vistas, validación de carga y rechazo de archivos inválidos."""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.test_dir = getattr(settings, 'TEST_PHOTOS_DIR', settings.BASE_DIR / 'EfficientNetB0_SVM' / 'fotos_test')

    def test_analyze_page_get(self):
        """Verifica que la página de análisis responda 200 con el formulario."""
        response = self.client.get(reverse('classifier:analyze'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Clasificador de Hojas de Mango")

    def test_reject_invalid_file_extension(self):
        """Rechaza archivos con extensiones no permitidas (.txt, .pdf, etc.)."""
        fake_file = SimpleUploadedFile("documento.txt", b"Contenido de texto plano", content_type="text/plain")
        response = self.client.post(reverse('classifier:analyze'), {'image': fake_file}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Formato no permitido")

    def test_reject_corrupted_image(self):
        """Rechaza archivos con extensión .jpg pero contenido corrupto o simulado."""
        corrupted_file = SimpleUploadedFile("virus.jpg", b"NO ES UN JPEG REAL", content_type="image/jpeg")
        response = self.client.post(reverse('classifier:analyze'), {'image': corrupted_file}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no es una imagen válida")

    def test_valid_image_upload_and_record_creation(self):
        """Sube una imagen JPEG válida generada programáticamente y verifica registro en DB."""
        file_obj = io.BytesIO()
        test_img = Image.new('RGB', (224, 224), color=(34, 139, 34))
        test_img.save(file_obj, format='JPEG')
        file_obj.seek(0)

        uploaded = SimpleUploadedFile("leaf_test.jpg", file_obj.read(), content_type="image/jpeg")
        self.client.login(username='testuser', password='password123')
        response = self.client.post(reverse('classifier:analyze'), {'image': uploaded})

        self.assertEqual(response.status_code, 302)
        record = AnalysisRecord.objects.filter(original_filename='leaf_test.jpg').first()
        self.assertIsNotNone(record)
        self.assertEqual(record.user, self.user)
        self.assertTrue(len(record.predicted_class) > 0)
        self.assertTrue(0.0 <= record.confidence <= 1.0)

    def test_pdf_report_generation(self):
        """Verifica la generación del PDF técnico para un registro."""
        record = AnalysisRecord.objects.create(
            user=self.user,
            original_filename="hoja_prueba.jpg",
            predicted_class="Anthracnose",
            predicted_class_es="Antracnosis",
            confidence=0.9992,
            confidence_pct=99.92,
            is_healthy=False,
            probabilities_json={"Anthracnose": 0.9992, "Healthy": 0.0001},
            inference_time_ms=85.0
        )
        pdf_bytes = generate_analysis_pdf(record)
        self.assertTrue(pdf_bytes.startswith(b'%PDF'))
        self.assertGreater(len(pdf_bytes), 1000)

        # Probar endpoint de descarga HTTP
        response = self.client.get(reverse('classifier:download_pdf', kwargs={'record_id': record.id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])
