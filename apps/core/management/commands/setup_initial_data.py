from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from apps.classifier.services.inference import predict_mango_leaf
from apps.classifier.models import AnalysisRecord
from django.conf import settings
from django.core.files.base import ContentFile
from pathlib import Path

class Command(BaseCommand):
    help = 'Crea usuarios de prueba y ejecuta inferencia sobre muestras de test iniciales'

    def handle(self, *args, **options):
        # 1. Crear Superusuario admin
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@mangoleaf.ai',
                password='adminpassword123',
                first_name='Administrador',
                last_name='Sistema'
            )
            self.stdout.write(self.style.SUCCESS("Superusuario 'admin' creado con contraseña 'adminpassword123'"))
        else:
            admin_user = User.objects.get(username='admin')

        # 2. Crear usuario Investigador
        if not User.objects.filter(username='investigador').exists():
            investigador = User.objects.create_user(
                username='investigador',
                email='investigador@mangoleaf.ai',
                password='investigador123',
                first_name='Camila',
                last_name='Vargas'
            )
            self.stdout.write(self.style.SUCCESS("Usuario 'investigador' creado con contraseña 'investigador123'"))
        else:
            investigador = User.objects.get(username='investigador')

        # 3. Analizar prueba_01.jpg si aún no hay registros
        if AnalysisRecord.objects.count() == 0:
            test_dir = getattr(settings, 'TEST_PHOTOS_DIR', settings.BASE_DIR / 'EfficientNetB0_SVM' / 'fotos_test')
            p1 = Path(test_dir) / 'prueba_01.jpg'
            p2 = Path(test_dir) / 'prueba_02.jpg'

            for p in (p1, p2):
                if p.exists():
                    res = predict_mango_leaf(p)
                    with open(p, 'rb') as f:
                        data = f.read()
                    rec = AnalysisRecord(
                        user=investigador,
                        original_filename=p.name,
                        predicted_class=res['predicted_class'],
                        predicted_class_es=res['predicted_class_es'],
                        confidence=res['confidence'],
                        confidence_pct=res['confidence_pct'],
                        is_healthy=res['is_healthy'],
                        probabilities_json=res['probabilities'],
                        inference_time_ms=res['inference_time_ms'],
                        model_version=res['model_info']['name'],
                        notes=f"Registro semilla de validación experimental ({p.name})"
                    )
                    rec.image.save(p.name, ContentFile(data), save=True)
                    self.stdout.write(self.style.SUCCESS(f"Registro generado para {p.name}: {res['predicted_class_es']} ({res['confidence_pct']}%)"))

        self.stdout.write(self.style.SUCCESS("Setup inicial finalizado con éxito."))
