import time

from fastapi.testclient import TestClient


def wait_for_job(client: TestClient, job_id: str) -> dict[str, object]:
    for _ in range(100):
        body = client.get(f"/api/analysis-jobs/{job_id}").json()
        if body["status"] in {"completed", "failed", "cancelled"}:
            return body  # type: ignore[no-any-return]
        time.sleep(0.01)
    raise AssertionError("analysis job did not finish")


def test_background_job_streams_and_persists_results(client: TestClient) -> None:
    client.delete("/api/privacy/all-data")
    response = client.post(
        "/api/analysis-jobs",
        json={
            "job_title": "Senior AI Engineer",
            "job_description_text": (
                "Senior AI Engineer\nPython and FastAPI production experience is required."
            ),
            "candidates": [
                {
                    "candidate_id": "candidate-a",
                    "display_name": "Alex Morgan",
                    "resume_text": (
                        "Alex Morgan\nBuilt Python and FastAPI production services for users."
                    ),
                },
                {
                    "candidate_id": "candidate-b",
                    "display_name": "Jordan Lee",
                    "resume_text": (
                        "Jordan Lee\nLed customer onboarding and product documentation programs."
                    ),
                },
            ],
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    result = wait_for_job(client, job_id)
    assert result["status"] == "completed"
    assert result["completed_count"] == 2
    assert len(result["comparison_ids"]) == 2

    events = client.get(f"/api/analysis-jobs/{job_id}/events")
    assert events.status_code == 200
    assert "event: progress" in events.text
    assert "skill_normalization" in events.text
    assert "event: complete" in events.text

    history = client.get("/api/comparisons").json()
    assert len(history) == 2
    assert {item["candidate_display_name"] for item in history} == {
        "Alex Morgan",
        "Jordan Lee",
    }
    comparison = client.get(f"/api/comparisons/{result['comparison_ids'][0]}").json()
    assert comparison["interview_questions"]
    assert comparison["clarification_flags"] is not None

    retried = client.post(
        f"/api/analysis-jobs/retry/{result['comparison_ids'][0]}",
        json={"provider": "mock", "blind_review": True},
    )
    assert retried.status_code == 202
    retried_result = wait_for_job(client, retried.json()["job_id"])
    assert retried_result["status"] == "completed"


def test_blind_background_history_uses_neutral_name(client: TestClient) -> None:
    client.delete("/api/privacy/all-data")
    response = client.post(
        "/api/analysis-jobs",
        json={
            "job_description_text": "AI Engineer\nProduction Python experience is required.",
            "blind_review": True,
            "candidates": [
                {
                    "candidate_id": "private",
                    "display_name": "Personally Identifying Name",
                    "resume_text": (
                        "Personally Identifying Name\nBuilt Python production services."
                    ),
                }
            ],
        },
    )
    result = wait_for_job(client, response.json()["job_id"])
    assert result["status"] == "completed"
    history = client.get("/api/comparisons").json()
    assert history[0]["candidate_display_name"] == "Candidate 1"
    assert "Personally Identifying Name" not in str(history[0])


def test_background_analysis_reuses_saved_job_and_populates_overview(
    client: TestClient,
) -> None:
    client.delete("/api/privacy/all-data")
    job_text = "AI Engineer\nProduction Python experience is required."
    saved_job = client.post(
        "/api/jobs",
        json={"title": "AI Engineer", "raw_text": job_text},
    ).json()
    extracted = client.post(
        f"/api/jobs/{saved_job['id']}/scorecard/extract",
        json={"provider": "mock"},
    ).json()
    reviewed = client.put(
        f"/api/jobs/{saved_job['id']}/scorecard",
        json={"requirements": extracted["requirements"], "approve": True},
    )
    assert reviewed.status_code == 200
    candidate = client.post(
        "/api/candidates",
        json={
            "display_name": "Alex Morgan",
            "resume": {
                "raw_text": "Alex Morgan\nBuilt Python production services for users."
            },
        },
    ).json()
    resume = candidate["resumes"][0]

    response = client.post(
        "/api/analysis-jobs",
        json={
            "job_id": saved_job["id"],
            "job_title": saved_job["title"],
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
    assert response.status_code == 202
    result = wait_for_job(client, response.json()["job_id"])
    assert result["status"] == "completed"

    jobs = client.get("/api/jobs").json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == saved_job["id"]
    assert jobs[0]["candidate_count"] == 1
    assert jobs[0]["comparison_count"] == 1
    assert jobs[0]["last_analysis_at"] is not None
    candidates = client.get("/api/candidates").json()
    assert len(candidates) == 1
    assert candidates[0]["id"] == candidate["id"]
    assert candidates[0]["comparison_count"] == 1
    assert candidates[0]["job_count"] == 1

    overview = client.get(f"/api/jobs/{saved_job['id']}/overview")
    assert overview.status_code == 200
    assert overview.json()["job"]["id"] == saved_job["id"]
    assert overview.json()["comparisons"][0]["candidate_display_name"] == "Alex Morgan"
    candidate_overview = client.get(f"/api/candidates/{candidate['id']}/overview")
    assert candidate_overview.status_code == 200
    assert candidate_overview.json()["comparisons"][0]["job_title"] == "AI Engineer"


def test_saved_job_analysis_rejects_changed_description(client: TestClient) -> None:
    client.delete("/api/privacy/all-data")
    saved_job = client.post(
        "/api/jobs",
        json={
            "title": "AI Engineer",
            "raw_text": "AI Engineer\nProduction Python experience is required.",
        },
    ).json()
    response = client.post(
        "/api/analysis-jobs",
        json={
            "job_id": saved_job["id"],
            "job_description_text": "AI Engineer\nA different requirement is now required.",
            "candidates": [
                {
                    "candidate_id": "candidate-a",
                    "display_name": "Alex Morgan",
                    "resume_text": "Alex Morgan\nBuilt Python production services for users.",
                }
            ],
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "JOB_DESCRIPTION_MISMATCH"


def test_saved_job_analysis_requires_an_approved_scorecard(client: TestClient) -> None:
    client.delete("/api/privacy/all-data")
    job_text = "AI Engineer\nProduction Python experience is required."
    saved_job = client.post(
        "/api/jobs", json={"title": "AI Engineer", "raw_text": job_text}
    ).json()

    response = client.post(
        "/api/analysis-jobs",
        json={
            "job_id": saved_job["id"],
            "job_description_text": job_text,
            "candidates": [
                {
                    "candidate_id": "candidate-a",
                    "display_name": "Alex Morgan",
                    "resume_text": "Alex Morgan\nBuilt Python production services for users.",
                }
            ],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "JOB_SCORECARD_NOT_APPROVED"
    assert response.json()["error"]["message"] == (
        "Approve the job scorecard before finding talent."
    )
