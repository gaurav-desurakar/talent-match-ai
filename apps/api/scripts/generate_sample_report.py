from pathlib import Path

from app.providers.mock import MockProvider
from app.schemas.comparison import ComparisonRequest
from app.services.exports import report_pdf
from app.workflows.comparison import ComparisonWorkflow

JOB = """Senior AI Product Engineer
Production experience with Python and FastAPI is required.
Experience with RAG and React is strongly preferred.
The role leads architecture and works with business stakeholders.
"""

RESUME = """Alex Morgan
Designed and deployed Python and FastAPI RAG services used by 12,000 employees.
Built React workflows for operations teams.
Led architecture workshops with legal and business stakeholders.
Reduced evaluation time by 42 percent across three product teams.
"""


def main() -> None:
    result = ComparisonWorkflow(MockProvider()).run(
        ComparisonRequest(job_description_text=JOB, resume_text=RESUME)
    )
    output = Path(__file__).parents[3] / "output" / "pdf" / "sample-candidate-report.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(report_pdf(result))
    print(output)


if __name__ == "__main__":
    main()
