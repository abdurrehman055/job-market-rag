from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from vector_store import search_similar_chunks, get_total_chunks, deduplicate_by_posting
from llm_service import ask_gpt

router = APIRouter()
templates = Jinja2Templates(directory="templates")

_SYSTEM_PROMPT = """\
You are an expert career advisor specializing in the Pakistani tech job market.
Analyze the candidate's CV against the provided job posting excerpts.

SCORING GUIDE:
- 80-100: Candidate meets all or nearly all requirements
- 60-79: Strong candidate with minor gaps
- 40-59: Moderate match, notable learning needed
- 20-39: Significant skill gaps
- 0-19: Poor alignment

MISSING_SKILLS RULES (strictly follow):
- Only list technical skills REQUIRED by the job postings that are COMPLETELY ABSENT from the candidate's CV.
- Do NOT list skills the candidate already has, even if phrased differently in the CV.
- Do NOT list generic soft skills (communication, teamwork) unless the posting explicitly demands them as hard requirements.
- List at most 8 skills, ranked by importance to the role.
- Write "None" if the candidate already covers all required skills.

Your response MUST follow this EXACT format with no extra lines or deviations:

MATCH_SCORE: [integer 0-100]
BEST_MATCH: [Company Name — Role Title]
MISSING_SKILLS: [comma-separated skills, or "None"]
RECOMMENDATION: [2-3 sentence actionable advice tailored to the Pakistani tech market]
ANALYSIS: [3-4 sentence paragraph covering strengths, gaps, and overall fit]\
"""


def _parse_response(raw: str) -> dict:
    result = {
        "match_score": 0,
        "best_match": "N/A",
        "missing_skills": [],
        "recommendation": "",
        "analysis": raw.strip(),
    }
    for line in raw.strip().splitlines():
        if line.startswith("MATCH_SCORE:"):
            try:
                result["match_score"] = int(
                    line.split(":", 1)[1].strip().strip("[]")
                )
            except ValueError:
                pass
        elif line.startswith("BEST_MATCH:"):
            result["best_match"] = line.split(":", 1)[1].strip().strip("[]")
        elif line.startswith("MISSING_SKILLS:"):
            raw_skills = line.split(":", 1)[1].strip().strip("[]")
            if raw_skills.lower() != "none":
                result["missing_skills"] = [
                    s.strip() for s in raw_skills.split(",") if s.strip()
                ]
        elif line.startswith("RECOMMENDATION:"):
            result["recommendation"] = line.split(":", 1)[1].strip().strip("[]")
        elif line.startswith("ANALYSIS:"):
            result["analysis"] = line.split(":", 1)[1].strip().strip("[]")
    return result


@router.get("/cv-match", response_class=HTMLResponse)
async def cv_match_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="cv_match.html",
        context={"has_postings": get_total_chunks() > 0},
    )


@router.post("/cv-match", response_class=HTMLResponse)
async def cv_match_analyze(
    request: Request,
    cv_text: str = Form(...),
    db: Session = Depends(get_db),
):
    result = None
    sources = []
    error = None
    insight_note = None

    try:
        if len(cv_text.strip()) < 100:
            error = "CV text is too short. Please paste your full CV or resume (minimum 100 characters)."
        else:
            raw_chunks = search_similar_chunks(cv_text, n_results=6)
            unique_chunks = deduplicate_by_posting(raw_chunks)

            if not unique_chunks:
                error = "No job postings found. Please upload some postings first."
            else:
                n = len(unique_chunks)
                insight_note = (
                    "Matched against a single posting."
                    if n == 1
                    else f"Matched against {n} unique postings."
                )

                context_parts = [
                    f"[Job {i}: {c['metadata']['company_name']} — {c['metadata']['role_title']}]\n{c['document']}"
                    for i, c in enumerate(unique_chunks, 1)
                ]
                context = "\n\n---\n\n".join(context_parts)

                user_message = (
                    f"Job Postings Context:\n\n{context}\n\n"
                    f"Candidate CV:\n{cv_text[:3000]}\n\n"
                    "Analyze this CV against the job postings and provide structured feedback."
                )

                raw_response = ask_gpt(_SYSTEM_PROMPT, user_message, max_tokens=1800)
                result = _parse_response(raw_response)
                sources = unique_chunks

    except Exception as exc:
        error = f"Analysis failed: {exc}"

    return templates.TemplateResponse(
        request=request,
        name="cv_match.html",
        context={
            "result": result,
            "sources": sources,
            "error": error,
            "has_postings": True,
            "cv_text": cv_text,
            "insight_note": insight_note,
        },
    )
