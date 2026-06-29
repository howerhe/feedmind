import pytest


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database path for testing."""
    return str(tmp_path / "test_memory.db")
