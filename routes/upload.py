from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db, JobPosting, hash_text
from vector_store import store_job_posting

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={},
    )


@router.post("/upload", response_class=HTMLResponse)
async def upload_posting(
    request: Request,
    company_name: str = Form(...),
    role_title: str = Form(...),
    job_text: str = Form(...),
    db: Session = Depends(get_db),
):
    success = None
    error = None
    chunks_count = 0

    company_name = company_name.strip()
    role_title = role_title.strip()
    job_text = job_text.strip()

    # Preserve form values so user doesn't lose work on error
    form_data = {"company_name": company_name, "role_title": role_title, "job_text": job_text}

    try:
        if not company_name:
            error = "Company name is required."
        elif not role_title:
            error = "Role title is required."
        elif len(job_text) < 50:
            error = "Job posting text is too short. Please paste the full job description (minimum 50 characters)."
        else:
            # Duplicate detection: same company + role + identical text content
            incoming_hash = hash_text(job_text)
            candidates = db.query(JobPosting).filter(
                JobPosting.company_name == company_name,
                JobPosting.role_title == role_title,
            ).all()

            if any(hash_text(p.raw_text.strip()) == incoming_hash for p in candidates):
                error = "This posting already exists."
            else:
                posting = JobPosting(
                    company_name=company_name,
                    role_title=role_title,
                    raw_text=job_text,
                )
                db.add(posting)
                db.commit()
                db.refresh(posting)

                chunks_count = store_job_posting(
                    posting_id=posting.id,
                    company_name=posting.company_name,
                    role_title=posting.role_title,
                    text=posting.raw_text,
                )

                success = (
                    f"Successfully uploaded \"{posting.role_title}\" at \"{posting.company_name}\". "
                    f"Created {chunks_count} searchable chunks."
                )
                form_data = {}  # Clear form on success

    except Exception as exc:
        db.rollback()
        error = f"Upload failed: {exc}"

    return templates.TemplateResponse(
        request=request,
        name="upload.html",
        context={
            "success": success,
            "error": error,
            "chunks_count": chunks_count,
            **form_data,
        },
    )
