# -*- coding: utf-8 -*-
"""Inferencia híbrida; importe este módulo una sola vez por proceso de Django."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageOps
import tensorflow as tf
import joblib
ROOT=Path(__file__).resolve().parent
CONFIG=json.loads((ROOT/'config.json').read_text(encoding='utf-8'))
EXTRACTOR=tf.keras.models.load_model(ROOT/CONFIG['extractor_file'],compile=False)
CLASSIFIER=joblib.load(ROOT/CONFIG['classifier_file']) # Solo archivos propios confiables.
assert EXTRACTOR.output_shape[-1] == CONFIG['feature_dim']
assert np.array_equal(np.asarray(CLASSIFIER.classes_,dtype=int),np.arange(len(CONFIG['classes'])))

def predict_image(image_path):
    with Image.open(image_path) as image:
        rgb=ImageOps.exif_transpose(image).convert('RGB')
        rgb=rgb.resize(tuple(CONFIG['image_size']),Image.Resampling.BILINEAR)
        x=np.asarray(rgb,dtype=np.float32)[None,...]
    preprocessing=CONFIG['preprocess']
    if preprocessing=='resnet50':
        x=tf.keras.applications.resnet50.preprocess_input(x)
    elif preprocessing=='mobilenet_v2':
        x=tf.keras.applications.mobilenet_v2.preprocess_input(x)
    elif preprocessing=='efficientnetb0':
        pass # Modelo Keras EfficientNet ya realiza preprocessing internamente.
    else:
        raise ValueError('Preprocesamiento desconocido: '+preprocessing)
    emb=EXTRACTOR.predict(x,verbose=0)
    assert emb.shape==(1,CONFIG['feature_dim'])
    probs=np.asarray(CLASSIFIER.predict_proba(emb)[0],dtype=float)
    assert probs.shape==(len(CONFIG['classes']),) and np.isfinite(probs).all()
    i=int(np.argmax(probs))
    return {'predicted_id':i,'predicted_class':CONFIG['classes'][i],
            'predicted_class_es':CONFIG['labels_es'][i],
            'confidence':float(probs[i]),
            'probabilities':{name:float(probs[j]) for j,name in enumerate(CONFIG['classes'])},
            'warning':CONFIG['disclaimer']}
