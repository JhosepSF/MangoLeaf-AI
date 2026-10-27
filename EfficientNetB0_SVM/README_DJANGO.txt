IMPLEMENTACIÓN DJANGO — TESIS CAMILA VARGAS

Modelo seleccionado por F1-macro de CV: EfficientNet-B0 + SVM
No fue elegido mediante métricas Test.

ARCHIVOS:
artefactos/extractor.keras — extractor CNN de 2048 o 1280 dimensiones.
artefactos/svm_pipeline.joblib — StandardScaler + SVC entrenado.
artefactos/config.json — clases, RGB, tamaño y preprocesamiento.
artefactos/inferencia.py — función predict_image(image_path).
fotos_test/ — dos imágenes demostrativas originales de Test.
prueba_inferencia.csv — verificación técnica de predicción.

INTEGRACIÓN:
1. Instale versiones compatibles TensorFlow/Keras, scikit-learn, joblib, Pillow y NumPy.
2. Conserve todos los archivos de artefactos/ juntos.
3. En Django importe inferencia.predict_image y cargue el módulo una vez por worker.
4. Valide imagen subida: formato auténtico, tamaño máximo y contenido.
5. Muestre predicted_class_es, confidence y probabilities.
6. Nunca cargue joblib de terceros: puede ejecutar código durante su lectura.

Test se utilizó únicamente en la prueba técnica del paquete; nunca en la selección.
Este paquete no es un ejecutable nativo ni conversión ONNX/TFLite.
Nota: los resultados Test de experimentos individuales ya fueron consultados;
conservar esta limitación metodológica al reportar generalización.
