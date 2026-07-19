import time

from fastapi.testclient import TestClient


def wait_for_job(client: TestClient, job_id: str) -> dict[str, object]:
    for _ in range(100):
        body = client.get(f"/api/analysis-jobs/{job_id}").json()
        if body["status"] in {"completed", "failed", "cancelled"}:
            return body  # type: ignore[no-any-return]
        time.sleep(0.01)
    raise AssertionError("analysis job did not finish")


def create_saved_job(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/jobs",
        json={
            "title": "Senior AI Engineer",
            "raw_text": (
                "Senior AI Engineer\n"
                "Production Python experience is required.\n"
                "Experience with Docker is preferred."
            ),
        },
    )
    assert response.status_code == 201
    return response.json()  # type: ignore[no-any-return]


def test_scorecard_extract_review_and_saved_job_enforcement(client: TestClient) -> None:
    client.delete("/api/privacy/all-data")
    job = create_saved_job(client)
    job_id = str(job["id"])

    empty = client.get(f"/api/jobs/{job_id}/scorecard")
    assert empty.status_code == 200
    assert empty.json()["status"] == "empty"
    assert empty.json()["version"] == 0

    extracted = client.post(
        f"/api/jobs/{job_id}/scorecard/extract",
        json={"provider": "mock"},
    )
    assert extracted.status_code == 200
    assert extracted.json()["status"] == "draft"
    assert extracted.json()["version"] == 1
    requirements = extracted.json()["requirements"]
    assert requirements
    assert all(item["included"] for item in requirements)

    requirements[-1]["included"] = False
    reviewed = client.put(
        f"/api/jobs/{job_id}/scorecard",
        json={"requirements": requirements, "approve": True},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "reviewed"
    assert reviewed.json()["version"] == 1
    assert reviewed.json()["reviewed_at"] is not None
    summary = client.get("/api/jobs").json()[0]
    assert summary["scorecard_status"] == "reviewed"
    assert summary["scorecard_version"] == 1
    assert summary["scorecard_requirement_count"] == len(
        [item for item in requirements if item["included"]]
    )

    analysis = client.post(
        "/api/analysis-jobs",
        json={
            "job_id": job_id,
            "job_description_text": job["raw_text"],
            "candidates": [
                {
                    "candidate_id": "candidate-a",
                    "display_name": "Alex Morgan",
                    "resume_text": "Alex Morgan\nBuilt and operated Python production services.",
                }
            ],
        },
    )
    result = wait_for_job(client, analysis.json()["job_id"])
    assert result["status"] == "completed"
    comparison = client.get(f"/api/comparisons/{result['comparison_ids'][0]}").json()
    assert comparison["scorecard_version"] == 1
    included_ids = {item["id"] for item in requirements if item["included"]}
    actual_ids = {
        item["requirement"]["id"] for item in comparison["requirement_matches"]
    }
    assert actual_ids == included_ids


def test_editing_reviewed_scorecard_creates_new_version(client: TestClient) -> None:
    client.delete("/api/privacy/all-data")
    job = create_saved_job(client)
    job_id = str(job["id"])
    extracted = client.post(
        f"/api/jobs/{job_id}/scorecard/extract", json={"provider": "mock"}
    ).json()
    first = client.put(
        f"/api/jobs/{job_id}/scorecard",
        json={"requirements": extracted["requirements"], "approve": True},
    ).json()
    first["requirements"][0]["importance"] = 0.75
    second = client.put(
        f"/api/jobs/{job_id}/scorecard",
        json={"requirements": first["requirements"], "approve": True},
    )
    assert second.status_code == 200
    assert second.json()["version"] == 2


def test_changing_job_description_invalidates_reviewed_scorecard(
    client: TestClient,
) -> None:
    client.delete("/api/privacy/all-data")
    job = create_saved_job(client)
    job_id = str(job["id"])
    extracted = client.post(
        f"/api/jobs/{job_id}/scorecard/extract", json={"provider": "mock"}
    ).json()
    client.put(
        f"/api/jobs/{job_id}/scorecard",
        json={"requirements": extracted["requirements"], "approve": True},
    )

    updated = client.put(
        f"/api/jobs/{job_id}",
        json={
            "raw_text": (
                "Senior AI Engineer\n"
                "Production Python and FastAPI experience is required."
            )
        },
    )
    assert updated.status_code == 200
    scorecard = client.get(f"/api/jobs/{job_id}/scorecard").json()
    assert scorecard["status"] == "draft"
    assert scorecard["version"] == 2
    assert scorecard["requirements"] == []
    assert "Regenerate and approve" in scorecard["warnings"][0]


def test_scorecard_rejects_unverified_and_protected_requirements(client: TestClient) -> None:
    client.delete("/api/privacy/all-data")
    job = client.post(
        "/api/jobs",
        json={
            "title": "Engineer",
            "raw_text": (
                "Engineer role requiring production Python experience. "
                "Nationality: Singaporean is required."
            ),
        },
    ).json()
    base = {
        "id": "req-1",
        "canonical_concept": None,
        "classification": "mandatory",
        "category": "core_technical_skills",
        "importance": 1,
        "source_reference": "job-line-1",
        "included": True,
    }
    missing = client.put(
        f"/api/jobs/{job['id']}/scorecard",
        json={
            "requirements": [{**base, "text": "Kubernetes experience is required."}],
            "approve": True,
        },
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "JOB_SCORECARD_REQUIREMENT_NOT_FOUND"

    protected = client.put(
        f"/api/jobs/{job['id']}/scorecard",
        json={
            "requirements": [
                {**base, "text": "Nationality: Singaporean is required."}
            ],
            "approve": True,
        },
    )
    assert protected.status_code == 422
    assert protected.json()["error"]["code"] == "JOB_SCORECARD_PROTECTED_ATTRIBUTE"
