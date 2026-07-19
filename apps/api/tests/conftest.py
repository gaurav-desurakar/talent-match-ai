import os

import pytest
from fastapi.testclient import TestClient

os.environ["TALENTMATCH_DATABASE_URL"] = "sqlite:////tmp/talentmatch-api-tests.db"
os.environ["TALENTMATCH_ENV"] = "testing"


@pytest.fixture
def client() -> TestClient:
    from app.db.session import initialize_database
    from app.main import app

    initialize_database()
    return TestClient(app)
