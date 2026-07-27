"""
Tests de integración de la capa ORM (SQLAlchemy).

A diferencia de los tests unitarios, estos SÍ ejecutan sentencias SQL reales
contra una base de datos (SQLite de pruebas), validando que los modelos,
las relaciones, los constraints (CHECK, UNIQUE, FOREIGN KEY) y las cascadas
definidas en models.py se comporten como se documentó en el diagrama ER
del Workshop 2.
"""
from datetime import date, time, datetime

import pytest
from sqlalchemy.exc import IntegrityError

import models


def _make_user(db_session, email="user@test.com", role=models.RoleEnum.STUDENT):
    user = models.User(
        email=email,
        password_hash="hashed-value",
        full_name="Test User",
        role=role,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestUserModel:
    def test_create_user_persists_and_reloads(self, db_session):
        user = _make_user(db_session, email="persist@test.com")
        fetched = db_session.query(models.User).filter_by(email="persist@test.com").first()
        assert fetched is not None
        assert fetched.id == user.id
        assert fetched.is_active is True

    def test_email_unique_constraint_is_enforced(self, db_session):
        _make_user(db_session, email="dup@test.com")
        db_session.add(models.User(
            email="dup@test.com",
            password_hash="another-hash",
            full_name="Duplicate",
            role=models.RoleEnum.STUDENT,
        ))
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_deleting_user_cascades_to_student_profile(self, db_session):
        user = _make_user(db_session, email="cascade@test.com")
        profile = models.StudentProfile(user_id=user.id, learning_goals="Álgebra")
        db_session.add(profile)
        db_session.commit()

        db_session.delete(user)
        db_session.commit()

        remaining = db_session.query(models.StudentProfile).filter_by(user_id=user.id).first()
        assert remaining is None


class TestTutorProfileAndSubjects:
    def test_many_to_many_relationship_between_tutor_and_subjects(self, db_session):
        tutor_user = _make_user(db_session, email="tutor@test.com", role=models.RoleEnum.TUTOR)
        profile = models.TutorProfile(user_id=tutor_user.id, hourly_rate=25000)
        math = models.Subject(name="Matemáticas")
        physics = models.Subject(name="Física")
        db_session.add_all([profile, math, physics])
        db_session.commit()

        profile.subjects = [math, physics]
        db_session.commit()
        db_session.refresh(profile)

        subject_names = {s.name for s in profile.subjects}
        assert subject_names == {"Matemáticas", "Física"}
        # La relación es bidireccional
        assert profile in math.tutors

    def test_subject_name_unique_constraint(self, db_session):
        db_session.add(models.Subject(name="Química"))
        db_session.commit()
        db_session.add(models.Subject(name="Química"))
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestAvailabilityConstraints:
    def test_valid_time_range_is_persisted(self, db_session):
        tutor_user = _make_user(db_session, email="avail_ok@test.com", role=models.RoleEnum.TUTOR)
        profile = models.TutorProfile(user_id=tutor_user.id, hourly_rate=10000)
        db_session.add(profile)
        db_session.commit()

        availability = models.Availability(
            tutor_profile_id=profile.id,
            day_of_week=models.DayOfWeek.MONDAY,
            start_time=time(14, 0),
            end_time=time(16, 0),
        )
        db_session.add(availability)
        db_session.commit()
        assert availability.id is not None

    def test_check_constraint_rejects_end_time_before_start_time(self, db_session):
        tutor_user = _make_user(db_session, email="avail_bad@test.com", role=models.RoleEnum.TUTOR)
        profile = models.TutorProfile(user_id=tutor_user.id, hourly_rate=10000)
        db_session.add(profile)
        db_session.commit()

        bad_availability = models.Availability(
            tutor_profile_id=profile.id,
            day_of_week=models.DayOfWeek.TUESDAY,
            start_time=time(16, 0),
            end_time=time(14, 0),  # inválido: termina antes de empezar
        )
        db_session.add(bad_availability)
        with pytest.raises(IntegrityError):
            db_session.commit()


class TestBookingConstraintsAndRelationships:
    def _make_student_and_tutor(self, db_session):
        student = _make_user(db_session, email="student@test.com", role=models.RoleEnum.STUDENT)
        tutor = _make_user(db_session, email="tutor_b@test.com", role=models.RoleEnum.TUTOR)
        return student, tutor

    def test_check_constraint_rejects_end_before_start(self, db_session):
        student, tutor = self._make_student_and_tutor(db_session)
        booking = models.Booking(
            student_user_id=student.id,
            tutor_user_id=tutor.id,
            start_time=datetime(2026, 8, 1, 11, 0),
            end_time=datetime(2026, 8, 1, 10, 0),  # inválido
        )
        db_session.add(booking)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_booking_relationships_resolve_correctly(self, db_session):
        student, tutor = self._make_student_and_tutor(db_session)
        booking = models.Booking(
            student_user_id=student.id,
            tutor_user_id=tutor.id,
            start_time=datetime(2026, 8, 1, 10, 0),
            end_time=datetime(2026, 8, 1, 11, 0),
            status=models.BookingStatus.PENDING,
        )
        db_session.add(booking)
        db_session.commit()
        db_session.refresh(booking)

        assert booking.student.email == "student@test.com"
        assert booking.tutor.email == "tutor_b@test.com"
        assert booking in student.bookings_as_student
        assert booking in tutor.bookings_as_tutor

    def test_deleting_booking_cascades_to_review(self, db_session):
        student, tutor = self._make_student_and_tutor(db_session)
        booking = models.Booking(
            student_user_id=student.id,
            tutor_user_id=tutor.id,
            start_time=datetime(2026, 8, 1, 10, 0),
            end_time=datetime(2026, 8, 1, 11, 0),
            status=models.BookingStatus.COMPLETED,
        )
        db_session.add(booking)
        db_session.commit()

        review = models.Review(booking_id=booking.id, student_user_id=student.id, rating=5)
        db_session.add(review)
        db_session.commit()

        db_session.delete(booking)
        db_session.commit()

        assert db_session.query(models.Review).filter_by(id=review.id).first() is None


class TestReviewConstraints:
    def test_rating_out_of_range_is_rejected_by_check_constraint(self, db_session):
        student = _make_user(db_session, email="rev_student@test.com", role=models.RoleEnum.STUDENT)
        tutor = _make_user(db_session, email="rev_tutor@test.com", role=models.RoleEnum.TUTOR)
        booking = models.Booking(
            student_user_id=student.id,
            tutor_user_id=tutor.id,
            start_time=datetime(2026, 8, 1, 10, 0),
            end_time=datetime(2026, 8, 1, 11, 0),
            status=models.BookingStatus.COMPLETED,
        )
        db_session.add(booking)
        db_session.commit()

        invalid_review = models.Review(booking_id=booking.id, student_user_id=student.id, rating=7)
        db_session.add(invalid_review)
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_review_is_unique_per_booking(self, db_session):
        student = _make_user(db_session, email="rev_student2@test.com", role=models.RoleEnum.STUDENT)
        tutor = _make_user(db_session, email="rev_tutor2@test.com", role=models.RoleEnum.TUTOR)
        booking = models.Booking(
            student_user_id=student.id,
            tutor_user_id=tutor.id,
            start_time=datetime(2026, 8, 1, 10, 0),
            end_time=datetime(2026, 8, 1, 11, 0),
            status=models.BookingStatus.COMPLETED,
        )
        db_session.add(booking)
        db_session.commit()

        db_session.add(models.Review(booking_id=booking.id, student_user_id=student.id, rating=4))
        db_session.commit()

        db_session.add(models.Review(booking_id=booking.id, student_user_id=student.id, rating=5))
        with pytest.raises(IntegrityError):
            db_session.commit()
