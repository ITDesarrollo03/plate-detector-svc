# Plate Detector Service

Servicio de detección y OCR de placas vehiculares para Honduras usando FastAPI, YOLO y Tesseract.

## 📋 Características

- 🚗 **Detección de placas** con YOLO v8
- 🔍 **OCR especializado** para placas hondureñas (formato AAA####)
- 📄 **Extracción de documentos** (DNI, Licencias, Despachos)
- 🖼️ **Debug viewer** integrado
- 🚀 **API REST** con FastAPI
- 🪟 **Deployment en Windows Server 2022** con IIS

## 🚀 Quick Start

### Desarrollo Local (Linux/Mac/WSL)

```bash
# Clonar repositorio
git clone <repo-url>
cd plate-detector-svc

# Crear virtual environment
python3.11 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servicio
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Acceder a: http://localhost:8000/docs

### Deployment en Windows Server 2022

Ver [Guía de Deployment](deployment/README.md) para instalación completa.

**Instalación rápida:**

1. Descargar release ZIP desde [Releases](../../releases)
2. Extraer en el servidor
3. Ejecutar `INSTALL.ps1` como Administrador
4. Acceder a http://localhost:8000

## 📚 Documentación

- **[CLAUDE.md](CLAUDE.md)** - Documentación técnica del proyecto
- **[Deployment Guide](deployment/README.md)** - Guía de instalación en Windows Server
- **[CI/CD Setup](docs/CI-CD-SETUP.md)** - Configuración de pipelines (Azure/GitHub)

## 🏗️ Arquitectura

```
plate-detector-svc/
├── app/
│   ├── adapters/          # Implementaciones (YOLO, Tesseract)
│   ├── api/               # Endpoints FastAPI
│   ├── core/              # Configuración
│   ├── domain/            # Lógica de negocio
│   └── ports/             # Interfaces (hexagonal architecture)
├── models/
│   └── plate-detector.pt  # Modelo YOLO (~6MB)
├── deployment/            # Scripts PowerShell para IIS
├── docs/                  # Documentación adicional
└── web.config             # Configuración IIS
```

**Patrón**: Hexagonal Architecture (Ports & Adapters)

## 🔌 API Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/detect` | POST | Detectar placa en imagen |
| `/ocr` | POST | Detectar + OCR de placa |
| `/extract-info` | POST | Extraer info de documento de despacho |
| `/dni/extract` | POST | Extraer info de DNI |
| `/license/extract` | POST | Extraer info de licencia |
| `/debug/viewer` | GET | Visor de imágenes debug |
| `/docs` | GET | Documentación interactiva (Swagger) |

## 🧪 Ejemplo de Uso

```python
import requests

# Detectar placa
url = "http://localhost:8000/ocr"
files = {"file": open("placa.jpg", "rb")}
response = requests.post(url, files=files)

print(response.json())
# {
#   "fileName": "placa.jpg",
#   "plateText": "ABC 1234",
#   "rawText": "ABC1234",
#   "detConf": 0.95,
#   "bbox": {"x": 100, "y": 50, "w": 200, "h": 80}
# }
```

## ⚙️ Configuración

Variables de entorno (definidas en `web.config` o `.env`):

| Variable | Default | Descripción |
|----------|---------|-------------|
| `MODEL_PATH` | `models/plate-detector.pt` | Ruta al modelo YOLO |
| `DEBUG_DIR` | `{temp}/debug_plates` | Directorio para imágenes debug |
| `TESSERACT_CMD` | Auto-detectado | Ruta a Tesseract (Windows) |
| `CONF` | `0.25` | Umbral de confianza YOLO |
| `IMG_SIZE` | `640` | Tamaño de imagen YOLO |

## 📊 Performance

En CPU (sin GPU):

- Detección YOLO: **200-500ms**
- Preprocesamiento: **100-200ms**
- OCR Tesseract: **500-1500ms**
- **Total: 1-2.5 segundos por imagen**

Memoria: **800MB - 1GB**

## 🛠️ Requisitos

### Desarrollo

- Python 3.11+
- OpenCV
- PyTorch (CPU o GPU)
- Tesseract OCR
- FastAPI + Uvicorn

### Producción (Windows Server 2022)

- Windows Server 2022
- IIS 10
- Python 3.11 (instalado automáticamente)
- Tesseract OCR (instalado automáticamente)
- Visual C++ Redistributables (instalado automáticamente)
- HttpPlatformHandler (instalado automáticamente)

## 🚢 Deployment

### Opción 1: Manual

```powershell
# Clonar proyecto
git clone <repo-url>
cd plate-detector-svc

# Crear release
.\create-release.ps1

# Copiar ZIP al servidor y ejecutar INSTALL.ps1
```

### Opción 2: CI/CD

**Azure Pipelines:**
- Configurado en `azure-pipelines.yml`
- Builds automáticos en push/PR
- Artifacts publicados automáticamente

**GitHub Actions:**
- Configurado en `.github/workflows/release.yml`
- Releases automáticos con tags `v*`

Ver [CI/CD Setup Guide](docs/CI-CD-SETUP.md)

## 🐛 Troubleshooting

### Error: "Tesseract not found"

```powershell
# Verificar instalación
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version

# Verificar datos español
Test-Path "C:\Program Files\Tesseract-OCR\tessdata\spa.traineddata"
```

### Error: HTTP 503 en IIS

```powershell
# Revisar logs
Get-Content "C:\inetpub\wwwroot\PlateDetector\logs\stdout.log" -Tail 50

# Reiniciar Application Pool
Restart-WebAppPool -Name "PlateDetectorAppPool"
```

### OCR no detecta placas

- Verificar formato esperado: **AAA####** (3 letras, 4 dígitos)
- Ver imágenes debug en `/debug/viewer`
- Revisar preprocesamiento en `app/domain/image_utils.py`

## 📦 Crear Release

### Automático (CI/CD)

```bash
# Crear tag
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0

# El pipeline creará el release automáticamente
```

### Manual

```powershell
# Ejecutar script de release
.\create-release.ps1

# El ZIP se crea en: release/PlateDetector-Release-<timestamp>.zip
```

## 🧑‍💻 Desarrollo

### Estructura de Código

```python
# Hexagonal Architecture

# Ports (interfaces)
app/ports/
  - detector_port.py       # Interface para detectores
  - ocr_port.py            # Interface para OCR
  - info_extractor_port.py # Interface para extractores

# Adapters (implementaciones)
app/adapters/
  - detector/yolo_adapter.py        # YOLO implementation
  - ocr/tesseract_adapter.py        # Tesseract implementation
  - extraction/regex_id_adapter.py  # Regex extraction

# Domain (lógica de negocio)
app/domain/
  - models.py       # Pydantic models
  - services.py     # Business logic (normalización, parsing)
  - image_utils.py  # Image preprocessing
```

### Agregar Nuevo Endpoint

1. Crear función en `app/api/routers.py`
2. Usar dependency injection para adapters
3. Documentar con docstrings (Swagger lo detecta automáticamente)

```python
@router.post("/mi-endpoint")
async def mi_endpoint(
    file: UploadFile = File(...),
    detector: PlateDetectorPort = Depends(get_detector)
):
    """Descripción del endpoint"""
    # Tu lógica aquí
    return {"result": "data"}
```

## 🤝 Contribuir

1. Fork del proyecto
2. Crear branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -m 'Add nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Abrir Pull Request

## 📄 Licencia

Este proyecto es privado/interno. Consultar con el equipo sobre licenciamiento.

## 📞 Soporte

- **Documentación**: Ver [CLAUDE.md](CLAUDE.md)
- **Issues**: Crear issue en el repositorio
- **Logs**: `C:\inetpub\wwwroot\PlateDetector\logs\stdout.log`

---

**Desarrollado para detección de placas vehiculares en Honduras** 🇭🇳
