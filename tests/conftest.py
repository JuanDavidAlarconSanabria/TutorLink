"""
Configuración compartida de pytest para TutorLink.

IMPORTANTE sobre la base de datos de pruebas:
-----------------------------------------------
`database.py` lee `DATABASE_URL` en tiempo de import y `main.py` ejecuta
`Base.metadata.create_all(bind=engine)` también en tiempo de import. Por eso
las variables de entorno de prueba se fijan ANTES de importar cualquier
módulo de la aplicación (database, models, security, main).

Se usa SQLite (archivo temporal, no `:memory:`) como base de datos de pruebas:
- Es liviana y no requiere levantar un servidor Postgres para correr la suite.
- Al ser un archivo, todas las conexiones dentro de una misma prueba ven el
  mismo estado (evita las sorpresas de `:memory:` con pools multi-conexión).
- Respeta las mismas foreign keys y CHECK constraints que se validan en
  `tests/integration`, ya que SQLite los soporta de forma nativa.

La suite de integración real contra PostgreSQL (con Testcontainers) se corre
en el pipeline de CI/CD (ver .github/workflows/ci.yml), donde sí se dispone
de un contenedor de Postgres.
"""
import os
import tempfile

os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-not-for-production")

_TMP_DIR = tempfile.mkdtemp(prefix="tutorlink_test_")
_TEST_DB_PATH = os.path.join(_TMP_DIR, "test_tutorlink.db")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TEST_DB_PATH}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event, BigInteger  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(BigInteger, "sqlite")
def _compile_big_integer_as_integer_on_sqlite(type_, compiler, **kw):
    """
    Nota de portabilidad ORM (Postgres -> SQLite):
    models.py usa BigInteger para las llaves primarias, que en Postgres se
    traduce a BIGSERIAL con autoincremento. En SQLite, una columna sólo se
    convierte en alias del rowid (y por tanto autoincrementa) si su tipo
    declarado es exactamente "INTEGER"; con "BIGINT" pierde ese comportamiento
    y las inserciones fallan por violar NOT NULL en la PK.
    Este compilador sólo aplica al dialecto "sqlite" usado en pruebas: no
    modifica el esquema real de Postgres en producción.

    CRÍTICO: este decorador debe registrarse ANTES de importar `main`, porque
    `main.py` ejecuta `Base.metadata.create_all(bind=engine)` en tiempo de
    import; si el parche llegara después, la primera creación de tablas
    quedaría con el DDL roto (BIGINT) y ese esquema persistiría hasta el
    primer drop_all/create_all del ciclo de fixtures.
    """
    return "INTEGER"


import database  # noqa: E402
import models  # noqa: E402  (registra las tablas en Base.metadata)
from main import app  # noqa: E402


@event.listens_for(database.engine, "connect")
def _enable_sqlite_fk(dbapi_connection, connection_record):
    """SQLite no aplica foreign keys por defecto; se activa explícitamente."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


@pytest.fixture(scope="function")
def db_session():
    """Entrega una sesión de BD con esquema limpio para cada prueba."""
    database.Base.metadata.create_all(bind=database.engine)
    session = database.SessionLocal()
    try:
        yield session
    finally:
        session.close()
        database.Base.metadata.drop_all(bind=database.engine)


@pytest.fixture(scope="function")
def client(db_session):
    """TestClient de FastAPI con la dependencia get_db sobreescrita."""

    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[database.get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers de dominio reutilizables entre módulos de tests
# ---------------------------------------------------------------------------
def register_user(client, email, password, full_name, role):
    resp = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": full_name,
            "role": role,
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def login_user(client, email, password):
    resp = client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def student_client(client):
    """Cliente autenticado como estudiante recién registrado."""
    register_user(client, "student1@tutorlink.example.com", "password123", "Sofía Estudiante", "STUDENT")
    token = login_user(client, "student1@tutorlink.example.com", "password123")
    return client, auth_headers(token)


@pytest.fixture
def tutor_client(client):
    """Cliente autenticado como tutor recién registrado."""
    register_user(client, "tutor1@tutorlink.example.com", "password123", "Tomás Tutor", "TUTOR")
    token = login_user(client, "tutor1@tutorlink.example.com", "password123")
    return client, auth_headers(token)


@pytest.fixture
def admin_client(client):
    """Cliente autenticado como admin recién registrado."""
    register_user(client, "admin1@tutorlink.example.com", "password123", "Ana Admin", "ADMIN")
    token = login_user(client, "admin1@tutorlink.example.com", "password123")
    return client, auth_headers(token)
