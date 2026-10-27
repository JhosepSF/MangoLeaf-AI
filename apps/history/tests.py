from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from apps.classifier.models import AnalysisRecord

class HistorySecurityAndFilterTests(TestCase):
    """Pruebas de seguridad, aislamiento de usuarios y filtros del historial."""

    def setUp(self):
        self.client = Client()
        self.user_a = User.objects.create_user(username='agronomo_a', password='passA123')
        self.user_b = User.objects.create_user(username='agronomo_b', password='passB123')

        # Registros de usuario A
        self.rec_a1 = AnalysisRecord.objects.create(
            user=self.user_a,
            original_filename="hoja_a1.jpg",
            predicted_class="Anthracnose",
            predicted_class_es="Antracnosis",
            confidence=0.95,
            confidence_pct=95.0,
            is_healthy=False,
            probabilities_json={"Anthracnose": 0.95}
        )
        self.rec_a2 = AnalysisRecord.objects.create(
            user=self.user_a,
            original_filename="hoja_a2_sana.jpg",
            predicted_class="Healthy",
            predicted_class_es="Hoja sana",
            confidence=0.98,
            confidence_pct=98.0,
            is_healthy=True,
            probabilities_json={"Healthy": 0.98}
        )

        # Registro de usuario B
        self.rec_b1 = AnalysisRecord.objects.create(
            user=self.user_b,
            original_filename="hoja_b1.jpg",
            predicted_class="Powdery Mildew",
            predicted_class_es="Oídio",
            confidence=0.92,
            confidence_pct=92.0,
            is_healthy=False,
            probabilities_json={"Powdery Mildew": 0.92}
        )

    def test_history_requires_authentication(self):
        """El acceso no autenticado a /historial/ debe redirigir al login."""
        response = self.client.get(reverse('history:history_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/cuenta/login/', response.url)

    def test_user_only_sees_own_records(self):
        """El usuario A solo debe visualizar sus propios registros, nunca los de B."""
        self.client.login(username='agronomo_a', password='passA123')
        response = self.client.get(reverse('history:history_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "hoja_a1.jpg")
        self.assertContains(response, "hoja_a2_sana.jpg")
        self.assertNotContains(response, "hoja_b1.jpg")

    def test_history_filtering_by_health(self):
        """Filtro por estado de salud foliar (healthy vs disease)."""
        self.client.login(username='agronomo_a', password='passA123')
        response = self.client.get(reverse('history:history_list') + '?health=healthy')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "hoja_a2_sana.jpg")
        self.assertNotContains(response, "hoja_a1.jpg")

    def test_user_cannot_access_or_download_other_user_detail(self):
        """El usuario B no debe tener acceso a ver detalles de registros de usuario A."""
        self.client.login(username='agronomo_b', password='passB123')
        # Intentar ver resultado de usuario A
        response = self.client.get(reverse('classifier:result_detail', kwargs={'record_id': self.rec_a1.id}))
        self.assertEqual(response.status_code, 302)  # Redirige a historial con advertencia
