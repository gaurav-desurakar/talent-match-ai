import time

from fastapi.testclient import TestClient


def wait_for_analysis(client: TestClient, analysis_job_id: str) -> dict[str, object]:
    for _ in range(100):
        body = client.get(f"/api/analysis-jobs/{analysis_job_id}").json()
        if body["status"] in {"completed", "failed", "cancelled"}:
            return body  # type: ignore[no-any-return]
        time.sleep(0.01)
    raise AssertionError("analysis job did not finish")


def create_completed_comparison(client: TestClient) -> tuple[str, str, str]:
    job_text = "AI Engineer\nProduction Python experience is required for this role."
    job = client.post(
        "/api/jobs",
        json={"title": "AI Engineer", "raw_text": job_text},
    ).json()
    scorecard = client.post(
        f"/api/jobs/{job['id']}/scorecard/extract",
        json={"provider": "mock"},
    ).json()
    approved = client.put(
        f"/api/jobs/{job['id']}/scorecard",
        json={"requirements": scorecard["requirements"], "approve": True},
    )
    assert approved.status_code == 200
    candidate = client.post(
        "/api/candidates",
        json={
            "display_name": "Alex Morgan",
            "resume": {"raw_text": "Alex Morgan\nBuilt Python production services for customers."},
        },
    ).json()
    resume = candidate["resumes"][0]
    started = client.post(
        "/api/analysis-jobs",
        json={
            "job_id": job["id"],
            "job_description_text": job_text,
            "candidates": [
                {
                    "candidate_id": "candidate-a",
                    "display_name": "Alex Morgan",
                    "stored_candidate_id": candidate["id"],
                    "resume_id": resume["id"],
                    "resume_text": resume["raw_text"],
                }
            ],
        },
    )
    result = wait_for_analysis(client, started.json()["job_id"])
    assert result["status"] == "completed"
    comparison_id = str(result["comparison_ids"][0])  # type: ignore[index]
    return job["id"], candidate["id"], comparison_id


def test_recruiter_actions_are_manual_audited_and_visible(client: TestClient) -> None:
    client.delete("/api/privacy/all-data")
    job_id, candidate_id, comparison_id = create_completed_comparison(client)

    policy = client.put(
        f"/api/jobs/{job_id}/triage-policy",
        json={
            "shortlist_fit_threshold": 0,
            "shortlist_evidence_threshold": 0,
            "require_mandatory_met": False,
            "require_no_clarification_flags": False,
        },
    )
    assert policy.status_code == 200
    assert policy.json()["version"] == 2

    initial = client.get(f"/api/comparisons/{comparison_id}/disposition")
    assert initial.status_code == 200
    assert initial.json()["status"] == "new"
    assert initial.json()["triage_suggestion"] == "meets_shortlist_threshold"
    assert initial.json()["events"] == []

    shortlisted = client.put(
        f"/api/comparisons/{comparison_id}/disposition",
        json={
            "status": "shortlisted",
            "note": "Relevant evidence reviewed by the recruiting team.",
            "assigned_recruiter": "Recruiting Team A",
        },
    )
    assert shortlisted.status_code == 200
    assert shortlisted.json()["status"] == "shortlisted"
    assert shortlisted.json()["events"][0]["previous_status"] is None

    job_overview = client.get(f"/api/jobs/{job_id}/overview").json()
    assert job_overview["comparisons"][0]["recruiter_status"] == "shortlisted"
    candidate_overview = client.get(f"/api/candidates/{candidate_id}/overview").json()
    assert candidate_overview["comparisons"][0]["recruiter_status"] == "shortlisted"

    missing_reason = client.put(
        f"/api/comparisons/{comparison_id}/disposition",
        json={"status": "not_progressing"},
    )
    assert missing_reason.status_code == 422
    missing_other_note = client.put(
        f"/api/comparisons/{comparison_id}/disposition",
        json={"status": "not_progressing", "reason_code": "other"},
    )
    assert missing_other_note.status_code == 422

    not_progressing = client.put(
        f"/api/comparisons/{comparison_id}/disposition",
        json={
            "status": "not_progressing",
            "reason_code": "role_alignment_gap",
            "note": "The evidence does not align with this role's current scope.",
        },
    )
    assert not_progressing.status_code == 200
    assert not_progressing.json()["events"][0]["previous_status"] == "shortlisted"
    assert len(not_progressing.json()["events"]) == 2


def test_global_triage_defaults_are_copied_to_new_jobs(client: TestClient) -> None:
    client.delete("/api/privacy/all-data")
    updated = client.put(
        "/api/settings",
        json={
            "default_triage_policy": {
                "shortlist_fit_threshold": 75,
                "shortlist_evidence_threshold": 70,
                "require_mandatory_met": True,
                "require_no_clarification_flags": False,
            }
        },
    )
    assert updated.status_code == 200
    created = client.post(
        "/api/jobs",
        json={
            "title": "Platform Engineer",
            "raw_text": "Platform Engineer with production infrastructure experience required.",
        },
    )
    assert created.status_code == 201
    assert created.json()["triage_policy"]["shortlist_fit_threshold"] == 75
    assert created.json()["triage_policy"]["require_no_clarification_flags"] is False
