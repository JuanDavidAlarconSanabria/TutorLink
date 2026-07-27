# TutorLink — Documentación de Modelos y Esquemas

Este documento describe el modelo de dominio (SQLAlchemy ORM, `models.py`) y los esquemas de la API (Pydantic, `schemas.py`) de TutorLink.

## Tabla de contenido

- [Enumeraciones](#enumeraciones)
- [Modelo de datos (ORM)](#modelo-de-datos-orm)
- [Diagrama de relaciones](#diagrama-de-relaciones)
- [Esquemas de la API (Pydantic)](#esquemas-de-la-api-pydantic)

---

## Enumeraciones

| Enum | Valores | Uso |
|---|---|---|
| `RoleEnum` | `STUDENT`, `TUTOR`, `ADMIN` | Rol del usuario dentro del sistema |
| `BookingStatus` | `PENDING`, `CONFIRMED`, `COMPLETED`, `CANCELLED`, `RESCHEDULED` | Estado de una reserva/sesión |
| `DayOfWeek` | `MONDAY` … `SUNDAY` | Día de la semana para disponibilidad recurrente |

---

## Modelo de datos (ORM)


### `User` (tabla `users`)

Usuario base del sistema (estudiante, tutor o admin).

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigInteger (PK) | |
| `email` | String(255) | único, indexado |
| `password_hash` | String(255) | |
| `role` | Enum(`RoleEnum`) | |
| `full_name` | String(255) | |
| `created_at` | DateTime | default: ahora (UTC) |
| `updated_at` | DateTime | se actualiza automáticamente |
| `is_active` | Boolean | default: `True` |

**Relaciones:**
- `student_profile` → `StudentProfile` (1:1, cascada delete-orphan)
- `tutor_profile` → `TutorProfile` (1:1, cascada delete-orphan)
- `bookings_as_student` → `Booking` (1:N, vía `student_user_id`)
- `bookings_as_tutor` → `Booking` (1:N, vía `tutor_user_id`)
- `sent_messages` / `received_messages` → `Message` (1:N)

---

### `StudentProfile` (tabla `student_profiles`)

Perfil extendido de un usuario con rol `STUDENT`.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigInteger (PK) | |
| `user_id` | BigInteger (FK → `users.id`) | único (1:1) |
| `learning_goals` | Text | opcional |
| `preferred_schedule` | Text | opcional, JSON serializado como texto |

---

### `TutorProfile` (tabla `tutor_profiles`)

Perfil extendido de un usuario con rol `TUTOR`.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigInteger (PK) | |
| `user_id` | BigInteger (FK → `users.id`) | único (1:1) |
| `bio` | Text | opcional |
| `qualifications` | Text | opcional |
| `hourly_rate` | Numeric(10,2) | default: 0 |
| `average_rating` | Numeric(3,2) | default: 0 |

**Relaciones:**
- `subjects` → `Subject` (N:M, vía `tutor_subjects`)
- `availabilities` → `Availability` (1:N, cascada delete-orphan)

---

### `Subject` (tabla `subjects`)

Materia/tema que un tutor puede enseñar.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | Integer (PK) | |
| `name` | String(120) | único |

**Relaciones:**
- `tutors` → `TutorProfile` (N:M, vía `tutor_subjects`)

---

### `tutor_subjects` (tabla de asociación)

Relación muchos-a-muchos entre tutores y materias.

| Campo | Tipo |
|---|---|
| `tutor_profile_id` | FK → `tutor_profiles.id` (PK compuesta) |
| `subject_id` | FK → `subjects.id` (PK compuesta) |

---

### `Availability` (tabla `availabilities`)

Franjas horarias en las que un tutor está disponible.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigInteger (PK) | |
| `tutor_profile_id` | BigInteger (FK → `tutor_profiles.id`) | |
| `day_of_week` | Enum(`DayOfWeek`), nullable | `null` si es fecha específica |
| `start_time` | Time | |
| `end_time` | Time | debe ser mayor que `start_time` (constraint `ck_availability_time_order`) |
| `is_recurring` | Boolean | default: `True` |
| `specific_date` | Date, nullable | usada cuando `is_recurring = False` |
| `is_available` | Boolean | default: `True` |

---

### `Booking` (tabla `bookings`)

Reserva de una sesión entre estudiante y tutor.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigInteger (PK) | |
| `student_user_id` | BigInteger (FK → `users.id`) | |
| `tutor_user_id` | BigInteger (FK → `users.id`) | |
| `subject_id` | Integer (FK → `subjects.id`), nullable | |
| `start_time` | DateTime | |
| `end_time` | DateTime | debe ser mayor que `start_time` (constraint `ck_booking_time_order`) |
| `status` | Enum(`BookingStatus`) | default: `PENDING` |
| `notes` | Text, nullable | |
| `created_at` | DateTime | default: ahora (UTC) |

**Relaciones:**
- `student`, `tutor` → `User`
- `subject` → `Subject`
- `review` → `Review` (1:1, cascada delete-orphan)
- `messages` → `Message` (1:N)

---

### `Review` (tabla `reviews`)

Calificación y comentario que un estudiante deja sobre una reserva completada.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigInteger (PK) | |
| `booking_id` | BigInteger (FK → `bookings.id`) | único (1:1) |
| `student_user_id` | BigInteger (FK → `users.id`) | |
| `rating` | Integer | entre 1 y 5 (constraint `ck_review_rating_range`) |
| `comment` | Text, nullable | |
| `created_at` | DateTime | default: ahora (UTC) |
| `is_flagged` | Boolean | default: `False`, para moderación |

---

### `Message` (tabla `messages`)

Mensajería entre usuarios, opcionalmente ligada a una reserva. *(Modelo listo; endpoints se implementarán en Release 2.)*

| Campo | Tipo | Notas |
|---|---|---|
| `id` | BigInteger (PK) | |
| `sender_user_id` | BigInteger (FK → `users.id`) | |
| `receiver_user_id` | BigInteger (FK → `users.id`) | |
| `booking_id` | BigInteger (FK → `bookings.id`), nullable | |
| `content` | Text | |
| `sent_at` | DateTime | default: ahora (UTC) |
| `is_read` | Boolean | default: `False` |

---

## Diagrama de relaciones

```
User (1) ──── (1) StudentProfile
User (1) ──── (1) TutorProfile ──── (N:M) Subject
                     │
                     └── (1:N) Availability

User (student) (1:N) ──┐
                        ├── Booking ──── (0/1) Review
User (tutor)    (1:N) ──┘        │
                                  └── (1:N) Message

User (sender/receiver) (1:N) ──── Message
```

---

## Esquemas de la API (Pydantic)


### Auth / Usuario

| Esquema | Campos | Propósito |
|---|---|---|
| `UserCreate` | `email`, `password` (min 8), `full_name`, `role` | Registro de usuario |
| `UserOut` | `id`, `email`, `full_name`, `role`, `created_at` | Respuesta pública de usuario |
| `Token` | `access_token`, `token_type` (default `"bearer"`) | Respuesta de login |
| `TokenData` | `user_id` (opcional) | Payload interno del JWT |

### Subject

| Esquema | Campos | Propósito |
|---|---|---|
| `SubjectCreate` | `name` | Crear materia |
| `SubjectOut` | `id`, `name` | Respuesta de materia |

### Perfil de estudiante (FR-03)

| Esquema | Campos | Propósito |
|---|---|---|
| `StudentProfileUpsert` | `learning_goals`, `preferred_schedule` (ambos opcionales) | Crear/actualizar perfil |
| `StudentProfileOut` | `id`, `user_id`, `learning_goals`, `preferred_schedule` | Respuesta de perfil |

### Perfil de tutor (FR-02)

| Esquema | Campos | Propósito |
|---|---|---|
| `TutorProfileUpsert` | `bio`, `qualifications`, `hourly_rate` (default 0), `subject_ids` (lista) | Crear/actualizar perfil |
| `TutorProfileOut` | `id`, `user_id`, `bio`, `qualifications`, `hourly_rate`, `average_rating`, `subjects` | Respuesta de perfil completo |
| `TutorSearchResult` | `user_id`, `full_name`, `bio`, `hourly_rate`, `average_rating`, `subjects` | Resultado de búsqueda de tutores |

### Disponibilidad

| Esquema | Campos | Propósito |
|---|---|---|
| `AvailabilityCreate` | `day_of_week`, `start_time`, `end_time`, `is_recurring` (default `True`), `specific_date` | Crear franja de disponibilidad |
| `AvailabilityOut` | + `id`, `tutor_profile_id`, `is_available` | Respuesta de disponibilidad |

### Reserva (FR-05, FR-06)

| Esquema | Campos | Propósito |
|---|---|---|
| `BookingCreate` | `tutor_user_id`, `subject_id` (opcional), `start_time`, `end_time`, `notes` | Crear reserva |
| `BookingOut` | `id`, `student_user_id`, `tutor_user_id`, `subject_id`, `start_time`, `end_time`, `status`, `notes`, `created_at` | Respuesta de reserva |
| `BookingReschedule` | `start_time`, `end_time` | Reprogramar reserva |

### Review (FR-10)

| Esquema | Campos | Propósito |
|---|---|---|
| `ReviewCreate` | `booking_id`, `rating` (1–5), `comment` (opcional) | Crear reseña |
| `ReviewOut` | `id`, `booking_id`, `student_user_id`, `rating`, `comment`, `created_at`, `is_flagged` | Respuesta de reseña |
