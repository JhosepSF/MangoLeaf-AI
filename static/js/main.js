/**
 * MangoLeaf-AI — Lógica de Interfaz del Frontend
 * Drag & Drop, Previsualización y envío con indicador de inferencia en tiempo real
 */

document.addEventListener('DOMContentLoaded', function () {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('image-input');
  const previewContainer = document.getElementById('preview-container');
  const previewImage = document.getElementById('preview-image');
  const dropzonePrompt = document.getElementById('dropzone-prompt');
  const btnRemove = document.getElementById('btn-remove-preview');
  const analyzeForm = document.getElementById('analyze-form');
  const btnSubmit = document.getElementById('btn-submit-analyze');
  const processingOverlay = document.getElementById('processing-overlay');
  const processingStatus = document.getElementById('processing-status');

  if (!dropzone || !fileInput) return;

  // Manejo de Drag and Drop
  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, function (e) {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('drag-over');
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, function (e) {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('drag-over');
    }, false);
  });

  dropzone.addEventListener('drop', function (e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files && files.length > 0) {
      handleFileSelected(files[0]);
    }
  });

  // Clic en la zona activa
  dropzone.addEventListener('click', function (e) {
    if (e.target !== btnRemove && !btnRemove?.contains(e.target)) {
      if (!previewContainer.style.display || previewContainer.style.display === 'none') {
        fileInput.click();
      }
    }
  });

  fileInput.addEventListener('change', function () {
    if (this.files && this.files.length > 0) {
      handleFileSelected(this.files[0]);
    }
  });

  function handleFileSelected(file) {
    // Validar tipo MIME básico
    const validTypes = ['image/jpeg', 'image/png', 'image/jpg'];
    if (!validTypes.includes(file.type)) {
      alert('Por favor seleccione una imagen en formato JPG, JPEG o PNG.');
      return;
    }

    // Validar tamaño máximo (10 MB)
    const maxSize = 10 * 1024 * 1024;
    if (file.size > maxSize) {
      alert('La imagen excede el límite permitido de 10 MB.');
      return;
    }

    // Previsualizar
    const reader = new FileReader();
    reader.onload = function (e) {
      previewImage.src = e.target.result;
      dropzonePrompt.style.display = 'none';
      previewContainer.style.display = 'block';
      if (btnSubmit) btnSubmit.disabled = false;
    };
    reader.readAsDataURL(file);

    // Asignar al input si vino por drag & drop
    const dataTransfer = new DataTransfer();
    dataTransfer.items.add(file);
    fileInput.files = dataTransfer.files;
  }

  // Quitar previsualización
  if (btnRemove) {
    btnRemove.addEventListener('click', function (e) {
      e.preventDefault();
      e.stopPropagation();
      fileInput.value = '';
      previewImage.src = '';
      previewContainer.style.display = 'none';
      dropzonePrompt.style.display = 'block';
      if (btnSubmit) btnSubmit.disabled = true;
    });
  }

  // Envío del formulario con estado de progreso realista
  if (analyzeForm) {
    analyzeForm.addEventListener('submit', function (e) {
      if (!fileInput.files || fileInput.files.length === 0) {
        e.preventDefault();
        alert('Seleccione o arrastre una imagen de hoja antes de continuar.');
        return;
      }

      // Activar overlay de procesamiento
      if (processingOverlay) {
        processingOverlay.style.display = 'flex';
        if (btnSubmit) btnSubmit.disabled = true;

        const steps = [
          'Preprocesando imagen (EXIF, RGB y redimensionamiento 224x224)...',
          'Extrayendo 1,280 características profundas con EfficientNet-B0...',
          'Evaluando clasificador SVM (Support Vector Machine)...',
          'Consolidando puntuaciones fitosanitarias...'
        ];

        let stepIndex = 0;
        const intervalId = setInterval(() => {
          stepIndex++;
          if (stepIndex < steps.length && processingStatus) {
            processingStatus.innerText = steps[stepIndex];
          } else {
            clearInterval(intervalId);
          }
        }, 900);
      }
    });
  }
});
