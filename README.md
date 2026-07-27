# TutorLink

Backend de TutorLink: FastAPI + SQLAlchemy (PostgreSQL), con autenticación
JWT, perfiles de estudiante/tutor, catálogo de materias, disponibilidad,
reservas (bookings) y reseñas.

## Requisitos

- Python 3.12+
- PostgreSQL 16 (o Docker, ver más abajo)

## Instalación local

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt   # sólo si vas a correr los tests

uvicorn main:app --reload
```

La API queda disponible en `http://localhost:8000`, con documentación
interactiva Swagger UI en `http://localhost:8000/docs` (y ReDoc en `/redoc`),
generada automáticamente por FastAPI a partir de los schemas y tags de cada
endpoint en `main.py`.

## Testing y cobertura (Workshop 4)

La suite vive en `tests/` y está organizada en tres capas:

```
tests/
  conftest.py             # BD de pruebas (SQLite aislado) + fixtures compartidas
  unit/                   # funciones puras: hashing, JWT, validación Pydantic
  integration/            # capa ORM real: constraints, relaciones, cascadas
  acceptance/             # historias de usuario de punta a punta vía HTTP
```

Correr toda la suite con reporte de cobertura:

```bash
pytest
```

Esto genera automáticamente (configurado en `pytest.ini` / `.coveragerc`):
- Reporte en consola con líneas faltantes (`--cov-report=term-missing`)
- Reporte HTML navegable en `coverage_html/index.html`
- Reporte XML (`coverage.xml`) para integrarlo con CI/CD

Cobertura actual: **models.py y schemas.py 100%**, **security.py ~91%**,
**main.py ~92%**, **94.8% total** (55+ casos de prueba).

Para correr sólo una capa:

```bash
pytest tests/unit
pytest tests/integration
pytest tests/acceptance
```

> **Nota de portabilidad ORM:** los tests usan SQLite como base de datos de
> pruebas por simplicidad y velocidad. `models.py` define las llaves
> primarias como `BigInteger` (pensado para `BIGSERIAL` de Postgres); en
> SQLite eso rompe el autoincremento del rowid, así que `tests/conftest.py`
> registra un compilador (`@compiles`) que sólo afecta al dialecto SQLite de
> pruebas, sin tocar el esquema real de Postgres en producción.

## Despliegue con Docker

```bash
cp .env.example .env      # ajustar variables si es necesario
docker compose up --build
```

Esto levanta dos servicios:
- **db**: PostgreSQL 16, con volumen persistente y healthcheck.
- **backend**: la API de TutorLink (espera a que `db` esté saludable antes
  de arrancar), expuesta en `http://localhost:8000`.

Para correr la suite de tests dentro de un contenedor (perfil separado, no
se levanta con `docker compose up`):

```bash
docker compose run --rm tests
```
