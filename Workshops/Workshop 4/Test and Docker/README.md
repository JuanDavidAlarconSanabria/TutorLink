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

### Resultados de la última ejecución

\```
75 passed in 27.47s
\```

| Capa | Archivo | Casos | Qué valida |
|---|---|---|---|
| Unitaria | `tests/unit/test_security.py` | 10 | Hashing de contraseñas (Argon2), generación/decodificación de JWT |
| Unitaria | `tests/unit/test_schemas.py` | 20 | Validación Pydantic: email, longitud de password, roles, rangos de rating |
| Integración | `tests/integration/test_orm.py` | 12 | Constraints (UNIQUE, CHECK), relaciones many-to-many, cascadas de borrado |
| Aceptación | `tests/acceptance/test_user_stories.py` | 15 | Historias de usuario completas de punta a punta (registro, perfil de tutor, búsqueda, ciclo de reserva, reseñas) |
| Aceptación | `tests/acceptance/test_additional_coverage.py` | 18 | Ramas de error y endpoints complementarios (permisos 403, reservas 404/409/400, health check) |
| **Total** | | **75** | |

### Reporte de cobertura

\```
Name          Stmts   Miss   Cover   Missing
--------------------------------------------
database.py      12      4  66.67%   23-27
main.py         227     18  92.07%   124, 138-139, 156, 178-180, 261, 264,
                                      356, 387, 389, 407, 424, 428, 446, 472, 476
models.py       115      0 100.00%
schemas.py      107      0 100.00%
security.py      43      4  90.70%   53-55, 59
--------------------------------------------
TOTAL           504     26  94.84%
\```

- **models.py** y **schemas.py**: 100% — toda la lógica de dominio y validación está cubierta.
- **main.py**: 92% — las líneas sin cubrir son ramas de error muy específicas (algunos `404` compuestos y validaciones redundantes) que no forman parte de ninguna historia de usuario priorizada.
- **database.py**: 66% — las líneas sin cubrir (23-27) son el manejo de cierre de sesión dentro del generador `get_db`, que sólo se ejecuta en el ciclo de vida real de una petición HTTP contra Postgres, no en el entorno de pruebas con SQLite.
- **security.py**: 91% — falta cubrir directamente `get_current_user`/`require_role` como funciones aisladas (sí están cubiertas indirectamente por cada test de aceptación que usa autenticación).

El reporte HTML navegable (línea por línea) se genera en `coverage_html/index.html`
cada vez que se ejecuta `pytest`, y el XML (`coverage.xml`) queda listo para
integrarse a un pipeline de CI/CD.

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
