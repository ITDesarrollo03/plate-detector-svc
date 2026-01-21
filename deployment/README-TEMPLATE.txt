================================================================================
  PLATE DETECTOR SERVICE - RELEASE PACKAGE
  Version: VERSION_PLACEHOLDER
================================================================================

Este paquete contiene todo lo necesario para desplegar el servicio de
detección de placas vehiculares en Windows Server 2022 con IIS.

================================================================================
CONTENIDO DEL PAQUETE
================================================================================

  app/                          - Código fuente de la aplicación FastAPI
  models/                       - Modelo YOLO para detección de placas
  deployment/                   - Scripts PowerShell para instalación
  web.config                    - Configuración de IIS HttpPlatformHandler
  requirements-windows.txt      - Dependencias Python para Windows
  CLAUDE.md                     - Documentación técnica del proyecto
  README.txt                    - Este archivo

================================================================================
REQUISITOS PREVIOS
================================================================================

  - Windows Server 2022
  - IIS 10 instalado y configurado
  - Permisos de Administrador
  - Conexión a Internet (para descargar dependencias)

================================================================================
INSTALACIÓN RÁPIDA
================================================================================

1. Extraer este ZIP en una ubicación temporal (ej: C:\Temp\PlateDetector)

2. Abrir PowerShell como Administrador

3. Navegar al directorio extraído:
   cd C:\Temp\PlateDetector

4. Ejecutar INSTALL.ps1:
   .\INSTALL.ps1

5. Verificar que el servicio esté corriendo:
   - Abrir navegador: http://localhost:8000/docs
   - Revisar logs: C:\inetpub\wwwroot\PlateDetector\logs\stdout.log

Ver deployment\README.md para instalación manual paso a paso.

================================================================================
ESTRUCTURA FINAL EN EL SERVIDOR
================================================================================

  C:\inetpub\wwwroot\PlateDetector\
  ├── app\                      - Aplicación
  ├── models\                   - Modelo YOLO
  ├── venv\                     - Virtual environment Python
  ├── logs\                     - Logs del servicio
  ├── debug_plates\             - Imágenes de debug
  ├── web.config                - Configuración IIS
  └── requirements-windows.txt  - Dependencias

================================================================================
ENDPOINTS DISPONIBLES
================================================================================

  POST /detect              - Detectar placa en imagen
  POST /ocr                 - Detectar + OCR de placa
  POST /extract-info        - Extraer info de documento de despacho
  POST /dni/extract         - Extraer info de DNI
  POST /license/extract     - Extraer info de licencia
  GET  /debug/viewer        - Visor de imágenes debug
  GET  /docs                - Documentación interactiva API

================================================================================
TROUBLESHOOTING
================================================================================

Error: HTTP 503
  - Revisar logs: C:\inetpub\wwwroot\PlateDetector\logs\stdout.log
  - Verificar Application Pool iniciado
  - Verificar permisos en C:\inetpub\wwwroot\PlateDetector

Error: "Tesseract not found"
  - Verificar: C:\Program Files\Tesseract-OCR\tesseract.exe
  - Verificar datos español: tessdata\spa.traineddata
  - Reiniciar Application Pool

Para más ayuda, consultar deployment\README.md

================================================================================
PERFORMANCE ESPERADO (CPU)
================================================================================

  - Detección YOLO: 200-500ms
  - Preprocesamiento: 100-200ms
  - OCR Tesseract: 500-1500ms
  - Total por request: 1-2.5 segundos
  - Memoria: 800MB - 1GB

================================================================================
SOPORTE Y DOCUMENTACIÓN
================================================================================

  - Documentación técnica: CLAUDE.md
  - Guía de deployment: deployment\README.md
  - Logs del sistema: C:\inetpub\wwwroot\PlateDetector\logs\stdout.log

================================================================================
CONTACTO
================================================================================

  Generado: TIMESTAMP_PLACEHOLDER
  Versión: 1.0.0

================================================================================
