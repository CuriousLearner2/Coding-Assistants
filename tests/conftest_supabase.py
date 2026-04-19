import pytest
from unittest import mock
import os

# Ensure we use the Supabase .env for tests
from dotenv import load_dotenv
load_dotenv()

@pytest.fixture(autouse=True)
def mock_getpass():
    with mock.patch("getpass.getpass", return_value="Password1"):
        yield

@pytest.fixture(autouse=True)
def mock_input():
    # We might need to mock input() if tests don't already handle it
    # But integration tests usually call functions directly.
    yield

@pytest.fixture
def alice_session():
    """Return a mock session for the pre-seeded driver Alice."""
    from client.api import login
    resp = login("alice@example.com", "Password1")
    return {**resp["driver"], "token": resp["token"]}
