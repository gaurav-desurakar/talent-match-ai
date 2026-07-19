from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_and_provider_metadata() -> None:
    assert client.get("/api/health").json() == {"status": "ok"}
    provider = client.get("/api/providers").json()[0]
    assert provider["id"] == "mock"
    assert provider["requires_api_key"] is False
    assert provider["sends_documents_externally"] is False


def test_complete_comparison_returns_evidence() -> None:
    response = client.post(
        "/api/comparisons",
        json={
            "job_description_text": (
                "Senior AI Engineer\nPython and RAG production experience is required."
            ),
            "resume_text": (
                "Alex Morgan\nDesigned and deployed Python RAG systems in production "
                "for 5,000 users."
            ),
            "provider": "mock",
            "blind_review": False,
        },
    )
    assert response.status_code == 201
    result = response.json()
    assert result["status"] == "completed"
    assert result["fit_score"] > 0
    assert result["requirement_matches"][0]["evidence"][0]["source_reference"].startswith(
        "resume-line-"
    )
    assert len(result["workflow_events"]) == 9
    assert result["interview_questions"]
    assert result["quality_checks"]


def test_validation_error_does_not_echo_document() -> None:
    response = client.post(
        "/api/comparisons",
        json={"job_description_text": "short", "resume_text": "also short"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_FAILED"
    assert "also short" not in str(body)
    assert body["error"]["details"]["issues"][0].keys() == {
        "location",
        "message",
        "type",
    }


def test_resume_upload_extracts_text_without_persisting_file() -> None:
    response = client.post(
        "/api/resumes/upload",
        files={
            "file": (
                "candidate.txt",
                b"Alex Morgan\nSenior engineer\nBuilt Python services in production.",
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    result = response.json()
    assert result["document_type"] == "resume"
    assert result["filename"] == "candidate.txt"
    assert result["raw_text"].startswith("Alex Morgan")
    assert result["source_references"][0]["id"].endswith("line-1")


def test_upload_errors_use_safe_error_envelope() -> None:
    response = client.post(
        "/api/job-descriptions/upload",
        files={"file": ("malware.exe", b"not executable", "application/octet-stream")},
    )

    assert response.status_code == 400
    result = response.json()["error"]
    assert result["code"] == "UNSUPPORTED_FILE_TYPE"
    assert "not executable" not in str(result)
    assert result["request_id"]


def test_comparison_preserves_uploaded_source_references() -> None:
    job_upload = client.post(
        "/api/job-descriptions/upload",
        files={
            "file": (
                "job.txt",
                b"AI Engineer\nProduction Python experience is required.",
                "text/plain",
            )
        },
    ).json()
    resume_upload = client.post(
        "/api/resumes/upload",
        files={
            "file": (
                "resume.txt",
                b"Alex Morgan\nDesigned and deployed Python production services.",
                "text/plain",
            )
        },
    ).json()

    response = client.post(
        "/api/comparisons",
        json={
            "job_description_text": job_upload["raw_text"],
            "resume_text": resume_upload["raw_text"],
            "job_source_references": job_upload["source_references"],
            "resume_source_references": resume_upload["source_references"],
        },
    )

    assert response.status_code == 201
    match = response.json()["requirement_matches"][0]
    assert match["requirement"]["source_reference"].startswith(job_upload["document_id"])
    assert match["evidence"][0]["source_reference"].startswith(resume_upload["document_id"])


def test_comparison_rejects_stale_source_references() -> None:
    response = client.post(
        "/api/comparisons",
        json={
            "job_description_text": "AI Engineer\nProduction Python experience is required.",
            "resume_text": "Candidate\nBuilt Python production services for several teams.",
            "resume_source_references": [
                {
                    "id": "unrelated-paragraph",
                    "text": "Unrelated evidence text",
                    "location_type": "paragraph",
                    "paragraph": 1,
                }
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"


def test_batch_comparison_handles_multiple_candidates_in_input_order() -> None:
    response = client.post(
        "/api/comparisons/batch",
        json={
            "job_description_text": (
                "Senior AI Engineer\nPython and RAG production experience is required."
            ),
            "candidates": [
                {
                    "candidate_id": "candidate-a",
                    "display_name": "Alex Morgan",
                    "resume_text": (
                        "Alex Morgan\nDesigned and deployed Python RAG services in production."
                    ),
                },
                {
                    "candidate_id": "candidate-b",
                    "display_name": "Jordan Lee",
                    "resume_text": (
                        "Jordan Lee\nBuilt customer support workflows and technical documentation."
                    ),
                },
            ],
        },
    )

    assert response.status_code == 201
    result = response.json()
    assert result["candidate_count"] == 2
    assert [item["candidate_id"] for item in result["comparisons"]] == [
        "candidate-a",
        "candidate-b",
    ]
    assert (
        result["comparisons"][0]["comparison"]["fit_score"]
        > result["comparisons"][1]["comparison"]["fit_score"]
    )


def test_batch_blind_review_uses_neutral_candidate_labels() -> None:
    response = client.post(
        "/api/comparisons/batch",
        json={
            "job_description_text": "AI Engineer\nProduction Python experience is required.",
            "blind_review": True,
            "candidates": [
                {
                    "candidate_id": "private-candidate",
                    "display_name": "Personally Identifying Name",
                    "resume_text": (
                        "Personally Identifying Name\nBuilt Python production services."
                    ),
                }
            ],
        },
    )

    assert response.status_code == 201
    comparison = response.json()["comparisons"][0]
    assert comparison["display_name"] == "Candidate 1"
    assert comparison["comparison"]["candidate_display_name"] == "Candidate 1"


def test_batch_comparison_limits_candidate_count() -> None:
    candidates = [
        {
            "candidate_id": f"candidate-{index}",
            "display_name": f"Candidate {index}",
            "resume_text": "Candidate profile with enough Python production experience.",
        }
        for index in range(6)
    ]
    response = client.post(
        "/api/comparisons/batch",
        json={
            "job_description_text": "AI Engineer\nProduction Python experience is required.",
            "candidates": candidates,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_FAILED"
