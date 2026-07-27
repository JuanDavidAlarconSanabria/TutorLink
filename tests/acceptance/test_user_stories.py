"""
Tests de aceptación — Historias de usuario clave del MVP de TutorLink.

Cada clase corresponde a una historia de usuario del User Story Mapping
(Workshop 2/3) y la ejercita de punta a punta a través de la API HTTP real
(FastAPI TestClient), tal como la consumiría el frontend.

US-S1: Como estudiante, quiero registrarme e iniciar sesión para acceder a la plataforma.
US-T1: Como tutor, quiero crear mi perfil y publicar mi disponibilidad para que los
       estudiantes me encuentren.
US-S2: Como estudiante, quiero buscar tutores por materia para elegir con quién estudiar.
US-S3/US-T2: Como estudiante, quiero reservar una sesión con un tutor, y como tutor
       quiero poder aceptarla o rechazarla.
US-S4: Como estudiante, quiero calificar una sesión completada para dejar una reseña.
"""
from tests.conftest import register_user, login_user, auth_headers


class TestOnboardingUserStory:
    """US-S1 — Registro e inicio de sesión."""

    def test_student_can_register_login_and_fetch_own_profile(self, client):
        register_user(client, "ana@tutorlink.example.com", "password123", "Ana Pérez", "STUDENT")

        token = login_user(client, "ana@tutorlink.example.com", "password123")

        me = client.get("/users/me", headers=auth_headers(token))
        assert me.status_code == 200
        body = me.json()
        assert body["email"] == "ana@tutorlink.example.com"
        assert body["role"] == "STUDENT"

    def test_cannot_register_same_email_twice(self, client):
        register_user(client, "dup@tutorlink.example.com", "password123", "Dup User", "STUDENT")
        resp = client.post(
            "/auth/register",
            json={
                "email": "dup@tutorlink.example.com",
                "password": "password123",
                "full_name": "Dup User 2",
                "role": "STUDENT",
            },
        )
        assert resp.status_code == 400

    def test_login_with_wrong_password_is_rejected(self, client):
        register_user(client, "wrongpass@tutorlink.example.com", "password123", "User", "STUDENT")
        resp = client.post(
            "/auth/login",
            data={"username": "wrongpass@tutorlink.example.com", "password": "incorrecta"},
        )
        assert resp.status_code == 401

    def test_accessing_protected_route_without_token_is_unauthorized(self, client):
        resp = client.get("/users/me")
        assert resp.status_code == 401


class TestTutorProfileAndAvailabilityUserStory:
    """US-T1 — Perfil de tutor y disponibilidad."""

    def test_tutor_can_set_up_profile_and_publish_availability(self, tutor_client):
        client, headers = tutor_client

        profile_resp = client.put(
            "/tutors/me/profile",
            json={
                "bio": "Ingeniero con 5 años dando tutorías de cálculo",
                "qualifications": "MSc en Matemáticas Aplicadas",
                "hourly_rate": 30000,
                "subject_ids": [],
            },
            headers=headers,
        )
        assert profile_resp.status_code == 200
        assert profile_resp.json()["bio"].startswith("Ingeniero")

        availability_resp = client.post(
            "/tutors/me/availability",
            json={
                "day_of_week": "MONDAY",
                "start_time": "14:00:00",
                "end_time": "18:00:00",
                "is_recurring": True,
            },
            headers=headers,
        )
        assert availability_resp.status_code == 201
        assert availability_resp.json()["day_of_week"] == "MONDAY"

    def test_only_tutors_can_publish_availability(self, student_client):
        client, headers = student_client
        resp = client.post(
            "/tutors/me/availability",
            json={"start_time": "14:00:00", "end_time": "15:00:00"},
            headers=headers,
        )
        assert resp.status_code == 403


class TestDiscoveryUserStory:
    """US-S2 — Búsqueda de tutores por materia."""

    def test_student_can_find_tutor_by_subject(self, client, admin_client, tutor_client):
        _, admin_headers = admin_client
        tutor_c, tutor_headers = tutor_client

        subject_resp = client.post(
            "/subjects", json={"name": "Cálculo Diferencial"}, headers=admin_headers
        )
        assert subject_resp.status_code == 200
        subject_id = subject_resp.json()["id"]

        tutor_c.put(
            "/tutors/me/profile",
            json={"bio": "Experto en cálculo", "hourly_rate": 20000, "subject_ids": [subject_id]},
            headers=tutor_headers,
        )

        search_resp = client.get("/tutors/search", params={"subject": "Cálculo"})
        assert search_resp.status_code == 200
        results = search_resp.json()
        assert len(results) == 1
        assert results[0]["subjects"][0]["name"] == "Cálculo Diferencial"

    def test_search_with_no_matching_subject_returns_empty_list(self, client):
        resp = client.get("/tutors/search", params={"subject": "Materia Inexistente"})
        assert resp.status_code == 200
        assert resp.json() == []


class TestBookingLifecycleUserStory:
    """US-S3 / US-T2 — Reservar una sesión y que el tutor la gestione."""

    def _setup_tutor_with_profile(self, client):
        register_user(client, "tutor_booking@tutorlink.example.com", "password123", "Tutor Booking", "TUTOR")
        tutor_token = login_user(client, "tutor_booking@tutorlink.example.com", "password123")
        tutor_headers = auth_headers(tutor_token)
        client.put(
            "/tutors/me/profile",
            json={"bio": "Bio", "hourly_rate": 15000, "subject_ids": []},
            headers=tutor_headers,
        )
        me = client.get("/users/me", headers=tutor_headers).json()
        return me["id"], tutor_headers

    def test_student_books_session_and_tutor_accepts_it(self, client, student_client):
        student_c, student_headers = student_client
        tutor_user_id, tutor_headers = self._setup_tutor_with_profile(client)

        booking_resp = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_user_id,
                "start_time": "2026-08-10T10:00:00",
                "end_time": "2026-08-10T11:00:00",
                "notes": "Primera sesión de refuerzo",
            },
            headers=student_headers,
        )
        assert booking_resp.status_code == 201
        booking = booking_resp.json()
        assert booking["status"] == "PENDING"

        accept_resp = client.patch(
            f"/bookings/{booking['id']}/accept", headers=tutor_headers
        )
        assert accept_resp.status_code == 200
        assert accept_resp.json()["status"] == "CONFIRMED"

    def test_cannot_book_overlapping_slot_with_same_tutor(self, client, student_client):
        student_c, student_headers = student_client
        tutor_user_id, _ = self._setup_tutor_with_profile(client)

        first = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_user_id,
                "start_time": "2026-08-11T10:00:00",
                "end_time": "2026-08-11T11:00:00",
            },
            headers=student_headers,
        )
        assert first.status_code == 201

        overlapping = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_user_id,
                "start_time": "2026-08-11T10:30:00",
                "end_time": "2026-08-11T11:30:00",
            },
            headers=student_headers,
        )
        assert overlapping.status_code == 409

    def test_full_lifecycle_booking_to_completed_session(self, client, student_client):
        student_c, student_headers = student_client
        tutor_user_id, tutor_headers = self._setup_tutor_with_profile(client)

        booking = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_user_id,
                "start_time": "2026-08-12T09:00:00",
                "end_time": "2026-08-12T10:00:00",
            },
            headers=student_headers,
        ).json()

        client.patch(f"/bookings/{booking['id']}/accept", headers=tutor_headers)
        completed = client.patch(f"/bookings/{booking['id']}/complete", headers=tutor_headers)

        assert completed.status_code == 200
        assert completed.json()["status"] == "COMPLETED"


class TestReviewUserStory:
    """US-S4 — Dejar una reseña de una sesión completada."""

    def _complete_a_booking(self, client, student_client):
        student_c, student_headers = student_client
        register_user(client, "tutor_review@tutorlink.example.com", "password123", "Tutor Review", "TUTOR")
        tutor_token = login_user(client, "tutor_review@tutorlink.example.com", "password123")
        tutor_headers = auth_headers(tutor_token)
        tutor_user = client.get("/users/me", headers=tutor_headers).json()

        booking = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_user["id"],
                "start_time": "2026-08-15T09:00:00",
                "end_time": "2026-08-15T10:00:00",
            },
            headers=student_headers,
        ).json()
        client.patch(f"/bookings/{booking['id']}/accept", headers=tutor_headers)
        client.patch(f"/bookings/{booking['id']}/complete", headers=tutor_headers)
        return booking, tutor_user

    def test_student_can_review_completed_session_and_tutor_rating_updates(self, client, student_client):
        student_c, student_headers = student_client
        booking, tutor_user = self._complete_a_booking(client, student_client)

        review_resp = student_c.post(
            "/reviews",
            json={"booking_id": booking["id"], "rating": 5, "comment": "Excelente tutor"},
            headers=student_headers,
        )
        assert review_resp.status_code == 201

        reviews = client.get(f"/tutors/{tutor_user['id']}/reviews")
        assert reviews.status_code == 200
        assert len(reviews.json()) == 1
        assert reviews.json()[0]["rating"] == 5

    def test_cannot_review_a_session_that_is_not_completed(self, client, student_client):
        student_c, student_headers = student_client
        register_user(client, "tutor_pending@tutorlink.example.com", "password123", "Tutor Pending", "TUTOR")
        tutor_token = login_user(client, "tutor_pending@tutorlink.example.com", "password123")
        tutor_user = client.get("/users/me", headers=auth_headers(tutor_token)).json()

        booking = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_user["id"],
                "start_time": "2026-08-16T09:00:00",
                "end_time": "2026-08-16T10:00:00",
            },
            headers=student_headers,
        ).json()

        review_resp = student_c.post(
            "/reviews",
            json={"booking_id": booking["id"], "rating": 5},
            headers=student_headers,
        )
        assert review_resp.status_code == 400
