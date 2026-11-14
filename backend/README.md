# AstroHealth backend

FastAPI service for the AstroHealth MVP. Response shapes follow
[`docs/api_contract.md`](../docs/api_contract.md) v0.1.0.

- [English](#english)
- [Español](#español)

## English

### Current scope

BACKEND-01 (#3) only: service initialization and `GET /api/health`. There is no
database, no astronaut/readings/journal/summary/alerts endpoint, no analysis,
and no authentication yet.

### Requirements

- Python 3.13 (verified with 3.13.3 on Windows 11). The pinned dependencies
  require Python 3.11 or newer; other versions have not been verified.
- Runtime dependencies are pinned in `requirements.txt`; test dependencies in
  `requirements-dev.txt`, which includes the runtime file.

### Setup (PowerShell, from the repository root)

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
```

The commands below call the virtual environment's interpreter by path, so
activating it is optional. On macOS/Linux use `.venv/bin/python` instead.

### Run (from the `backend` folder)

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

| What | URL |
| --- | --- |
| Health | <http://localhost:8000/api/health> |
| Swagger UI | <http://localhost:8000/docs> |
| OpenAPI | <http://localhost:8000/openapi.json> |

The frontend uses `VITE_API_BASE_URL=http://localhost:8000`. Uvicorn listens on
`127.0.0.1` (IPv4). On Windows, command-line clients that try IPv6 first can
take about 2 seconds to connect through `localhost`; `http://127.0.0.1:8000`
avoids that delay.

### CORS

Allowed origins come from the `ASTROHEALTH_CORS_ORIGINS` environment variable:
a comma-separated list of exact origins. When it is unset or blank, the only
allowed origin is `http://localhost:5173`. The wildcard `*` is rejected at
startup.

```powershell
$env:ASTROHEALTH_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
```

### Checks (from the `backend` folder)

```powershell
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m pip check
```

Warnings are treated as test failures (`pytest.ini`).

## Español

### Alcance actual

Solo BACKEND-01 (#3): inicialización del servicio y `GET /api/health`. Todavía
no hay base de datos, endpoints de astronautas/readings/journal/summary/alerts,
análisis ni autenticación.

### Requisitos

- Python 3.13 (verificado con 3.13.3 en Windows 11). Las dependencias fijadas
  exigen Python 3.11 o superior; no se han verificado otras versiones.
- Las dependencias de ejecución están fijadas en `requirements.txt`; las de
  pruebas en `requirements-dev.txt`, que incluye el archivo de ejecución.

### Instalación (PowerShell, desde la raíz del repositorio)

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
```

Los comandos siguientes invocan el intérprete del entorno virtual por su ruta,
así que activarlo es opcional. En macOS/Linux usa `.venv/bin/python`.

### Arranque (desde la carpeta `backend`)

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

| Qué | Dirección |
| --- | --- |
| Estado | <http://localhost:8000/api/health> |
| Swagger UI | <http://localhost:8000/docs> |
| OpenAPI | <http://localhost:8000/openapi.json> |

El frontend usa `VITE_API_BASE_URL=http://localhost:8000`. Uvicorn escucha en
`127.0.0.1` (IPv4). En Windows, los clientes de línea de comandos que prueban
IPv6 primero pueden tardar unos 2 segundos en conectar mediante `localhost`;
`http://127.0.0.1:8000` evita esa demora.

### CORS

Los orígenes permitidos se leen de la variable de entorno
`ASTROHEALTH_CORS_ORIGINS`: una lista de orígenes exactos separados por comas.
Si no está definida o está vacía, el único origen permitido es
`http://localhost:5173`. El comodín `*` se rechaza al arrancar.

```powershell
$env:ASTROHEALTH_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
```

### Comprobaciones (desde la carpeta `backend`)

```powershell
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m pip check
```

Los avisos se tratan como fallos de prueba (`pytest.ini`).
