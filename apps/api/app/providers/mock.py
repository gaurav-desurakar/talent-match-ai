import re
from collections.abc import Iterable
from dataclasses import dataclass

from app.providers.base import LLMProvider
from app.schemas.comparison import (
    MatchType,
    ProviderAnalysis,
    ProviderJobAnalysis,
    ProviderRequirementMatch,
    Requirement,
    RequirementClassification,
    ScoreCategory,
    SourceEvidence,
)
from app.schemas.document import DocumentSourceReference


@dataclass(frozen=True)
class TaxonomyEntry:
    canonical: str
    aliases: tuple[str, ...]
    category: ScoreCategory = ScoreCategory.CORE_TECHNICAL_SKILLS


TAXONOMY: tuple[TaxonomyEntry, ...] = (
    TaxonomyEntry("Python", ("python",)),
    TaxonomyEntry("FastAPI", ("fastapi",)),
    TaxonomyEntry("React", ("react", "react.js", "reactjs")),
    TaxonomyEntry("Next.js", ("next.js", "nextjs", "next js")),
    TaxonomyEntry("TypeScript", ("typescript",)),
    TaxonomyEntry("RAG", ("rag", "retrieval-augmented generation", "semantic retrieval")),
    TaxonomyEntry("LLM applications", ("llm", "large language model", "generative ai", "genai")),
    TaxonomyEntry("Agent orchestration", ("langgraph", "agent orchestration", "workflow agents")),
    TaxonomyEntry("PostgreSQL", ("postgresql", "postgres")),
    TaxonomyEntry("Docker", ("docker", "containers", "containerization")),
    TaxonomyEntry("Kubernetes", ("kubernetes", "k8s")),
    TaxonomyEntry("AWS", ("aws", "amazon web services")),
    TaxonomyEntry("Azure", ("azure", "azure openai")),
    TaxonomyEntry("Google Cloud", ("gcp", "google cloud")),
    TaxonomyEntry(
        "Leadership",
        (
            "leadership",
            "lead",
            "led",
            "led a team",
            "team lead",
            "managed a team",
            "technical architecture",
            "architecture workshops",
        ),
        ScoreCategory.SENIORITY_AND_OWNERSHIP,
    ),
    TaxonomyEntry(
        "Stakeholder management",
        ("stakeholder", "stakeholders", "customer-facing", "client-facing"),
        ScoreCategory.STAKEHOLDER_AND_CUSTOMER_EXPERIENCE,
    ),
)

MANDATORY_MARKERS = ("must", "required", "minimum", "essential", "need to have")
PREFERRED_MARKERS = ("preferred", "nice to have", "desirable", "bonus")
PRODUCTION_MARKERS = ("production", "deployed", "launched", "scaled", "operated")
OWNERSHIP_MARKERS = ("designed", "architected", "led", "owned", "governed")


def _lines(
    text: str,
    prefix: str,
    source_references: list[DocumentSourceReference] | None = None,
) -> list[tuple[int, str, str]]:
    output: list[tuple[int, str, str]] = []
    if source_references:
        number = 0
        for reference in source_references:
            for value in reference.text.splitlines():
                cleaned = re.sub(r"^[\s*•#>\-\d.)]+", "", value).strip()
                cleaned = re.sub(r"\s+", " ", cleaned)
                if cleaned:
                    number += 1
                    output.append((number, cleaned, reference.id))
        if output:
            return output
    for number, value in enumerate(text.splitlines(), start=1):
        cleaned = re.sub(r"^[\s*•#>\-\d.)]+", "", value).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if cleaned:
            output.append((number, cleaned, f"{prefix}-line-{number}"))
    return output


def _contains_alias(text: str, alias: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text, re.IGNORECASE) is not None


def _classification(line: str) -> RequirementClassification:
    lowered = line.lower()
    if any(marker in lowered for marker in MANDATORY_MARKERS):
        return RequirementClassification.MANDATORY
    if any(marker in lowered for marker in PREFERRED_MARKERS):
        return RequirementClassification.PREFERRED
    return RequirementClassification.STRONGLY_PREFERRED


def _category(line: str) -> ScoreCategory:
    lowered = line.lower()
    if any(word in lowered for word in ("year", "experience")):
        return ScoreCategory.RELEVANT_EXPERIENCE
    if any(word in lowered for word in ("lead", "own", "architect", "mentor")):
        return ScoreCategory.SENIORITY_AND_OWNERSHIP
    if any(word in lowered for word in ("customer", "client", "stakeholder")):
        return ScoreCategory.STAKEHOLDER_AND_CUSTOMER_EXPERIENCE
    if any(word in lowered for word in ("degree", "certification", "bachelor", "master")):
        return ScoreCategory.EDUCATION_AND_CERTIFICATIONS
    if any(word in lowered for word in ("deliver", "responsible", "collaborate", "build")):
        return ScoreCategory.RESPONSIBILITY_ALIGNMENT
    return ScoreCategory.PROJECT_SIMILARITY


def _importance(classification: RequirementClassification) -> float:
    return {
        RequirementClassification.MANDATORY: 1.0,
        RequirementClassification.STRONGLY_PREFERRED: 0.85,
        RequirementClassification.PREFERRED: 0.65,
        RequirementClassification.CONTEXTUAL: 0.4,
        RequirementClassification.INFORMATIONAL: 0.2,
    }[classification]


def _first_title(lines: list[tuple[int, str, str]], fallback: str) -> str:
    for _, line, _ in lines[:4]:
        if 3 <= len(line) <= 80 and not any(marker in line.lower() for marker in MANDATORY_MARKERS):
            return line
    return fallback


class MockProvider(LLMProvider):
    """Deterministic local provider used for tests and product demonstration."""

    id = "mock"
    model = "mock-evidence-v1"

    def validate_credentials(self) -> bool:
        return True

    def list_models(self) -> list[str]:
        return [self.model]

    def health_check(self) -> str:
        return "available"

    def generate_analysis(
        self,
        job_description_text: str,
        resume_text: str,
        *,
        blind_review: bool,
        job_source_references: list[DocumentSourceReference] | None = None,
        resume_source_references: list[DocumentSourceReference] | None = None,
        approved_requirements: list[Requirement] | None = None,
    ) -> ProviderAnalysis:
        job_lines = _lines(job_description_text, "job", job_source_references)
        resume_lines = _lines(resume_text, "resume", resume_source_references)
        requirements = approved_requirements or self._extract_requirements(job_lines)
        matches = [self._match(requirement, resume_lines) for requirement in requirements]
        candidate_name = "Candidate" if blind_review else _first_title(resume_lines, "Candidate")
        return ProviderAnalysis(
            job_title=_first_title(job_lines, "Untitled role"),
            candidate_display_name=candidate_name,
            matches=matches,
            warnings=["Mock analysis uses deterministic heuristics and is for demonstration only."],
        )

    def generate_job_analysis(
        self,
        job_description_text: str,
        *,
        job_source_references: list[DocumentSourceReference] | None = None,
    ) -> ProviderJobAnalysis:
        job_lines = _lines(job_description_text, "job", job_source_references)
        return ProviderJobAnalysis(
            job_title=_first_title(job_lines, "Untitled role"),
            requirements=self._extract_requirements(job_lines),
            warnings=[
                "Mock extraction uses deterministic heuristics and is for demonstration only."
            ],
        )

    def _extract_requirements(self, lines: list[tuple[int, str, str]]) -> list[Requirement]:
        requirements: list[Requirement] = []
        seen: set[str] = set()
        for entry in TAXONOMY:
            for _, line, source_reference in lines:
                if entry.canonical.lower() in seen:
                    break
                if any(_contains_alias(line, alias) for alias in entry.aliases):
                    classification = _classification(line)
                    requirements.append(
                        Requirement(
                            id=f"req-{len(requirements) + 1}",
                            text=line,
                            canonical_concept=entry.canonical,
                            classification=classification,
                            category=entry.category,
                            importance=_importance(classification),
                            source_reference=source_reference,
                        )
                    )
                    seen.add(entry.canonical.lower())

        if not requirements:
            candidates = [
                (line, source_reference)
                for _, line, source_reference in lines
                if len(line.split()) >= 4 and len(line) <= 280
            ]
            for line, source_reference in candidates[:8]:
                classification = _classification(line)
                requirements.append(
                    Requirement(
                        id=f"req-{len(requirements) + 1}",
                        text=line,
                        classification=classification,
                        category=_category(line),
                        importance=_importance(classification),
                        source_reference=source_reference,
                    )
                )

        if not requirements:
            raise ValueError("No meaningful job requirements could be extracted")
        return requirements[:25]

    def _match(
        self, requirement: Requirement, resume_lines: list[tuple[int, str, str]]
    ) -> ProviderRequirementMatch:
        entry = next(
            (item for item in TAXONOMY if item.canonical == requirement.canonical_concept), None
        )
        aliases: Iterable[str]
        if entry:
            aliases = entry.aliases
        else:
            aliases = tuple(word for word in requirement.text.lower().split() if len(word) > 5)

        evidence: list[SourceEvidence] = []
        matched_alias: str | None = None
        for _, line, source_reference in resume_lines:
            alias = next((item for item in aliases if _contains_alias(line, item)), None)
            if alias:
                evidence.append(SourceEvidence(text=line, source_reference=source_reference))
                matched_alias = matched_alias or alias
            if len(evidence) == 3:
                break

        if not evidence:
            return ProviderRequirementMatch(
                requirement=requirement,
                match_type=MatchType.NO_EVIDENCE,
                match_strength=0.0,
                evidence_strength=0.0,
                evidence=[],
                explanation=(
                    "No supporting statement was found in the resume; this is an evidence "
                    "gap, not proof of absence."
                ),
                uncertainties=["The resume may omit relevant experience."],
            )

        combined = " ".join(item.text.lower() for item in evidence)
        canonical_is_present = bool(
            requirement.canonical_concept
            and _contains_alias(combined, requirement.canonical_concept.lower())
        )
        match_type = MatchType.EXACT if canonical_is_present else MatchType.EQUIVALENT
        match_strength = 1.0 if match_type is MatchType.EXACT else 0.9
        evidence_strength = 0.65
        if any(marker in combined for marker in PRODUCTION_MARKERS):
            evidence_strength += 0.15
        if any(marker in combined for marker in OWNERSHIP_MARKERS):
            evidence_strength += 0.15
        if re.search(r"\b\d+(?:\.\d+)?%?\b", combined):
            evidence_strength += 0.05
        evidence_strength = min(evidence_strength, 1.0)
        concept = requirement.canonical_concept or matched_alias or "the requirement"
        return ProviderRequirementMatch(
            requirement=requirement,
            match_type=match_type,
            match_strength=match_strength,
            evidence_strength=evidence_strength,
            evidence=evidence,
            explanation=f"The resume contains direct or equivalent evidence for {concept}.",
            uncertainties=(
                []
                if evidence_strength >= 0.8
                else ["Depth and production scope should be validated."]
            ),
        )
