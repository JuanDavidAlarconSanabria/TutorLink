"""
Tests unitarios de schemas.py.

Validan en aislamiento las reglas de los esquemas Pydantic usados como
request/response de la API, sin pasar por HTTP ni por la base de datos.
"""
import pytest
from pydantic import ValidationError

from schemas import UserCreate, BookingCreate, ReviewCreate, AvailabilityCreate
from models import RoleEnum


class TestUserCreateSchema:
    def test_accepts_valid_payload(self):
        user = UserCreate(
            email="valid@example.com",
            password="longenough1",
            full_name="Valid User",
            role=RoleEnum.STUDENT,
        )
        assert user.email == "valid@example.com"
        assert user.role == RoleEnum.STUDENT

    def test_rejects_invalid_email(self):
        with pytest.raises(ValidationError):
            UserCreate(
                email="not-an-email",
                password="longenough1",
                full_name="Valid User",
                role=RoleEnum.STUDENT,
            )

    def test_rejects_password_shorter_than_min_length(self):
        with pytest.raises(ValidationError):
            UserCreate(
                email="valid@example.com",
                password="short",
                full_name="Valid User",
                role=RoleEnum.STUDENT,
            )

    def test_rejects_invalid_role(self):
        with pytest.raises(ValidationError):
            UserCreate(
                email="valid@example.com",
                password="longenough1",
                full_name="Valid User",
                role="NOT_A_ROLE",
            )


class TestBookingCreateSchema:
    def test_accepts_valid_payload(self):
        booking = BookingCreate(
            tutor_user_id=1,
            subject_id=2,
            start_time="2026-08-01T10:00:00",
            end_time="2026-08-01T11:00:00",
            notes="Repaso de cálculo",
        )
        assert booking.tutor_user_id == 1

    def test_allows_optional_subject_and_notes_to_be_omitted(self):
        booking = BookingCreate(
            tutor_user_id=1,
            start_time="2026-08-01T10:00:00",
            end_time="2026-08-01T11:00:00",
        )
        assert booking.subject_id is None
        assert booking.notes is None

    def test_rejects_missing_required_fields(self):
        with pytest.raises(ValidationError):
            BookingCreate(tutor_user_id=1)


class TestReviewCreateSchema:
    @pytest.mark.parametrize("rating", [1, 2, 3, 4, 5])
    def test_accepts_ratings_within_valid_range(self, rating):
        review = ReviewCreate(booking_id=1, rating=rating)
        assert review.rating == rating

    @pytest.mark.parametrize("rating", [0, -1, 6, 10])
    def test_rejects_ratings_outside_valid_range(self, rating):
        with pytest.raises(ValidationError):
            ReviewCreate(booking_id=1, rating=rating)


class TestAvailabilityCreateSchema:
    def test_accepts_recurring_availability_with_day_of_week(self):
        availability = AvailabilityCreate(
            day_of_week="MONDAY",
            start_time="14:00:00",
            end_time="16:00:00",
        )
        assert availability.is_recurring is True

    def test_accepts_one_off_availability_with_specific_date(self):
        availability = AvailabilityCreate(
            start_time="14:00:00",
            end_time="16:00:00",
            is_recurring=False,
            specific_date="2026-08-10",
        )
        assert availability.specific_date is not None

    def test_rejects_invalid_day_of_week(self):
        with pytest.raises(ValidationError):
            AvailabilityCreate(
                day_of_week="SOMEDAY",
                start_time="14:00:00",
                end_time="16:00:00",
            )
