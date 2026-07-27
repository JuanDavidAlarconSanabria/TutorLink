"""
Tests de aceptación adicionales — completan la cobertura de endpoints y de
ramas de error (permisos, validaciones, estados inválidos) que no quedaban
ejercitadas por las historias de usuario principales en test_user_stories.py.
"""
from tests.conftest import register_user, login_user, auth_headers


class TestSystemHealth:
    def test_health_check_endpoint(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestSubjectsCatalog:
    def test_list_subjects_is_public(self, client):
        resp = client.get("/subjects")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_only_admin_can_create_subject(self, student_client):
        client, headers = student_client
        resp = client.post("/subjects", json={"name": "Historia"}, headers=headers)
        assert resp.status_code == 403

    def test_admin_cannot_create_duplicate_subject(self, admin_client):
        client, headers = admin_client
        client.post("/subjects", json={"name": "Biología"}, headers=headers)
        dup = client.post("/subjects", json={"name": "Biología"}, headers=headers)
        assert dup.status_code == 400


class TestStudentProfileEndpoints:
    def test_get_and_update_own_student_profile(self, student_client):
        client, headers = student_client

        get_resp = client.get("/students/me/profile", headers=headers)
        assert get_resp.status_code == 200

        update_resp = client.put(
            "/students/me/profile",
            json={"learning_goals": "Aprobar cálculo", "preferred_schedule": "Tardes"},
            headers=headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["learning_goals"] == "Aprobar cálculo"

    def test_tutor_cannot_access_student_profile_endpoint(self, tutor_client):
        client, headers = tutor_client
        resp = client.get("/students/me/profile", headers=headers)
        assert resp.status_code == 403


class TestTutorProfileEndpoints:
    def test_get_own_tutor_profile(self, tutor_client):
        client, headers = tutor_client
        resp = client.get("/tutors/me/profile", headers=headers)
        assert resp.status_code == 200

    def test_get_tutor_availability_public_endpoint(self, tutor_client):
        client, headers = tutor_client
        client.post(
            "/tutors/me/availability",
            json={"day_of_week": "FRIDAY", "start_time": "09:00:00", "end_time": "11:00:00"},
            headers=headers,
        )
        me = client.get("/users/me", headers=headers).json()

        resp = client.get(f"/tutors/{me['id']}/availability")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_add_availability_rejects_end_before_start(self, tutor_client):
        client, headers = tutor_client
        resp = client.post(
            "/tutors/me/availability",
            json={"start_time": "11:00:00", "end_time": "09:00:00"},
            headers=headers,
        )
        assert resp.status_code == 400


class TestBookingErrorBranches:
    def _make_tutor(self, client):
        register_user(client, "tutor_err@tutorlink.example.com", "password123", "Tutor Err", "TUTOR")
        token = login_user(client, "tutor_err@tutorlink.example.com", "password123")
        headers = auth_headers(token)
        me = client.get("/users/me", headers=headers).json()
        return me["id"], headers

    def test_create_booking_rejects_end_before_start(self, client, student_client):
        student_c, student_headers = student_client
        tutor_id, _ = self._make_tutor(client)

        resp = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_id,
                "start_time": "2026-09-01T11:00:00",
                "end_time": "2026-09-01T10:00:00",
            },
            headers=student_headers,
        )
        assert resp.status_code == 400

    def test_create_booking_with_nonexistent_tutor_returns_404(self, client, student_client):
        student_c, student_headers = student_client
        resp = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": 999999,
                "start_time": "2026-09-01T10:00:00",
                "end_time": "2026-09-01T11:00:00",
            },
            headers=student_headers,
        )
        assert resp.status_code == 404

    def test_list_my_bookings_returns_bookings_for_both_roles(self, client, student_client):
        student_c, student_headers = student_client
        tutor_id, tutor_headers = self._make_tutor(client)

        student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_id,
                "start_time": "2026-09-02T10:00:00",
                "end_time": "2026-09-02T11:00:00",
            },
            headers=student_headers,
        )

        student_list = student_c.get("/bookings/me", headers=student_headers)
        tutor_list = client.get("/bookings/me", headers=tutor_headers)
        assert len(student_list.json()) == 1
        assert len(tutor_list.json()) == 1

    def test_tutor_can_decline_pending_booking(self, client, student_client):
        student_c, student_headers = student_client
        tutor_id, tutor_headers = self._make_tutor(client)

        booking = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_id,
                "start_time": "2026-09-03T10:00:00",
                "end_time": "2026-09-03T11:00:00",
            },
            headers=student_headers,
        ).json()

        decline_resp = client.patch(f"/bookings/{booking['id']}/decline", headers=tutor_headers)
        assert decline_resp.status_code == 200
        assert decline_resp.json()["status"] == "CANCELLED"

    def test_student_can_cancel_own_pending_booking(self, client, student_client):
        student_c, student_headers = student_client
        tutor_id, _ = self._make_tutor(client)

        booking = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_id,
                "start_time": "2026-09-04T10:00:00",
                "end_time": "2026-09-04T11:00:00",
            },
            headers=student_headers,
        ).json()

        cancel_resp = student_c.patch(f"/bookings/{booking['id']}/cancel", headers=student_headers)
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "CANCELLED"

    def test_other_user_cannot_cancel_someone_elses_booking(self, client, student_client):
        student_c, student_headers = student_client
        tutor_id, _ = self._make_tutor(client)

        booking = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_id,
                "start_time": "2026-09-05T10:00:00",
                "end_time": "2026-09-05T11:00:00",
            },
            headers=student_headers,
        ).json()

        register_user(client, "intruder@tutorlink.example.com", "password123", "Intruder", "STUDENT")
        intruder_token = login_user(client, "intruder@tutorlink.example.com", "password123")
        resp = client.patch(
            f"/bookings/{booking['id']}/cancel", headers=auth_headers(intruder_token)
        )
        assert resp.status_code == 403

    def test_reschedule_booking_to_a_free_slot(self, client, student_client):
        student_c, student_headers = student_client
        tutor_id, _ = self._make_tutor(client)

        booking = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_id,
                "start_time": "2026-09-06T10:00:00",
                "end_time": "2026-09-06T11:00:00",
            },
            headers=student_headers,
        ).json()

        resched_resp = student_c.patch(
            f"/bookings/{booking['id']}/reschedule",
            json={"start_time": "2026-09-06T14:00:00", "end_time": "2026-09-06T15:00:00"},
            headers=student_headers,
        )
        assert resched_resp.status_code == 200
        assert resched_resp.json()["status"] == "RESCHEDULED"

    def test_reschedule_rejects_end_before_start(self, client, student_client):
        student_c, student_headers = student_client
        tutor_id, _ = self._make_tutor(client)

        booking = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_id,
                "start_time": "2026-09-07T10:00:00",
                "end_time": "2026-09-07T11:00:00",
            },
            headers=student_headers,
        ).json()

        resp = student_c.patch(
            f"/bookings/{booking['id']}/reschedule",
            json={"start_time": "2026-09-07T15:00:00", "end_time": "2026-09-07T14:00:00"},
            headers=student_headers,
        )
        assert resp.status_code == 400

    def test_only_assigned_tutor_can_accept_booking(self, client, student_client):
        student_c, student_headers = student_client
        tutor_id, _ = self._make_tutor(client)
        other_tutor_id, other_tutor_headers = self._make_tutor2(client)

        booking = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_id,
                "start_time": "2026-09-08T10:00:00",
                "end_time": "2026-09-08T11:00:00",
            },
            headers=student_headers,
        ).json()

        resp = client.patch(f"/bookings/{booking['id']}/accept", headers=other_tutor_headers)
        assert resp.status_code == 403

    def _make_tutor2(self, client):
        register_user(client, "tutor_err2@tutorlink.example.com", "password123", "Tutor Err 2", "TUTOR")
        token = login_user(client, "tutor_err2@tutorlink.example.com", "password123")
        headers = auth_headers(token)
        me = client.get("/users/me", headers=headers).json()
        return me["id"], headers

    def test_cannot_accept_a_non_pending_booking_twice(self, client, student_client):
        student_c, student_headers = student_client
        tutor_id, tutor_headers = self._make_tutor(client)

        booking = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_id,
                "start_time": "2026-09-09T10:00:00",
                "end_time": "2026-09-09T11:00:00",
            },
            headers=student_headers,
        ).json()

        client.patch(f"/bookings/{booking['id']}/accept", headers=tutor_headers)
        second_accept = client.patch(f"/bookings/{booking['id']}/accept", headers=tutor_headers)
        assert second_accept.status_code == 400

    def test_cannot_complete_a_booking_that_is_not_confirmed(self, client, student_client):
        student_c, student_headers = student_client
        tutor_id, tutor_headers = self._make_tutor(client)

        booking = student_c.post(
            "/bookings",
            json={
                "tutor_user_id": tutor_id,
                "start_time": "2026-09-10T10:00:00",
                "end_time": "2026-09-10T11:00:00",
            },
            headers=student_headers,
        ).json()

        resp = client.patch(f"/bookings/{booking['id']}/complete", headers=tutor_headers)
        assert resp.status_code == 400
