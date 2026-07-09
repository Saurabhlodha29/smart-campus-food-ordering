"""
pytest configuration for the FastAPI backend test suite.

All tests in this suite are async (pytest-asyncio with asyncio_mode = "auto"
in pyproject.toml).  Tests that hit a live DB require the .env to be populated
— run them with:

    cd backend-fastapi
    pytest tests/test_smoke.py -v
"""
import pytest


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"
