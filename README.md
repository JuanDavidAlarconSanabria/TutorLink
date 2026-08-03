# TutorLink (Video [Drive](https://drive.google.com/drive/folders/10YdFIl-4PLr8f3aXT0r5H_wPVPovR7AD?usp=sharing).)

Autores:

- Diego Fernando Mellizo Pedraza
- Axel Gomez Moreno
- David Santiago Ramirez Sanchez

-----------------------------------
 Cambios hacia la versión 2.0 por:
 
- Juan David Alarcón Sanabria
- Juan Sebastian Moya Alvarez


Plataforma que conecta estudiantes con tutores independientes: autenticación,
perfiles de estudiante/tutor, catálogo de materias, disponibilidad, reservas
(bookings) y reseñas.

- **Backend** (este repo): FastAPI + SQLAlchemy + PostgreSQL
- **Mobile**: Expo + React Native — repo separado, ver sección 2

---

## 1. Backend (FastAPI + PostgreSQL)

### Estructura

```
backend/
├── database.py     # Conexión a PostgreSQL
├── models.py        # Modelos SQLAlchemy
├── schemas.py       # Esquemas Pydantic (validación de requests/responses)
├── security.py      # JWT + hashing de contraseñas (Argon2) + control de roles
├── main.py           # Endpoints de la API
└── tests/             # Suite de pruebas (unit / integration / acceptance)
```

### Endpoints principales

| Módulo | Endpoint | Descripción |
|---|---|---|
| Auth | `POST /auth/register`, `POST /auth/login` | Registro y login (JWT) |
| Subjects | `GET/POST /subjects` | Catálogo de materias |
| Perfiles | `GET/PUT /students/me/profile`, `GET/PUT /tutors/me/profile` | Perfil de estudiante / tutor |
| Disponibilidad | `POST /tutors/me/availability`, `GET /tutors/{id}/availability` | Horarios de un tutor |
| Discovery | `GET /tutors/search` | Buscar tutores por materia, rating, día |
| Bookings | `POST /bookings`, `GET /bookings/me`, `PATCH /bookings/{id}/{accept\|decline\|cancel\|reschedule\|complete}` | Ciclo completo de una reserva |
| Reviews | `POST /reviews`, `GET /tutors/{id}/reviews` | Reseñas de un tutor |

Documentación interactiva en `/docs` (Swagger) y `/redoc` una vez el servidor esté corriendo.

### Cómo ejecutar

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # ajusta DATABASE_URL y JWT_SECRET_KEY
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs

Requisitos: Python 3.11+, PostgreSQL 14+. Las tablas se crean automáticamente
al arrancar (`Base.metadata.create_all`); no hay migraciones manuales en desarrollo.

**Con Docker:**

```bash
cp .env.example .env
docker compose up --build
```

### Testing

```bash
pytest                  # toda la suite, con reporte de cobertura
pytest tests/unit        # sólo unit / integration / acceptance
```

Cobertura actual: **93.98% total** (79 casos de prueba) — El reporte HTML se
genera en `coverage_html/index.html` en cada corrida.

### Pendiente (Release 2/3)

Mensajería in-app (WebSocket), notificaciones por email, panel de
administración, integración de videollamada.

---

## 2. Mobile (Expo + React Native)

Repositorio separado: **https://github.com/diegomel07/tutorlink-mobile**

Estado: MVP de **Estudiante** completo (auth, buscar tutores, reservar, mis reservas).

### Estructura

```
app/                       # Rutas (expo-router, file-based)
  _layout.jsx              # Providers + carga de fuentes + Stack
  index.jsx                # Redirección según sesión
  login.jsx / register.jsx
  student.jsx               # Protegido, rol STUDENT
  tutor.jsx / admin.jsx     # Protegidos, muestran ComingSoon
src/
  api/client.js             # Cliente fetch hacia el backend
  context/AuthContext.jsx   # Auth con AsyncStorage
  components/               # Layout, TutorCard, BookingModal, ProtectedRoute
  pages/                     # LoginPage, RegisterPage, StudentDashboard, etc.
  theme/tokens.js           # Colores, radios, fuentes
```

### Cómo ejecutar

```bash
cd tutorlink-mobile
npm install
cp .env.example .env   # ajusta EXPO_PUBLIC_API_URL, ver tabla abajo
npx expo start
```

Escanea el QR con **Expo Go**, o presiona `i` / `a` en la terminal para abrir un simulador/emulador.

`localhost` no apunta a tu computador desde un emulador/dispositivo, así que `EXPO_PUBLIC_API_URL` cambia según dónde corras la app:

| Entorno | URL |
|---|---|
| Web (`npx expo start --web`) | `http://localhost:8000` |
| Emulador Android | `http://10.0.2.2:8000` |
| Simulador iOS | `http://localhost:8000` |
| Dispositivo físico (Expo Go) | `http://<IP-LOCAL>:8000`, misma red Wi-Fi que el celular |

---

## 3. Notas de diseño

- **Autenticación**: JWT (HS256) + Argon2 para contraseñas.
- **Doble-booking**: validación de solapamiento en `_check_overlap()` (`main.py`).
- **Producción**: reemplazar `Base.metadata.create_all()` por migraciones con Alembic, y usar un `JWT_SECRET_KEY` gestionado como secreto.
