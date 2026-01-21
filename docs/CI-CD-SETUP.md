# CI/CD Setup - Plate Detector Service

Este documento describe cómo configurar CI/CD para crear releases automáticos del Plate Detector Service usando Azure Pipelines o GitHub Actions.

## 📋 Tabla de Contenidos

- [Opción 1: Azure Pipelines](#opción-1-azure-pipelines)
- [Opción 2: GitHub Actions](#opción-2-github-actions)
- [Crear Release Manual](#crear-release-manual)
- [Versionado](#versionado)
- [Troubleshooting](#troubleshooting)

---

## Opción 1: Azure Pipelines

Azure Pipelines es ideal si ya usas Azure DevOps para gestión de proyectos.

### Prerrequisitos

- Cuenta de Azure DevOps
- Proyecto en Azure DevOps
- Repositorio conectado (Azure Repos o GitHub)

### Configuración Inicial

#### 1. Crear Pipeline

1. Ir a **Azure DevOps** → Tu proyecto
2. Ir a **Pipelines** → **Pipelines**
3. Click en **New Pipeline**
4. Seleccionar fuente del código:
   - **Azure Repos Git** (si el repo está en Azure DevOps)
   - **GitHub** (si está en GitHub, requiere autenticación)
5. Seleccionar el repositorio
6. En "Configure your pipeline", seleccionar **Existing Azure Pipelines YAML file**
7. Seleccionar branch: `master` o `main`
8. Path: `/azure-pipelines.yml`
9. Click en **Continue**
10. Click en **Run** para ejecutar el primer build

#### 2. Configurar Variables (Opcional)

Para personalizar versiones:

1. Ir a **Pipelines** → Seleccionar pipeline → **Edit**
2. Click en **Variables** (esquina superior derecha)
3. Agregar variables:
   - `majorVersion`: 1 (versión major)
   - `minorVersion`: 0 (versión minor)
   - `patchVersion`: $(Build.BuildId) (incrementa automáticamente)

#### 3. Configurar Triggers

El pipeline ya está configurado para ejecutarse en:

- Push a `master` o `main`
- Push a branches `release/*`
- Tags que empiecen con `v*` (ej: `v1.0.0`)
- Pull Requests a `master` o `main`

Para modificar triggers, editar `azure-pipelines.yml`:

```yaml
trigger:
  branches:
    include:
      - master
      - main
      - release/*
  tags:
    include:
      - v*
```

### Ejecutar el Pipeline

#### Build Automático

El pipeline se ejecuta automáticamente cuando:
- Haces push a las branches configuradas
- Creas un tag `v*`
- Abres/actualizas un Pull Request

#### Build Manual

1. Ir a **Pipelines** → Seleccionar pipeline
2. Click en **Run pipeline**
3. Seleccionar branch/tag
4. Click en **Run**

### Descargar Artefactos

Después de que el pipeline termine:

1. Ir a **Pipelines** → Seleccionar el build completado
2. Click en la pestaña **Summary**
3. En la sección **Published**, encontrarás:
   - **PlateDetectorRelease** - El archivo ZIP
4. Click en el artefacto para descargar

### Configurar Deployment Automático (Opcional)

El pipeline incluye un stage de deployment a DEV que está comentado.

Para habilitarlo:

1. Crear un **Environment** en Azure DevOps:
   - Ir a **Pipelines** → **Environments**
   - Click en **New environment**
   - Nombre: `DEV-PlateDetector`
   - Description: "Servidor de desarrollo"
   - Resource: **None** (si es deployment manual) o configurar agente

2. Configurar agente en el servidor Windows (opcional):
   - Descargar agente de Azure DevOps
   - Instalar en Windows Server 2022
   - Conectar al environment `DEV-PlateDetector`

3. Descomentar el stage `DeployToDev` en `azure-pipelines.yml`

4. Implementar lógica de deployment en el script:
   ```yaml
   - task: PowerShell@2
     displayName: 'Deploy to IIS'
     inputs:
       targetType: 'inline'
       script: |
         # Detener Application Pool
         Stop-WebAppPool -Name "PlateDetectorAppPool"

         # Backup
         $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
         Copy-Item -Path "C:\inetpub\wwwroot\PlateDetector\app" `
                   -Destination "C:\inetpub\wwwroot\PlateDetector\app-backup-$timestamp" -Recurse

         # Deployment
         Expand-Archive -Path "$(Pipeline.Workspace)\PlateDetectorRelease\*.zip" `
                        -DestinationPath "C:\Temp\PlateDetectorDeploy" -Force

         # Copiar archivos
         Copy-Item -Path "C:\Temp\PlateDetectorDeploy\app\*" `
                   -Destination "C:\inetpub\wwwroot\PlateDetector\app\" -Recurse -Force

         # Iniciar Application Pool
         Start-WebAppPool -Name "PlateDetectorAppPool"

         # Health check
         Start-Sleep -Seconds 10
         Invoke-RestMethod -Uri "http://localhost:8000/debug/test"
   ```

### Pipeline Stages

El pipeline tiene 3 stages:

1. **Build** - Crea el package de release
   - Verifica modelo YOLO
   - Ejecuta `create-release.ps1`
   - Publica artefacto ZIP

2. **DeployToDev** (opcional) - Deployment a desarrollo
   - Solo se ejecuta en push a `master`
   - Requiere configuración de environment

3. **Release** (opcional) - Crear release oficial
   - Solo se ejecuta con tags `v*`
   - Crea release notes

---

## Opción 2: GitHub Actions

GitHub Actions es ideal si tu código está en GitHub.

### Prerrequisitos

- Repositorio en GitHub
- GitHub Actions habilitado (gratis para repos públicos)

### Configuración Inicial

#### 1. Verificar Workflow

El workflow ya está creado en: `.github/workflows/release.yml`

GitHub lo detectará automáticamente.

#### 2. Habilitar GitHub Actions

1. Ir a tu repositorio en GitHub
2. Ir a **Settings** → **Actions** → **General**
3. En "Actions permissions", seleccionar:
   - **Allow all actions and reusable workflows**
4. Click en **Save**

#### 3. Configurar Secrets (si es necesario)

Si necesitas secrets para deployment:

1. Ir a **Settings** → **Secrets and variables** → **Actions**
2. Click en **New repository secret**
3. Agregar secrets necesarios (ej: credenciales de servidor)

### Triggers Configurados

El workflow se ejecuta cuando:

- Push a `master` o `main`
- Tags que empiecen con `v*` (ej: `v1.0.0`)
- Pull Requests a `master` o `main`
- **Manualmente** (workflow_dispatch)

### Ejecutar el Workflow

#### Build Automático

El workflow se ejecuta automáticamente con push/tags.

#### Build Manual

1. Ir a **Actions** en GitHub
2. Seleccionar workflow **Build and Release**
3. Click en **Run workflow** (botón derecho)
4. Opcionalmente, ingresar número de versión
5. Click en **Run workflow**

### Descargar Artefactos

1. Ir a **Actions** → Seleccionar workflow run
2. Scroll hasta **Artifacts**
3. Click en **PlateDetector-Release** para descargar ZIP

Los artefactos se conservan por **90 días**.

### Crear Release en GitHub

Para crear un release oficial:

1. Crear un tag con formato `v*`:
   ```bash
   git tag -a v1.0.0 -m "Release 1.0.0"
   git push origin v1.0.0
   ```

2. El workflow automáticamente:
   - Crea el package
   - Genera release notes
   - Crea GitHub Release con el ZIP adjunto

3. Ver release en: `https://github.com/<usuario>/<repo>/releases`

### Personalizar Release Notes

Editar `.github/workflows/release.yml`, sección `Create Release Notes`:

```yaml
- name: Create Release Notes
  shell: pwsh
  run: |
    $releaseNotes = @"
    # Tu título personalizado

    ## Tus secciones personalizadas
    ...
    "@
```

---

## Crear Release Manual

Si prefieres crear releases manualmente sin CI/CD:

### En Windows

```powershell
# Navegar al directorio del proyecto
cd C:\Users\<tu-usuario>\source\repos\plate-detector-svc

# Ejecutar script de release
.\create-release.ps1

# El ZIP se creará en:
# release\PlateDetector-Release-<timestamp>.zip
```

### En Linux/Mac (WSL)

```bash
# Instalar PowerShell Core si no está instalado
# Ubuntu/Debian:
sudo apt-get install -y powershell

# Ejecutar script
pwsh create-release.ps1
```

### Renombrar con Versión

```powershell
# Después de crear el release
cd release
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$zipFile = Get-ChildItem -Filter "*.zip" | Select-Object -First 1
Rename-Item $zipFile.Name "PlateDetector-v1.0.0.zip"
```

---

## Versionado

### Esquema de Versionado

Usamos **Semantic Versioning** (SemVer): `MAJOR.MINOR.PATCH`

- **MAJOR**: Cambios incompatibles (breaking changes)
- **MINOR**: Nueva funcionalidad compatible
- **PATCH**: Bug fixes compatibles

Ejemplos:
- `v1.0.0` - Primera versión estable
- `v1.1.0` - Nueva funcionalidad (ej: nuevo endpoint)
- `v1.1.1` - Bug fix
- `v2.0.0` - Breaking change (ej: cambio en formato de API)

### Actualizar Versión

#### En Azure Pipelines

Actualizar variables en el pipeline:
- `majorVersion`: 1
- `minorVersion`: 1
- `patchVersion`: $(Build.BuildId)

Resultado: `v1.1.<buildId>`

#### En GitHub Actions

Crear un tag:

```bash
# Crear tag localmente
git tag -a v1.2.0 -m "Release version 1.2.0"

# Verificar
git tag

# Subir a GitHub
git push origin v1.2.0
```

#### En Manual

Editar `version.json` después de ejecutar `create-release.ps1`:

```json
{
  "version": "1.2.0",
  "buildDate": "...",
  "pythonVersion": "3.11.9",
  ...
}
```

---

## Troubleshooting

### Error: "YOLO model not found"

**Problema**: El modelo no está en el repositorio.

**Solución**:
1. Verificar que `models/plate-detector.pt` existe
2. Verificar que no está en `.gitignore`
3. Si es muy grande para Git, usar Git LFS:
   ```bash
   git lfs install
   git lfs track "*.pt"
   git add .gitattributes
   git add models/plate-detector.pt
   git commit -m "Add YOLO model with LFS"
   ```

### Error: "Permission denied" en Azure Pipelines

**Problema**: El agente no tiene permisos para escribir.

**Solución**:
1. Verificar que el agente corre con permisos adecuados
2. En hosted agents (Microsoft), no debería haber problema
3. En self-hosted agents, dar permisos al usuario del agente

### Error: "Artifact not found" en GitHub Actions

**Problema**: El artefacto no se publicó correctamente.

**Solución**:
1. Revisar logs del step "Create Release Package"
2. Verificar que `create-release.ps1` completó sin errores
3. Verificar que el step "Upload Artifact" ejecutó correctamente

### Build Muy Lento

**Problema**: El pipeline tarda mucho.

**Causa**: Subir/bajar artefactos grandes (modelo YOLO ~6MB).

**Solución**:
- Es normal, el modelo debe incluirse
- En Azure Pipelines hosted: 5-10 minutos
- En GitHub Actions: 5-10 minutos
- Para acelerar, usar self-hosted agents con caché

### Release No se Crea Automáticamente

**GitHub Actions**:
1. Verificar que el tag empieza con `v` (ej: `v1.0.0`)
2. Verificar permisos de GitHub Token:
   - Ir a **Settings** → **Actions** → **General**
   - **Workflow permissions**: "Read and write permissions"
3. Verificar que el step "Create GitHub Release" ejecutó

**Azure Pipelines**:
1. El stage "Release" solo corre con tags `v*`
2. Verificar que el tag matchea el pattern
3. Verificar logs del pipeline

---

## Mejores Prácticas

### 1. Branches

- `main`/`master`: Código estable, listo para producción
- `develop`: Desarrollo activo
- `release/*`: Branches de release (ej: `release/1.0`)
- `feature/*`: Features nuevas
- `hotfix/*`: Bug fixes urgentes

### 2. Tags y Releases

- Crear tags **solo** desde `main`/`master`
- Usar formato `v*` (ej: `v1.0.0`)
- Incluir changelog en release notes
- Probar el ZIP antes de publicar

### 3. CI/CD

- Ejecutar build en cada PR
- Deployment automático solo a DEV/QA
- Deployment a producción manual (con aprobación)
- Mantener artefactos por al menos 30 días

### 4. Seguridad

- No incluir secrets en `web.config` del repo
- Usar variables de pipeline/environment para secrets
- Revisar permisos de service connections
- Rotar credenciales regularmente

---

## Recursos Adicionales

### Azure Pipelines

- [Documentación oficial](https://docs.microsoft.com/en-us/azure/devops/pipelines/)
- [YAML schema reference](https://docs.microsoft.com/en-us/azure/devops/pipelines/yaml-schema/)
- [Predefined variables](https://docs.microsoft.com/en-us/azure/devops/pipelines/build/variables)

### GitHub Actions

- [Documentación oficial](https://docs.github.com/en/actions)
- [Workflow syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)
- [Contexts](https://docs.github.com/en/actions/learn-github-actions/contexts)

### Git

- [Semantic Versioning](https://semver.org/)
- [Git Tagging](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
- [Git LFS](https://git-lfs.github.com/)
