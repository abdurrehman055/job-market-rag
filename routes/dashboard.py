import re
from typing import Dict

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db, JobPosting
from vector_store import delete_job_posting, get_total_chunks

router = APIRouter()
templates = Jinja2Templates(directory="templates")

_SKILLS = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "PHP", "Ruby", "Kotlin",
    "React", "Vue", "Angular", "Next.js", "Node.js", "Express",
    "Django", "FastAPI", "Flask", "Spring Boot", "Laravel",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "SQLite",
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Linux", "Nginx",
    "Git", "CI/CD", "Jenkins", "GitHub Actions", "REST API", "GraphQL",
    "Microservices", "Machine Learning", "Deep Learning", "TensorFlow",
    "PyTorch", "NLP", "Pandas", "NumPy", "Scikit-learn",
    "HTML", "CSS", "Bootstrap", "Tailwind", "Agile", "Scrum", "DevOps",
]


def _count_skills(text: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    text_lower = text.lower()
    for skill in _SKILLS:
        pattern = r"\b" + re.escape(skill.lower()) + r"\b"
        n = len(re.findall(pattern, text_lower))
        if n > 0:
            counts[skill] = n
    return counts


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    postings = db.query(JobPosting).order_by(JobPosting.created_at.desc()).all()
    total_postings = len(postings)
    total_chunks = get_total_chunks()
    avg_chunks = round(total_chunks / total_postings, 1) if total_postings > 0 else 0

    aggregate: Dict[str, int] = {}
    for posting in postings:
        for skill, count in _count_skills(posting.raw_text).items():
            aggregate[skill] = aggregate.get(skill, 0) + count

    top_skills = sorted(aggregate.items(), key=lambda x: x[1], reverse=True)[:5]
    top_skill_name = top_skills[0][0] if top_skills else None

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "postings": postings,
            "top_skills": top_skills,
            "top_skill_name": top_skill_name,
            "total_postings": total_postings,
            "total_chunks": total_chunks,
            "avg_chunks": avg_chunks,
        },
    )


@router.post("/dashboard/delete/{posting_id}", include_in_schema=False)
async def delete_posting(posting_id: int, db: Session = Depends(get_db)):
    posting = db.query(JobPosting).filter(JobPosting.id == posting_id).first()
    if posting:
        delete_job_posting(posting_id)
        db.delete(posting)
        db.commit()
    return RedirectResponse(url="/dashboard", status_code=303)
