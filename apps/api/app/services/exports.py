import csv
import io
import json
from html import escape
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.comparison import ComparisonResponse, InterviewQuestion

BRAND = colors.HexColor("#087F78")
NAVY = colors.HexColor("#142B3A")
MUTED = colors.HexColor("#526572")
LINE = colors.HexColor("#DDE5E8")
CANVAS = colors.HexColor("#F5F8F8")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=23,
            leading=28,
            textColor=NAVY,
            spaceAfter=4 * mm,
        ),
        "heading": ParagraphStyle(
            "SectionHeading",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=NAVY,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=MUTED,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=MUTED,
        ),
        "score": ParagraphStyle(
            "Score",
            parent=base["Title"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=19,
            textColor=BRAND,
        ),
    }


def _paragraph(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(value)).replace("\n", "<br/>"), style)


def _rich(value: str, style: ParagraphStyle) -> Paragraph:
    """Render application-constructed markup whose dynamic values were already escaped."""
    return Paragraph(value, style)


def _footer(canvas, document) -> None:  # type: ignore[no-untyped-def]
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "TalentMatch AI - evidence-based decision support")
    canvas.drawRightString(192 * mm, 9 * mm, f"Page {document.page}")
    canvas.restoreState()


def report_pdf(result: ComparisonResponse) -> bytes:
    buffer = io.BytesIO()
    styles = _styles()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=f"TalentMatch report - {result.candidate_display_name}",
        author="TalentMatch AI",
    )
    story: list[Any] = [
        _paragraph("TalentMatch AI", styles["small"]),
        _paragraph("Candidate evidence report", styles["title"]),
        _paragraph(
            f"{result.candidate_display_name} compared with {result.job_title}", styles["body"]
        ),
        Spacer(1, 5 * mm),
    ]
    summary = Table(
        [
            [
                _rich(
                    f"{result.fit_score:.0f}<br/><font size='7'>FIT SCORE</font>",
                    styles["score"],
                ),
                _rich(
                    f"{result.evidence_confidence_score:.0f}<br/><font size='7'>EVIDENCE</font>",
                    styles["score"],
                ),
                _rich(
                    f"<b>{escape(result.mandatory_status.value.replace('_', ' ').title())}</b>"
                    "<br/><font size='7'>MANDATORY</font>",
                    styles["body"],
                ),
                _rich(
                    f"<b>{escape(result.recommendation.value.replace('_', ' ').title())}</b>"
                    "<br/><font size='7'>RECOMMENDATION</font>",
                    styles["body"],
                ),
            ]
        ],
        colWidths=[42 * mm, 42 * mm, 45 * mm, 45 * mm],
    )
    summary.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), CANVAS),
                ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (1, 0), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.extend([summary, _paragraph("Score breakdown", styles["heading"])])
    score_rows = [["Category", "Weight", "Score", "Evidence"]]
    for item in result.score_breakdown:
        score_rows.append(
            [
                item.category.value.replace("_", " ").title(),
                str(item.weight),
                f"{item.score:.0f}",
                str(item.evidence_count),
            ]
        )
    score_table = Table(score_rows, colWidths=[90 * mm, 25 * mm, 25 * mm, 30 * mm], repeatRows=1)
    score_table.setStyle(_table_style())
    story.extend([score_table, _paragraph("Requirement evidence", styles["heading"])])
    for match in result.requirement_matches:
        evidence = (
            "<br/>".join(
                f"&quot;{escape(item.text)}&quot; ({escape(item.source_reference)})"
                for item in match.evidence
            )
            or "No supporting statement found in the resume."
        )
        content = Table(
            [
                [
                    _paragraph(match.requirement.text, styles["body"]),
                    _paragraph(match.match_type.value.replace("_", " ").title(), styles["small"]),
                    _paragraph(f"{match.score:.0f}", styles["body"]),
                ],
                [
                    _paragraph(match.explanation, styles["small"]),
                    _rich(evidence, styles["small"]),
                    _paragraph(
                        "Clarify" if match.clarification_required else "Supported",
                        styles["small"],
                    ),
                ],
            ],
            colWidths=[78 * mm, 72 * mm, 20 * mm],
        )
        content.setStyle(_table_style(header_rows=0))
        story.extend([KeepTogether([content, Spacer(1, 2 * mm)])])

    if result.clarification_flags:
        story.append(_paragraph("Clarification points", styles["heading"]))
        for flag in result.clarification_flags:
            story.append(
                _rich(f"<b>{escape(flag.title)}</b> - {escape(flag.explanation)}", styles["body"])
            )
    story.append(PageBreak())
    story.append(_paragraph("Targeted interview questions", styles["title"]))
    for index, question in enumerate(result.interview_questions, start=1):
        story.append(
            _rich(
                f"<b>{index}. {escape(question.question)}</b><br/>{escape(question.rationale)}",
                styles["body"],
            )
        )
        story.append(Spacer(1, 3 * mm))
    story.extend(
        [
            _paragraph("Methodology and limitations", styles["heading"]),
            _paragraph(result.methodology_note, styles["body"]),
            Spacer(1, 2 * mm),
            _rich(f"<b>Important:</b> {escape(result.disclaimer)}", styles["body"]),
        ]
    )
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def _table_style(header_rows: int = 1) -> TableStyle:
    commands: list[tuple[Any, ...]] = [
        ("BOX", (0, 0), (-1, -1), 0.5, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]
    if header_rows:
        commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, header_rows - 1), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, header_rows - 1), colors.white),
                ("FONTNAME", (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
            ]
        )
    return TableStyle(commands)


def comparisons_json(results: list[ComparisonResponse]) -> bytes:
    return json.dumps(
        [item.model_dump(mode="json") for item in results], indent=2, ensure_ascii=True
    ).encode()


def comparisons_csv(results: list[ComparisonResponse]) -> bytes:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "candidate",
            "job",
            "fit_score",
            "evidence_confidence",
            "mandatory_status",
            "recommendation",
            "clarification_count",
        ]
    )
    for item in results:
        writer.writerow(
            [
                item.candidate_display_name,
                item.job_title,
                item.fit_score,
                item.evidence_confidence_score,
                item.mandatory_status.value,
                item.recommendation.value,
                len(item.clarification_flags),
            ]
        )
    return output.getvalue().encode()


def interview_guide_pdf(
    result: ComparisonResponse,
    selected_question_ids: set[str],
    custom_questions: list[str],
) -> bytes:
    questions: list[InterviewQuestion] = [
        item
        for item in result.interview_questions
        if not selected_question_ids or item.id in selected_question_ids
    ]
    copied = result.model_copy(
        update={
            "interview_questions": [
                *questions,
                *[
                    InterviewQuestion(
                        id=f"custom-{index}",
                        category="custom",
                        question=value,
                        rationale="Added by the recruiter.",
                    )
                    for index, value in enumerate(custom_questions, start=1)
                ],
            ]
        }
    )
    return report_pdf(copied)
