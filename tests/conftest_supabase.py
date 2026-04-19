import pytest
from unittest import mock
import os
from dotenv import load_dotenv

# Ensure we use the Supabase .env for tests
load_dotenv()

class MockInput:
    """A helper to simulate multiple terminal inputs for CLI testing."""
    def __init__(self, responses):
        self._responses = iter(responses)
    def __call__(self, prompt=""):
        try:
            val = next(self._responses)
            return val
        except StopIteration:
            return "b" # Default to 'back' to prevent infinite loops

@pytest.fixture
def mock_getpass():
    """Globally mock password entry for all tests."""
    with mock.patch("getpass.getpass", return_value="Password1"):
        yield

@pytest.fixture
def mock_cli_input():
    """
    A factory fixture to mock builtins.input with specific responses.
    """
    def _set_responses(responses):
        return mock.patch("builtins.input", MockInput(responses))
    return _set_responses

@pytest.fixture
def alice_session():
    """
    Return a real authenticated session from the remote Supabase backend.
    Includes a sanity check to ensure auth logic is working (non-trivial).
    """
    from client.api import login, AuthError
    
    # Non-trivial check: Verify that a wrong password actually fails
    try:
        login("alice@example.com", "WrongPassword")
        pytest.fail("Security Vulnerability: login() accepted a wrong password!")
    except AuthError:
        pass # Correct behavior
    
    # Real login
    try:
        resp = login("alice@example.com", "Password1")
        return {**resp["driver"], "token": resp["token"]}
    except Exception as e:
        pytest.fail(f"Failed to authenticate Alice against Supabase: {str(e)}")
