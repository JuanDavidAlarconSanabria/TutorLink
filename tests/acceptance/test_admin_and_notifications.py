import notifications


def test_admin_dashboard_and_subject_crud(client, admin_client):
    _, headers = admin_client

    resp = client.get("/admin/dashboard", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["students"] >= 0
    assert body["tutors"] >= 0
    assert body["subjects"] >= 0
    assert body["bookings"] >= 0

    resp = client.post("/admin/subjects", json={"name": "Algebra"}, headers=headers)
    assert resp.status_code == 201, resp.text
    subject = resp.json()
    assert subject["name"] == "Algebra"

    resp = client.get("/admin/subjects", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert any(item["id"] == subject["id"] for item in data)

    resp = client.put(
        f"/admin/subjects/{subject['id']}",
        json={"name": "Cálculo"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["name"] == "Cálculo"

    duplicate = client.post("/admin/subjects", json={"name": "Cálculo"}, headers=headers)
    assert duplicate.status_code == 400

    resp = client.delete(f"/admin/subjects/{subject['id']}", headers=headers)
    assert resp.status_code == 204


def test_admin_student_and_tutor_crud_and_role_validation(client, admin_client):
    _, headers = admin_client

    student_resp = client.post(
        "/admin/students",
        json={
            "email": "student.admin@test.com",
            "password": "password123",
            "full_name": "Student Admin",
        },
        headers=headers,
    )
    assert student_resp.status_code == 201, student_resp.text
    student = student_resp.json()

    student_list = client.get("/admin/students", headers=headers)
    assert student_list.status_code == 200
    assert any(item["id"] == student["id"] for item in student_list.json())

    student_get = client.get(f"/admin/students/{student['id']}", headers=headers)
    assert student_get.status_code == 200
    assert student_get.json()["email"] == "student.admin@test.com"

    update_resp = client.put(
        f"/admin/students/{student['id']}",
        json={
            "email": "student.admin.updated@test.com",
            "full_name": "Student Admin Updated",
            "password": "newpassword123",
            "is_active": False,
        },
        headers=headers,
    )
    assert update_resp.status_code == 200, update_resp.text
    updated_student = update_resp.json()
    assert updated_student["email"] == "student.admin.updated@test.com"
    assert updated_student["full_name"] == "Student Admin Updated"

    duplicate_email_resp = client.post(
        "/admin/students",
        json={
            "email": "student.admin.updated@test.com",
            "password": "password123",
            "full_name": "Duplicate Student",
        },
        headers=headers,
    )
    assert duplicate_email_resp.status_code == 400

    wrong_role_resp = client.get(f"/admin/students/{1}", headers=headers)
    assert wrong_role_resp.status_code == 400

    tutor_resp = client.post(
        "/admin/tutors",
        json={
            "email": "tutor.admin@test.com",
            "password": "password123",
            "full_name": "Tutor Admin",
        },
        headers=headers,
    )
    assert tutor_resp.status_code == 201, tutor_resp.text
    tutor = tutor_resp.json()

    tutor_get = client.get(f"/admin/tutors/{tutor['id']}", headers=headers)
    assert tutor_get.status_code == 200
    tutor_profile = tutor_get.json()
    assert tutor_profile["user_id"] == tutor["id"]

    tutor_update = client.put(
        f"/admin/tutors/{tutor['id']}",
        json={
            "email": "tutor.admin.updated@test.com",
            "full_name": "Tutor Admin Updated",
            "password": "newpassword123",
            "is_active": False,
        },
        headers=headers,
    )
    assert tutor_update.status_code == 200, tutor_update.text
    assert tutor_update.json()["email"] == "tutor.admin.updated@test.com"

    client.delete(f"/admin/students/{student['id']}", headers=headers)
    client.delete(f"/admin/tutors/{tutor['id']}", headers=headers)

    get_student_after_delete = client.get(f"/admin/students/{student['id']}", headers=headers)
    assert get_student_after_delete.status_code == 404


def test_admin_booking_crud_and_validation(client, admin_client):
    _, headers = admin_client

    subject_resp = client.post("/admin/subjects", json={"name": "Biología"}, headers=headers)
    assert subject_resp.status_code == 201, subject_resp.text
    subject_id = subject_resp.json()["id"]

    student_resp = client.post(
        "/admin/students",
        json={
            "email": "booking.student@test.com",
            "password": "password123",
            "full_name": "Booking Student",
        },
        headers=headers,
    )
    assert student_resp.status_code == 201, student_resp.text
    student_id = student_resp.json()["id"]

    tutor_resp = client.post(
        "/admin/tutors",
        json={
            "email": "booking.tutor@test.com",
            "password": "password123",
            "full_name": "Booking Tutor",
        },
        headers=headers,
    )
    assert tutor_resp.status_code == 201, tutor_resp.text
    tutor_id = tutor_resp.json()["id"]

    create_booking_resp = client.post(
        "/admin/bookings",
        json={
            "student_user_id": student_id,
            "tutor_user_id": tutor_id,
            "subject_id": subject_id,
            "start_time": "2026-08-03T09:00:00",
            "end_time": "2026-08-03T10:00:00",
            "notes": "Needs help with biology",
            "status": "PENDING",
        },
        headers=headers,
    )
    assert create_booking_resp.status_code == 201, create_booking_resp.text
    booking = create_booking_resp.json()

    list_bookings = client.get("/admin/bookings", headers=headers)
    assert list_bookings.status_code == 200
    assert any(item["id"] == booking["id"] for item in list_bookings.json())

    get_booking = client.get(f"/admin/bookings/{booking['id']}", headers=headers)
    assert get_booking.status_code == 200
    assert get_booking.json()["id"] == booking["id"]

    update_booking = client.put(
        f"/admin/bookings/{booking['id']}",
        json={
            "notes": "Updated notes",
            "status": "CONFIRMED",
        },
        headers=headers,
    )
    assert update_booking.status_code == 200, update_booking.text
    assert update_booking.json()["status"] == "CONFIRMED"

    invalid_booking = client.get("/admin/bookings/999999", headers=headers)
    assert invalid_booking.status_code == 404

    invalid_create = client.post(
        "/admin/bookings",
        json={
            "student_user_id": 999999,
            "tutor_user_id": tutor_id,
            "subject_id": subject_id,
            "start_time": "2026-08-03T09:00:00",
            "end_time": "2026-08-03T10:00:00",
            "status": "PENDING",
        },
        headers=headers,
    )
    assert invalid_create.status_code == 404

    bad_update = client.put(
        f"/admin/bookings/{booking['id']}",
        json={
            "start_time": "2026-08-03T11:00:00",
            "end_time": "2026-08-03T10:00:00",
        },
        headers=headers,
    )
    assert bad_update.status_code == 400

    delete_booking = client.delete(f"/admin/bookings/{booking['id']}", headers=headers)
    assert delete_booking.status_code == 204


def test_notifications_helper_branches(monkeypatch):
    monkeypatch.setattr(notifications, "SMTP_HOST", None)
    monkeypatch.setattr(notifications, "SMTP_PORT", 587)
    monkeypatch.setattr(notifications, "SMTP_USERNAME", None)
    monkeypatch.setattr(notifications, "SMTP_PASSWORD", None)
    monkeypatch.setattr(notifications, "SMTP_FROM_EMAIL", "noreply@tutorlink.local")

    skipped = notifications.send_email_notification("student@test.com", "Subject", "Body")
    assert skipped["status"] == "skipped"

    monkeypatch.setattr(notifications, "SMTP_HOST", "smtp.test.local")
    monkeypatch.setattr(notifications, "SMTP_USERNAME", "user")
    monkeypatch.setattr(notifications, "SMTP_PASSWORD", "pass")

    class FakeSMTP:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def starttls(self):
            return None

        def login(self, username, password):
            return None

        def send_message(self, message):
            self.message = message

    monkeypatch.setattr(notifications.smtplib, "SMTP", lambda host, port: FakeSMTP())
    sent = notifications.send_email_notification("student@test.com", "Subject", "Body")
    assert sent["status"] == "sent"

    class FailingSMTP(FakeSMTP):
        def login(self, username, password):
            raise RuntimeError("smtp error")

    monkeypatch.setattr(notifications.smtplib, "SMTP", lambda host, port: FailingSMTP())
    failed = notifications.send_email_notification("student@test.com", "Subject", "Body")
    assert failed["status"] == "failed"

    monkeypatch.setattr(notifications.smtplib, "SMTP", lambda host, port: FakeSMTP())
    created = notifications.send_booking_notification(
        "student@test.com",
        123,
        "created",
        tutor_name="Tutor Name",
        student_name="Student Name",
    )
    assert created["status"] == "sent"

    accepted = notifications.send_booking_notification(
        "student@test.com",
        123,
        "accepted",
        tutor_name="Tutor Name",
        student_name="Student Name",
    )
    assert accepted["status"] == "sent"

    declined = notifications.send_booking_notification(
        "student@test.com",
        123,
        "declined",
        tutor_name="Tutor Name",
        student_name="Student Name",
    )
    assert declined["status"] == "sent"

    defaulted = notifications.send_booking_notification(
        "student@test.com",
        123,
        "something-else",
        tutor_name="Tutor Name",
        student_name="Student Name",
    )
    assert defaulted["status"] == "sent"
