import pytest
import os
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.database.session import Base, get_db
from app.config.config import settings
from app.database.seeder import seed_database
from app.models.models import User, Policy, Finding, Obligation, Role

# Setup SQLite test DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_fixture.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="module")
def db_session():
    # Create tables
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Seed test db
        seed_database(db, force=True)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        if os.path.exists("./test_fixture.db"):
            try:
                os.remove("./test_fixture.db")
            except PermissionError:
                pass

@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

def test_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_auth_flows(client):
    # 1. Register new user
    reg_response = client.post("/api/v1/auth/register", json={
        "username": "testauditor",
        "email": "testauditor@example.com",
        "password": "securepassword",
        "role_name": "Auditor"
    })
    assert reg_response.status_code == 200
    assert reg_response.json()["username"] == "testauditor"

    # 2. Login
    login_response = client.post("/api/v1/auth/login", data={
        "username": "testauditor",
        "password": "securepassword"
    })
    assert login_response.status_code == 200
    assert "access_token" in login_response.json()
    token = login_response.json()["access_token"]

    # 3. Read profile
    headers = {"Authorization": f"Bearer {token}"}
    me_response = client.get("/api/v1/auth/me", headers=headers)
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "testauditor"

def test_dataset_statistics(client):
    response = client.get("/api/v1/dataset/statistics")
    assert response.status_code == 200
    data = response.json()
    assert data["policies_count"] == 30
    assert data["obligations_count"] > 0
    assert data["findings_count"] > 0

def test_dataset_policies(client):
    response = client.get("/api/v1/dataset/policies")
    assert response.status_code == 200
    assert len(response.json()) == 30

def test_dashboard_summary(client):
    response = client.get("/api/v1/dashboard/summary")
    assert response.status_code == 200
    data = response.json()
    assert "governance_score" in data
    assert data["total_policies"] == 30

def test_dashboard_search(client):
    # Search for Password Policy
    response = client.get("/api/v1/dashboard/search?policy=Password")
    assert response.status_code == 200
    # Search by severity
    high_response = client.get("/api/v1/dashboard/search?severity=HIGH")
    assert high_response.status_code == 200

def test_evaluation(client):
    response = client.get("/api/v1/evaluation")
    assert response.status_code == 200
    data = response.json()
    assert "precision" in data
    assert "recall" in data
    assert "accuracy" in data
    assert "f1_score" in data

def test_reports(client):
    # Login to get Auditor token
    login_response = client.post("/api/v1/auth/login", data={
        "username": "auditor",
        "password": "auditorpassword"
    })
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Request report generation
    response = client.post("/api/v1/reports?title=Test%20Report&format_type=JSON", headers=headers)
    assert response.status_code == 202
    report_data = response.json()
    assert report_data["title"] == "Test Report"
    assert report_data["status"] == "Completed"
    
    # Download report
    report_id = report_data["id"]
    download_response = client.get(f"/api/v1/reports/{report_id}/download", headers=headers)
    assert download_response.status_code == 200
