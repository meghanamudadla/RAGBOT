"""
Unit tests for Google OAuth helpers (URL + state handling, no network).
"""
import unittest
from urllib.parse import parse_qs, urlparse

from app.services.google_auth import create_google_auth_url, validate_state


class TestGoogleAuthState(unittest.TestCase):
    def test_auth_url_contains_state_and_expected_params(self):
        url = create_google_auth_url()
        parsed = urlparse(url)
        query = parse_qs(parsed.query)

        self.assertEqual(parsed.scheme, "https")
        self.assertIn("accounts.google.com", parsed.netloc)
        self.assertIn("response_type", query)
        self.assertEqual(query["response_type"], ["code"])
        self.assertIn("scope", query)
        self.assertIn("openid", query["scope"][0])
        self.assertIn("state", query)

    def test_state_is_single_use(self):
        url = create_google_auth_url()
        state = parse_qs(urlparse(url).query)["state"][0]

        self.assertTrue(validate_state(state))
        # Second use of the same state must fail (consumed on first try)
        self.assertFalse(validate_state(state))

    def test_unknown_state_fails(self):
        self.assertFalse(validate_state("unknown-state-token"))


if __name__ == "__main__":
    unittest.main()