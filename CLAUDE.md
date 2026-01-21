# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a FastAPI microservice for Honduras vehicle plate detection and OCR, plus identity document (DNI/license) extraction. It uses YOLO for detection, Tesseract for OCR, and implements extensive image preprocessing for Honduras-specific license plate formats (AAA####).

## Commands

### Running the Service

```bash
# Run locally (Linux/Mac/WSL)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Build Docker image
docker build -t plate-detector-svc .

# Run Docker container
docker run -p 8000:8000 -v $(pwd)/models:/app/models plate-detector-svc
```

### Windows Server Deployment

```powershell
# Create release package
.\create-release.ps1

# Quick installation (from extracted release)
.\INSTALL.ps1
```

See `deployment/README.md` for detailed deployment instructions.

### Environment Variables

- `MODEL_PATH`: Path to YOLO model (default: `models/plate-detector.pt`)
- `DEBUG_DIR`: Debug images directory (default: system temp + `debug_plates`)
- `TESSERACT_CMD`: Path to Tesseract executable (Windows: auto-detected)
- `TESSDATA_PREFIX`: Path to Tesseract language data
- `CONF`: Detection confidence threshold (default: `0.25`)
- `IMG_SIZE`: YOLO inference image size (default: `640`)

## Architecture

### Hexagonal Architecture (Ports & Adapters)

The codebase follows hexagonal architecture with clear separation:

- **Ports** (app/ports/): Protocol interfaces defining contracts
  - `PlateDetectorPort`: Interface for plate detection
  - `OcrPort`: Interface for OCR engines
  - `InfoExtractorPort`: Interface for information extraction

- **Adapters** (app/adapters/): Concrete implementations of ports
  - `YoloAdapter`: YOLO-based plate detector (uses Ultralytics)
  - `TesseractPlateAdapter`: Tesseract OCR configured for plates
  - `TesseractDocumentAdapter`: Tesseract OCR for full documents
  - `RegexIdAdapter`: Regex-based extraction for Honduras ID numbers (13 digits in 4-4-5 format)

- **Domain** (app/domain/): Business logic and pure functions
  - `models.py`: Pydantic models (BoundingBox, DetectionResult, OcrResult)
  - `services.py`: Pure domain logic for plate normalization and dispatch parsing
  - `image_utils.py`: Image preprocessing functions (deskewing, cropping, thresholding)

- **API** (app/api/): HTTP endpoints and dependency injection
  - `routers.py`: All FastAPI routes with cached dependency injection using `@lru_cache()`

### Key Domain Logic

**Honduras Plate Normalization** (app/domain/services.py:46):
- Format: AAA#### (3 letters, 4 digits, e.g., "TCI 3368")
- Handles OCR confusion: digits→letters in first 3 positions, letters→digits in last 4
- Special first-letter corrections: I/L/1 → T for truck plates
- Position-aware character translation tables (`LETTER_FIX`, `DIGIT_FIX`)

**Image Preprocessing Pipeline** (app/domain/image_utils.py:165):
1. Deskewing using contour analysis (max 10° rotation)
2. Vertical crop (30%-75% of height) to exclude "HONDURAS" header and "CENTROAMERICA" footer
3. 5x upscaling for better OCR
4. Unsharp mask + CLAHE contrast enhancement
5. Adaptive thresholding with Otsu fallback
6. Morphological operations to clean noise while preserving character integrity
7. Lateral edge trimming and projection-based cropping

**Debug System**:
- OCR endpoint saves debug images to `/tmp/debug_plates/{uuid}_01_crop.jpg` and `{uuid}_02_processed.jpg`
- Access via `/debug/viewer` endpoint for HTML viewer
- `/debug/images` lists all saved images
- `/debug/images/{filename}` downloads specific image

### API Endpoints

- `POST /detect`: Detects plate and returns cropped plate image
- `POST /ocr`: Full pipeline - detect → preprocess → OCR → normalize (Honduras format)
  - Falls back through 4 different OCR configurations if initial extraction fails
  - Returns `plateText` (normalized), `rawText`, `detConf`, `bbox`
- `POST /extract-info`: Extract driver dispatch information from document images
- `POST /dni/extract`: Extract identity number and name from DNI
- `POST /license/extract`: Extract identity number and name from driver's license
- `GET /debug/viewer`: HTML viewer for debug images
- `GET /debug/images`: List debug images
- `GET /debug/images/{filename}`: Download debug image

### Dependencies and Singleton Pattern

Adapters are cached as singletons via `@lru_cache()` decorator on dependency functions in app/api/routers.py:20-35. This ensures:
- YOLO model loads only once
- Tesseract configurations are reused
- Memory efficiency across requests

### Dispatch Info Extraction

The `parse_dispatch_info` function (app/domain/services.py:129) extracts structured data from Honduras driver dispatch documents:
- Field matching via regex patterns
- Phone normalization to ####-#### format
- Spanish field names in output (horaDespacho, motorista, licencia, placa, telefono, color, marca, anio, motor, vin, codigo, transporte, rtn)

### Identity Document Extraction

Honduras DNI/License extraction uses regex patterns for:
- 13-digit identity numbers in 4-4-5 format (with OCR error correction)
- Name extraction using label detection (Nombre/Forename, Apellido/Surname)
- Fallback heuristics based on letter/digit ratios
- Special handling for OCR misreads: O/Q→0, I/l/|→1, S→5, B→8, G→6
- Year correction: handles common OCR error where "1" in year reads as "4"

### Important Preprocessing Details

**Deskewing** (app/domain/image_utils.py:74):
- Only corrects rotations between 0.5° and 10° (very conservative)
- Uses character contour analysis, requires minimum 3 valid contours
- Filters contours by height (15%-95% of image) and aspect ratio (0.15-2.5)

**Multiple OCR Fallback Strategy** (app/api/routers.py:122-138):
1. Primary: Preprocessed binary image with PSM 7
2. Fallback 1: PSM 6 with DPI 300
3. Fallback 2: Grayscale without preprocessing
4. Fallback 3: Grayscale with alternate config
- Returns HTTP 422 if all fallbacks fail to match Honduras format

### Testing Considerations

No test suite exists. When adding tests:
- Test domain logic in isolation (services.py functions are pure)
- Mock ports for adapter testing
- Use sample images for integration tests
- Test OCR fallback chains
- Validate Honduras plate format edge cases (T13368 → TCI 3368)

## Deployment and CI/CD

### Windows Server 2022 Deployment

The project is configured for deployment on Windows Server 2022 with IIS using HttpPlatformHandler.

**Directory Structure on Server:**
```
C:\inetpub\wwwroot\PlateDetector\
├── app/                  # Application code
├── models/               # YOLO model (6MB)
├── venv/                 # Python virtual environment
├── logs/                 # Application logs
├── debug_plates/         # Debug images
├── web.config            # IIS configuration
└── requirements-windows.txt
```

**Key Files:**
- `web.config`: HttpPlatformHandler configuration for IIS
- `create-release.ps1`: Creates deployment package (ZIP)
- `deployment/INSTALL.ps1`: Quick installer script
- `deployment/01-10-*.ps1`: Individual installation steps

**Installation:**
1. Extract release ZIP
2. Run `INSTALL.ps1` as Administrator
3. Access http://localhost:8000

See `deployment/README.md` for complete installation guide.

### Creating Releases

**Manual:**
```powershell
.\create-release.ps1
# Creates: release/PlateDetector-Release-<timestamp>.zip
```

**Automated (CI/CD):**

**Azure Pipelines** (`azure-pipelines.yml`):
- Triggers: push to master/main, tags v*, PRs
- Stages: Build, DeployToDev (optional), Release (for tags)
- Artifacts: Published as `PlateDetectorRelease`
- Version: `{major}.{minor}.{buildId}`

**GitHub Actions** (`.github/workflows/release.yml`):
- Triggers: push to master/main, tags v*, manual dispatch
- Jobs: build, release (for tags)
- Artifacts: Retained 90 days
- Releases: Automatic GitHub Releases for tags v*

See `docs/CI-CD-SETUP.md` for detailed CI/CD configuration.

### Cross-Platform Compatibility

Code changes for Windows compatibility:
- `app/core/config.py`: `debug_dir` using `tempfile.gettempdir()` (works on both Linux and Windows)
- `app/adapters/ocr/*.py`: Auto-detect Tesseract path on Windows via `os.name == 'nt'`
- `app/main.py`: Startup validation creates debug directory cross-platform

The same codebase works on:
- Linux (Docker, development)
- Windows Server 2022 (IIS, production)
- Mac/WSL (development)
