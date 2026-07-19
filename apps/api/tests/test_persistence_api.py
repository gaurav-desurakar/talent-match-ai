from fastapi.testclient import TestClient

from app.db.session import initialize_database
from app.main import app

initialize_database()
client = TestClient(app)


def reset_data() -> None:
    client.delete("/api/privacy/all-data")


def test_job_candidate_crud_and_delete_all() -> None:
    reset_data()
    job = client.post(
        "/api/jobs",
        json={
            "title": "Senior AI Engineer",
            "external_job_id": " AI-1042 ",
            "raw_text": "Senior AI Engineer requiring Python production experience.",
        },
    )
    assert job.status_code == 201
    job_id = job.json()["id"]
    assert client.get(f"/api/jobs/{job_id}").json()["title"] == "Senior AI Engineer"
    assert job.json()["external_job_id"] == "AI-1042"
    updated = client.put(
        f"/api/jobs/{job_id}",
        json={"title": "Principal AI Engineer", "external_job_id": None},
    )
    assert updated.json()["title"] == "Principal AI Engineer"
    assert updated.json()["external_job_id"] is None

    candidate = client.post(
        "/api/candidates",
        json={
            "display_name": "Alex Morgan",
            "resume": {
                "raw_text": "Alex Morgan built Python production systems for enterprise users.",
                "source_file": "alex-morgan-v1.pdf",
            },
        },
    )
    assert candidate.status_code == 201
    assert len(candidate.json()["resumes"]) == 1
    candidate_id = candidate.json()["id"]
    assert client.get(f"/api/candidates/{candidate_id}").status_code == 200
    summaries = client.get("/api/candidates").json()
    assert summaries[0]["display_name"] == "Alex Morgan"
    assert summaries[0]["resume_count"] == 1
    assert summaries[0]["comparison_count"] == 0
    assert summaries[0]["job_count"] == 0

    resume_version = client.post(
        f"/api/candidates/{candidate_id}/resumes",
        json={
            "raw_text": (
                "Alex Morgan built Python and Kubernetes production systems "
                "for enterprise users."
            ),
            "source_file": "alex-morgan-v2.pdf",
        },
    )
    assert resume_version.status_code == 201
    duplicate_version = client.post(
        f"/api/candidates/{candidate_id}/resumes",
        json={
            "raw_text": (
                "  alex MORGAN built Python and Kubernetes production systems "
                "for enterprise users.  "
            )
        },
    )
    assert duplicate_version.status_code == 409
    assert duplicate_version.json()["error"]["code"] == "CANDIDATE_RESUME_DUPLICATE"
    overview = client.get(f"/api/candidates/{candidate_id}/overview")
    assert overview.status_code == 200
    assert overview.json()["summary"]["resume_count"] == 2
    assert len(overview.json()["candidate"]["resumes"]) == 2
    assert overview.json()["comparisons"] == []

    dashboard = client.get("/api/dashboard").json()
    assert dashboard["active_jobs"] == 1
    assert dashboard["candidates_analyzed"] == 1

    deletion = client.delete("/api/privacy/all-data")
    assert deletion.status_code == 200
    assert deletion.json()["jobs_deleted"] == 1
    assert deletion.json()["candidates_deleted"] == 1
    assert client.get("/api/jobs").json() == []


def test_settings_validate_weights_and_retention() -> None:
    response = client.put(
        "/api/settings",
        json={
            "provider": "mock",
            "selected_model": "mock-evidence-v1",
            "retention_policy_days": 14,
            "blind_review_enabled": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["retention_policy_days"] == 14
    assert response.json()["blind_review_enabled"] is True
    assert response.json()["credential_configured"] is False
    assert client.post("/api/privacy/retention/run").status_code == 200

    invalid = client.put(
        "/api/settings",
        json={"scoring_configuration": {"core_technical_skills": 100}},
    )
    assert invalid.status_code == 422


def test_not_found_uses_safe_error_envelope() -> None:
    response = client.get("/api/jobs/missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "JOB_NOT_FOUND"
    diagnostics = client.get("/api/diagnostics")
    assert diagnostics.status_code == 404
    assert diagnostics.json()["error"]["code"] == "DIAGNOSTICS_DISABLED"
