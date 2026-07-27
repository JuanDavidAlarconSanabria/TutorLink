"""
Tests unitarios de security.py.

Estas pruebas no tocan la base de datos: validan en aislamiento las
funciones puras de hashing de contraseñas y de generación/decodificación
de tokens JWT (NFR-02).
"""
import pytest
from jose import jwt
from datetime import timedelta

from security import (
    hash_password,
    verify_password,
    create_access_token,
    SECRET_KEY,
    ALGORITHM,
)


class TestPasswordHashing:
    def test_hash_password_produces_different_string_than_plain(self):
        plain = "MySecurePass123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert len(hashed) > 0

    def test_hash_password_is_not_deterministic(self):
        """Argon2 usa salt aleatorio: dos hashes del mismo password difieren."""
        plain = "MySecurePass123"
        assert hash_password(plain) != hash_password(plain)

    def test_verify_password_succeeds_with_correct_password(self):
        plain = "CorrectHorseBatteryStaple"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_password_fails_with_incorrect_password(self):
        hashed = hash_password("CorrectPassword1")
        assert verify_password("WrongPassword1", hashed) is False

    @pytest.mark.parametrize("empty_like", ["", " ", "a"])
    def test_verify_password_fails_for_unrelated_short_inputs(self, empty_like):
        hashed = hash_password("ARealPassword123")
        assert verify_password(empty_like, hashed) is False


class TestAccessToken:
    def test_create_access_token_contains_expected_claims(self):
        token = create_access_token({"sub": "42", "role": "STUDENT"})
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        assert payload["sub"] == "42"
        assert payload["role"] == "STUDENT"
        assert "exp" in payload

    def test_create_access_token_respects_custom_expiration(self):
        token = create_access_token({"sub": "1"}, expires_delta=timedelta(minutes=5))
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert "exp" in payload

    def test_create_access_token_uses_configured_algorithm(self):
        token = create_access_token({"sub": "1"})
        header = jwt.get_unverified_header(token)
        assert header["alg"] == ALGORITHM

    def test_decoding_with_wrong_secret_fails(self):
        token = create_access_token({"sub": "1"})
        with pytest.raises(Exception):
            jwt.decode(token, "wrong-secret-key", algorithms=[ALGORITHM])
