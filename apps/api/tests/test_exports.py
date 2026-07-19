import io
import time

from fastapi.testclient import TestClient
from pypdf import PdfReader


def create_persisted_comparison(client: TestClient) -> str:
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
                }
            ],
        },
    )
    job_id = response.json()["job_id"]
    for _ in range(100):
        job = client.get(f"/api/analysis-jobs/{job_id}").json()
        if job["status"] == "completed":
            return str(job["comparison_ids"][0])
        time.sleep(0.01)
    raise AssertionError("comparison did not complete")


def test_json_csv_and_pdf_exports(client: TestClient) -> None:
    comparison_id = create_persisted_comparison(client)
    request = {"comparison_ids": [comparison_id]}

    json_response = client.post("/api/export/json", json=request)
    assert json_response.status_code == 200
    assert json_response.json()[0]["candidate_display_name"] == "Alex Morgan"
    assert "api_key" not in json_response.text.lower()

    csv_response = client.post("/api/export/csv", json=request)
    assert csv_response.status_code == 200
    assert "candidate,job,fit_score" in csv_response.text
    assert "Alex Morgan" in csv_response.text

    pdf_response = client.post("/api/export/report", json=request)
    assert pdf_response.status_code == 200
    assert pdf_response.content.startswith(b"%PDF")
    reader = PdfReader(io.BytesIO(pdf_response.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Candidate evidence report" in text
    assert "Alex Morgan" in text
    assert "sole basis for employment decisions" in " ".join(text.split())


def test_interview_guide_supports_selected_and_custom_questions(
    client: TestClient,
) -> None:
    comparison_id = create_persisted_comparison(client)
    response = client.post(
        "/api/export/interview-guide",
        json={
            "comparison_id": comparison_id,
            "custom_questions": ["Describe the evaluation dataset and baseline."],
        },
    )
    assert response.status_code == 200
    reader = PdfReader(io.BytesIO(response.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Targeted interview questions" in text
    assert "evaluation dataset and baseline" in text
