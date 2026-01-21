# Deployment Scripts for Windows Server 2022 + IIS

Este directorio contiene scripts PowerShell para desplegar el servicio Plate Detector en Windows Server 2022 con IIS usando HttpPlatformHandler.

## Requisitos Previos

- Windows Server 2022
- IIS 10 instalado
- Acceso de administrador
- Conexión a Internet

## Orden de Ejecución

Ejecutar los scripts en el siguiente orden (todos requieren permisos de administrador):

### Fase 1: Instalación de Dependencias del Sistema

1. **01-install-python.ps1**
   - Instala Python 3.11.9
   - Configura PATH automáticamente
   - Incluye pip

2. **02-install-vcredist.ps1**
   - Instala Visual C++ Redistributable 2015-2022 x64
   - Requerido por OpenCV y PyTorch

3. **03-install-tesseract.ps1**
   - Instala Tesseract OCR 5.3.3
   - **IMPORTANTE:** Verificar que se instalen los datos en español
   - Si falta `spa.traineddata`, descargar manualmente de:
     https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata
   - Colocar en: `C:\Program Files\Tesseract-OCR\tessdata\`

4. **04-install-httpplatformhandler.ps1**
   - Instala HttpPlatformHandler 1.2 para IIS
   - Reinicia IIS automáticamente

### Fase 2: Configuración de la Aplicación

5. **05-setup-directories.ps1**
   - Crea estructura de directorios en `C:\inetpub\wwwroot\PlateDetector`
   - Configura permisos para IIS AppPool

6. **06-setup-venv.ps1**
   - Crea virtual environment en `C:\inetpub\wwwroot\PlateDetector\venv`
   - Instala todas las dependencias Python
   - **NOTA:** Este proceso puede tomar 5-10 minutos

### Fase 3: Deployment de la Aplicación

7. **07-deploy-app.ps1**
   - **EJECUTAR DESDE LA RAÍZ DEL PROYECTO**
   - Copia archivos de aplicación a `C:\inetpub\wwwroot\PlateDetector`
   - Copia modelo YOLO
   - Copia `web.config`

### Fase 4: Configuración de IIS

8. **08-create-iis-site.ps1**
   - Crea Application Pool: `PlateDetectorAppPool`
   - Crea sitio IIS: `PlateDetectorService`
   - Configura binding en `http://localhost:8000`
   - Inicia el sitio

### Fase 5: Verificación

9. **09-test-service.ps1**
   - Prueba endpoints del servicio
   - Verifica que el servicio responda correctamente

10. **10-verify-dependencies.ps1**
    - Verifica todas las dependencias instaladas
    - Verifica estructura de directorios
    - Verifica modelo YOLO
    - Verifica paquetes Python

## Ejemplo de Ejecución Completa

```powershell
# Abrir PowerShell como Administrador

# Fase 1: Dependencias del Sistema
cd deployment
.\01-install-python.ps1
.\02-install-vcredist.ps1
.\03-install-tesseract.ps1
# Verificar que spa.traineddata esté instalado
.\04-install-httpplatformhandler.ps1

# Fase 2: Configuración
.\05-setup-directories.ps1
.\06-setup-venv.ps1

# Fase 3: Deployment (ejecutar desde raíz del proyecto)
cd ..
.\deployment\07-deploy-app.ps1

# Fase 4: IIS
cd deployment
.\08-create-iis-site.ps1

# Fase 5: Verificación
.\10-verify-dependencies.ps1
.\09-test-service.ps1
```

## Verificación Post-Deployment

1. Abrir navegador: `http://localhost:8000/docs`
2. Verificar logs: `C:\inetpub\wwwroot\PlateDetector\logs\stdout.log`
3. Probar endpoint de debug: `http://localhost:8000/debug/test`
4. Revisar debug viewer: `http://localhost:8000/debug/viewer`

## Troubleshooting

### Error: "Python not found"
- Cerrar y volver a abrir PowerShell después de instalar Python
- O agregar manualmente a PATH: `C:\Program Files\Python311`

### Error: "Tesseract not found"
- Verificar que `TESSERACT_CMD` esté configurado en `web.config`
- Verificar instalación: `& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version`

### Error: "Spanish language data missing"
- Descargar manualmente: https://github.com/tesseract-ocr/tessdata/raw/main/spa.traineddata
- Colocar en: `C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata`
- Reiniciar Application Pool en IIS

### Error: HTTP 503
- Revisar logs: `C:\inetpub\wwwroot\PlateDetector\logs\stdout.log`
- Verificar que Application Pool esté iniciado
- Verificar permisos en `C:\inetpub\wwwroot\PlateDetector`

### Error: "Module not found"
- Verificar que virtual environment esté correctamente configurado
- Verificar ruta en `web.config`: `C:\inetpub\wwwroot\PlateDetector\venv\Scripts\python.exe`
- Re-ejecutar `06-setup-venv.ps1`

## Mantenimiento

### Actualizar la Aplicación

1. Detener Application Pool:
   ```powershell
   Stop-WebAppPool -Name "PlateDetectorAppPool"
   ```

2. Backup actual:
   ```powershell
   $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
   Copy-Item -Path "C:\inetpub\wwwroot\PlateDetector\app" -Destination "C:\inetpub\wwwroot\PlateDetector\app-backup-$timestamp" -Recurse
   ```

3. Desplegar nueva versión:
   ```powershell
   cd <proyecto-root>
   .\deployment\07-deploy-app.ps1
   ```

4. Iniciar Application Pool:
   ```powershell
   Start-WebAppPool -Name "PlateDetectorAppPool"
   ```

### Rotar Logs

Crear tarea programada semanal:
```powershell
$logFile = "C:\inetpub\wwwroot\PlateDetector\logs\stdout.log"
$archiveDir = "C:\inetpub\wwwroot\PlateDetector\logs\archive"
New-Item -ItemType Directory -Path $archiveDir -Force
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
Move-Item -Path $logFile -Destination "$archiveDir\stdout-$timestamp.log"
Restart-WebAppPool -Name "PlateDetectorAppPool"
```

### Limpiar Debug Images

Crear tarea programada diaria:
```powershell
Get-ChildItem -Path "C:\inetpub\wwwroot\PlateDetector\debug_plates" -Filter "*.jpg" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
    Remove-Item -Force
```

## Performance Esperado

- **Detección YOLO**: 200-500ms (CPU)
- **Preprocesamiento**: 100-200ms
- **OCR Tesseract**: 500-1500ms
- **Total por request**: 1-2.5 segundos
- **Memoria**: 800MB - 1GB

## Soporte

Para más información, consultar:
- CLAUDE.md en la raíz del proyecto
- Plan de deployment: `/home/jpvasquez/.claude/plans/humming-stirring-porcupine.md`
- Documentación de FastAPI: https://fastapi.tiangolo.com/
- Documentación de Tesseract: https://github.com/tesseract-ocr/tesseract
