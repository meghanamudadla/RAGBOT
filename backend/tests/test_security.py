"""
Unit tests for security, password hashing, and JWT token management.
"""
import unittest
import uuid
from datetime import timedelta
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
)


class TestSecurity(unittest.TestCase):
    def test_password_hashing_and_verification(self):
        plain = "SuperSecretPassword123!"
        hashed = hash_password(plain)

        # Hash should not equal plain text
        self.assertNotEqual(plain, hashed)

        # Correct password must verify
        self.assertTrue(verify_password(plain, hashed))

        # Incorrect password must fail
        self.assertFalse(verify_password("WrongPassword456!", hashed))

    def test_access_token_creation_and_decoding(self):
        user_id = uuid.uuid4()
        token = create_access_token(user_id)

        # Decodes cleanly with expected type 'access'
        decoded_sub = decode_token(token, expected_type="access")
        self.assertEqual(decoded_sub, str(user_id))

    def test_refresh_token_creation_and_decoding(self):
        user_id = uuid.uuid4()
        token = create_refresh_token(user_id)

        # Decodes cleanly with expected type 'refresh'
        decoded_sub = decode_token(token, expected_type="refresh")
        self.assertEqual(decoded_sub, str(user_id))

    def test_token_type_mismatch_fails(self):
        user_id = uuid.uuid4()
        access_token = create_access_token(user_id)

        # Attempting to use access token as refresh token must raise ValueError
        with self.assertRaises(ValueError) as ctx:
            decode_token(access_token, expected_type="refresh")
        self.assertIn("Invalid token type", str(ctx.exception))

    def test_invalid_token_signature_fails(self):
        with self.assertRaises(ValueError):
            decode_token("invalid.token.signature", expected_type="access")


if __name__ == "__main__":
    unittest.main()
