# -*- coding: utf-8 -*-
"""
Servicio de Inferencia para MangoLeaf-AI
Modelo Híbrido: EfficientNet-B0 + SVM (F1-macro CV: 98.18%)
Tesis: 'Modelo híbrido de visión computacional para la clasificación automática
de enfermedades en hojas de mango usando aprendizaje profundo'
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional

import numpy as np
from PIL import Image, ImageOps
from django.conf import settings

logger = logging.getLogger('mangoleaf.inference')

# Metadatos agronómicos de las 8 categorías del estudio
CATEGORY_METADATA = {
    "Anthracnose": {
        "nombre_es": "Antracnosis",
        "agente": "Colletotrichum gloeosporioides (Hongo)",
        "gravedad": "Alta",
        "color_badge": "danger",
        "descripcion": "Enfermedad fúngica muy destructiva en el cultivo de mango. Afecta hojas, brotes tiernos, inflorescencias y frutos, provocando pérdidas considerables de rendimiento.",
        "sintomas": "Manchas necróticas de color marrón oscuro a negro, de bordes irregulares, que a menudo coalescen cubriendo grandes áreas foliares. En condiciones húmedas se aprecian masas de esporas rosáceas.",
        "recomendaciones": [
            "Poda sanitaria de ramas y brotes infectados para favorecer la aireación.",
            "Recolección y destrucción de restos vegetales caídos debajo de la copa.",
            "Aplicación preventiva de fungicidas a base de cobre antes de floración y durante brotes tiernos.",
            "Evitar el riego por aspersión que moje el follaje."
        ]
    },
    "Bacterial Canker": {
        "nombre_es": "Cancro bacteriano",
        "agente": "Xanthomonas citri pv. mangiferaeindicae (Bacteria)",
        "gravedad": "Alta",
        "color_badge": "danger",
        "descripcion": "Bacteriosis severa que afecta el tejido vascular y foliar del mango, transmitida por salpicaduras de lluvia, viento y herramientas no desinfectadas.",
        "sintomas": "Lesiones angulares delimitadas por las nervaduras foliares, inicialmente acuosas que evolucionan a pústulas necróticas marrones con halo clorótico amarillento pronunciado.",
        "recomendaciones": [
            "Establecer cortinas rompevientos para reducir lesiones mecánicas que facilitan la entrada bacteriana.",
            "Desinfección estricta de tijeras y herramientas de poda con alcohol o hipoclorito de sodio.",
            "Tratamientos a base de oxicloruro de cobre u óxido cuproso.",
            "Eliminación inmediata de material vegetal gravemente comprometido."
        ]
    },
    "Cutting Weevil": {
        "nombre_es": "Gorgojo del corte",
        "agente": "Deporaus marginatus (Insecto - Curculionidae)",
        "gravedad": "Media",
        "color_badge": "warning",
        "descripcion": "Plaga insectil cuyas hembras cortan las hojas tiernas de mango después de depositar sus huevos en la lámina foliar.",
        "sintomas": "Hojas tiernas cortadas transversalmente de forma limpia como si hubiesen sido cortadas con tijeras. Pérdida severa de follaje joven en periodos de brotación.",
        "recomendaciones": [
            "Monitoreo constante durante las etapas de flujo vegetativo o brotación tierna.",
            "Recolección manual y destrucción de hojas cortadas caídas al suelo para romper el ciclo biológico.",
            "Uso de trampas luminosas o cromotrópicas para captura de adultos.",
            "Aplicación selectiva de insecticidas biorracionales autorizados en focos detectados."
        ]
    },
    "Die Back": {
        "nombre_es": "Muerte regresiva",
        "agente": "Lasiodiplodia theobromae (Hongo endófito / patógeno oportunista)",
        "gravedad": "Muy Alta",
        "color_badge": "danger",
        "descripcion": "Enfermedad sistémica y vascular caracterizada por la desecación y muerte progresiva de ramas desde el ápice hacia la base.",
        "sintomas": "Decoloración y desecación de hojas que permanecen adheridas a las ramas secas. Muerte descendente de ramillas, agrietamiento de corteza y exudación de goma (gomosis).",
        "recomendaciones": [
            "Poda de ramas enfermas cortando de 5 a 10 cm en madera sana visible.",
            "Sellado inmediato de cortes de poda con pasta fúngica o pintura cicatrizante.",
            "Control del estrés hídrico y nutricional del árbol para fortalecer sus defensas.",
            "Manejo de insectos perforadores que sirven como vectores del patógeno."
        ]
    },
    "Gall Midge": {
        "nombre_es": "Mosquito de la agalla",
        "agente": "Procontarinia matteiana (Insecto - Cecidomyiidae)",
        "gravedad": "Media",
        "color_badge": "warning",
        "descripcion": "Díptero cuyas larvas inducen la formación de agallas o pequeñas protuberancias verrugosas en el tejido foliar del mango.",
        "sintomas": "Presencia de numerosas agallas cónicas o redondeadas similares a verrugas en el haz y envés de las hojas. En infestaciones severas causa amarilleamiento y caída prematura.",
        "recomendaciones": [
            "Fomentar la presencia de enemigos naturales parasitoides (e.g., Platygaster spp.).",
            "Poda de aclareo para permitir mayor entrada de radiación solar en el dosel.",
            "Labores de rastreo suave bajo la copa para exponer pupas presentes en el suelo.",
            "Aplicación de aceite agrícola o bioinsecticidas en picos de emergencia de adultos."
        ]
    },
    "Healthy": {
        "nombre_es": "Hoja sana",
        "agente": "Sin patología detectada",
        "gravedad": "Ninguna",
        "color_badge": "success",
        "descripcion": "La hoja presenta características fisiológicas normales, coloración verde homogénea, superficie lisa y ausencia de lesiones bióticas o daños mecánicos.",
        "sintomas": "Lámina foliar turgente, cutícula íntegra, venación uniforme y desarrollo foliar óptimo sin manchas ni deformaciones.",
        "recomendaciones": [
            "Mantener el plan de nutrición equilibrada acorde al ciclo fenológico del huerto.",
            "Continuar con el régimen de riego adecuado evitando excesos o estrés por sequía.",
            "Realizar monitoreos periódicos preventivos para detección temprana de plagas o patógenos.",
            "Preservar la biodiversidad y fauna benéfica en el agroecosistema."
        ]
    },
    "Powdery Mildew": {
        "nombre_es": "Oídio",
        "agente": "Oidium mangiferae / Erysiphe mangiferae (Hongo)",
        "gravedad": "Alta",
        "color_badge": "warning",
        "descripcion": "Enfermedad fúngica muy frecuente en climas secos con noches frías y rocío matutino. Afecta severamente el follaje joven y la floración.",
        "sintomas": "Aparición de un polvillo blanquecino o grisáceo pulverulento en la superficie de las hojas y panículas. Las hojas tiernas se enrollan, se distorsionan y se caen.",
        "recomendaciones": [
            "Monitorear la floración y brotación tierna bajo condiciones climáticas predisponentes.",
            "Aplicaciones preventivas de azufre elemental o fungicidas sistémicos específicos autorizados.",
            "Podas de aclareo para reducir el microclima húmedo y sombreado dentro del árbol.",
            "Eliminar inflorescencias fuertemente afectadas."
        ]
    },
    "Sooty Mould": {
        "nombre_es": "Fumagina",
        "agente": "Capnodium mangiferae / Meliola spp. (Complejo fúngico no parásito)",
        "gravedad": "Media",
        "color_badge": "secondary",
        "descripcion": "Hongo superficial no parásito que se desarrolla sobre las secreciones azucaradas (melaza) producidas por insectos chupadores (pulgones, cochinillas, mosca blanca).",
        "sintomas": "Capa o película de aspecto negro aterciopelado semejante al hollín sobre la superficie foliar. Reduce drásticamente la capacidad fotosintética de la hoja.",
        "recomendaciones": [
            "Controlar prioritariamente los insectos picadores-chupadores productores de melaza.",
            "Lavado de hojas con soluciones jabonosas potásicas agrícolas para desprender la costra fúngica.",
            "Aplicación de insecticidas ecológicos como aceite de neem para frenar plagas chupadoras.",
            "Favorecer la ventilación de la copa mediante podas estructurales."
        ]
    }
}


class ModelNotConfiguredError(Exception):
    """Excepción lanzada cuando los artefactos del modelo no se encuentran."""
    pass


class HybridInferenceEngine:
    """
    Motor singleton para inferencia de visión computacional con el modelo
    híbrido EfficientNet-B0 + SVM.
    Carga los pesos una sola vez en memoria de forma segura.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(HybridInferenceEngine, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self.extractor = None
            self.classifier = None
            self.config = None
            self.artifacts_dir = None
            self.is_ready = False
            self.error_message = None
            self._load_artifacts()
            self._initialized = True

    def _load_artifacts(self):
        """Busca y carga extractor.keras y svm_pipeline.joblib."""
        try:
            # Buscar directorio de artefactos configurado
            candidates = [
                getattr(settings, 'MODEL_ARTIFACTS_DIR', None),
                settings.BASE_DIR / 'EfficientNetB0_SVM' / 'artefactos',
                settings.BASE_DIR / 'artefactos',
            ]
            valid_dir = None
            for c in candidates:
                if c and Path(c).is_dir():
                    valid_dir = Path(c)
                    break

            if not valid_dir:
                self.error_message = "Directorio de artefactos no encontrado."
                logger.warning(self.error_message)
                return

            self.artifacts_dir = valid_dir
            config_file = valid_dir / 'config.json'
            if not config_file.exists():
                self.error_message = f"Archivo config.json no hallado en {valid_dir}"
                return

            with open(config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)

            extractor_path = valid_dir / self.config.get('extractor_file', 'extractor.keras')
            classifier_path = valid_dir / self.config.get('classifier_file', 'svm_pipeline.joblib')

            if not extractor_path.exists() or not classifier_path.exists():
                self.error_message = f"Faltan archivos del modelo (.keras o .joblib) en {valid_dir}"
                return

            logger.info("Cargando extractor EfficientNet-B0 desde %s...", extractor_path)
            import tensorflow as tf
            import joblib

            # Carga del extractor Keras sin compilación (solo inferencia)
            self.extractor = tf.keras.models.load_model(extractor_path, compile=False)

            # Carga del clasificador Scikit-learn (StandardScaler + SVC)
            self.classifier = joblib.load(classifier_path)

            # Verificación técnica de dimensiones y consistencia
            feature_dim = self.config.get('feature_dim', 1280)
            assert self.extractor.output_shape[-1] == feature_dim, (
                f"Dimensión de características esperada {feature_dim}, obtenida {self.extractor.output_shape[-1]}"
            )

            expected_classes_count = len(self.config['classes'])
            assert np.array_equal(
                np.asarray(self.classifier.classes_, dtype=int),
                np.arange(expected_classes_count)
            ), "Inconsistencia en el orden de clases del clasificador SVM."

            self.is_ready = True
            logger.info("Modelo híbrido EfficientNet-B0 + SVM cargado exitosamente. Clases: %d", expected_classes_count)

        except Exception as exc:
            self.error_message = f"Error al inicializar el modelo híbrido: {str(exc)}"
            logger.exception(self.error_message)
            self.is_ready = False

    def check_status(self) -> Dict[str, Any]:
        """Devuelve el estado operativo actual del modelo."""
        return {
            'is_ready': self.is_ready,
            'model_name': self.config.get('winner', 'EfficientNet-B0 + SVM') if self.config else None,
            'feature_dim': self.config.get('feature_dim', 1280) if self.config else None,
            'cv_f1_macro': self.config.get('cv_f1_mean', 0.9818) if self.config else None,
            'classes': self.config.get('classes', []) if self.config else [],
            'labels_es': self.config.get('labels_es', []) if self.config else [],
            'artifacts_dir': str(self.artifacts_dir) if self.artifacts_dir else None,
            'error': self.error_message
        }

    def predict(self, image_input) -> Dict[str, Any]:
        """
        Ejecuta la inferencia real de extremo a extremo:
        1. Preprocesamiento seguro de imagen (EXIF, RGB, 224x224).
        2. Extracción de 1 280 características con EfficientNet-B0.
        3. Clasificación con SVM Pipeline (StandardScaler + SVC predict_proba).
        4. Mapeo y estructuración con metadatos agronómicos.
        """
        if not self.is_ready:
            raise ModelNotConfiguredError(
                self.error_message or "El modelo híbrido no está configurado o sus artefactos no están disponibles."
            )

        start_time = time.perf_counter()

        # Abrir imagen de forma segura
        if isinstance(image_input, (str, Path)):
            with Image.open(image_input) as img:
                rgb = ImageOps.exif_transpose(img).convert('RGB')
        elif hasattr(image_input, 'read'):
            # Objeto de archivo en memoria (UploadedFile)
            image_input.seek(0)
            with Image.open(image_input) as img:
                rgb = ImageOps.exif_transpose(img).convert('RGB')
        elif isinstance(image_input, Image.Image):
            rgb = ImageOps.exif_transpose(image_input).convert('RGB')
        else:
            raise ValueError("Tipo de entrada de imagen no compatible.")

        # Redimensionamiento oficial a 224x224 con filtro Bilinear
        target_size = tuple(self.config.get('image_size', [224, 224]))
        rgb = rgb.resize(target_size, Image.Resampling.BILINEAR)

        # Matriz numpy flotante
        x = np.asarray(rgb, dtype=np.float32)[None, ...]

        # Preprocesamiento: EfficientNetB0 Keras incluye el escalado internamente
        # Extraer vector de 1 280 características profundas
        embedding = self.extractor.predict(x, verbose=0)
        expected_dim = self.config.get('feature_dim', 1280)
        if embedding.shape != (1, expected_dim):
            raise ValueError(f"Dimensión de vector inesperada: {embedding.shape}")

        # Clasificación con el pipeline SVM entrenado
        raw_probs = self.classifier.predict_proba(embedding)[0]
        probs = np.asarray(raw_probs, dtype=float)

        if not np.isfinite(probs).all():
            raise ValueError("El clasificador generó probabilidades no finitas.")

        pred_idx = int(np.argmax(probs))
        pred_class_en = self.config['classes'][pred_idx]
        pred_class_es = self.config['labels_es'][pred_idx]
        confidence = float(probs[pred_idx])
        confidence_pct = round(confidence * 100, 2)

        # Distribución de probabilidades en orden exacto
        probabilities_dict = {}
        probabilities_list = []
        for j, class_en in enumerate(self.config['classes']):
            class_es = self.config['labels_es'][j]
            p_val = float(probs[j])
            probabilities_dict[class_en] = p_val
            probabilities_list.append({
                'id': j,
                'class_en': class_en,
                'class_es': class_es,
                'probability': p_val,
                'percentage': round(p_val * 100, 2),
                'is_winner': (j == pred_idx)
            })

        # Ordenar lista descendente para ranking visual
        ranked_list = sorted(probabilities_list, key=lambda item: item['probability'], reverse=True)

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 1)

        category_data = CATEGORY_METADATA.get(pred_class_en, {
            "nombre_es": pred_class_es,
            "agente": "No especificado",
            "gravedad": "Desconocida",
            "color_badge": "secondary",
            "descripcion": "Sin información fitosanitaria detallada.",
            "sintomas": "Sin descripción registrada.",
            "recomendaciones": ["Consultar con un agrónomo especialista."]
        })

        is_healthy = (pred_class_en == "Healthy")

        return {
            'predicted_id': pred_idx,
            'predicted_class': pred_class_en,
            'predicted_class_es': pred_class_es,
            'confidence': confidence,
            'confidence_pct': confidence_pct,
            'is_healthy': is_healthy,
            'probabilities': probabilities_dict,
            'probabilities_list': probabilities_list,
            'ranked_list': ranked_list,
            'inference_time_ms': elapsed_ms,
            'category_info': category_data,
            'disclaimer': self.config.get(
                'disclaimer',
                'Este resultado es una clasificación automatizada de carácter orientativo y académico. No sustituye la evaluación de un especialista fitosanitario.'
            ),
            'model_info': {
                'name': self.config.get('winner', 'EfficientNet-B0 + SVM'),
                'cv_f1_macro': self.config.get('cv_f1_mean', 0.9818),
                'feature_dim': expected_dim,
                'selection_rule': self.config.get('selection_rule', 'Mayor F1-macro medio de CV-10')
            }
        }


# Instancia accesible a nivel de módulo
_engine = None

def get_inference_engine() -> HybridInferenceEngine:
    """Devuelve la instancia singleton del motor de inferencia."""
    global _engine
    if _engine is None:
        _engine = HybridInferenceEngine()
    return _engine


def predict_mango_leaf(image_input) -> Dict[str, Any]:
    """Función de alto nivel para invocar inferencia desde vistas o tareas."""
    engine = get_inference_engine()
    return engine.predict(image_input)
